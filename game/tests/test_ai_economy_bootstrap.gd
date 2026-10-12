extends SceneTree
# Paid opening and real miner production. Positional safety cases are fixtures,
# not normal-match or balance evidence.
const Data=preload("res://scripts/data_store.gd")
const Simulation=preload("res://scripts/battle_sim.gd")
const AI=preload("res://scripts/tactical_ai.gd")
var checks: int=0
var failures: Array=[]
var trial: bool=false

func verify(ok: bool,note: String):
	checks+=1
	if not ok:failures.append(note)

func opening(side: int,until: float=15.5,opponent: bool=false):
	var sim=Simulation.new(Data.new())
	sim.start({"map":"map.01.04","faction":"bai","enemy":"bai","starting_gold":160,"enemy_starting_gold":160,"ai_warmup":0,"seed":137})
	sim.ai_enabled=[false,false]
	if trial:
		sim.config["experimental_ai_economy_bootstrap"]=true
		sim.config["experimental_ai_economy_bootstrap_side"]=side
	for id in ["unit.bai.mirror","unit.bai.repeater"]:
		verify(sim.request(side,"recruit",{"id":id}).ok,"Opening fighters pay their real fee / "+str(side))
	if opponent:verify(sim.request(1-side,"recruit",{"id":"unit.bai.mirror"}).ok,"Threat actor also pays its fee / "+str(side))
	while sim.time<until:sim.tick(1.0/60.0)
	verify(sim.population(side,false,false)==2,"Opening fighters finish actual production / "+str(side))
	verify(sim.population(side,true,false)==2,"Initial crew contains two miners / "+str(side))
	return sim

func run():
	trial=OS.get_cmdline_user_args().has("--economy-trial")
	for side in [0,1]:
		var sim=opening(side)
		var p: Dictionary=sim.players[side]
		verify(p.gold>=35 and p.gold<70,"Real mining reaches the missing third-miner cash window / "+str(side))
		verify(float(sim.stats[side].gold_delivered)>0,"Cash comes from actual delivery / "+str(side))
		var cash: float=float(p.gold)
		var recruited: int=int(sim.stats[side].recruited)
		var studied: Array=p.studied.duplicate()
		sim.drain_events();AI.turn(sim,side)
		verify(p.queue==["unit.bai.worker"],"Safe cash window queues the third miner / "+str(side))
		verify(is_equal_approx(float(p.gold),cash-35),"Third miner costs its ordinary 35 gold / "+str(side))
		verify(sim.stats[side].recruited==recruited+1,"Only one paid order is added / "+str(side))
		verify(sim.population(side,true,false)==2,"Queued miner is not born instantly / "+str(side))
		verify(p.studied==studied and p.research.is_empty(),"Expansion grants no free study / "+str(side))
		verify(float(p.get("ai_build_reserve",0))==0,"Opening expansion precedes optional watchpost reservation / "+str(side))
		var due: float=sim.time+float(sim.db.balance.units["unit.bai.worker"].production_seconds)+.05
		while sim.time<due:sim.tick(1.0/60.0)
		var births: Array=sim.drain_events().filter(func(e):return e.kind=="spawn" and e.side==side and e.id=="unit.bai.worker" and e.get("origin","")=="production")
		verify(births.size()==1 and sim.population(side,true,false)==3,"Third miner finishes the real production queue / "+str(side))
		verify(is_equal_approx(float(p.gold),160+float(sim.stats[side].gold_delivered)-185),"Opening ledger contains only 150 fighter fees and 35 miner fee / "+str(side))

		var poor=opening(side,5.2)
		cash=float(poor.players[side].gold);AI.turn(poor,side)
		verify(poor.players[side].queue.is_empty() and is_equal_approx(float(poor.players[side].gold),cash),"Insufficient real cash does not order a miner / "+str(side))

		var saving=opening(side)
		saving.players[side].ai_research="tech.bai.unit.scribe"
		cash=float(saving.players[side].gold);AI.turn(saving,side)
		verify(not saving.players[side].queue.has("unit.bai.worker") and is_equal_approx(float(saving.players[side].gold),cash),"A selected paid study keeps its existing funding reserve / "+str(side))

		var unsafe=opening(side,15.5,true)
		var enemy: Dictionary=unsafe.units.filter(func(u):return u.side!=side and u.id=="unit.bai.mirror")[0]
		var miner: Dictionary=unsafe.units.filter(func(u):return u.side==side and u.id=="unit.bai.worker")[0]
		unsafe.map.apply_anchor(enemy,unsafe.map.project(Vector2(miner.x+.5,miner.y)))
		unsafe.visibility.refresh()
		verify(unsafe.visible_to(side,enemy),"Safety fixture uses a currently visible paid enemy / "+str(side))
		AI.turn(unsafe,side)
		verify(not unsafe.players[side].queue.has("unit.bai.worker"),"Immediate visible threat prevents optional expansion / "+str(side))

	var quota=opening(1)
	quota.config["ai_phases"]=[{"id":"qa.two-worker-quota","at":0,"style":"counter","workers":2}]
	AI.turn(quota,1)
	verify(quota.population(1,true,true)==2,"Authored two-worker quota is respected")
	verify(float(quota.players[1].get("ai_build_reserve",0))>0,"A satisfied smaller quota can still reserve an optional tower")
	print("AI_ECONOMY_BOOTSTRAP: ",checks," checks; failures=",failures)
	quit(0 if failures.is_empty() else 1)

func _initialize():call_deferred("run")
