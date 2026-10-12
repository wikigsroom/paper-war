extends SceneTree
const Data=preload("res://scripts/data_store.gd")
const Simulation=preload("res://scripts/battle_sim.gd")
const Readiness=preload("res://scripts/recruitment_readiness.gd")
var checks: int=0
var failures: Array=[]
func check(ok: bool,note: String):
	checks+=1
	if not ok:failures.append(note)
func _initialize():call_deferred("run")
func run():
	for side in [0,1]:
		var s=Simulation.new(Data.new())
		s.start({"map":"map.01.01","faction":"mu","enemy":"mu","starting_gold":1000,"enemy_starting_gold":1000})
		s.ai_enabled=[false,false]
		var id: String="unit.mu.medic"
		var before: String=JSON.stringify(s.players[side])
		var estimate: Dictionary=Readiness.first_investment(s,side,id)
		check(estimate.gold==187 and is_equal_approx(estimate.exit_seconds,7.8),"Locked support includes real research plus production")
		check(JSON.stringify(s.players[side])==before,"Inspector never spends or changes progression")
		var heavy: Dictionary=Readiness.first_investment(s,side,"unit.mu.colossus")
		check(heavy.gold==207+float(s.db.balance.units["unit.mu.colossus"].gold) and heavy.research_count==2 and heavy.research_seconds==15,"Heavy unit includes unfinished medic prerequisite exactly once")
		check(Readiness.first_investment(s,side,"unit.yin.axe").is_empty() and Readiness.first_investment(s,-1,id).is_empty(),"Foreign roster and invalid side have no production estimate")
		check(s.request(side,"recruit",{"id":"unit.mu.worker"}).ok and s.request(side,"recruit",{"id":"unit.mu.worker"}).ok,"Paid existing FIFO for parallel timing")
		estimate=Readiness.first_investment(s,side,id)
		check(is_equal_approx(estimate.exit_seconds,7.8),"Short existing FIFO runs during research, not after it")
		check(s.request(side,"research",{"id":"tech.mu.unit.medic"}).ok,"Research payment actually accepted")
		for i in range(30):s.tick(1.0/60.0)
		estimate=Readiness.first_investment(s,side,id)
		check(estimate.gold==110 and is_equal_approx(estimate.exit_seconds,7.3),"Paid research is not charged again; remaining time used")
		while not s.players[side].research.is_empty():s.tick(1.0/60.0)
		var started: float=s.time
		var cash: float=s.players[side].gold
		check(s.request(side,"recruit",{"id":id}).ok and s.players[side].gold==cash-110,"Actual post-unlock order costs displayed remaining gold")
		var produced: bool=false
		while s.time<started+4 and not produced:
			s.tick(1.0/60.0)
			produced=s.units.any(func(u):return u.side==side and u.id==id)
		check(produced and absf(s.time-7.8)<=2.0/60.0+.001,"Actual parallel research FIFO and production agree within two ticks")
		s.start({"map":"map.01.01","faction":"mu","enemy":"mu","starting_gold":1000,"enemy_starting_gold":1000});s.ai_enabled=[false,false]
		check(s.request(side,"research",{"id":"tech.mu.unit.warden"}).ok,"Unrelated research occupies single study slot")
		estimate=Readiness.first_investment(s,side,id)
		check(estimate.gold==187 and is_equal_approx(estimate.exit_seconds,12.8),"Busy study channel delays target without charging unrelated research twice")
		while not s.players[side].research.is_empty():s.tick(1.0/60.0)
		check(is_equal_approx(Readiness.first_investment(s,side,id).exit_seconds,7.8),"Finished unrelated project removes only its wait")
		check(Readiness.investment_notice(s,side,id).contains("187") and Readiness.investment_notice(s,side,id).contains("足额金币"),"Notice states cost and funding assumption")
		check(Readiness.reinforcement_seconds(s,side,id)==-1,"No own selected-route front means no response claim")
		var front=s.spawn("unit.mu.guard",side,float(s.bases[side].x)+(.65 if side==0 else -.65))
		s.map.advance(front,20,side)
		var response: float=Readiness.reinforcement_seconds(s,side,id)
		check(response>Readiness.first_investment(s,side,id).exit_seconds,"Response includes actual road travel beyond study and production")
		before=JSON.stringify([s.players,s.units,s.map.choices])
		Readiness.reinforcement_seconds(s,side,id)
		check(before==JSON.stringify([s.players,s.units,s.map.choices]),"Combined response query cannot alter army, cash or selected roads")
		s.spawn("unit.mu.colossus",1-side,float(front.x))
		check(is_equal_approx(response,Readiness.reinforcement_seconds(s,side,id)),"Enemy movement cannot leak into own response estimate")
		for order in range(6):s.request(side,"recruit",{"id":"unit.mu.guard"})
		var queued_response: float=Readiness.reinforcement_seconds(s,side,id)
		while not s.players[side].queue.is_empty():s.cancel_queue(side,0)
		check(queued_response>response and is_equal_approx(response,Readiness.reinforcement_seconds(s,side,id)),"Real FIFO orders delay response and actual cancellation restores it")
		check(Readiness.reinforcement_notice(s,side,id).contains("研究＋出仓＋行军") and Readiness.reinforcement_notice(s,side,id).contains("未计战线移动"),"Notice distinguishes total response from future moving battle prediction")
	print("FIRST_INVESTMENT: ",checks," checks; failures=",failures)
	quit(0 if failures.is_empty() else 1)
