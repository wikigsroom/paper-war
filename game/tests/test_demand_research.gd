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
		var sniper: Dictionary=sim.db.tech("tech.qi.unit.sniper")
		var executioner: Dictionary=sim.db.tech("tech.qi.unit.executioner")
		var enemy=sim.spawn("unit.mo.blade",1-side,sim.bases[1-side].x)
		sim.visibility.refresh()
		check(AI.research_demand_score(sim,side,sniper,[],[enemy])==0,"Hidden melee cannot devalue a shooter")
		check(AI.research_demand_score(sim,side,executioner,[],[enemy])==0,"Hidden melee cannot favor an unlock")
		var scout=sim.spawn("unit.qi.vanguard",side,enemy.x)
		sim.visibility.refresh()
		check(AI.research_demand_score(sim,side,sniper,[scout],[enemy])<0,"Visible basic melee has no support/range counter need")
		check(AI.research_demand_score(sim,side,executioner,[scout],[enemy])>0,"Visible melee pressure favors frontline investment")
		check(AI.choose_research(sim,side,[sniper,executioner],{},[scout],[enemy]).id==sniper.id,"Default order unchanged")
		sim.config["experimental_ai_demand_research"]=true
		check(AI.choose_research(sim,side,[sniper,executioner],{},[scout],[enemy]).id==executioner.id,"Demand pilot chooses relevant formation role")
		check(AI.choose_research(sim,side,[sniper,executioner],{"prefer_units":[sniper.grant]},[scout],[enemy]).id==sniper.id,"Campaign authored counter lesson remains available")
		sim.config["experimental_ai_demand_research_side"]=1-side
		check(AI.choose_research(sim,side,[sniper,executioner],{},[scout],[enemy]).id==sniper.id,"Pilot is confined to requested side")
		enemy.id="unit.mu.medic"
		check(AI.research_demand_score(sim,side,sniper,[scout],[enemy])==0,"True support target retains original counter bonus")
		var medic: Dictionary=sim.db.tech("tech.mu.unit.medic")
		check(AI.research_demand_score(sim,side,medic,[scout],[])<0,"Healthy own formation has no current healing need")
		scout.hp=float(scout.max_hp)*.5
		check(AI.research_demand_score(sim,side,medic,[scout],[])==0,"Living injury removes lack-of-need penalty")
	print("DEMAND_RESEARCH: ",checks," checks; failures=",failures)
	quit(0 if failures.is_empty() else 1)
