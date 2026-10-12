extends SceneTree
const Data=preload("res://scripts/data_store.gd")
const Simulation=preload("res://scripts/battle_sim.gd")
var checks: int=0
var failures: Array=[]
func _initialize():call_deferred("run")
func canonical(s) -> String:
	return JSON.stringify({"time":s.time,"players":s.players,"units":s.units,"buildings":s.buildings,"bases":s.bases,"corpses":s.corpses,"projectiles":s.projectiles,"areas":s.spell_areas,"scheduled":s.scheduled,"events":s.events,"stats":s.stats,"choices":s.map.choices,"winner":s.winner,"vision":s.visibility.current,"explored":s.visibility.explored,"remembered":s.visibility.last_seen,"sim_rng":s.rng.state,"ai_rng":[s.ai_rng[0].state,s.ai_rng[1].state]})
func run():
	var db=Data.new();var args=OS.get_cmdline_user_args()
	var path: String=args[args.find("--baseline")+1]
	var baseline=GDScript.new();baseline.source_code=FileAccess.get_file_as_string(path)
	if baseline.reload()!=OK:quit(1);return
	var cases: Array=[]
	for map_id in ["map.01.01","map.01.04","map.01.11"]:
		for mirror in [false,true]:
			var a=baseline.new(db);var b=Simulation.new(db)
			var config: Dictionary={"map":map_id,"faction":"mu" if mirror else "yin","enemy":"yin" if mirror else "mu","seed":137,"difficulty":1,"ai_style":"counter","starting_gold":300,"enemy_starting_gold":300,"full_tech":false,"win":"destroy_base"}
			for s in [a,b]:s.start(config);s.ai_enabled=[true,true];s.ai_clock[1]=4
			var equal: bool=true;var steps: int=0
			for i in range(240*60):
				a.tick(1.0/60.0);b.tick(1.0/60.0);checks+=1;steps+=1
				if canonical(a)!=canonical(b):
					equal=false;failures.append({"map":map_id,"mirror":mirror,"tick":i});break
				a.drain_events();b.drain_events()
				if a.winner!=-2:break
			cases.append({"map":map_id,"mirror":mirror,"equal":equal,"steps":steps,"time":b.time,"winner":b.winner})
			print("PAID_RUNTIME_CASE ",map_id," mirror=",mirror," equal=",equal," steps=",steps)
	var output: String=args[args.find("--output")+1]
	FileAccess.open(output,FileAccess.WRITE).store_string(JSON.stringify({"passed":failures.is_empty(),"checks":checks,"failures":failures,"cases":cases,"baseline_sha256":FileAccess.get_sha256(path),"simulation_sha256":FileAccess.get_sha256("res://scripts/battle_sim.gd"),"observer_sha256":FileAccess.get_sha256(get_script().resource_path),"scope":"Exact state, fog authority, events, economy and random streams every60Hz step. Six native CPU normal300-gold locked-tech paid AI cases, three maps and mirrored Yin/Mu,4s enemy warmup, up to240 simulation seconds. Not rendered FPS or global balance."},"  "))
	print("PAID_RUNTIME_EQUIVALENCE: ",checks," checks; failures=",failures)
	quit(0 if failures.is_empty() else 1)
