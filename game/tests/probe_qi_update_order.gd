extends SceneTree
const Data=preload("res://scripts/data_store.gd")
const Simulation=preload("res://scripts/battle_sim.gd")
func _initialize():call_deferred("run")
func run():
	var db=Data.new();var records: Array=[]
	for order in ["native","west_first","east_first"]:
		var s=Simulation.new(db);s.start({"map":"map.01.04","faction":"qi","enemy":"qi","starting_gold":300,"enemy_starting_gold":300,"ai_warmup":0,"seed":137});s.ai_enabled=[true,true]
		var opening: Array=[]
		for step in range(150*60):
			if order!="native":
				var first: int=0 if order=="west_first" else 1
				s.units.sort_custom(func(a,b):return int(a.uid)<int(b.uid) if a.side==b.side else int(a.side)==first)
			s.tick(1.0/60.0);s.drain_events()
			if step%300==299 and s.time<=40:
				opening.append({"time":s.time,"gold_delivered":[s.stats[0].gold_delivered,s.stats[1].gold_delivered],"army":[s.population(0,false),s.population(1,false)]})
			if s.winner!=-2:break
		records.append({"order":order,"winner":s.winner,"time":s.time,"opening":opening,"sides":[{"base_hp":s.bases[0].hp,"workers":s.population(0,true),"stats":s.stats[0]},{"base_hp":s.bases[1].hp,"workers":s.population(1,true),"stats":s.stats[1]}]})
	var report={"scope":"Normal paid qi mirror; experimental ordering of units array before each native tick, also affecting same-side traversal/target ties. No shipped simulation change; not isolated simultaneous-hit causality or human balance.","inputs":{},"records":records}
	for path in ["res://scripts/battle_sim.gd","res://scripts/unit_abilities.gd","res://scripts/tactical_ai.gd","res://data/maps.json","res://data/balance-prototype.json","res://tests/probe_qi_update_order.gd"]:report.inputs[path]=FileAccess.get_sha256(path)
	var file=FileAccess.open(OS.get_cmdline_user_args()[0],FileAccess.WRITE);file.store_string(JSON.stringify(report,"  "));file.close();print("QI_UPDATE_ORDER ",records.size());quit()
