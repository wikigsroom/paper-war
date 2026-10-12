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
		var siege: Dictionary=sim.db.tech("tech.qi.unit.siege")
		var enemy=sim.spawn("unit.mu.medic",1-side,sim.bases[1-side].x)
		sim.visibility.refresh()
		check(not sim.visible_to(side,enemy),"Enemy-base support remains hidden")
		check(AI.research_context_score(sim,side,sniper,[],[enemy])==0,"Hidden support cannot affect research")
		var scout=sim.spawn("unit.qi.vanguard",side,enemy.x)
		sim.visibility.refresh()
		check(sim.visible_to(side,enemy),"Actual scout reveals target")
		check(AI.research_context_score(sim,side,sniper,[scout],[enemy])>0,"Visible real support benefits sniper research")
		check(AI.choose_research(sim,side,[siege,sniper],{},[scout],[enemy]).id==siege.id,"Default policy preserves stable ordering")
		sim.config["experimental_ai_context_research"]=true
		check(AI.choose_research(sim,side,[siege,sniper],{},[scout],[enemy]).id==sniper.id,"Pilot prioritizes actual counter")
		sim.config["experimental_ai_context_research_side"]=1-side
		check(AI.choose_research(sim,side,[siege,sniper],{},[scout],[enemy]).id==siege.id,"Other side remains unchanged")
		sim.config.erase("experimental_ai_context_research_side")
		check(AI.choose_research(sim,side,[siege,sniper],{"prefer_units":[siege.grant]},[scout],[enemy]).id==siege.id,"Authored teaching intent stays above contextual tie-breaking")
		enemy.id="unit.qi.javelin"
		check(AI.research_context_score(sim,side,sniper,[scout],[enemy])==0,"Ordinary ranged unit is not confused with support")
		var lancer: Dictionary=sim.db.tech("tech.yuan.unit.lancer")
		check(AI.research_context_score(sim,side,lancer,[scout],[enemy])>0,"Real anti-fast multiplier uses the same 1.2 threshold as combat")
		enemy.id="unit.qi.sniper"
		check(AI.research_context_score(sim,side,lancer,[scout],[enemy])==0,"Slow target does not manufacture anti-fast benefit")
		var medic: Dictionary=sim.db.tech("tech.mu.unit.medic")
		check(AI.research_context_score(sim,side,medic,[scout],[])==0,"Healthy formation has no fabricated healing need")
		scout.hp=float(scout.max_hp)*.5
		check(AI.research_context_score(sim,side,medic,[scout],[])>0,"Actual living injury contributes healing need")
		scout.hp=0
		check(AI.research_context_score(sim,side,medic,[scout],[])==0,"Dead actor does not justify healing research")
	check(failures.is_empty(),"Both sides completed visibility and choice boundaries")
	print("CONTEXT_RESEARCH: ",checks," checks; failures=",failures)
	quit(0 if failures.is_empty() else 1)
