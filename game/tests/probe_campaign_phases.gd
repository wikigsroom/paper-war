extends SceneTree
const Data=preload("res://scripts/data_store.gd")
const Simulation=preload("res://scripts/battle_sim.gd")
func run():
	var db=Data.new();var records: Array=[]
	for index in [0,3,6,10,11,19,39,59,99,199]:
		var level: Dictionary=db.campaign[index]
		var s=Simulation.new(db);s.start(level);s.ai_enabled=[true,true]
		var samples: Array=[];var previous: String=""
		for i in range(150*60):
			s.tick(1.0/60.0)
			s.drain_events()
			var current: String=s.players[1].get("ai_phase","")
			if current!=previous or i%1800==0:
				var army: Dictionary={}
				for u in s.units:
					if u.side==1:army[u.id]=int(army.get(u.id,0))+1
				samples.append({"time":s.time,"phase":current,"gold":s.players[1].gold,"army":army,"queue":s.players[1].queue.duplicate(),"studied":s.players[1].studied.duplicate(),"stats":s.stats[1].duplicate(true)})
				previous=current
			if s.winner!=-2:break
		var record={"id":level.id,"map":level.map,"objective":level.win,"winner":s.winner,"time":s.time,"samples":samples}
		records.append(record);print("CAMPAIGN_PHASE_PROBE ",level.id," t=",s.time," winner=",s.winner)
	var args=OS.get_cmdline_user_args();var output=args[args.find("--output")+1]
	var file=FileAccess.open(output,FileAccess.WRITE)
	file.store_string(JSON.stringify({"scope":"Ten native paid AI-vs-AI campaign probes, 150 seconds maximum, formal fog and authored phases. Not human completion or all-level balance evidence.","inputs":{"ai":FileAccess.get_sha256("res://scripts/tactical_ai.gd"),"campaign":FileAccess.get_sha256("res://data/campaign.json"),"simulation":FileAccess.get_sha256("res://scripts/battle_sim.gd")},"records":records},"  "));file.close();quit()
func _initialize():call_deferred("run")
