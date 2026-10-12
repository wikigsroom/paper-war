extends SceneTree
const Data=preload("res://scripts/data_store.gd")
const Simulation=preload("res://tests/white_spell_trace_sim.gd")
func _initialize():call_deferred("run")
func run():
	var db=Data.new();var args=OS.get_cmdline_user_args()
	if args.has("--unit-overrides"):push_error("The rooted-unit trial was retired; it is not a shipping mechanic. Use --price-overrides only for explicit price pilots.");quit(1);return
	var start: int=int(args[args.find("--start")+1]) if args.has("--start") else 0
	var count: int=int(args[args.find("--count")+1]) if args.has("--count") else 100
	var output: String=args[args.find("--output")+1]
	var map_id: String=args[args.find("--map")+1] if args.has("--map") else "map.01.04"
	var seed_value: int=int(args[args.find("--seed")+1]) if args.has("--seed") else 137
	var sample_seconds: int=maxi(1,int(args[args.find("--sample-seconds")+1])) if args.has("--sample-seconds") else 15
	var removed_edges: Array=[]
	if args.has("--remove-edge"):
		var edge_id: String=args[args.find("--remove-edge")+1]
		var control: Dictionary=db.map_definition(map_id).duplicate(true)
		for anchor in control.mines+control.build_sites+[control.objective_anchor]:
			if anchor.edge==edge_id:push_error("Cannot remove an edge with authored objects");quit(1);return
		var original_count: int=control.edges.size()
		control.edges=control.edges.filter(func(edge):return edge.id!=edge_id)
		if control.edges.size()==original_count:push_error("Requested experimental edge does not exist");quit(1);return
		control.erase("route_lengths");control.erase("geometry_sha256")
		db.maps[control.id]=control;removed_edges.append(edge_id)
	var price_overrides: Dictionary={}
	if args.has("--price-overrides"):
		var override_path: String=args[args.find("--price-overrides")+1]
		price_overrides=JSON.parse_string(FileAccess.get_file_as_string(override_path))
		for id in price_overrides:
			if not db.balance.units.has(id) or float(price_overrides[id])<=0:
				push_error("Invalid experimental price override: "+str(id));quit(1);return
			db.balance.units[id].gold=float(price_overrides[id])
	var report={"scope":"Paid AI-vs-AI baseline, 150s observation ceiling, normal research and formal fog. Includes mirrored side assignments; not human skill balance or all-map evidence.","map":map_id,"seed":seed_value,"inputs":{},"records":[]}
	report["experimental_price_overrides"]=price_overrides
	report["sample_seconds"]=sample_seconds
	report["experimental_map_removed_edges"]=removed_edges
	if not removed_edges.is_empty():
		report["experimental_map_sha256"]=JSON.stringify(db.map_definition(map_id)).sha256_text()
		report.scope="Experimental branch removal on the same map; actual road geometry is recorded by experimental_map_sha256. NOT a shipping map. Paid AI-vs-AI with normal research/fog, 150s observation ceiling."
	if not price_overrides.is_empty():report.scope="Experimental paid price pilot: runtime unit costs explicitly overridden below; NOT shipped balance or human acceptance. 150s observation ceiling, normal research and formal fog."
	for path in ["res://scripts/battle_sim.gd","res://scripts/battle_visibility.gd","res://scripts/unit_abilities.gd","res://scripts/tactical_ai.gd","res://scripts/map_runtime.gd","res://tests/probe_white_spell_trace.gd","res://tests/white_spell_trace_sim.gd","res://data/balance-prototype.json","res://data/maps.json","res://data/technology.json"]:
		if FileAccess.file_exists(path):report.inputs[path]=FileAccess.get_sha256(path)
	for index in range(start,mini(100,start+count)):
		if args.has("--indices") and not args[args.find("--indices")+1].split(",").has(str(index)):continue
		if args.has("--mirrors") and index/10!=index%10:continue
		var west: String=db.FACTIONS[index/10];var east: String=db.FACTIONS[index%10]
		var battle=Simulation.new(db)
		battle.start({"map":map_id,"faction":west,"enemy":east,"starting_gold":300,"enemy_starting_gold":300,"ai_warmup":0,"full_tech":false,"seed":seed_value})
		battle.ai_enabled=[true,true]
		var timeline: Array=[]
		for step in range(150*60):
			battle.tick(1.0/60.0);battle.drain_events()
			if args.has("--timeline") and step%(sample_seconds*60)==sample_seconds*60-1:
				var sample={"time":battle.time,"sides":[]}
				for side in range(2):
					var army: Dictionary={};var worker_hp: float=0;var known_enemies: Array=[]
					for unit in battle.units:
						if unit.side!=side and unit.hp>0 and battle.visible_to(side,unit):known_enemies.append({"uid":unit.uid,"id":unit.id,"x":unit.x,"y":unit.y,"edge":unit.edge,"s":unit.s})
						if unit.side!=side or unit.hp<=0:continue
						if db.balance.units[unit.id].get("economy",false):worker_hp+=unit.hp
						else:
							if not army.has(unit.id):army[unit.id]={"count":0,"hp":0.0,"x":[],"actors":[]}
							army[unit.id].count+=1;army[unit.id].hp+=unit.hp;army[unit.id].x.append(unit.x)
							army[unit.id].actors.append({"uid":unit.uid,"x":unit.x,"y":unit.y,"edge":unit.edge,"s":unit.s,"hp":unit.hp,"target":unit.target,"windup":unit.windup})
					var player: Dictionary=battle.players[side]
					sample.sides.append({"army":army,"worker_hp":worker_hp,"workers":battle.population(side,true),"gold":player.gold,"mana":player.mana,"base_hp":battle.bases[side].hp,"route_choices":battle.map.choices[side].duplicate(true),"known_enemies":known_enemies,"studied":player.studied.duplicate(),"research":player.research.duplicate(true),"saving":player.ai_research,"queue":player.queue.duplicate(),"stats":battle.stats[side].duplicate(true)})
				timeline.append(sample)
			if battle.winner!=-2:break
		var sides: Array=[]
		for side in range(2):
			var player: Dictionary=battle.players[side]
			sides.append({"base_hp":battle.bases[side].hp,"gold":player.gold,"mana":player.mana,"workers":battle.population(side,true,true),"combat":battle.population(side,false,true),"studied":player.studied.duplicate(),"queue":player.queue.duplicate(),"stats":battle.stats[side].duplicate(true)})
		var row={"index":index,"west":west,"east":east,"winner":battle.winner,"time":battle.time,"sides":sides}
		if args.has("--timeline"):row["timeline"]=timeline
		row["white_spell_trace"]=battle.spell_trace
		row["white_blocked_trace"]=battle.blocked_trace
		report.records.append(row)
		var file=FileAccess.open(output,FileAccess.WRITE);file.store_string(JSON.stringify(report,"  "));file.close()
		print("FACTION_MATCHUP ",index," ",west,"/",east," winner=",battle.winner," time=",battle.time)
	quit()
