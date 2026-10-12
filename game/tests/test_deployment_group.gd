extends SceneTree
const Data=preload("res://scripts/data_store.gd")
const Simulation=preload("res://scripts/battle_sim.gd")
const Readiness=preload("res://scripts/recruitment_readiness.gd")
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
		s.ai_enabled=[false,false];s.units.clear()
		var sign: float=1 if side==0 else -1
		var front=s.spawn("unit.mu.guard",side,s.bases[side].x+2*sign)
		var rear=s.spawn("unit.mu.poisoner",side,s.bases[side].x+3*sign)
		var before: String=JSON.stringify([s.units,s.players,s.map.choices])
		var group: Dictionary=Readiness.deployment_group(s,side)
		check(group.supported and group.front_count==1 and group.members.size()==2,"Nearby living same-route bodies form a group")
		check(before==JSON.stringify([s.units,s.players,s.map.choices]),"Group query cannot mutate army, funds or route")
		s.map.advance(rear,15,side)
		check(Readiness.deployment_group(s,side).members.is_empty(),"Far same-route bodies cannot stand in for a nearby formation")
		var p: Dictionary=s.players[side]
		p.ai_unit_plan="unit.mu.medic";p.ai_unit_plan_until=-1;p.gold=110
		p.unlocked.append("unit.mu.medic");p.studied.append("tech.mu.unit.medic")
		s.config["experimental_ai_sequential_deployment"]=true
		s.visibility.refresh();AI.turn(s,side)
		check(not p.queue.has("unit.mu.medic") and not p.queue.is_empty(),"Actual AI cannot bypass dispersed-group gate with full support cash")
		rear.hp=0;p.queue.clear()
		check(Readiness.deployment_group(s,side).members.is_empty(),"Dead body does not complete a group")
		s.spawn("unit.mu.worker",side,front.x+sign)
		check(Readiness.deployment_group(s,side).members.is_empty(),"Workers do not complete a fighting group")
		p.queue.append("unit.mu.poisoner")
		check(Readiness.deployment_group(s,side).members.is_empty(),"Paid but unproduced order is not a living formation")
		var known: String=JSON.stringify(Readiness.deployment_group(s,side))
		var hidden=s.spawn("unit.mu.guard",1-side,s.bases[1-side].x)
		hidden.hp=1
		check(known==JSON.stringify(Readiness.deployment_group(s,side)),"Enemy position or HP cannot influence own formation")
		s.config["enemy_entries"]=[{"edge":front.edge,"s":front.s}]
		check(Readiness.deployment_group(s,side).supported==(side==0),"Custom enemy entries are not falsely given a standard base route")
		s.start({"map":"map.01.04","faction":"mu","enemy":"mu"});s.units.clear()
		for node in s.map.nodes:
			var choices: Array=s.map.outgoing[node] if side==0 else s.map.incoming[node]
			if choices.size()<2:continue
			var selected: String=choices[0];var other: String=choices[1]
			s.map.choices[side][node]=selected
			front=s.spawn("unit.mu.guard",side,s.bases[side].x)
			rear=s.spawn("unit.mu.poisoner",side,s.bases[side].x)
			s.map.apply_anchor(front,s.map.anchor(other,float(s.map.edges[other].length)*.5))
			s.map.apply_anchor(rear,s.map.anchor(other,float(s.map.edges[other].length)*.5+sign))
			group=Readiness.deployment_group(s,side)
			check(group.front_count==0 and group.members.is_empty(),"Opposite branch cannot justify support on selected road")
			s.map.choices[side][node]=other
			check(Readiness.deployment_group(s,side).members.size()==2,"Actual route switch admits the living branch formation")
			break
	print("DEPLOYMENT_GROUP: ",checks," checks; failures=",failures)
	quit(0 if failures.is_empty() else 1)
