extends SceneTree
const App=preload("res://scripts/main.gd")
func _initialize():call_deferred("run")
func run():
	var args=OS.get_cmdline_user_args();var folder: String=args[args.find("--output")+1]
	DirAccess.make_dir_recursive_absolute(folder)
	var app=App.new();root.add_child(app);app.set_process(false)
	app.audio.silent=true;app.audio.set_background(true);app.mode="skirmish"
	app.start_battle({"title":"纸商混编 · 受控验收","map":"map.01.01","faction":"yuan","enemy":"yin","full_tech":true,"starting_gold":300})
	app.sim.ai_enabled=[false,false];app.accumulator=-100000;app.sim.units.clear();app.sim.buildings.clear();app.sim.drain_events()
	var target=app.sim.spawn("unit.yin.axe",1,20)
	target.hp=10000;target.max_hp=10000;target.cooldown=1000;target.special_cd=1000;target.speed_override=0
	var front=app.sim.spawn("unit.yuan.vanguard",0,19.3)
	front.cooldown=1000;front.special_cd=1000;front.speed_override=0
	var cannon=app.sim.spawn("unit.yuan.artillery",0,13)
	var archer=app.sim.spawn("unit.yuan.archer",0,12.2)
	var releases: Dictionary={};var hits: Dictionary={}
	for i in range(12*60):
		app.sim.tick(1.0/60.0)
		for e in app.sim.drain_events():
			if e.kind=="attack":releases[e.uid]=int(releases.get(e.uid,0))+1
			if e.kind=="hit":hits[e.get("source_uid",0)]=int(hits.get(e.get("source_uid",0),0))+1
	app.view.follow_front=false;app.view.camera_x=17;app.view.target_camera=17
	app._process(.016);app.update_hud();app.view.queue_redraw()
	await process_frame;await process_frame;await RenderingServer.frame_post_draw
	var err: Error=root.get_texture().get_image().save_png(folder+"/mixed.png")
	var members: Array=[];var passed: bool=err==OK
	for member in [cannon,archer]:
		members.append({"id":member.id,"releases":int(releases.get(member.uid,0)),"hits":int(hits.get(member.uid,0)),"distance":app.sim.combat_distance(member,target,app.db.balance.units[member.id])})
		passed=passed and int(releases.get(member.uid,0))>=3 and int(hits.get(member.uid,0))>0
	var report={"scope":"Native Windows source-project GPU mixed ranged formation facing inert target. Injected mobile metrics, not paid match balance, exported release or Android hardware.","passed":passed,"mobile":app.mobile_ui,"members":members,"inputs":{}}
	for path in ["res://scripts/main.gd","res://scripts/battle_sim.gd","res://scripts/battle_view.gd","res://scripts/unit_frame_player.gd","res://tests/mixed_formation_ui_qa.gd"]:report.inputs[path]=FileAccess.get_sha256(path)
	FileAccess.open(folder+"/report.json",FileAccess.WRITE).store_string(JSON.stringify(report,"  "))
	print("MIXED_FORMATION_UI ",passed);quit(0 if passed else 1)
