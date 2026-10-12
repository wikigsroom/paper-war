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
		s.start({"map":"map.01.01","faction":"mu","enemy":"mu"})
		s.ai_enabled=[false,false]
		var sign: float=1 if side==0 else -1
		var own=s.spawn("unit.mu.guard",side,s.bases[side].x+3*sign)
		own.hp=90
		var enemy=s.spawn("unit.mu.guard",1-side,own.x+sign)
		s.visibility.refresh()
		var node: Dictionary=s.db.tech("tech.mu.unit.medic")
		check(AI.research_arrival_ready(s,side,node,[own]),"Pilot disabled leaves formal research unchanged")
		s.config["experimental_ai_research_arrival"]=true
		check(AI.support_arrival_viable(s,side,"unit.mu.medic",[own]),"Production-only support can arrive for this known front")
		check(not AI.research_arrival_ready(s,side,node,[own]),"Research delay makes the same support too late")
		check(AI.research_arrival_ready(s,side,s.db.tech("tech.mu.unit.warden"),[own]),"Non-healing research not indiscriminately blocked")
		var before: String=JSON.stringify(s.players[side])
		AI.research_arrival_ready(s,side,node,[own])
		check(JSON.stringify(s.players[side])==before,"Screening does not spend resources or change queue")
		s.map.apply_anchor(enemy,s.map.at_node(s.map.definition.bases[1-side].node,1-side));s.visibility.refresh()
		check(AI.research_arrival_ready(s,side,node,[own]),"Hidden enemy cannot veto research")
		enemy.hp=1
		check(AI.research_arrival_ready(s,side,node,[own]),"Hidden health does not affect investment")
	print("RESEARCH_ARRIVAL: ",checks," checks; failures=",failures)
	quit(0 if failures.is_empty() else 1)
