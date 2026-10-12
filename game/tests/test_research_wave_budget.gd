extends SceneTree
const Data=preload("res://scripts/data_store.gd")
const Simulation=preload("res://scripts/battle_sim.gd")
const AI=preload("res://scripts/tactical_ai.gd")
func _initialize():call_deferred("run")
func run():
	var failures: Array=[]
	for side in [0,1]:
		var s=Simulation.new(Data.new())
		s.start({"map":"map.01.01","faction":"mu","enemy":"mu","ai_warmup":0})
		s.ai_enabled=[false,false]
		s.config["experimental_ai_research_screen_budget"]=true
		s.config["experimental_ai_deployment_commitment"]=true
		var p: Dictionary=s.players[side]
		var node: Dictionary=s.db.tech("tech.mu.unit.medic")
		var total: float=float(node.gold)+maxf(70,110)
		p.gold=total-1;p.ai_research_at=0
		var sign: float=1 if side==0 else -1
		s.spawn("unit.mu.worker",side,s.bases[side].x)
		s.spawn("unit.mu.guard",side,s.bases[side].x+sign)
		s.spawn("unit.mu.guard",side,s.bases[side].x+2*sign)
		s.visibility.refresh();AI.turn(s,side)
		if p.ai_research!=node.id or not p.research.is_empty() or p.gold!=total-1:failures.append("Unfunded wave must retain its target without spending")
		p.gold+=1;AI.turn(s,side)
		if p.research.get("id","")!=node.id or p.get("ai_unit_plan","")!=node.grant:failures.append("Funded research must establish a real deployment commitment")
		var remaining: float=p.gold
		for id in p.queue:remaining+=float(s.db.balance.units[id].gold)
		if remaining!=110:failures.append("Research must leave exactly the paid or reserved first-deployment budget")
		for i in range(310):s.tick(1.0/60.0)
		var before: float=p.gold
		AI.turn(s,side)
		if not p.queue.has(node.grant) or p.gold!=before-110:failures.append("Completed unlock must make an actual paid support order")
		for i in range(180):s.tick(1.0/60.0)
		if not s.units.any(func(u):return u.side==side and u.id==node.grant and u.hp>0):failures.append("Paid support must exit production")
	print("RESEARCH_WAVE_BUDGET: 10 checks; failures=",failures)
	quit(0 if failures.is_empty() else 1)
