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
		var x: float=float(sim.bases[side].x)+direction*15.0
		var front=sim.spawn("unit.qi.vanguard",side,x)
		var back=sim.spawn("unit.qi.javelin",side,x-direction*2.0)
		var enemy=sim.spawn("unit.bai.scribe",1-side,x+direction*2.0)
		sim.visibility.refresh()
		var p: Dictionary=sim.players[side]
		var id: String="unit.qi.sniper"
		check(AI.visible_counter_deployment_target(sim,side,[front,back],[enemy])=="","Uncompleted research cannot create deployment")
		p.studied.append("tech.qi.unit.sniper");p.unlocked.append(id)
		check(AI.visible_counter_deployment_target(sim,side,[front,back],[enemy])==id,"Visible support permits paid counter saving")
		var hidden=sim.spawn("unit.bai.scribe",1-side,sim.bases[1-side].x)
		sim.visibility.refresh()
		check(not sim.visible_to(side,hidden) and AI.visible_counter_deployment_target(sim,side,[front,back],[hidden])=="","Hidden enemy cannot trigger a paid counter goal")
		back.hp=0
		check(AI.visible_counter_deployment_target(sim,side,[front,back],[enemy])=="","Dead ally cannot manufacture formation")
		back.hp=back.max_hp
		var worker=sim.spawn("unit.qi.worker",side,x)
		check(AI.visible_counter_deployment_target(sim,side,[front,worker],[enemy])=="","Economic unit cannot manufacture fighting formation")
		p.roster.erase(id)
		check(AI.visible_counter_deployment_target(sim,side,[front,back],[enemy])=="","Restricted roster stays authoritative")
		p.roster.append(id)
		check(AI.visible_counter_deployment_target(sim,side,[back],[enemy])=="","Missing screen does not suppress recovery")
		check(AI.visible_counter_deployment_target(sim,side,[front], [enemy])=="","One body is not a two-soldier formation")
		check(AI.visible_counter_deployment_target(sim,side,[front,back],[])=="","No visible need releases saving")
		enemy.id="unit.qi.javelin"
		check(AI.visible_counter_deployment_target(sim,side,[front,back],[enemy])==id,"Actual range advantage is a separate counter need")
		enemy.id="unit.qi.vanguard"
		check(AI.visible_counter_deployment_target(sim,side,[front,back],[enemy])=="","Generic melee enemy does not force expensive shooter")
		enemy.id="unit.bai.scribe"
		p.queue.append(id)
		check(AI.visible_counter_deployment_target(sim,side,[front,back],[enemy])=="","Paid queued counter releases goal")
		p.queue.clear()
		p.gold=147;p.ai_research="tech.qi.unit.executioner"
		sim.config["experimental_ai_visible_counter_deployment"]=true
		AI.turn(sim,side)
		check(p.queue==[id] and p.gold==0,"Actual normal request pays full 147 and queues exactly one counter")
		check(p.ai_research=="" and p.research.is_empty(),"First counter order takes precedence over unrelated next research")
	print("VISIBLE_COUNTER_DEPLOYMENT: ",checks," checks; failures=",failures)
	quit(0 if failures.is_empty() else 1)
