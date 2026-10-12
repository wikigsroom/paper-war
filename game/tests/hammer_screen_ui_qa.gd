extends SceneTree
# Ordinary paid commands, normal fog and walking; only the short clip is rendered offline.
const App=preload("res://scripts/main.gd")
func _initialize():call_deferred("run")
func run():
	var args=OS.get_cmdline_user_args()
	var folder: String=args[args.find("--output")+1]
	DirAccess.make_dir_recursive_absolute(folder+"/frames")
	var app=App.new();root.add_child(app)
	await process_frame
	app.set_process(false);app.audio.silent=true;app.audio.set_background(true);app.mode="skirmish"
	app.start_battle({"title":"殷折重锤 · 实战验收","map":"map.01.04","faction":"yin","enemy":"yin","starting_gold":300,"enemy_starting_gold":300,"full_tech":false,"ai_warmup":0,"seed":137})
	app.sim.ai_enabled=[false,false];app.accumulator=-100000;app.sim.drain_events()
	var orders: Array=[]
	orders.append(app.sim.request(0,"research",{"id":"tech.yin.unit.hammer"}))
	orders.append(app.sim.request(0,"recruit",{"id":"unit.yin.axe"}))
	for i in range(6):orders.append(app.sim.request(1,"recruit",{"id":"unit.yin.axe"}))
	var ordered: bool=false;var premium: Dictionary={};var hits: int=0;var damage: float=0.0
	var clip_start: float=-1;var captures: Array=[];var states: Dictionary={}
	app.view.follow_front=false
	for step in range(180*60):
		if not ordered and app.sim.players[0].studied.has("tech.yin.unit.hammer"):
			orders.append(app.sim.request(0,"recruit",{"id":"unit.yin.hammer"}));ordered=true
		app.sim.tick(1.0/60.0)
		for event in app.sim.drain_events():
			app.view.on_event(event)
			if event.kind=="spawn" and event.id=="unit.yin.hammer" and event.side==0:
				premium=app.sim.actor(int(event.uid))
			if event.kind=="hit" and not premium.is_empty() and int(event.get("source_uid",0))==int(premium.uid):
				hits+=1;damage+=float(event.amount)
		app.view.update(1.0/60.0,false)
		if not premium.is_empty():
			if clip_start<0 and premium.anim=="windup":clip_start=app.sim.time
			if clip_start>=0 and app.sim.time<=clip_start+1.2 and step%4==0:
				app.view.camera_x=float(premium.x)+1.3;app.view.target_camera=app.view.camera_x
				app.update_hud();app.view.queue_redraw()
				await process_frame;await RenderingServer.frame_post_draw
				var name: String="frames/frame-%03d.png"%captures.size()
				var error: Error=root.get_texture().get_image().save_png(folder+"/"+name)
				if error!=OK:app.capture_errors.append(name)
				states[premium.anim]=true
				captures.append({"path":name,"time":app.sim.time,"state":premium.anim,"target":premium.target,"x":premium.x})
			if premium.hp<=0 and app.sim.players[0].queue.is_empty() and app.sim.players[1].queue.is_empty():break
	if app.mobile_ui:
		app.mobile.card_info("unit.yin.hammer",false)
		await process_frame;await process_frame
		await app.qa_snapshot(folder,"unit-info")
	var passed: bool=orders.all(func(r):return r.ok) and hits>0 and captures.size()>=12 and states.has("windup") and states.has("attack") and app.capture_errors.is_empty()
	var report: Dictionary={"scope":"Native Windows GPU offline excerpt of a real paid research/production/walking recipe against six paid basic soldiers. No actor, HP, position, tech or fog fixtures. Mobile mode injects Windows display metrics; not Android hardware, human play, realtime performance or full balance.","passed":passed,"mobile":app.mobile_ui,"orders":orders,"hit_events":hits,"event_damage":damage,"captures":captures,"states":states,"capture_errors":app.capture_errors,"inputs":{}}
	for path in ["res://scripts/main.gd","res://scripts/ui_theme.gd","res://scripts/mobile_ui.gd","res://scripts/battle_sim.gd","res://scripts/battle_command_rules.gd","res://scripts/battle_view.gd","res://scripts/unit_frame_player.gd","res://scripts/unit_abilities.gd","res://scripts/battle_visibility.gd","res://data/balance-prototype.json","res://data/maps.json","res://data/technology.json","res://data/assets.json","res://data/unit-frames.json","res://tests/hammer_screen_ui_qa.gd","res://assets/animation/frames-v1/unit-yin-hammer-atlas.png","res://assets/animation/frames-v1/unit-yin-axe-atlas.png"]:report.inputs[path]=FileAccess.get_sha256(path)
	FileAccess.open(folder+"/report.json",FileAccess.WRITE).store_string(JSON.stringify(report,"  "))
	print("HAMMER_SCREEN_UI ",passed," frames=",captures.size()," hits=",hits)
	quit(0 if passed else 1)
