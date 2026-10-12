extends SceneTree
const App=preload("res://scripts/main.gd")
func _initialize():call_deferred("run")
func run():
	var args=OS.get_cmdline_user_args()
	var folder: String=args[args.find("--output")+1]
	DirAccess.make_dir_recursive_absolute(folder)
	var app=App.new();root.add_child(app);app.set_process(false)
	app.audio.silent=true;app.audio.set_background(true)
	app.mode="skirmish"
	app.start_battle({"title":"守矿告警 · 受控验收","map":"map.01.01","faction":"yin","enemy":"mo","full_tech":true,"starting_gold":300})
	app.sim.ai_enabled=[false,false];app.accumulator=-100000
	var worker=app.sim.spawn("unit.yin.worker",0,20)
	app.view.follow_front=false;app.view.camera_x=32;app.view.target_camera=32
	app.sim.visibility.refresh();app.sim.drain_events();app.sim.damage(worker,1,1,false)
	app._process(.016);app.update_hud()
	await process_frame;await process_frame;await RenderingServer.frame_post_draw
	var image=root.get_texture().get_image()
	var saved: Error=image.save_png(folder+"/alarm.png")
	var passed: bool=saved==OK and app.toast_text.contains("纸工遇袭") and app.status_label.text.contains("纸工遇袭") and not app.view.economy_warning.is_empty() and app.view.target_camera>25
	var exported: bool=OS.get_executable_path().get_file()=="PaperWarfront.exe"
	var report={"scope":"Actual exported Windows EXE using external controlled QA fixture; not Android hardware." if exported else "Windows native GPU source-project controlled real worker damage; mobile metrics injected, not exported executable or Android hardware.","executable":OS.get_executable_path(),"version":ProjectSettings.get_setting("application/config/version"),"passed":passed,"mobile":app.mobile_ui,"physical_size":[image.get_width(),image.get_height()],"toast":app.toast_text,"warning":app.view.economy_warning,"camera":app.view.target_camera,"inputs":{}}
	for path in ["res://scripts/main.gd","res://scripts/battle_sim.gd","res://scripts/battle_view.gd","res://scripts/audio_controller.gd","res://scripts/match_projection.gd","res://scripts/local_duel.gd","res://scripts/lan_session.gd","res://tests/economy_alarm_ui_qa.gd"]:
		if FileAccess.file_exists(path):report.inputs[path]=FileAccess.get_sha256(path)
	FileAccess.open(folder+"/report.json",FileAccess.WRITE).store_string(JSON.stringify(report,"  "))
	print("ECONOMY_ALARM_UI ",passed);quit(0 if passed else 1)
