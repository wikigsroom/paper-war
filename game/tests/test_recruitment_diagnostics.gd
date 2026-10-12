extends SceneTree
const Data=preload("res://scripts/data_store.gd")
const Simulation=preload("res://scripts/battle_sim.gd")
var checks: int=0
var failures: Array=[]
func check(ok: bool,note: String):
	checks+=1
	if not ok:failures.append(note)
func _initialize():call_deferred("run")
func run():
	var plain=Simulation.new(Data.new())
	var observed=Simulation.new(Data.new())
	var config: Dictionary={"map":"map.01.04","faction":"qi","enemy":"bai","starting_gold":300,"enemy_starting_gold":300,"ai_warmup":0,"full_tech":false,"seed":137}
	plain.start(config.duplicate(true));observed.start(config.duplicate(true))
	plain.ai_enabled=[true,true];observed.ai_enabled=[true,true]
	observed.config["observe_ai_recruitment"]=true
	var plain_events: Array=[];var observed_events: Array=[]
	for step in range(1800):
		plain.tick(1.0/60.0);observed.tick(1.0/60.0)
		plain_events.append_array(plain.drain_events());observed_events.append_array(observed.drain_events())
		if step%60==59:
			check(JSON.stringify([plain.players,plain.units,plain.bases,plain.stats,plain.winner])==JSON.stringify([observed.players,observed.units,observed.bases,observed.stats,observed.winner]),"Paid world unchanged at step "+str(step))
			check(plain.ai_rng[0].state==observed.ai_rng[0].state and plain.ai_rng[1].state==observed.ai_rng[1].state,"Diagnostic consumes no AI random draws")
			check(JSON.stringify(plain_events)==JSON.stringify(observed_events),"Commands and combat events identical")
			plain_events.clear();observed_events.clear()
	check(not observed.config.get("ai_recruitment_trace",[]).is_empty(),"Opt-in diagnostic actually recorded decisions")
	check(not plain.config.has("ai_recruitment_trace"),"Ordinary match does not allocate diagnostic trace")
	print("RECRUITMENT_DIAGNOSTICS: ",checks," checks; failures=",failures)
	quit(0 if failures.is_empty() else 1)
