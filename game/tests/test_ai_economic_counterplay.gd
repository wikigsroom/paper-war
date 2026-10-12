extends SceneTree
const Data=preload("res://scripts/data_store.gd")
const Simulation=preload("res://scripts/battle_sim.gd")
const AI=preload("res://scripts/tactical_ai.gd")
var checks: int=0
var failures: Array=[]
func check(ok: bool,note: String):
	checks+=1
	if not ok:failures.append(note)
func fixture(faction: String):
	var s=Simulation.new(Data.new())
	s.start({"map":"map.01.04","faction":faction,"enemy":"yin","full_tech":true,"starting_gold":0})
	s.units.clear();s.ai_enabled=[false,false];s.time=20
	return s
func _initialize():call_deferred("run")
func run():
	var s=fixture("mu")
	var worker=s.spawn("unit.mu.worker",0,20)
	var raider=s.spawn("unit.yin.spear",1,24);raider.target=worker.uid;raider.windup=.2
	s.players[0].mana=30;s.players[0].unlocked=["spell.mu.bind"];s.visibility.refresh()
	check(not s.visible_to(0,raider),"Raider starts beyond worker sight")
	check(not AI.economic_attack(s,0,raider),"Hidden target relationship does not give AI information")
	s.attack(raider,worker);s.visibility.refresh()
	check(AI.economic_attack(s,0,raider),"Actual firing reveals economic pressure")
	AI.cast_spells(s,0,[raider],[],false)
	check(raider.statuses.has("bind") and raider.windup==0,"Cheap lone raider receives an emergency interrupt")
	check(s.players[0].mana==0 and s.stats[0].casts==1,"Emergency uses real mana and spell cooldown")
	s=fixture("yin");worker=s.spawn("unit.yin.worker",0,20)
	raider=s.spawn("unit.yin.spear",1,23);raider.target=worker.uid
	var costly=s.spawn("unit.mu.colossus",1,22);s.players[0].mana=40;s.players[0].unlocked=["spell.yin.lightning"];s.visibility.refresh()
	AI.cast_spells(s,0,[costly,raider],[],false)
	check(raider.hp==0 and costly.hp==costly.max_hp,"Killable worker raider outranks idle expensive unit")
	s=fixture("mu");worker=s.spawn("unit.mu.worker",0,20)
	var guard=s.spawn("unit.mu.guard",0,20)
	raider=s.spawn("unit.yin.spear",1,23);raider.target=worker.uid;raider.windup=.2
	costly=s.spawn("unit.mu.colossus",1,21);costly.target=guard.uid;costly.windup=.5
	s.players[0].mana=30;s.players[0].unlocked=["spell.mu.bind"];s.visibility.refresh()
	AI.cast_spells(s,0,[raider,costly],[guard],false)
	check(costly.statuses.has("bind") and not raider.statuses.has("bind"),"Heavy windup retains priority over economic harassment")
	raider.target=guard.uid
	check(not AI.economic_attack(s,0,raider),"Ordinary army contact is not economic emergency")
	raider.target=worker.uid;raider.side=0
	check(not AI.economic_attack(s,0,raider),"Ownership change clears hostile economic pressure")
	print("AI_ECONOMIC_COUNTERPLAY: ",checks," checks; failures=",failures)
	quit(0 if failures.is_empty() else 1)
