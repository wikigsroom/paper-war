extends SceneTree
const Data=preload("res://scripts/data_store.gd")
const Simulation=preload("res://scripts/battle_sim.gd")
const AI=preload("res://scripts/tactical_ai.gd")
var checks: int=0
var failures: Array=[]

func check(ok: bool,note: String):
	checks+=1
	if not ok:failures.append(note)

func paid_formation(side: int,shooters: int=3):
	var sim=Simulation.new(Data.new())
	# The four-body case is an explicitly controlled 420-gold, three-worker
	# scenario. The separate first-wave case retains the normal 300-gold start.
	var starting: int=300 if shooters==1 else 420
	sim.start({"map":"map.01.11","faction":"jin" if side==0 else "yin","enemy":"yin" if side==0 else "jin","starting_gold":starting,"enemy_starting_gold":starting,"worker_limit":3,"ai_warmup":0,"ai_style":"counter","experimental_ai_budget_planner":true,"experimental_ai_budget_planner_side":side})
	sim.ai_enabled=[false,false]
	var orders: Array=["unit.jin.berserker"]
	for i in range(shooters):orders.append("unit.jin.archer")
	orders.append("unit.jin.worker")
	for id in orders:
		check(sim.request(side,"recruit",{"id":id}).ok,"Opening pays the ordinary fee: "+id+" / "+str(side))
	# The opposite body also pays its fee and completes ordinary production.
	check(sim.request(1-side,"recruit",{"id":"unit.yin.axe"}).ok,"Opposite test body is paid / "+str(side))
	var due: float=2.4+shooters*1.8+1.6+.1
	while sim.time<due:sim.tick(1.0/60.0)
	check(sim.players[side].queue.is_empty() and sim.population(side,false)==shooters+1 and sim.population(side,true)==3,"Opening finishes its actual paid bodies and three workers / "+str(side))
	check(sim.players[side].gold>=60 and sim.players[side].gold<125,"Actual transport has not yet funded a second 125-gold front / "+str(side))
	sim.drain_events()
	return sim

func run():
	for side in [0,1]:
		var first=paid_formation(side,1)
		var first_cash: float=float(first.players[side].gold)
		AI.turn(first,side)
		check(first.players[side].queue==["unit.jin.archer"] and is_equal_approx(float(first.players[side].gold),first_cash-60),"One front and one shooter can fund the second early shooter / "+str(side))
		check(first.players[side].research.is_empty(),"An incomplete first wave does not start technology / "+str(side))
		var sim=paid_formation(side)
		var p: Dictionary=sim.players[side]
		var cash: float=float(p.gold)
		var unlocks: Array=p.unlocked.duplicate()
		AI.turn(sim,side)
		check(p.queue.is_empty() and is_equal_approx(float(p.gold),cash),"Safe formation saves actual cash for its missing second front / "+str(side))
		check(not sim.drain_events().any(func(e):return e.kind=="recruit" and e.side==side),"Safe formation does not repeatedly buy a cheaper archer / "+str(side))
		check(p.unlocked==unlocks and p.research.is_empty(),"The protected contact fee is not spent on another study / "+str(side))
		var delivered: float=float(sim.stats[side].gold_delivered)
		while p.gold<125 and sim.time<45:sim.tick(1.0/60.0)
		check(p.gold>=125 and sim.stats[side].gold_delivered>delivered,"Ordinary mining and return transport fund the missing front / "+str(side))
		cash=float(p.gold);sim.drain_events()
		AI.turn(sim,side)
		check(p.queue==["unit.jin.berserker"] and is_equal_approx(float(p.gold),cash-125),"The saved front enters the real queue and pays exactly 125 gold / "+str(side))
		check(sim.drain_events().filter(func(e):return e.kind=="recruit" and e.side==side and e.id=="unit.jin.berserker").size()==1,"One paid front order is issued / "+str(side))
		var due: float=sim.time+float(sim.db.balance.units["unit.jin.berserker"].production_seconds)
		while sim.time<due+.05:sim.tick(1.0/60.0)
		check(sim.drain_events().filter(func(e):return e.kind=="spawn" and e.side==side and e.id=="unit.jin.berserker" and e.origin=="production").size()==1,"The second front is born through ordinary production / "+str(side))
		check(p.queue.is_empty() and sim.population(side,false)==5,"No free or substitute body was added / "+str(side))

		sim=paid_formation(side);p=sim.players[side]
		var miner: Dictionary=sim.units.filter(func(u):return u.side==side and u.id=="unit.jin.worker")[0]
		var enemy: Dictionary=sim.units.filter(func(u):return u.side!=side and u.id=="unit.yin.axe")[0]
		# Explicit positional fixture tests urgency only; this is not balance evidence.
		var sign: float=1 if side==0 else -1
		sim.map.apply_anchor(enemy,sim.map.project(Vector2(miner.x+sign*.5,miner.y)))
		sim.visibility.refresh()
		check(sim.visible_to(side,enemy) and AI.immediate_economic_threat(sim,side,[enemy],2.4),"Actual visible threat can reach a living miner before front production / "+str(side))
		cash=float(p.gold);AI.turn(sim,side)
		check(p.queue==["unit.jin.archer"] and is_equal_approx(float(p.gold),cash-60),"Urgent economic defence can still buy the affordable 60-gold archer / "+str(side))

	var restricted=Simulation.new(Data.new())
	restricted.start({"map":"map.01.11","faction":"jin","enemy":"yin","starting_gold":80,"enemy_starting_gold":300,"restrict_roster":true,"combat_slots":2,"player_roster":["unit.jin.archer","unit.jin.artillery"],"available_roster":["unit.jin.archer","unit.jin.artillery"],"experimental_ai_budget_planner":true,"experimental_ai_budget_planner_side":0})
	restricted.ai_enabled=[false,false]
	check(not restricted.players[0].roster.has("unit.jin.berserker"),"Ranged-only scenario genuinely excludes the front")
	AI.turn(restricted,0)
	check(restricted.players[0].queue==["unit.jin.archer"] and is_equal_approx(float(restricted.players[0].gold),20),"A restricted ranged roster does not save forever for an unavailable front")
	print("AI_CONTACT_FUNDING: ",checks," checks; failures=",failures)
	quit(0 if failures.is_empty() else 1)

func _initialize():call_deferred("run")
