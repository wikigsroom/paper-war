extends SceneTree
# Real 160-gold opening, transport, payments and construction/study timers.
# Opposing AI is disabled to isolate funding order, not to measure balance.
const Data=preload("res://scripts/data_store.gd")
const Simulation=preload("res://scripts/battle_sim.gd")
const AI=preload("res://scripts/tactical_ai.gd")
var checks: int=0
var failures: Array=[]
func verify(ok: bool,note: String):
	checks+=1
	if not ok:failures.append(note)
func start(side: int,faction: String):
	var sim=Simulation.new(Data.new())
	sim.start({"map":"map.01.04","faction":faction if side==0 else "yin","enemy":"yin" if side==0 else faction,"starting_gold":160,"enemy_starting_gold":160,"ai_warmup":0,"seed":137})
	sim.ai_enabled=[false,false]
	return sim
func advance(sim,until: float):
	while sim.time<until:sim.tick(1.0/60.0)
func run():
	for side in [0,1]:
		var sim=start(side,"deng")
		var p: Dictionary=sim.players[side]
		for id in ["unit.deng.mirror","unit.deng.fire"]:
			verify(sim.request(side,"recruit",{"id":id}).ok,"Facility opening pays its real fighter fees / "+str(side))
		advance(sim,13)
		var cash: float=float(p.gold)
		verify(cash>=35 and cash<80 and float(sim.stats[side].gold_delivered)>0,"Real transport produces a contested facility/miner budget / "+str(side))
		verify(sim.population(side,false,false)==2 and sim.population(side,true,false)==2,"Facility budget uses two produced fighters and the actual starting crew / "+str(side))
		AI.turn(sim,side)
		verify(p.queue.is_empty() and is_equal_approx(float(p.gold),cash),"Optional miner cannot consume the unbuilt facility budget / "+str(side))
		verify(float(p.ai_build_reserve)==80 and sim.buildings.is_empty(),"Facility is reserved, not built for free / "+str(side))
		while p.gold<80 and sim.time<40:sim.tick(1.0/60.0)
		verify(p.gold>=80,"Real deliveries fund the facility / "+str(side))
		cash=float(p.gold);AI.turn(sim,side)
		var owned: Array=sim.buildings.filter(func(b):return b.side==side and b.id=="building.deng.mana")
		verify(owned.size()==1 and is_equal_approx(float(p.gold),cash-55),"Facility pays its ordinary 55 gold / "+str(side))
		if owned.is_empty():continue
		verify(owned[0].state=="constructing" and owned[0].construction>0,"Paid facility retains its actual construction wait / "+str(side))
		advance(sim,sim.time+float(owned[0].construction)+.05)
		verify(owned[0].state=="active", "Facility becomes active through the normal construction timer / "+str(side))
		verify(is_equal_approx(float(p.gold),160+float(sim.stats[side].gold_delivered)-170),"Facility ledger contains 115 fighter fees and 55 facility fee / "+str(side))

	var authored=start(1,"yin")
	var p: Dictionary=authored.players[1]
	for id in ["unit.yin.axe","unit.yin.spear"]:
		verify(authored.request(1,"recruit",{"id":id}).ok,"Authored opening pays its actual fighter fees")
	advance(authored,5.2)
	authored.config["ai_phases"]=[{"id":"qa.paid-cannon-path","at":0,"style":"economy","workers":3,"prefer_units":["unit.yin.cannon"]}]
	var cash: float=float(p.gold)
	verify(cash>=35 and cash<66 and authored.population(1,false,false)==2,"Authored path enters the real pre-study cash window")
	AI.turn(authored,1)
	verify(p.ai_research=="tech.yin.unit.hammer" and p.research.is_empty(),"Authored cannon prerequisite is selected without a free unlock")
	verify(p.queue.is_empty() and is_equal_approx(float(p.gold),cash),"Optional miner preserves the authored prerequisite budget")
	while p.gold<66 and authored.time<25:authored.tick(1.0/60.0)
	verify(p.gold>=66 and authored.stats[1].gold_delivered>0,"Actual transport funds the authored prerequisite")
	cash=float(p.gold);AI.turn(authored,1)
	verify(p.research.get("id","")=="tech.yin.unit.hammer" and is_equal_approx(float(p.gold),cash-66),"Authored study pays the full 66 gold")
	verify(not p.unlocked.has("unit.yin.hammer"),"Research payment does not bypass its timer")
	advance(authored,authored.time+5.05)
	verify(p.unlocked.has("unit.yin.hammer"),"Prerequisite finishes the normal five-second research timer")
	verify(is_equal_approx(float(p.gold),160+float(authored.stats[1].gold_delivered)-171),"Authored ledger contains 105 fighter fees and 66 study fee")
	print("AI_BOOTSTRAP_INVESTMENTS: ",checks," checks; failures=",failures)
	quit(0 if failures.is_empty() else 1)
func _initialize():call_deferred("run")
