extends SceneTree
const Data=preload("res://scripts/data_store.gd")
const Simulation=preload("res://scripts/battle_sim.gd")
const AI=preload("res://scripts/tactical_ai.gd")
func _initialize():call_deferred("run")
func run():
	var db=Data.new();var records: Array=[];var exposure_cases: Array=[];var checked: int=0;var shared: int=0;var absent: int=0;var fork_maps: Dictionary={}
	for map_id in db.maps:
		for side in [0,1]:
			var s=Simulation.new(db);s.start({"map":map_id,"faction":"mu","enemy":"mo"});s.ai_enabled=[false,false];s.units.clear();s.buildings.clear();s.time=20
			for site in s.map.definition.build_sites:
				if int(site.owner)==side or not site.get("types",["tower","mana"]).has("tower"):continue
				var anchor: Dictionary=s.map.anchor(site.edge,float(site.s))
				for fork in s.map.fork_nodes(side):
					checked+=1;fork_maps[map_id]=true
					var coverage: Dictionary={};var exposure: Dictionary={};var covered: int=0
					for edge in fork.options:
						coverage[edge]=AI.structure_covers_road(s,"building.mo.tower" if side==0 else "building.mu.tower",Vector2(anchor.x,anchor.y),edge)
						var length: float=s.map.edges[edge].length;var slices: int=int(ceil(length/.1));var exposed: float=0
						for sample in range(slices):
							if s.map.point(edge,(sample+.5)*length/slices).distance_to(Vector2(anchor.x,anchor.y))<=4.3:exposed+=length/slices
						exposure[edge]={"road_length":length,"sampled_fire_length":exposed}
						if coverage[edge]:covered+=1
					exposure_cases.append({"map":map_id,"side":side,"site":site.get("id",""),"exposure":exposure})
					if covered==0:absent+=1
					if covered==fork.options.size():shared+=1
					s.visibility.last_seen[side].clear();s.time=20
					AI.choose_routes(s,side,[],[],"counter")
					var baseline: String=s.map.choices[side][fork.node]
					var memory={"id":"building.mo.tower" if side==0 else "building.mu.tower","x":anchor.x,"y":anchor.y,"seen_at":20.0}
					s.visibility.last_seen[side][999]=memory
					AI.choose_routes(s,side,[],[],"counter")
					var fresh: String=s.map.choices[side][fork.node]
					s.buildings=[{"uid":999,"building":true,"id":memory.id,"side":1-side,"hp":360.0,"x":anchor.x,"y":anchor.y,"edge":site.edge,"s":site.s,"state":"active","disabled":0}]
					s.config["fog"]=false
					s.visibility.visible_uids[side][999]=true
					AI.choose_routes(s,side,[],[],"counter")
					var visible: String=s.map.choices[side][fork.node]
					s.buildings.clear();s.visibility.visible_uids[side].erase(999)
					s.config["fog"]=true
					s.time=50;AI.choose_routes(s,side,[],[],"counter")
					records.append({"map":map_id,"side":side,"site":site.id,"node":fork.node,"coverage":coverage,"baseline":baseline,"fresh_memory":fresh,"visible_tower":visible,"expired_memory":s.map.choices[side][fork.node],"exact_fire_lengths":fork.options.map(func(edge):return {"edge":edge,"length":AI.structure_fire_length(s,memory.id,Vector2(anchor.x,anchor.y),edge)})})
	var report={"scope":"All authored enemy tower sites near forks, controlled historical sightings; no actual building purchase/placement, battle or rendering. Route-policy observation only.","inputs":{},"records":records,"summary":{"maps_scanned":db.maps.size(),"fork_maps_with_enemy_tower_sites":fork_maps.size(),"site_fork_side_pairs":checked,"all_branches_covered":shared,"no_branch_covered":absent,"unequal_coverage":checked-shared-absent}}
	report["exposure_cases"]=exposure_cases
	for path in ["res://scripts/tactical_ai.gd","res://scripts/battle_sim.gd","res://scripts/map_runtime.gd","res://data/maps.json","res://tests/probe_route_tower_choices.gd"]:report.inputs[path]=FileAccess.get_sha256(path)
	var file=FileAccess.open(OS.get_cmdline_user_args()[0],FileAccess.WRITE);file.store_string(JSON.stringify(report,"  "));file.close();print("ROUTE_TOWER_CHOICES ",records.size());quit()
