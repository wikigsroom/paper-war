extends SceneTree
const Data=preload("res://scripts/data_store.gd")
const Simulation=preload("res://scripts/battle_sim.gd")
const AI=preload("res://scripts/tactical_ai.gd")
func _initialize():call_deferred("run")
func run():
	var failures: Array=[]
	for side in [0,1]:
		var s=Simulation.new(Data.new())
		s.start({"map":"map.01.01","faction":"mu","enemy":"mu"})
		var p: Dictionary=s.players[side]
		var node: Dictionary=s.db.tech("tech.mu.unit.medic")
		p.gold=float(node.gold)+70-1
		if not AI.screen_budget_ready(s,side,node):failures.append("Default policy changed")
		s.config["experimental_ai_research_screen_budget"]=true
		if AI.screen_budget_ready(s,side,node):failures.append("Insufficient military reserve accepted")
		p.gold+=1
		if not AI.screen_budget_ready(s,side,node):failures.append("Exact reserve rejected")
		s.config["experimental_ai_research_screen_budget_side"]=1-side;p.gold=0
		if not AI.screen_budget_ready(s,side,node):failures.append("Opponent policy changed")
		s.start({"map":"map.01.01","faction":"mu","enemy":"mu","ai_warmup":0})
		s.ai_enabled=[false,false];s.config["experimental_ai_research_screen_budget"]=true
		p=s.players[side];p.gold=float(node.gold)+69;p.ai_research_at=0
		var sign: float=1 if side==0 else -1
		s.spawn("unit.mu.worker",side,s.bases[side].x)
		s.spawn("unit.mu.guard",side,s.bases[side].x+sign)
		s.spawn("unit.mu.guard",side,s.bases[side].x+2*sign)
		s.visibility.refresh();AI.turn(s,side)
		if p.ai_research!=node.id or not p.research.is_empty() or p.gold!=float(node.gold)+69:failures.append("Target must survive while payment is short by one gold")
		p.gold+=1;AI.turn(s,side)
		var military_cash: float=p.gold
		for id in p.queue:military_cash+=float(s.db.balance.units[id].gold)
		if p.research.get("id","")!=node.id or military_cash!=70:failures.append("Exact budget must buy research without losing remaining military cash or paid orders")
	print("RESEARCH_SCREEN_BUDGET: 12 checks; failures=",failures)
	quit(0 if failures.is_empty() else 1)
