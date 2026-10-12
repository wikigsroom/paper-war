extends SceneTree
# Explicit control/position/cash fixtures, not normal paid match evidence.
const Data=preload("res://scripts/data_store.gd")
const Simulation=preload("res://scripts/battle_sim.gd")
const AI=preload("res://scripts/tactical_ai.gd")
var checks: int=0
var failures: Array=[]
func verify(ok: bool,note: String):
	checks+=1
	if not ok:failures.append(note)
func make(side: int):
	var sim=Simulation.new(Data.new())
	sim.start({"map":"map.01.04","faction":"yin" if side==0 else "mu","enemy":"mu" if side==0 else "yin","starting_gold":60,"enemy_starting_gold":60,"ai_warmup":0})
	sim.ai_enabled=[false,false];sim.time=50;sim.players[side].mana=0
	return sim
func offer(sim,side: int,front: Dictionary,enemy: Dictionary,extra: Array=[]) -> String:
	return AI.contact_ranged_offer(sim,side,[front]+extra,[enemy])
func run():
	for side in [0,1]:
		var sim=make(side);var p: Dictionary=sim.players[side]
		var direction: float=1 if side==0 else -1
		var front: Dictionary=sim.spawn("unit.yin.axe",side,22)
		var enemy: Dictionary=sim.spawn("unit.mu.warden",1-side,22+3*direction)
		sim.visibility.refresh()
		verify(sim.visible_to(side,enemy),"control fixture is currently visible / "+str(side))
		verify(offer(sim,side,front,enemy)=="","ordinary approach does not interrupt investment / "+str(side))
		for status in ["bind","stun","root","cold"]:
			front.statuses.clear();sim.set_status(front,status,5,0,1-side,enemy.uid)
			verify(offer(sim,side,front,enemy)=="unit.yin.spear","observed hostile "+status+" denies frontline contact / "+str(side))
		front.statuses.clear();sim.set_status(front,"bind",5,0,1-side,enemy.uid)
		var rng_before: int=sim.ai_rng[side].state;var gold: float=p.gold
		verify(offer(sim,side,front,enemy)=="unit.yin.spear" and sim.ai_rng[side].state==rng_before and p.gold==gold and p.queue.is_empty(),"query neither pays nor consumes RNG / "+str(side))
		p.roster.erase("unit.yin.spear")
		verify(offer(sim,side,front,enemy)=="","restricted roster is respected / "+str(side))
		p.roster.append("unit.yin.spear");p.unlocked.erase("unit.yin.spear")
		verify(offer(sim,side,front,enemy)=="","unfinished technology is not granted / "+str(side))
		p.unlocked.append("unit.yin.spear");p.queue.append("unit.yin.spear")
		verify(offer(sim,side,front,enemy)=="","already paid ranged production is not duplicated / "+str(side))
		p.queue.clear()
		var shooter: Dictionary=sim.spawn("unit.yin.spear",side,22+.8*direction)
		verify(offer(sim,side,front,enemy,[shooter])=="","living adequate weapon satisfies demand / "+str(side))
		sim.map.apply_anchor(shooter,sim.map.project(Vector2(float(sim.bases[side].x),0)))
		verify(offer(sim,side,front,enemy,[shooter])=="","adequate weapon still in transit prevents duplicate counter purchases / "+str(side))
		shooter.hp=0
		verify(offer(sim,side,front,enemy,[shooter])=="unit.yin.spear","dead weapon does not satisfy demand / "+str(side))
		shooter.hp=80;shooter.side=1-side
		verify(offer(sim,side,front,enemy,[shooter])=="unit.yin.spear","foreign weapon does not satisfy demand / "+str(side))
		enemy.hp=0
		verify(offer(sim,side,front,enemy)=="","dead attacker does not redirect funds / "+str(side))
		enemy.hp=105;enemy.side=side
		verify(offer(sim,side,front,enemy)=="","ownership change clears hostile demand / "+str(side))
		enemy.side=1-side;front.hp=0
		sim.map.apply_anchor(enemy,sim.map.project(Vector2(float(sim.bases[1-side].x),0)));sim.visibility.refresh()
		verify(not sim.visible_to(side,enemy) and offer(sim,side,front,enemy)=="","hidden supplied attacker cannot reveal a counter / "+str(side))
		sim=make(side);p=sim.players[side];front=sim.spawn("unit.yin.axe",side,22)
		enemy=sim.spawn("unit.mu.warden",1-side,22+5*direction)
		sim.spawn("unit.yin.worker",side,enemy.x);sim.visibility.refresh();sim.set_status(front,"bind",5,0,1-side,enemy.uid)
		verify(sim.visible_to(side,enemy) and offer(sim,side,front,enemy)=="","remote sighting without weapon contact does not spend / "+str(side))
		sim=make(side);p=sim.players[side];front=sim.spawn("unit.yin.axe",side,22)
		enemy=sim.spawn("unit.mu.warden",1-side,22+3*direction);sim.visibility.refresh();sim.set_status(front,"bind",5,0,1-side,enemy.uid)
		var camper: Dictionary=sim.spawn("unit.mu.guard",1-side,float(sim.bases[side].x)+.65*direction);sim.visibility.refresh()
		verify(AI.contact_ranged_offer(sim,side,[front],[enemy,camper])=="","occupied outlet keeps melee survival priority / "+str(side))
		sim=make(side);p=sim.players[side];front=sim.spawn("unit.yin.axe",side,22)
		enemy=sim.spawn("unit.mu.warden",1-side,22+3*direction);sim.visibility.refresh();sim.set_status(front,"bind",5,0,1-side,enemy.uid)
		p["ai_grant_goal"]="unit.yin.guard";p.unlocked.append("unit.yin.guard")
		AI.turn(sim,side)
		verify(p.queue==["unit.yin.spear"] and p.gold==0,"normal decision pays exact60 gold / "+str(side))
		verify(p.ai_grant_goal=="unit.yin.guard" and not p.get("ai_grant_first_ordered",false),"emergency counter preserves the completed study's first-order goal / "+str(side))
		sim=make(side);p=sim.players[side];p.gold=59;front=sim.spawn("unit.yin.axe",side,22)
		enemy=sim.spawn("unit.mu.warden",1-side,22+3*direction);sim.visibility.refresh();sim.set_status(front,"bind",5,0,1-side,enemy.uid);AI.turn(sim,side)
		verify(not p.queue.has("unit.yin.spear") and p.gold>=0,"insufficient gold grants no recruit / "+str(side))
		sim=make(side);front=sim.spawn("unit.yin.axe",side,22);enemy=sim.spawn("unit.mu.warden",1-side,22+.5*direction)
		sim.visibility.refresh();sim.set_status(front,"root",5,0,1-side,enemy.uid)
		verify(offer(sim,side,front,enemy)=="","root in melee reach still allows attacks / "+str(side))
		front.statuses.clear();sim.set_status(front,"cold",5,0,1-side,enemy.uid)
		verify(offer(sim,side,front,enemy)=="","cold in melee reach still allows attacks / "+str(side))
	print("STALLED_FRONT_RECRUITMENT: ",checks," checks; failures=",failures)
	quit(0 if failures.is_empty() else 1)
func _initialize():call_deferred("run")
