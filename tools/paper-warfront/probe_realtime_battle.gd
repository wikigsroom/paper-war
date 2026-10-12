extends SceneTree
# Actual App._process advances the battle. This observer never ticks simulation.
const App = preload("res://scripts/main.gd")
class MeasuredView:
	extends "res://scripts/battle_view.gd"
	var observation_draw_us: int=0
	var observation_event_us: int=0
	func _draw():
		var before: int=Time.get_ticks_usec()
		super._draw()
		observation_draw_us=Time.get_ticks_usec()-before
	func on_event(event: Dictionary):
		var before: int=Time.get_ticks_usec()
		super.on_event(event)
		observation_event_us+=Time.get_ticks_usec()-before
class MeasuredApp:
	extends "res://scripts/main.gd"
	var observation_process_us: int = 0
	var observation_steps: int=0
	func _ready():
		super._ready()
		var prior=view
		var measured=MeasuredView.new()
		add_child(measured)
		for property in prior.get_property_list():
			if int(property.usage)&PROPERTY_USAGE_SCRIPT_VARIABLE:measured.set(property.name,prior.get(property.name))
		measured.transform=prior.transform
		view=measured;remove_child(prior);prior.queue_free()
	func _process(delta):
		var before: int = Time.get_ticks_usec()
		var tick_before: int=0 if sim==null else sim.tick_count
		view.observation_event_us=0
		super._process(delta)
		observation_process_us = Time.get_ticks_usec()-before
		observation_steps=(0 if sim==null else sim.tick_count)-tick_before
var app
var folder: String
var frames: Array = []
var snapshots: Array = []
var captures: Array = []
var capture_windows: Array = []

func _initialize():call_deferred("run")

func argument(name_value: String, fallback: String) -> String:
	var args = OS.get_cmdline_user_args()
	return args[args.find(name_value)+1] if args.has(name_value) else fallback

func distribution(values: Array) -> Dictionary:
	if values.is_empty():return {}
	values.sort()
	var total: float = 0
	for value in values:total += float(value)
	return {"samples":values.size(),"mean_ms":total/values.size(),"p50_ms":values[int(values.size()*.5)],
		"p95_ms":values[mini(values.size()-1,int(values.size()*.95))],
		"p99_ms":values[mini(values.size()-1,int(values.size()*.99))],"max_ms":values[-1]}

func capture(name_value: String, wall: float):
	var before: int = Time.get_ticks_usec()
	await RenderingServer.frame_post_draw
	var path: String = folder+"/"+name_value+".png"
	var error: int = root.get_texture().get_image().save_png(path)
	captures.append({"path":path,"sha256":FileAccess.get_sha256(path),"error":error,
		"wall_seconds":wall,"simulation_seconds":app.sim.time,"camera_x":app.view.camera_x})
	capture_windows.append(Vector2(float(before),float(Time.get_ticks_usec()+500000)))

