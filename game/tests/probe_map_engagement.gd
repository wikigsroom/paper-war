extends SceneTree
const Data=preload("res://scripts/data_store.gd")
const Sim=preload("res://scripts/battle_sim.gd")
var db
func _initialize():call_deferred("run")
func pair(map_id: String,id: String,delay: float=0) -> Dictionary:
	var s=Sim.new(db)
	s.start({"map":map_id,"faction":"yin","enemy":"yin","full_tech":true})
	s.units.clear();s.ai_enabled=[false,false];s.events.clear()
	var west: Dictionary=s.map.at_node(s.map.definition.bases[0].node,0)
	var east: Dictionary=s.map.at_node(s.map.definition.bases[1].node,1)
	var a: Dictionary={};var b: Dictionary={}
	if delay<=0:
		a=s.spawn(id,0,west.x);s.map.apply_anchor(a,west)
		b=s.spawn(id,1,east.x);s.map.apply_anchor(b,east)
	var contact: Dictionary={}
	for tick in range(60*180):
		if a.is_empty() and s.time>=delay:
			a=s.spawn(id,0,west.x);s.map.apply_anchor(a,west)
			b=s.spawn(id,1,east.x);s.map.apply_anchor(b,east)
		s.tick(1.0/60)
		for e in s.drain_events():
			if e.kind=="attack" and not a.is_empty() and ((e.uid==a.uid and e.target_uid==b.uid) or (e.uid==b.uid and e.target_uid==a.uid)):
				contact={"first_release_seconds":s.time,"x0":a.x,"x1":b.x,"walk0":a.walk,"walk1":b.walk,"separation":s.melee_distance(a,b),"edge0":a.edge,"edge1":b.edge}
				break
		if not contact.is_empty():break
	return contact
func run():
	db=Data.new()
	var rows: Array=[]
	for map_def in db.maps.values():
		var s=Sim.new(db);s.start({"map":map_def.id,"faction":"yin","enemy":"yin"})
		var start: Dictionary=s.map.at_node(map_def.bases[0].node,0)
		var end: Dictionary=s.map.at_node(map_def.bases[1].node,1)
		var path: Dictionary=s.map.shortest_nodes(map_def.bases[0].node,map_def.bases[1].node)
		var mines: Array=[]
		for mine in map_def.mines:
			var side: int=int(mine.owner)
			mines.append({"id":mine.id,"side":side,"base_distance":s.map.route_to(s.bases[side],mine).distance,"capacity":mine.capacity,"service_seconds":mine.mine_seconds})
		rows.append({"id":map_def.id,"name":map_def.name,"canvas_length":map_def.length,"base_horizontal":absf(end.x-start.x),"shortest_road":path.distance,"configured_route_lengths":map_def.get("route_lengths",{}),"mines":mines,"baseline_axe":pair(map_def.id,"unit.yin.axe")})
	var representatives: Array=[]
	for map_def in db.maps.values():
		if not str(map_def.get("design_card",{}).get("id","")).begins_with("W"):continue
		var row: Dictionary={"id":map_def.id,"archetype":map_def.design_card.id,"pairs":{}}
		for id in ["unit.yin.axe","unit.yin.spear","unit.yin.cannon"]:row.pairs[id]=pair(map_def.id,id,2)
		representatives.append(row)
	var inputs: Dictionary={}
	for path in ["res://data/maps.json","res://data/balance-prototype.json","res://scripts/battle_sim.gd","res://scripts/map_runtime.gd","res://tests/probe_map_engagement.gd"]:inputs[path]=FileAccess.get_sha256(path)
	var args=OS.get_cmdline_user_args()
	FileAccess.open(args[args.find("--report")+1],FileAccess.WRITE).store_string(JSON.stringify({"maps":rows,"representatives":representatives,"inputs":inputs,"scope":"Native Godot 60 Hz, controlled mirrored units, no AI/workers, default route selection, first weapon release. Not a paid ordinary match, original game measurement or first damage timing. Selected pairs delayed by 2 seconds model one empty default production queue."},"\t"))
	print("MAP_ENGAGEMENT maps ",rows.size()," representatives ",representatives.size());quit()
