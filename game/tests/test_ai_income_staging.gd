extends SceneTree
const Data=preload("res://scripts/data_store.gd")
const Simulation=preload("res://scripts/battle_sim.gd")
const AI=preload("res://scripts/tactical_ai.gd")
var checks: int=0
var failures: Array=[]

func check(ok: bool,note: String):
	checks+=1
	if not ok:failures.append(note)

func opening(side: int):
	var sim=Simulation.new(Data.new())
	sim.start({"map":"map.01.11","faction":"jin" if side==0 else "yin","enemy":"yin" if side==0 else "jin","starting_gold":300,"enemy_starting_gold":300,"ai_warmup":0,"ai_style":"counter","experimental_ai_budget_planner":true,"experimental_ai_budget_planner_side":side})
	sim.ai_enabled=[false,false]
	for id in ["unit.jin.berserker","unit.jin.archer","unit.jin.worker","unit.jin.archer"]:
		check(sim.request(side,"recruit",{"id":id}).ok,"Normal 300-gold opening pays "+id+" / "+str(side))
	check(sim.request(1-side,"recruit",{"id":"unit.yin.axe"}).ok,"Opposing boundary actor also pays its fee / "+str(side))
	while sim.time<7.7:sim.tick(1.0/60.0)
	while sim.players[side].gold<35 and sim.time<15:sim.tick(1.0/60.0)
	check(sim.population(side,false)==3 and sim.population(side,true)==3 and sim.players[side].queue.is_empty(),"Real production forms three fighters and three miners / "+str(side))
	check(sim.players[side].gold>=35 and sim.players[side].gold<60,"Real returns can fund a miner before another shooter / "+str(side))
	sim.drain_events()
	return sim

func finish_miner(sim,side: int,expected: int):
	var due: float=sim.time+float(sim.db.balance.units["unit.jin.worker"].production_seconds)+.05
	while sim.time<due:sim.tick(1.0/60.0)
	check(sim.population(side,true)==expected and sim.players[side].queue.is_empty(),"The next miner finishes ordinary production / "+str(side)+" / "+str(expected))
	check(sim.drain_events().filter(func(e):return e.kind=="spawn" and e.side==side and e.id=="unit.jin.worker" and e.origin=="production").size()==1,"Exactly one paid miner is born / "+str(side)+" / "+str(expected))

func run():
	for side in [0,1]:
		var sim=opening(side)
		var p: Dictionary=sim.players[side]
		var cash: float=float(p.gold)
		var unlocked: Array=p.unlocked.duplicate()
		AI.turn(sim,side)
		check(p.queue==["unit.jin.worker"] and is_equal_approx(float(p.gold),cash-35),"Safe three-body formation pays the fourth miner before another shooter / "+str(side))
		check(p.research.is_empty() and p.unlocked==unlocked,"Three fighters do not waive the four-body research gate / "+str(side))
		check(sim.population(side,true,false)==3,"Paying an order does not produce an instant miner / "+str(side))
		finish_miner(sim,side,4)
		var returned: float=float(sim.stats[side].gold_delivered)
		while p.gold<35 and sim.time<30:sim.tick(1.0/60.0)
		check(p.gold>=35 and sim.stats[side].gold_delivered>returned,"Real mining funds the fifth miner / "+str(side))
		cash=float(p.gold);sim.drain_events();AI.turn(sim,side)
		check(p.queue==["unit.jin.worker"] and is_equal_approx(float(p.gold),cash-35),"The fifth miner pays its own 35-gold fee / "+str(side))
		finish_miner(sim,side,5)
		while p.gold<60 and sim.time<40:sim.tick(1.0/60.0)
		check(p.gold>=60,"Expanded paid crew returns enough for the fourth fighter / "+str(side))
		cash=float(p.gold);AI.turn(sim,side)
		check(p.queue==["unit.jin.archer"] and is_equal_approx(float(p.gold),cash-60),"After the paid crew the fourth fighter still pays its ordinary 60-gold fee / "+str(side))
		check(p.research.is_empty() and p.unlocked==unlocked,"Queued fourth fighter does not grant technology for free / "+str(side))

		sim=opening(side);p=sim.players[side]
		var miner: Dictionary=sim.units.filter(func(u):return u.side==side and u.id=="unit.jin.worker")[0]
		var enemy: Dictionary=sim.units.filter(func(u):return u.side!=side and u.id=="unit.yin.axe")[0]
		# Positional threat fixture, explicitly separate from normal match evidence.
		var sign: float=1 if side==0 else -1
		sim.map.apply_anchor(enemy,sim.map.project(Vector2(miner.x+sign*.5,miner.y)))
		sim.visibility.refresh();cash=float(p.gold);AI.turn(sim,side)
		check(sim.visible_to(side,enemy),"Boundary actor is actually visible / "+str(side))
		check(p.queue.is_empty() and is_equal_approx(float(p.gold),cash),"Immediate miner threat suppresses optional expansion / "+str(side))
		check(p.research.is_empty(),"Unsafe formation does not start another study / "+str(side))
		var tempo=Simulation.new(Data.new())
		tempo.start({"map":"map.01.11","faction":"yuan" if side==0 else "yin","enemy":"yin" if side==0 else "yuan","starting_gold":300,"enemy_starting_gold":300,"ai_warmup":0,"ai_style":"counter","experimental_ai_budget_planner":true,"experimental_ai_budget_planner_side":side})
		tempo.ai_enabled=[false,false]
		for id in ["unit.yuan.vanguard","unit.yuan.archer","unit.yuan.worker","unit.yuan.vanguard"]:
			check(tempo.request(side,"recruit",{"id":id}).ok,"Junction opening pays "+id+" / "+str(side))
		while tempo.time<7.1:tempo.tick(1.0/60.0)
		check(tempo.population(side,false,false)==3 and tempo.population(side,true,false)==3 and tempo.players[side].queue.is_empty(),"Junction opening genuinely produces its initial group / "+str(side))
		cash=float(tempo.players[side].gold);AI.turn(tempo,side)
		check(tempo.players[side].queue==["unit.yuan.archer"] and is_equal_approx(float(tempo.players[side].gold),cash-60),"Junction army queues its fourth fighter before optional miners / "+str(side))
		check(tempo.population(side,true,true)==3,"Junction first wave retains a three-miner crew / "+str(side))
	print("AI_INCOME_STAGING: ",checks," checks; failures=",failures)
	quit(0 if failures.is_empty() else 1)

func _initialize():call_deferred("run")