func run():
	folder = argument("--output","")
	if folder.is_empty() or FileAccess.file_exists(folder+"/report.json"):quit(2);return
	DirAccess.make_dir_recursive_absolute(folder)
	var duration: float = float(argument("--duration","160"))
	var capture_interval: float = maxf(0.0,float(argument("--capture-interval","0")))
	app = MeasuredApp.new();root.add_child(app)
	await process_frame;await process_frame;await process_frame
	app.mode = "skirmish"
	app.start_battle({"title":"遭遇战","map":argument("--map","map.01.04"),
		"faction":argument("--west","yin"),"enemy":argument("--east","mu"),"seed":137,
		"difficulty":1,"ai_style":"counter","starting_gold":300,"enemy_starting_gold":300,
		"full_tech":false,"win":"destroy_base"})
	app.sim.ai_enabled = [true,true]
	var stress: bool = OS.get_cmdline_user_args().has("--stress-120")
	if stress:
		# Deliberate capacity fixture, distinct from normal paid gameplay evidence.
		app.sim.ai_enabled = [false,false]
		for side in [0,1]:
			for i in range(60):
				var ids: Array = app.sim.players[side].roster
				var actor = app.sim.spawn(ids[i%ids.size()],side,18+float(i%12)*.25+side*7)
				actor.hp=100000;actor.max_hp=actor.hp
		app.sim.visibility.refresh()
	app.view.follow_front = true
	# A recorded 60/30 FPS cap is an observation setting, not a shipping rule.
	Engine.max_fps = int(argument("--fps-cap","60"))
	var started: int = Time.get_ticks_usec()
	var last: int = started
	var next_snapshot: float = 0
	var next_capture: float = capture_interval if capture_interval>0.0 else minf(90,duration*.5)
	while float(Time.get_ticks_usec()-started)/1000000.0 < duration:
		await process_frame
		var now: int = Time.get_ticks_usec()
		var wall: float = float(now-started)/1000000.0
		frames.append([now,wall,float(now-last)/1000.0,float(app.observation_process_us)/1000.0,
			app.sim.time,app.sim.units.size(),app.sim.projectiles.size(),app.view.particles.size(),
			app.db.textures.size(),Performance.get_monitor(Performance.RENDER_TOTAL_DRAW_CALLS_IN_FRAME),
			app.observation_steps,float(app.view.observation_draw_us)/1000.0,float(app.view.observation_event_us)/1000.0])
		last = now
		if wall >= next_snapshot:
			next_snapshot = floorf(wall)+1
			var atlases: Array = []
			for path in app.db.textures:
				if str(path).begins_with("res://assets/animation/frames-v1/") and str(path).ends_with("-atlas.png"):atlases.append(path)
			snapshots.append({"wall_seconds":wall,"simulation_seconds":app.sim.time,"screen":app.screen,
				"units":app.sim.units.size(),"living_units":app.sim.units.filter(func(u):return u.hp>0).size(),
				"projectiles":app.sim.projectiles.size(),"particles":app.view.particles.size(),"effects":app.view.effects.size(),
				"texture_count":app.db.textures.size(),"unit_atlases":atlases,"engine_fps":Performance.get_monitor(Performance.TIME_FPS),
				"texture_bytes":Performance.get_monitor(Performance.RENDER_TEXTURE_MEM_USED),
				"buffer_bytes":Performance.get_monitor(Performance.RENDER_BUFFER_MEM_USED),
				"engine_process_peak_ms":Performance.get_monitor(Performance.TIME_PROCESS)*1000,
				"layer_cpu_us":app.view.get("layer_cpu_us").duplicate(true) if app.view.get("layer_cpu_us") is Dictionary else null,
				"static_memory_bytes":Performance.get_monitor(Performance.MEMORY_STATIC),
				"render_objects":Performance.get_monitor(Performance.RENDER_TOTAL_OBJECTS_IN_FRAME),
				"render_draw_calls":Performance.get_monitor(Performance.RENDER_TOTAL_DRAW_CALLS_IN_FRAME),
				"stats":app.sim.stats.duplicate(true),"bases":app.sim.bases.duplicate(true)})
		if wall >= next_capture:
			if capture_interval>0.0:
				next_capture += capture_interval
				if next_capture>=duration:next_capture=INF
			else:
				next_capture = duration-1 if captures.is_empty() else INF
			await capture("%02d-battle"%(captures.size()+1),wall)
		if app.sim.winner != -2:break
	var all_intervals: Array = []
	var stable_intervals: Array = []
	var cpu: Array = []
	var drawing: Array=[]
	var events: Array=[]
	var csv = FileAccess.open(folder+"/frames.csv",FileAccess.WRITE)
	csv.store_csv_line(PackedStringArray(["wall_seconds","frame_ms","app_process_ms","simulation_seconds","units","projectiles","particles","texture_count","draw_calls","simulation_steps","draw_callback_ms","visual_event_ms","capture_excluded"]))
	for frame in frames:
		var excluded: bool = capture_windows.any(func(span):return float(frame[0])>=span.x and float(frame[0])<=span.y)
		all_intervals.append(frame[2])
		if frame[1]>=2 and not excluded:stable_intervals.append(frame[2]);cpu.append(frame[3]);drawing.append(frame[11]);events.append(frame[12])
		var row = PackedStringArray()
		for i in range(1,frame.size()):row.append(str(frame[i]))
		row.append(str(excluded));csv.store_csv_line(row)
	csv.close()
	var inputs: Dictionary = {}
	for name_value in ["main","battle_sim","battle_view","data_store","tactical_ai","battle_visibility","theatre_fog","theatre_ground","theatre_ground_cache","unit_frame_player","audio_controller"]:
		var path: String = "res://scripts/"+name_value+(".gd" if FileAccess.file_exists("res://scripts/"+name_value+".gd") else ".gdc")
		if FileAccess.file_exists(path):inputs[path] = FileAccess.get_sha256(path)
	var report: Dictionary = {"passed":not frames.is_empty() and captures.all(func(c):return c.error==OK),
		"version":ProjectSettings.get_setting("application/config/version"),"inputs":inputs,
		"observer_sha256":FileAccess.get_sha256(get_script().resource_path),"frames_sha256":FileAccess.get_sha256(folder+"/frames.csv"),
		"config":app.sim.config,"wall_seconds":float(Time.get_ticks_usec()-started)/1000000.0,
		"simulation_seconds":app.sim.time,"winner":app.sim.winner,"fps_cap":Engine.max_fps,
		"vsync":DisplayServer.window_get_vsync_mode(),"renderer":RenderingServer.get_current_rendering_method(),
		"video_adapter":RenderingServer.get_video_adapter_name(),"window_size":root.size,
		"window_visible":root.visible,"window_mode":root.mode,"mobile_ui":app.mobile_ui,
		"capacity_fixture":stress,
		"audio_silent":app.audio.silent,"audio_background":app.audio.background,"audio_settings":app.audio.settings,
		"intervals_all":distribution(all_intervals),"intervals_steady":distribution(stable_intervals),"app_process_steady":distribution(cpu),
		"draw_callback_steady":distribution(drawing),"visual_event_steady":distribution(events),
		"snapshots":snapshots,"captures":captures,"final_stats":app.sim.stats,
		"monitor_scope":"Observer subclasses time the real inherited App._process, View._draw and View.on_event. MeasuredView copies the original script variables and transform before the battle starts; gameplay/rendering superclass methods come from the selected source project or compiled pack. App processing excludes draw callbacks, the audio child and engine work. Draw timing measures CPU command submission, not GPU execution. Godot4.7 TIME_PROCESS is the previous reporting interval's maximum, updated roughly once per second; retained only as a peak snapshot, never per-frame CPU samples. Release static-memory monitor may be zero.",
		"scope":"Native Windows actual App._process, recorded 60/30FPS observation cap and owned-front camera. No manual simulation ticks. Normal mode uses ordinary300-gold locked-tech rules and enemy warmup4, with west as an explicit AI autoplayer. capacity_fixture=true instead disables AI, directly places60 combat actors per side and assigns100000HP to sustain load; it is stress evidence, never paid normal gameplay or balance evidence. Real monotonic-clock frame samples exclude first2 seconds and PNG readback plus0.5 seconds for steady metrics. Phone injection is Windows GPU evidence, not Android hardware. Observer and1Hz bookkeeping overhead remain included."}
	FileAccess.open(folder+"/report.json",FileAccess.WRITE).store_string(JSON.stringify(report,"  "))
	print("REALTIME_BATTLE ",report.passed," wall=",report.wall_seconds," sim=",report.simulation_seconds,
		" frame_ms=",report.intervals_steady," app_ms=",report.app_process_steady)
	quit(0 if report.passed else 1)
