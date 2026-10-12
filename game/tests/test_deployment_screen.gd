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
		s.config["experimental_ai_deployment_commitment"]=true
		var p: Dictionary=s.players[side]
		p.gold=70;p.ai_research_at=999;p.ai_unit_plan="unit.mu.medic";p.ai_unit_plan_until=30
		p.unlocked.append("unit.mu.medic")
		s.visibility.refresh();AI.turn(s,side)
		if p.queue!=["unit.mu.guard"] or p.gold!=0:failures.append("Absent screen must receive exact paid guard before support savings on side "+str(side))
		for i in range(120):s.tick(1.0/60.0)
		if not s.units.any(func(u):return u.side==side and u.id=="unit.mu.guard" and u.hp>0):failures.append("Paid screen did not exit production")
	print("DEPLOYMENT_SCREEN: 4 checks; failures=",failures)
	quit(0 if failures.is_empty() else 1)
