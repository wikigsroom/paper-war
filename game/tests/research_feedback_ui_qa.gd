extends SceneTree
const App=preload("res://scripts/main.gd")
func _initialize():call_deferred("run")
func run():
	var args=OS.get_cmdline_user_args();var folder: String=args[args.find("--output")+1]
	DirAccess.make_dir_recursive_absolute(folder)
	var app=App.new();root.add_child(app);app.set_process(false)
	app.audio.silent=true;app.audio.set_background(true);app.mode="skirmish"
	app.start_battle({"title":"白签研究回法 · 受控验收","map":"map.01.01","faction":"bai","enemy":"mo","full_tech":false,"starting_gold":300})
	app.sim.ai_enabled=[false,false];app.accumulator=-100000;app.sim.drain_events()
	var paid: Dictionary=app.sim.request(0,"research",{"id":"tech.bai.unit.scribe"})
	for i in range(301):app.sim.tick(1.0/60.0)
	app._process(.016);app.update_hud()
	await process_frame;await process_frame;await RenderingServer.frame_post_draw
	var image=root.get_texture().get_image();var err: Error=image.save_png(folder+"/research.png")
	var passed: bool=paid.ok and err==OK and app.toast_text.contains("研究回法 +8") and app.status_label.text.contains("研究回法 +8") and app.sim.players[0].unlocked.has("unit.bai.scribe")
	var report={"scope":"Native Windows GPU source-project paid five-second research and ordinary completion UI; injected mobile metrics if requested. Unshipped source, not rc9 executable or Android hardware.","passed":passed,"mobile":app.mobile_ui,"toast":app.toast_text,"mana":app.sim.players[0].mana,"inputs":{}}
	for path in ["res://scripts/main.gd","res://scripts/data_store.gd","res://scripts/battle_sim.gd","res://scripts/local_duel.gd","res://scripts/match_projection.gd","res://tests/research_feedback_ui_qa.gd"]:report.inputs[path]=FileAccess.get_sha256(path)
	FileAccess.open(folder+"/report.json",FileAccess.WRITE).store_string(JSON.stringify(report,"  "))
	print("RESEARCH_FEEDBACK_UI ",passed);quit(0 if passed else 1)
