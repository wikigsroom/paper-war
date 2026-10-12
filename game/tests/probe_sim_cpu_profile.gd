extends SceneTree
const Data=preload("res://scripts/data_store.gd")
const Profiler=preload("res://tests/sim_cpu_profiler.gd")
func _initialize():call_deferred("run")
func run():
	var db=Data.new();var s=Profiler.new(db)
	s.start({"map":"map.01.04","faction":"yin","enemy":"mo","full_tech":true})
	s.units.clear();s.ai_enabled=[false,false]
	for side in [0,1]:
		for i in range(60):
			var ids: Array=s.players[side].roster
			var u=s.spawn(ids[i%ids.size()],side,18+float(i%12)*.25+side*7)
			u.hp=100000;u.max_hp=u.hp
	s.visibility.refresh();s.timings.clear()
	var t=Time.get_ticks_usec()
	for i in range(120):s.tick(1.0/60.0)
	var report={"scope":"Instrumented native headless 120-unit CPU diagnosis. Timings are nested/cumulative and include instrumentation overhead; not rendered FPS or Android hardware evidence.","samples":120,"total_us":Time.get_ticks_usec()-t,"timings":s.timings,"inputs":{}}
	for path in ["res://scripts/battle_sim.gd","res://scripts/unit_abilities.gd","res://scripts/map_runtime.gd","res://scripts/battle_visibility.gd","res://data/balance-prototype.json","res://tests/sim_cpu_profiler.gd","res://tests/probe_sim_cpu_profile.gd"]:report.inputs[path]=FileAccess.get_sha256(path)
	var file=FileAccess.open(OS.get_cmdline_user_args()[0],FileAccess.WRITE)
	if file==null:push_error("Cannot write CPU profile");quit(1);return
	file.store_string(JSON.stringify(report,"  "));print(JSON.stringify(report));quit()
