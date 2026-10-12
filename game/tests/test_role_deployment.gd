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
		sim.start({"map":"map.01.01","faction":"qi","enemy":"qi","ai_warmup":0})
		sim.ai_enabled=[false,false]
		sim.config["experimental_ai_sequential_deployment"]=true
		sim.config["experimental_ai_role_deployment"]=true
		for id in ["unit.qi.sniper","unit.bai.scribe","unit.shuang.scribe","unit.deng.summoner","unit.bai.illusionist"]:
			check(not AI.requires_deployment_group(sim,side,sim.db.balance.units[id]),"Offensive/control/self-guardian unit does not require an allied pair: "+id)
		for id in ["unit.mu.medic","unit.ji.engineer","unit.mo.priest","unit.deng.illusionist"]:
			check(AI.requires_deployment_group(sim,side,sim.db.balance.units[id]),"Healing/repair/corpse support retains formation condition: "+id)
		var p: Dictionary=sim.players[side]
		var target: String="unit.qi.sniper"
		p.gold=147;p.unlocked.append(target);p.studied.append("tech.qi.unit.sniper");p.ai_unit_plan=target
		sim.spawn("unit.qi.worker",side,sim.bases[side].x)
		sim.visibility.refresh();AI.turn(sim,side)
		check(p.queue==[target] and p.gold==0,"Actual paid offensive deployment does not buy an unrelated escort first")
		check(p.ai_unit_plan==target,"Paid order clears goal on the following ordinary AI turn")
		AI.turn(sim,side)
		check(p.ai_unit_plan=="","Queued deployment releases research commitment")
		sim.config["experimental_ai_role_deployment_side"]=1-side
		check(AI.requires_deployment_group(sim,side,sim.db.balance.units[target]),"Role-only side restriction preserves sequential policy on the other side")
		sim.config.erase("experimental_ai_role_deployment_side")
		sim.config["experimental_ai_sequential_deployment_side"]=1-side
		check(AI.requires_deployment_group(sim,side,sim.db.balance.units[target]),"Role pilot cannot change the other side")
		sim.config.erase("experimental_ai_sequential_deployment_side")
		sim.config["experimental_ai_role_deployment"]=false
		check(AI.requires_deployment_group(sim,side,sim.db.balance.units[target]),"Existing sequential baseline retains its old gate")
	print("ROLE_DEPLOYMENT: ",checks," checks; failures=",failures)
	quit(0 if failures.is_empty() else 1)
