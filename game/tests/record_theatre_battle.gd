extends SceneTree
# Native GPU replay of ordinary paid commands; no actor/HP/technology fixtures.
func _initialize():call_deferred("run")

func run():
	var args=OS.get_cmdline_user_args()
	var folder: String=args[args.find("--output")+1]
	DirAccess.make_dir_recursive_absolute(folder+"/frames")
	var app=load("res://main.tscn").instantiate();root.add_child(app)
	await process_frame
	app.mode="skirmish";app.start_battle(app.db.campaign[3].duplicate(true))
	if args.has("--level"):app.start_battle(app.db.campaign[int(args[args.find("--level")+1])].duplicate(true))
	app.set_process(false);app.sim.ai_enabled=[true,true];app.paused=false
	app.view.follow_front=false;app.view.camera_x=22;app.view.target_camera=22
	var choices: Array=[];var counts: Dictionary={};var frames: int=0;var captures: Array=[];var frame_times: Array=[]
	# An ordinary route order chooses the longer paper bridge before recruits arrive.
	if app.sim.map.edges.has("bridge"):choices.append(app.sim.request(0,"route",{"node":"fork","edge":"bridge"}))
	for tick in range(60*540):
		app.sim.tick(1.0/60.0)
		for event in app.sim.drain_events():
			counts[event.kind]=int(counts.get(event.kind,0))+1
			app.view.on_event(event);app.audio.battle_event(event,app.view.camera_x)
		app.view.update(1.0/60.0,false)
		if tick%4==0 and ((app.sim.time>=14 and app.sim.time<24) or (app.sim.time>=40 and app.sim.time<50)):
			if app.sim.time>=40:
				var leading: float=app.sim.bases[0].x
				for actor in app.sim.units:
					if actor.side==0 and actor.hp>0 and not app.db.balance.units[actor.id].get("economy",false):leading=maxf(leading,actor.x)
				var half: float=minf(app.view.width/app.view.PX*.5,app.sim.map.length*.5)
				app.view.camera_x=clampf(leading,half,app.sim.map.length-half);app.view.target_camera=app.view.camera_x
			app.update_hud();app.view.queue_redraw()
			await process_frame;await RenderingServer.frame_post_draw
			var picture=root.get_texture().get_image()
			var result: int=picture.save_png(folder+"/frames/frame-%04d.png"%frames)
			if result!=OK:push_error("Capture failed");quit(1);return
			frames+=1
			frame_times.append(app.sim.time)
		if tick%60==0 and int(app.sim.time) in [7,14,22,30,60]:
			app.update_hud();await app.qa_snapshot(folder,"battle-%03d"%int(app.sim.time))
			captures.append(int(app.sim.time))
		if app.sim.winner!=-2:break
	app.show_result();await app.qa_snapshot(folder,"result")
	var report: Dictionary={"scope":"Native GPU replay: authored campaign budget and opening forces, both tactical AIs use paid public commands; W04 additionally has one ordinary player bridge order. 60Hz simulation. Silent 15fps offline excerpt has a deliberate cut from seconds14–24 to40–50; not realtime performance, human play or Android hardware evidence.","map":app.sim.config.map,"engine":Engine.get_version_info(),"winner":app.sim.winner,"reason":app.sim.result_reason,"seconds":app.sim.time,"frames":frames,"frame_times":frame_times,"captures":captures,"commands":choices,"events":counts,"stats":app.sim.stats,"inputs":{},"capture_errors":app.capture_errors}
	for path in ["res://scripts/main.gd","res://scripts/battle_view.gd","res://scripts/theatre_ground.gd","res://scripts/battle_sim.gd","res://scripts/tactical_ai.gd","res://data/assets.json","res://data/maps.json","res://data/campaign.json","res://data/balance-prototype.json"]:report.inputs[path]=FileAccess.get_sha256(path)
	for path in ["res://assets/fonts/NotoSansSC.ttf","res://assets/fonts/NotoSerifSC.ttf"]:report.inputs[path]=FileAccess.get_sha256(path)
	var file=FileAccess.open(folder+"/report.json",FileAccess.WRITE);file.store_string(JSON.stringify(report,"\t"));file.close()
	print("NATIVE_PLAY_REPLAY ",JSON.stringify({"winner":report.winner,"seconds":report.seconds,"frames":frames,"events":counts}))
	quit(0 if frames>0 and report.winner!=-2 and app.capture_errors.is_empty() else 1)
