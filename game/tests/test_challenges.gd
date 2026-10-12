extends SceneTree
const Data=preload("res://scripts/data_store.gd")
const Simulation=preload("res://scripts/battle_sim.gd")
func _initialize():call_deferred("run")
func run():
	var db=Data.new();var results: Array = []
	for config in db.read_json("res://data/campaign.json").challenges:
		var sim=Simulation.new(db);sim.start(config);sim.ai_enabled=[true,true]
		for i in range(60*540):
			sim.tick(1.0/60.0);sim.drain_events()
			if sim.winner!=-2:break
		results.append({"id":config.id,"winner":sim.winner,"time":sim.time,"reason":sim.result_reason,"stats":sim.stats[0]})
	var unresolved: Array = results.filter(func(r):return r.winner==-2)
	var report: Dictionary = {"passed":unresolved.is_empty(),"results":results,"scope":"six preserved tactical challenges under their authored budgets; both sides use public simulation rules; not human challenge-star completion"}
	report["engine"]=Engine.get_version_info();report["inputs"]={}
	for path in ["res://data/balance-prototype.json","res://data/maps.json","res://data/campaign.json","res://scripts/battle_sim.gd","res://scripts/tactical_ai.gd"]:report.inputs[path]=FileAccess.get_sha256(path)
	var args=OS.get_cmdline_user_args();var destination: String=args[args.find("--output")+1] if args.has("--output") else "res://tests/challenges-report.json"
	var file=FileAccess.open(destination,FileAccess.WRITE);file.store_string(JSON.stringify(report,"\t"));file.close()
	print("CHALLENGES "+JSON.stringify(report));quit(0 if report.passed else 1)
