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
	var loaded_simulation: GDScript=Simulation
	var loaded_source_matches: bool=loaded_simulation.get_source_code().replace("\r\n","\n")==FileAccess.get_file_as_string("res://scripts/battle_sim.gd").replace("\r\n","\n")
	var inputs_before: Dictionary={}
	for name in ["battle_sim","unit_abilities","battle_visibility","map_runtime"]:
		var resource: String="res://scripts/"+name+".gd"
		inputs_before[resource]=FileAccess.get_sha256(resource)
		var loaded=load(resource)
		loaded_source_matches=loaded_source_matches and loaded.get_source_code().replace("\r\n","\n")==FileAccess.get_file_as_string(resource).replace("\r\n","\n")
	if not loaded_source_matches:failures.append({"reason":"Loaded source differs from frozen file bytes"})
	var path: String=args[args.find("--baseline")+1]
	var baseline=GDScript.new();baseline.source_code=FileAccess.get_file_as_string(path)
	if baseline.reload()!=OK:quit(1);return
	var cases: Array=[]
	var paired_cpu: Array=[]
	for map_id in ["map.01.01","map.01.04","map.01.11"]:
		var config: Dictionary={"map":map_id,"faction":"yin","enemy":"mu","seed":137,"difficulty":1,"ai_style":"counter","starting_gold":300,"enemy_starting_gold":300,"full_tech":false,"win":"destroy_base"}
		var a=baseline.new(db);var b=Simulation.new(db)
		for s in [a,b]:
			s.start(config);s.ai_enabled=[false,false]
			for side in [0,1]:
				for i in range(60):
					var ids: Array=s.players[side].roster
					var u=s.spawn(ids[i%ids.size()],side,18+float(i%12)*.25+float(side)*7)
					u.hp=100000;u.max_hp=u.hp
			s.visibility.refresh();s.drain_events()
		var equal: bool=true;var steps: int=0
		for tick in range(1200):
			var before: int;var a_us: int;var b_us: int
			if tick%2==0:
				before=Time.get_ticks_usec();a.tick(1.0/60.0);a_us=Time.get_ticks_usec()-before
				before=Time.get_ticks_usec();b.tick(1.0/60.0);b_us=Time.get_ticks_usec()-before
			else:
				before=Time.get_ticks_usec();b.tick(1.0/60.0);b_us=Time.get_ticks_usec()-before
				before=Time.get_ticks_usec();a.tick(1.0/60.0);a_us=Time.get_ticks_usec()-before
			paired_cpu.append({"map":map_id,"tick":tick,"baseline_us":a_us,"candidate_us":b_us})
			checks+=1;steps+=1
			if canonical(a)!=canonical(b):
				equal=false;failures.append({"map":map_id,"tick":tick});break
			a.drain_events();b.drain_events()
		cases.append({"map":map_id,"equal":equal,"steps":steps,"time":b.time,"units":b.units.size()})
		print("CAPACITY_EQUIVALENCE ",map_id," equal=",equal," steps=",steps)
	var output: String=args[args.find("--output")+1]
	var unchanged: bool=true
	for resource in inputs_before:unchanged=unchanged and FileAccess.get_sha256(resource)==inputs_before[resource]
	if not unchanged:failures.append({"reason":"Source changed during complete-state observation"})
	FileAccess.open(output,FileAccess.WRITE).store_string(JSON.stringify({"passed":failures.is_empty(),"checks":checks,"failures":failures,"cases":cases,"paired_cpu":paired_cpu,"loaded_source_matches":loaded_source_matches,"source_unchanged":unchanged,"inputs_before":inputs_before,"baseline_sha256":FileAccess.get_sha256(path),"simulation_sha256":FileAccess.get_sha256("res://scripts/battle_sim.gd"),"observer_sha256":FileAccess.get_sha256(get_script().resource_path),"scope":"Three maps, sustained124-actor Yin/Mu fixture,20 simulation seconds each; exact complete actor/economy/event/projectile/status/RNG/vision state every60Hz step against frozen rc27. Alternating execution order in the same native process gives paired CPU observations; no nested profiler. Fixture with AI disabled and raised HP; not paid gameplay, rendered FPS or Android hardware."},"  "))
	quit(0 if failures.is_empty() else 1)
