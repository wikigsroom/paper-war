extends SceneTree
const Data=preload("res://scripts/data_store.gd")
const Simulation=preload("res://scripts/battle_sim.gd")
func _initialize():call_deferred("run")
func run():
	var db=Data.new();var records: Array=[]
	for map_id in ["map.01.01","map.01.04","map.01.11"]:
		for pair in [["yin","mu"],["mu","yin"],["yin","bai"],["bai","yin"]]:
			var s=Simulation.new(db)
			s.start({"map":map_id,"faction":pair[0],"enemy":pair[1],"starting_gold":300,"enemy_starting_gold":300,"ai_warmup":0,"full_tech":false,"seed":271})
			s.ai_enabled=[true,true]
			var current: Array=[{},{}];var contacts: Array=[];var last_actor: Dictionary={};var first_hits: Dictionary={}
			for step in range(60*60):
				for u in s.units:last_actor[u.uid]=u
				for side in [0,1]:
					var visible: Dictionary={}
					for u in s.visibility.enemies[side]:
						if u.get("building",false) or u.hp<=0 or int(u.side)==side:continue
						visible[u.uid]=true
						if not current[side].has(u.uid):current[side][u.uid]={"seen_at":s.time,"id":u.id,"anchor":s.physical_anchor(u).duplicate(true),"released":false,"worker_released":false}
					for uid in current[side].keys():
						if not visible.has(uid):current[side].erase(uid)
				s.tick(1.0/60.0)
				for e in s.drain_events():
					if e.kind=="attack" and int(e.uid)>0:
						var side: int=1-int(e.side);var sight: Dictionary=current[side].get(e.uid,{})
						var target: Dictionary=last_actor.get(int(e.target_uid),{})
						var worker: bool=not target.is_empty() and db.balance.units[target.id].get("economy",false)
						if not sight.is_empty() and sight.released and (not worker or sight.worker_released):continue
						var kind: String="first_worker_release" if worker else "first_release"
						var row={"observer_side":side,"uid":e.uid,"id":e.id,"kind":kind,"release_at":s.time,"target_uid":e.target_uid,"release_x":e.x,"target_x":e.target_x,"seen_at":null,"warning_seconds":null,"seen_anchor":null}
						row["source_visible_after_release"]=s.visible_to(side,s.actor(int(e.uid)))
						if not sight.is_empty():
							row.seen_at=sight.seen_at;row.warning_seconds=s.time-float(sight.seen_at);row.seen_anchor=sight.anchor
							sight.released=true
							if worker:sight.worker_released=true
						contacts.append(row)
					if e.kind=="hit" and int(e.get("source_uid",0))>0:
						var key: String=str(e.side)+"/"+str(e.source_uid)
						if not first_hits.has(key):first_hits[key]=s.time
				if s.winner!=-2:break
			for row in contacts:
				var key: String=str(row.observer_side)+"/"+str(row.uid)
				row["source_first_hit_at"]=first_hits.get(key,null)
			records.append({"map":map_id,"shortest_road":s.map.shortest_nodes(s.map.definition.bases[0].node,s.map.definition.bases[1].node).distance,"canvas_length":s.map.definition.length,"west":pair[0],"east":pair[1],"duration":s.time,"contacts":contacts,"base_hp":[s.bases[0].hp,s.bases[1].hp],"workers":[s.population(0,true),s.population(1,true)]})
	var report={"scope":"Native 60Hz paid AI observations, first 60 seconds, seed271, formal fog. Sightings sampled from legal visible enemies before each tick; sight loss starts a new episode. Release is not impact; source_first_hit_at is the actor's first damage over the observation, not per-episode impact. No original-game equivalence, new-unit-arrival or human reaction-time claim.","records":records,"inputs":{}}
	for path in ["res://scripts/battle_sim.gd","res://scripts/tactical_ai.gd","res://scripts/battle_visibility.gd","res://scripts/map_runtime.gd","res://scripts/unit_abilities.gd","res://data/balance-prototype.json","res://data/maps.json","res://data/technology.json","res://tests/probe_warning_windows.gd"]:report.inputs[path]=FileAccess.get_sha256(path)
	var file=FileAccess.open(OS.get_cmdline_user_args()[0],FileAccess.WRITE)
	if file==null:push_error("Cannot write warning windows");quit(1);return
	file.store_string(JSON.stringify(report,"  "));print("WARNING_WINDOWS ",records.size());quit()
