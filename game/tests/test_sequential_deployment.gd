extends SceneTree
const Data=preload("res://scripts/data_store.gd")
const Simulation=preload("res://scripts/battle_sim.gd")
const AI=preload("res://scripts/tactical_ai.gd")
var checks: int=0
var failures: Array=[]
func check(ok: bool,note: String):
	checks+=1
	if not ok:failures.append(note)
func _initialize():call_deferred("run")
func run():
	for side in [0,1]:
		var s=Simulation.new(Data.new())
		s.start({"map":"map.01.01","faction":"mu","enemy":"mu","ai_warmup":0})
		s.ai_enabled=[false,false];s.config["experimental_ai_sequential_deployment"]=true
		var p: Dictionary=s.players[side]
		var node: Dictionary=s.db.tech("tech.mu.unit.medic")
		p.gold=float(node.gold)+110;p.ai_research_at=0
		var sign: float=1 if side==0 else -1
		s.spawn("unit.mu.worker",side,s.bases[side].x)
		s.spawn("unit.mu.guard",side,s.bases[side].x+sign)
		s.spawn("unit.mu.guard",side,s.bases[side].x+2*sign)
		s.visibility.refresh();AI.turn(s,side)
		check(p.research.get("id","")==node.id and p.get("ai_unit_plan","")==node.grant,"Paid research establishes deployment goal")
		check(p.gold==110,"Actual recruit cost remains in cash")
		for i in range(310):s.tick(1.0/60.0)
		check(p.unlocked.has(node.grant),"Unlock waits for actual study")
		p.ai_unit_plan_until=s.time-1
		AI.turn(s,side)
		check(p.queue==[node.grant] and p.gold==0,"Old timer cannot silently discard paid unlock before real recruitment")
		AI.turn(s,side)
		check(p.ai_unit_plan=="","Paid queued deployment releases goal")
		for i in range(180):s.tick(1.0/60.0)
		check(s.units.any(func(u):return u.side==side and u.id==node.grant and u.hp>0),"Paid advanced unit exits production")
		s.start({"map":"map.01.01","faction":"mu","enemy":"mu","ai_warmup":0})
		s.ai_enabled=[false,false];s.config["experimental_ai_sequential_deployment"]=true
		p=s.players[side];p.ai_unit_plan=node.grant;p.ai_unit_plan_until=-1;p.gold=70
		p.unlocked.append(node.grant);p.studied.append(node.id)
		s.visibility.refresh();AI.turn(s,side)
		check(p.queue==["unit.mu.guard"] and p.gold==0,"Absent frontline uses actual cash for recovery before support")
		check(p.ai_unit_plan==node.grant and p.research.is_empty(),"Recovery suspends deployment without replacing it with another research")
		s.start({"map":"map.01.01","faction":"mu","enemy":"mu","ai_warmup":0})
		s.ai_enabled=[false,false];s.config["experimental_ai_sequential_deployment"]=true
		p=s.players[side];p.ai_unit_plan=node.grant;p.ai_unit_plan_until=-1;p.gold=70
		p.unlocked.append(node.grant);p.studied.append(node.id)
		s.spawn("unit.mu.guard",side,s.bases[side].x+sign)
		s.visibility.refresh();AI.turn(s,side)
		check(not p.queue.is_empty() and not p.queue.has(node.grant) and p.gold<70,"One-body formation must buy a real second fighter before support savings")
		check(p.ai_unit_plan==node.grant,"Formation recovery preserves the deployment goal")
		s.start({"map":"map.01.01","faction":"mu","enemy":"mu","ai_warmup":0})
		s.ai_enabled=[false,false];s.config["experimental_ai_sequential_deployment"]=true;s.config["experimental_ai_sequential_deployment_side"]=1-side
		p=s.players[side];p.gold=float(node.gold)+110;p.ai_research_at=0
		s.spawn("unit.mu.worker",side,s.bases[side].x)
		s.spawn("unit.mu.guard",side,s.bases[side].x+sign);s.spawn("unit.mu.guard",side,s.bases[side].x+2*sign)
		s.visibility.refresh();AI.turn(s,side)
		check(p.get("ai_unit_plan","")=="","Pilot cannot add deployment goal to the other side")
	print("SEQUENTIAL_DEPLOYMENT: ",checks," checks; failures=",failures)
	quit(0 if failures.is_empty() else 1)
