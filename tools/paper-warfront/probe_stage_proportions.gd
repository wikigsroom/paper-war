extends SceneTree
# Native stage geometry and ordinary paid AI render observations.
# No generated concept image, actor injection or Android hardware claim.
const App=preload("res://scripts/main.gd")
var app
var folder: String
var checks: Array=[]
var measurements: Array=[]
var captures: Array=[]
func verify(value: bool,note: String,details: Dictionary={}):
	checks.append({"passed":value,"name":note,"details":details})
func _initialize():call_deferred("run")
func unit_height(id: String) -> float:
	if app.view.has_method("unit_height"):return app.view.unit_height(id)
	return float(app.db.assets[id].world_height)*app.view.PX*app.view.PUPPET_SCALE
func capture(name_value: String):
	app.update_hud();app.view.queue_redraw()
	await process_frame;await process_frame;await RenderingServer.frame_post_draw
	var path: String=folder+"/"+name_value+".png"
	verify(root.get_texture().get_image().save_png(path)==OK,"save "+name_value)
	captures.append({"path":path,"sha256":FileAccess.get_sha256(path)})
func run():
	var args=OS.get_cmdline_user_args();folder=args[args.find("--output")+1]
	DirAccess.make_dir_recursive_absolute(folder)
	app=App.new();root.add_child(app);await process_frame
	app.set_process(false);app.audio.silent=true;app.audio.set_background(true);app.mode="skirmish"
	for map_id in app.db.maps:
		app.start_battle({"title":"纸面尺度核验","map":map_id,"faction":app.db.maps[map_id].region,"enemy":"mo","seed":137})
		app.sim.ai_enabled=[false,false];app.view.follow_front=false
		var field: Rect2=app.view.playfield_rect()
		verify(unit_height("unit.mo.giant")>=unit_height("unit.yin.axe")*1.35,"giant remains visibly larger "+map_id)
		var tallest: float=0
		for id in app.db.balance.units:
			var height_value: float=unit_height(id)
			tallest=maxf(tallest,height_value)
			if app.mobile_ui:
				var minimum: float=52 if app.db.balance.units[id].get("economy",false) else 60
				verify(height_value*app.view.scale.y>=minimum-.001,"phone readable body "+map_id+" "+id)
		for edge in app.sim.map.edges.values():
			for p in edge.points:
				var foot: Vector2=app.view.point_to_screen(p.x,p.y)
				verify(foot.y-tallest-22>=field.position.y-.01,"upper road and giant fit "+map_id,{"head":foot.y-tallest-22,"stage_top":field.position.y})
		for b in app.sim.bases:
			var foot: Vector2=app.view.point_to_screen(b.x,b.y)
			verify(foot.y-310>=field.position.y-.01,"base and name fit "+map_id)
		for site in app.sim.map.definition.build_sites:
			var foot: Vector2=app.view.point_to_screen(site.x,site.y)
			verify(foot.y-245>=field.position.y-.01,"construction on actual site fits "+map_id)
		var floor: float=app.view.floor_y()+app.sim.map.bounds.end.y*app.view.PY
		var depth: float=(field.end.y-floor)*app.view.scale.y
		verify(depth>=(52 if app.mobile_ui else 120)-.01,"cut earth remains visible "+map_id,{"depth_in_ui_units":depth})
		measurements.append({"map":map_id,"single_view_world_width":app.view.width/app.view.PX,"cut_earth_ui_units":depth,"ordinary_height_ui_units":unit_height("unit.yin.axe")*app.view.scale.y,"giant_height_ui_units":unit_height("unit.mo.giant")*app.view.scale.y,"y_world_scale":app.view.PY,"view_scale":app.view.scale.y})
		if map_id in ["map.01.01","map.01.04","map.08.20"]:
			app.view.camera_x=minf(app.view.width/app.view.PX*.5,app.sim.map.length*.5);app.view.target_camera=app.view.camera_x
			await capture(map_id+"-home")
	# Ordinary paid simulation: exact authored map, initial resources and public AI.
	app.start_battle({"title":"纸桥交锋","map":"map.01.04","faction":"yin","enemy":"mo","seed":137})
	app.sim.ai_enabled=[true,true];app.view.follow_front=false
	var events: Dictionary={};var paid_orders: int=0;var draw_times: Array=[]
	for tick in range(60*60):
		app.sim.tick(1.0/60.0)
		for event in app.sim.drain_events():
			events[event.kind]=int(events.get(event.kind,0))+1
			if event.kind in ["research_start","recruit"]:paid_orders+=1
			app.view.on_event(event)
		app.view.update(1.0/60.0,false)
		if tick%60==59:
			var half: float=minf(app.view.width/app.view.PX*.5,app.sim.map.length*.5)
			app.view.camera_x=clampf(app.sim.front(),half,app.sim.map.length-half);app.view.target_camera=app.view.camera_x
			app.update_hud();var stamp: int=Time.get_ticks_usec();app.view.queue_redraw()
			await process_frame;await RenderingServer.frame_post_draw
			draw_times.append((Time.get_ticks_usec()-stamp)/1000.0)
		if tick in [20*60-1,45*60-1,60*60-1]:await capture("paid-battle-%02d"%roundi(app.sim.time))
		if app.sim.winner!=-2:break
	verify(paid_orders>0 and events.get("hit",0)>0,"ordinary paid actors reach real combat",{"paid_orders":paid_orders,"hits":events.get("hit",0)})
	var inputs: Dictionary={}
	for name_value in ["main","battle_view","theatre_ground","theatre_fog","battle_visibility","mobile_ui","local_duel","battle_sim","map_runtime"]:
		var base: String="res://scripts/"+name_value
		var path: String=base+(".gd" if FileAccess.file_exists(base+".gd") else ".gdc")
		inputs[path]=FileAccess.get_sha256(path)
	var report: Dictionary={"passed":checks.all(func(c):return c.passed),"version":ProjectSettings.get_setting("application/config/version"),"mobile":app.mobile_ui,"checks":checks,"measurements":measurements,"captures":captures,"ordinary_paid_events":events,"capture_wait_ms":draw_times,"inputs":inputs,"observer_sha256":FileAccess.get_sha256(get_script().resource_path),"scope":"Native Windows Godot stage geometry on all 200 maps, actual GPU images and authored-resource paid AI battle. Screen metrics are injected. Frame waits include synchronization and are not device FPS measurements. Android hardware and human gameplay are unverified."}
	FileAccess.open(folder+"/report.json",FileAccess.WRITE).store_string(JSON.stringify(report,"  "))
	print("STAGE_PROPORTIONS ",report.passed," checks=",checks.size())
	for c in checks:
		if not c.passed:print(c)
	quit(0 if report.passed else 1)
