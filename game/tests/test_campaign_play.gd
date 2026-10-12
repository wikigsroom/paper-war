extends SceneTree
const Data=preload("res://scripts/data_store.gd")
const Simulation=preload("res://scripts/battle_sim.gd")
var db
func _initialize():call_deferred("run")
func run():
	db=Data.new()
	var args=OS.get_cmdline_user_args();var start: int = 0;var end: int = 200;var step: float = 1.0/60.0
	if args.has("--range"):
		var i: int = args.find("--range");start=int(args[i+1]);end=int(args[i+2])
	if args.has("--coarse"):step=1.0/10.0
	var selected: Array = []
	if args.has("--only-failures"):
		var source: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(args[args.find("--only-failures")+1]))
		for row in source.results:
			if int(row.winner)!=0:selected.append(int(row.index))
	var results: Array = []
	var stamp: int = Time.get_ticks_msec()
	for index in range(start,end):
		if args.has("--only-failures") and not selected.has(index):continue
		var config: Dictionary = db.campaign[index].duplicate(true)
		if args.has("--player-style"):config["player_ai_style"]=args[args.find("--player-style")+1]
		var sim=Simulation.new(db);sim.start(config);sim.ai_enabled=[true,true]
		var error: String = ""
		var limit: float = 540
		if args.has("--limit"):limit=maxf(1,float(args[args.find("--limit")+1]))
		for tick in range(int(limit/step)):
			sim.tick(step);sim.drain_events()
			if sim.winner!=-2:break
		var result: Dictionary = {"index":index,"id":config.id,"map":config.map,"win_type":config.win,"winner":sim.winner,"time":snappedf(sim.time,.01),"reason":sim.result_reason,"player":sim.stats[0],"enemy":sim.stats[1],"base_hp":[sim.bases[0].hp,sim.bases[1].hp],"queue_sizes":[sim.players[0].queue.size(),sim.players[1].queue.size()],"gold":[sim.players[0].gold,sim.players[1].gold]}
		results.append(result)
		print("CAMPAIGN %03d winner %d at %.1fs : %s"%[index+1,sim.winner,sim.time,sim.result_reason])
	var victories: int = results.filter(func(r):return r.winner==0).size()
	var unresolved: Array = results.filter(func(r):return r.winner==-2)
	var report: Dictionary = {"range":[start,end],"step":step,"limit":float(args[args.find("--limit")+1]) if args.has("--limit") else 540.0,"player_style_override":str(args[args.find("--player-style")+1]) if args.has("--player-style") else "none","elapsed_seconds":(Time.get_ticks_msec()-stamp)/1000.0,"results":results,"victories":victories,"unresolved":unresolved,"scope":"authored campaign, both sides use same resource and command rules; player is tactical AI, not a human"}
	var path: String = "res://tests/campaign-play-%03d-%03d-%s%s.json"%[start,end,"coarse" if args.has("--coarse") else "fixed",("-"+str(args[args.find("--player-style")+1])) if args.has("--player-style") else ""]
	if args.has("--output"):path=args[args.find("--output")+1]
	report["engine"]=Engine.get_version_info();report["inputs"]={}
	for input in ["res://data/maps.json","res://data/campaign.json","res://data/balance-prototype.json","res://scripts/map_runtime.gd","res://scripts/battle_sim.gd","res://scripts/tactical_ai.gd"]:report.inputs[input]=FileAccess.get_sha256(input)
	var file=FileAccess.open(path,FileAccess.WRITE);file.store_string(JSON.stringify(report,"\t"));file.close()
	print("CAMPAIGN_REPORT "+JSON.stringify({"range":[start,end],"victories":victories,"unresolved":unresolved.size(),"seconds":report.elapsed_seconds}));quit(0 if unresolved.is_empty() else 1)
