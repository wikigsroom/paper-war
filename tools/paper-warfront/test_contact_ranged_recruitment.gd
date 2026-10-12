extends SceneTree
# Explicit placement/cash fixtures for decision boundaries, not paid match proof.
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
func run():
	for side in [0,1]:
		var sim=make(side);var p: Dictionary=sim.players[side]
		var direction: float=1 if side==0 else -1
		var front: Dictionary=sim.spawn("unit.yin.axe",side,22)
		var enemy: Dictionary=sim.spawn("unit.mu.warden",1-side,22+3*direction)
		sim.visibility.refresh()
		verify(sim.visible_to(side,enemy),"the ranged contact is a current legal sighting / "+str(side))
		var rng_before: int=sim.ai_rng[side].state;var gold: float=p.gold
		verify(AI.contact_ranged_offer(sim,side,[front],[enemy])=="unit.yin.spear","own unlocked weapon outranges the observed caster / "+str(side))
		verify(sim.ai_rng[side].state==rng_before and p.gold==gold and p.queue.is_empty(),"offer query neither pays nor consumes random decisions / "+str(side))
		p.roster.erase("unit.yin.spear")
		verify(AI.contact_ranged_offer(sim,side,[front],[enemy])=="","restricted roster cannot request another unit / "+str(side))
		p.roster.append("unit.yin.spear");p.unlocked.erase("unit.yin.spear")
		verify(AI.contact_ranged_offer(sim,side,[front],[enemy])=="","counter cannot grant unfinished technology / "+str(side))
		p.unlocked.append("unit.yin.spear");p.queue.append("unit.yin.spear")
		verify(AI.contact_ranged_offer(sim,side,[front],[enemy])=="","already committed ranged production is not duplicated / "+str(side))
		p.queue.clear()
		var shooter: Dictionary=sim.spawn("unit.yin.spear",side,22+.8*direction)
		verify(AI.contact_ranged_offer(sim,side,[front,shooter],[enemy])=="","actual friendly fire coverage satisfies this contact / "+str(side))
		shooter.hp=0
		verify(AI.contact_ranged_offer(sim,side,[front,shooter],[enemy])=="unit.yin.spear","dead shooter is not firing coverage / "+str(side))
		shooter.hp=80;shooter.side=1-side
		verify(AI.contact_ranged_offer(sim,side,[front,shooter],[enemy])=="unit.yin.spear","foreign shooter cannot cover our engagement / "+str(side))
		enemy.hp=0
		verify(AI.contact_ranged_offer(sim,side,[front],[enemy])=="","dead contact does not redirect a budget / "+str(side))
		enemy.hp=105;enemy.side=side
		verify(AI.contact_ranged_offer(sim,side,[front],[enemy])=="","ownership change clears hostile demand / "+str(side))
		enemy.side=1-side;front.hp=0
		sim.map.apply_anchor(enemy,sim.map.project(Vector2(float(sim.bases[1-side].x),0)));sim.visibility.refresh()
		verify(not sim.visible_to(side,enemy) and AI.contact_ranged_offer(sim,side,[],[enemy])=="","hidden supplied actor cannot leak into counter selection / "+str(side))
		sim=make(side);p=sim.players[side];front=sim.spawn("unit.yin.axe",side,22)
		enemy=sim.spawn("unit.mu.warden",1-side,22+5*direction)
		var scout: Dictionary=sim.spawn("unit.yin.worker",side,enemy.x)
		sim.visibility.refresh()
		verify(sim.visible_to(side,enemy) and AI.contact_ranged_offer(sim,side,[front],[enemy])=="","visible distant caster without contact does not consume investment / "+str(side))
		enemy.target=scout.uid
		verify(AI.contact_ranged_offer(sim,side,[front],[enemy])=="unit.yin.spear","actual ranged economic attack is a relevant contact / "+str(side))
		var camper: Dictionary=sim.spawn("unit.mu.guard",1-side,float(sim.bases[side].x)+.65*direction)
		sim.visibility.refresh()
		verify(AI.contact_ranged_offer(sim,side,[front],[enemy,camper])=="","occupied production outlet retains melee survival priority / "+str(side))
		sim=make(side);p=sim.players[side];front=sim.spawn("unit.yin.axe",side,22)
		enemy=sim.spawn("unit.mu.warden",1-side,22+3*direction);sim.visibility.refresh()
		AI.turn(sim,side)
		verify(p.queue==["unit.yin.spear"] and p.gold==0,"normal decision pays the exact60 gold for the visible ranged response / "+str(side))
		sim=make(side);p=sim.players[side];p.gold=59;front=sim.spawn("unit.yin.axe",side,22)
		enemy=sim.spawn("unit.mu.warden",1-side,22+3*direction);sim.visibility.refresh();AI.turn(sim,side)
		verify(not p.queue.has("unit.yin.spear") and p.gold>=0,"59 gold cannot buy a60-gold counter or trigger unpaid saving / "+str(side))
	print("CONTACT_RANGED_RECRUITMENT: ",checks," checks; failures=",failures)
	quit(0 if failures.is_empty() else 1)
func _initialize():call_deferred("run")
