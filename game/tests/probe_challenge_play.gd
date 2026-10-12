extends SceneTree
const Data=preload("res://scripts/data_store.gd")
const Simulation=preload("res://scripts/battle_sim.gd")
func run():
	var db=Data.new();var records: Array=[]
	for c in db.read_json("res://data/campaign.json").challenges:
		var s=Simulation.new(db);s.start(c);s.ai_enabled=[true,true]
		for i in range(181*60):
			s.tick(1.0/60.0);s.drain_events()
			if s.winner!=-2:break
		records.append({"id":c.id,"winner":s.winner,"time":s.time,"progress":s.ChallengeRules.progress(s),"target":c.challenge_rule.target,"score":s.ChallengeRules.score(s),"stats":s.stats[0],"reason":s.result_reason})
		print("CHALLENGE_PLAY ",c.id," winner=",s.winner," progress=",s.ChallengeRules.progress(s))
	var args=OS.get_cmdline_user_args();var file=FileAccess.open(args[args.find("--output")+1],FileAccess.WRITE)
	file.store_string(JSON.stringify({"scope":"Six paid native AI-vs-AI challenge plays; AI is not a human specialist and failure does not prove human impossibility.","simulation_sha":FileAccess.get_sha256("res://scripts/battle_sim.gd"),"rules_sha":FileAccess.get_sha256("res://scripts/challenge_rules.gd"),"records":records},"  "));file.close();quit()
func _initialize():call_deferred("run")
