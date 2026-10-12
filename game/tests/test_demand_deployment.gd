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
		var sim=Simulation.new(Data.new())
		sim.start({"map":"map.01.01","faction":"qi","enemy":"qi","ai_warmup":0,"ai_style":"rush","player_ai_style":"rush"})
		sim.ai_enabled=[false,false]
		var direction: float=1.0 if side==0 else -1.0
		var x: float=float(sim.bases[side].x)+direction*15
		var front=sim.spawn("unit.qi.vanguard",side,x)
		var back=sim.spawn("unit.qi.javelin",side,x-direction*2)
		var enemy=sim.spawn("unit.mo.blade",1-side,x+direction*2)
		sim.visibility.refresh()
		var p: Dictionary=sim.players[side]
		var id: String="unit.qi.executioner"
		check(AI.research_demand_deployment_target(sim,side,[front,back],[enemy])=="","No free research or unlock")
		p.studied.append("tech.qi.unit.executioner");p.unlocked.append(id)
		check(AI.research_demand_deployment_target(sim,side,[front,back],[enemy])==id,"Completed frontline counter has current visible need")
		check(AI.research_demand_deployment_target(sim,side,[front,back],[])=="","No enemy need releases frontline investment")
		check(AI.research_demand_deployment_target(sim,side,[back],[enemy])=="","Missing own screen releases saving")
		p.queue.append(id)
		check(AI.research_demand_deployment_target(sim,side,[front,back],[enemy])=="","Paid queue satisfies first deployment")
		p.queue.clear()
		check(AI.resolve_demand_deployment(sim,side,[front,back],[enemy],false)==id,"Visible need starts finite investment intent")
		sim.time=6
		check(AI.resolve_demand_deployment(sim,side,[front,back],[],false)==id,"Brief loss of vision does not restart budget")
		sim.time=12.01
		check(AI.resolve_demand_deployment(sim,side,[front,back],[],false)=="","Unseen counter intent expires after twelve seconds")
		sim.time=20
		check(AI.resolve_demand_deployment(sim,side,[front,back],[enemy],false)==id,"New actual sighting can restart finite intent")
		check(AI.resolve_demand_deployment(sim,side,[front,back],[],true)=="","Emergency cancels memory and releases defense funds")
		p.queue.append(id)
		check(AI.resolve_demand_deployment(sim,side,[front,back],[enemy],false)=="","Paid queue cannot create another memory goal")
		p.queue.clear()
		p.gold=127;p.ai_build_reserve=120;p.ai_research="tech.qi.unit.sniper"
		sim.config["experimental_ai_demand_deployment"]=true
		AI.turn(sim,side)
		check(p.queue==[id] and p.gold==0,"Exactly 127 paid through original recruit command")
		check(p.ai_research=="" and p.ai_build_reserve==0,"Next research and stale nonurgent building budget do not steal first order")
		var soldier=sim.spawn(id,side,x)
		p.queue.clear()
		check(AI.research_demand_deployment_target(sim,side,[front,back,soldier],[enemy])=="","Living researched soldier satisfies goal")
	print("DEMAND_DEPLOYMENT: ",checks," checks; failures=",failures)
	quit(0 if failures.is_empty() else 1)
