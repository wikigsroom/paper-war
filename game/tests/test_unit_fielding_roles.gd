extends SceneTree
# Ownership/visibility/ability eligibility fixtures, not paid matches or balance.
const Data=preload("res://scripts/data_store.gd")
const Simulation=preload("res://scripts/battle_sim.gd")
const AI=preload("res://scripts/tactical_ai.gd")
var checks: int=0
var failures: Array=[]
func verify(ok: bool,note: String):
	checks+=1
	if not ok:failures.append(note)
func make(side: int,full: bool=true):
	var sim=Simulation.new(Data.new())
	sim.start({"map":"map.01.20","faction":"mu" if side==0 else "yin","enemy":"yin" if side==0 else "mu","starting_gold":160,"enemy_starting_gold":160,"full_tech":full,"ai_warmup":0})
	sim.ai_enabled=[false,false]
	return sim
func run():
	for side in [0,1]:
		var sim=make(side)
		var p: Dictionary=sim.players[side]
		var x: float=float(sim.bases[side].x)
		var guard: Dictionary=sim.spawn("unit.mu.guard",side,x)
		var shooter: Dictionary=sim.spawn("unit.mu.poisoner",side,x)
		var worker: Dictionary=sim.units.filter(func(u):return u.side==side and sim.db.balance.units[u.id].get("economy",false))[0]
		var foreign: Dictionary=sim.spawn("unit.yin.axe",1-side,float(sim.bases[1-side].x))
		var dead: Dictionary=guard.duplicate(true);dead["hp"]=0
		verify(AI.paid_grant_formation(sim,side,"unit.mu.phoenix",[],false,false),"Independent frontline can rebuild an empty safe army / "+str(side))
		verify(AI.paid_grant_formation(sim,side,"unit.mu.warden",[guard],false,false),"Offensive ranged role can use one living screen / "+str(side))
		verify(not AI.paid_grant_formation(sim,side,"unit.mu.medic",[guard],false,false),"Medic needs a second living fighter / "+str(side))
		verify(AI.paid_grant_formation(sim,side,"unit.mu.medic",[guard,shooter],false,false),"Medic can join its actual two-fighter group / "+str(side))
		verify(not AI.paid_grant_formation(sim,side,"unit.mu.medic",[worker,worker],false,false),"Paper workers are not a support formation / "+str(side))
		verify(not AI.paid_grant_formation(sim,side,"unit.mu.warden",[foreign],false,false),"Foreign frontline cannot screen this faction / "+str(side))
		verify(not AI.paid_grant_formation(sim,side,"unit.mu.warden",[dead],false,false),"A dead frontline cannot screen an order / "+str(side))
		verify(not AI.paid_grant_formation(sim,side,"unit.mu.medic",[guard,worker],false,false),"A miner cannot satisfy the second-fighter requirement / "+str(side))
		verify(not AI.paid_grant_formation(sim,side,"unit.mu.medic",[guard,dead],false,false),"A corpse cannot satisfy the second-fighter requirement / "+str(side))
		verify(not AI.paid_grant_formation(sim,side,"unit.mu.medic",[foreign,shooter],false,false),"A foreign unit cannot satisfy the support screen / "+str(side))
		verify(not AI.paid_grant_formation(sim,side,"unit.mu.warden",[guard,shooter],true,false),"Danger interrupts discretionary ranged savings / "+str(side))
		p.gold=164
		verify(not AI.paid_grant_formation(sim,side,"unit.mu.phoenix",[],true,true),"Emergency advanced frontline cannot spend unaffordable cash / "+str(side))
		p.gold=165
		verify(AI.paid_grant_formation(sim,side,"unit.mu.phoenix",[],true,true),"Affordable unlocked frontline can itself replace the screen / "+str(side))
		p.unlocked.erase("unit.mu.phoenix")
		verify(not AI.paid_grant_formation(sim,side,"unit.mu.phoenix",[],true,true),"Unfinished study cannot grant an emergency frontline / "+str(side))
		p["ai_grant_goal"]="unit.mu.phoenix"
		verify(AI.paid_grant_target(sim,side)=="unit.mu.phoenix","First delivery survives the real research wait / "+str(side))
		p.queue.append("unit.mu.phoenix")
		verify(AI.paid_grant_target(sim,side)=="" and p.ai_grant_goal=="","An already-paid queue does not duplicate the first recruit / "+str(side))
		p["ai_grant_goal"]="unit.yin.hammer"
		verify(AI.paid_grant_target(sim,side)=="" and p.ai_grant_goal=="","Off-roster target cannot trap recruitment savings / "+str(side))
		sim.config["experimental_ai_sequential_deployment"]=true
		sim.config["experimental_ai_sequential_deployment_side"]=side
		verify(AI.legacy_deployment_active(sim,side),"Explicit alternate planner retains ownership of its plan / "+str(side))
		verify(not AI.legacy_deployment_active(sim,1-side),"One side's planner does not disable the other side's normal pipeline / "+str(side))
		sim=make(side,false);p=sim.players[side]
		guard=sim.spawn("unit.mu.guard",side,float(sim.bases[side].x));shooter=sim.spawn("unit.mu.poisoner",side,float(sim.bases[side].x))
		foreign=sim.spawn("unit.yin.axe",1-side,float(sim.bases[1-side].x));sim.visibility.refresh()
		var ordinary: Dictionary=AI.first_grant_offer(sim,side,{},[guard,shooter],[])
		verify(not ordinary.is_empty() and p.roster.has(ordinary.grant),"First investment selects an available role from the owned roster / "+str(side))
		verify(not sim.visible_to(side,foreign),"Opposite-base fixture is actually beyond current vision / "+str(side))
		var cash: float=float(p.gold);var mana: float=float(p.mana);var rng_state: int=sim.ai_rng[side].state
		var hidden: Dictionary=AI.first_grant_offer(sim,side,{},[guard,shooter],[foreign])
		verify(hidden.get("id","")==ordinary.get("id",""),"Passing hidden enemy data cannot alter the investment / "+str(side))
		verify(is_equal_approx(float(p.gold),cash) and is_equal_approx(float(p.mana),mana) and sim.ai_rng[side].state==rng_state,"Offer query neither pays nor consumes gameplay RNG / "+str(side))
		var phase: Dictionary={"prefer_units":["unit.mu.colossus"]}
		phase["research_path"]=AI.preferred_research_path(sim,phase)
		verify(AI.first_grant_offer(sim,side,phase,[guard,shooter],[]).get("grant","")=="unit.mu.medic","Authored colossus path keeps its actual medic prerequisite / "+str(side))
	print("UNIT_FIELDING_ROLES: ",checks," checks; failures=",failures)
	quit(0 if failures.is_empty() else 1)
func _initialize():call_deferred("run")
