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
		s.start({"map":"map.01.01","faction":"mu","enemy":"mu","starting_gold":1000,"enemy_starting_gold":1000,"full_tech":false,"ai_warmup":0})
		s.ai_enabled=[false,false]
		check(s.request(side,"research",{"id":"tech.mu.unit.medic"}).ok,"Deployment requires real research payment")
		for step in range(301):s.tick(1.0/60.0)
		var allies: Array=[]
		for index in range(3):allies.append(s.spawn("unit.mu.guard",side,float(s.bases[side].x)+(1+index*.6)*(1 if side==0 else -1)))
		check(AI.research_deployment_target(s,side,allies,{})=="unit.mu.medic","Completed research identifies missing support")
		check(AI.research_deployment_target(s,side,allies,{"prefer_units":["unit.mu.phoenix"]})=="","Prerequisite deployment cannot block explicit campaign target")
		s.config["experimental_ai_research_deployment"]=true;s.players[side].gold=110
		s.visibility.refresh();AI.turn(s,side)
		check(s.players[side].queue==["unit.mu.medic"] and s.players[side].gold==0,"Real first deployment pays full unit cost before optional worker")
		check(AI.research_deployment_target(s,side,allies,{})=="","Queued support prevents duplicate budget commitment")
		check(AI.research_deployment_target(s,side,[],{})=="","Missing screen never commits to advanced support")
		s.players[side].queue.clear();s.players[side].production=0
		for ally in allies:ally.hp=5
		var enemy=s.spawn("unit.mu.guard",1-side,float(allies[0].x)+(1 if side==0 else -1))
		s.visibility.refresh()
		check(not AI.support_arrival_viable(s,side,"unit.mu.medic",allies),"Known nearby damage rejects late support for collapsing screen")
		s.map.apply_anchor(enemy,s.map.at_node(s.map.definition.bases[1-side].node,1-side));s.visibility.refresh()
		check(AI.support_arrival_viable(s,side,"unit.mu.medic",allies),"Hidden remote enemy does not count as known pressure")
		enemy.hp=1
		check(AI.support_arrival_viable(s,side,"unit.mu.medic",allies),"Hidden health changes cannot alter support estimate")
	print("AI_RESEARCH_DEPLOYMENT: ",checks," checks; failures=",failures)
	quit(0 if failures.is_empty() else 1)
