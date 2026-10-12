extends SceneTree
const Data=preload("res://scripts/data_store.gd")
const Profiler=preload("res://tests/capacity_cpu_profiler.gd")
var samples: Array=[]
func _initialize():call_deferred("run")
func run():
	var db=Data.new();var s=Profiler.new(db)
	s.start(JSON.parse_string(FileAccess.get_file_as_string("res://capacity-config.json")))
	s.ai_enabled=[false,false]
	for side in [0,1]:
		for i in range(60):
			var ids: Array=s.players[side].roster
			var u=s.spawn(ids[i%ids.size()],side,18+float(i%12)*.25+float(side)*7)
			u.hp=100000;u.max_hp=u.hp
	s.visibility.refresh();s.drain_events()
	for segment in range(10):
		s.timings.clear();var before: int=Time.get_ticks_usec()
		for step in range(120):s.tick(1.0/60.0);s.drain_events()
		samples.append({"simulation_seconds":s.time,"ticks":120,"total_us":Time.get_ticks_usec()-before,"timings":s.timings.duplicate(true),"units":s.units.size(),"projectiles":s.projectiles.size(),"statuses":s.units.reduce(func(count,u):return count+u.statuses.size(),0)})
		print("CAPACITY_CPU at=",s.time," ms_per_step=",float(samples[-1].total_us)/120000.0)
	var inputs: Dictionary={}
	for directory in ["scripts","data","tests"]:
		for file in DirAccess.get_files_at("res://"+directory):
			if file.ends_with(".gd") or file.ends_with(".json"):inputs[directory+"/"+file]=FileAccess.get_sha256("res://"+directory+"/"+file)
	var output: String=OS.get_cmdline_user_args()[0]
	FileAccess.open(output,FileAccess.WRITE).store_string(JSON.stringify({"config":s.config,"samples":samples,"inputs":inputs,"observer_sha256":FileAccess.get_sha256(get_script().resource_path),"scope":"Native headless diagnostic with the real-time124-actor Yin/Mu configuration. Ten2-second windows of sustained combat; instrumentation is nested/cumulative. Not FPS, normal paid gameplay or Android hardware."},"  "))
	quit()
