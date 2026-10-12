extends SceneTree
# Native GPU inspection fixtures. Not a played match, timing or balance proof.
const App=preload("res://scripts/main.gd")
var app
var folder: String
var checks: Array=[]
var shots: Array=[]
func verify(value: bool,note: String,details: Dictionary={}):
	checks.append({"passed":value,"name":note,"details":details})
func _initialize():call_deferred("run")
func render(name_value: String) -> Image:
	app.update_hud();app.view.queue_redraw()
	await process_frame;await process_frame;await RenderingServer.frame_post_draw
	var img: Image=root.get_texture().get_image()
	var path: String=folder+"/"+name_value+".png"
	verify(img.save_png(path)==OK,"save "+name_value)
	shots.append({"path":path,"sha256":FileAccess.get_sha256(path)})
	return img
func start_case(map_id: String):
	app.start_battle({"title":"迷雾边界核验","map":map_id,"faction":"yin","enemy":"mo","seed":137})
	app.sim.ai_enabled=[false,false];app.accumulator=-100000
	app.sim.drain_events();app.view.follow_front=false
func difference(a: Image,b: Image,p: Vector2) -> float:
	var q: Vector2i=Vector2i(p).clamp(Vector2i.ZERO,a.get_size()-Vector2i.ONE)
	var ca: Color=a.get_pixelv(q);var cb: Color=b.get_pixelv(q)
	return (absf(ca.r-cb.r)+absf(ca.g-cb.g)+absf(ca.b-cb.b))/3.0
func run():
	var args=OS.get_cmdline_user_args();folder=args[args.find("--output")+1]
	DirAccess.make_dir_recursive_absolute(folder)
	app=App.new();root.add_child(app);await process_frame
	app.set_process(false);app.audio.silent=true;app.audio.set_background(true);app.mode="skirmish"
	start_case("map.01.01")
	app.view.camera_x=app.sim.map.length*.5;app.view.target_camera=app.view.camera_x
	var vision: Dictionary=app.sim.visibility.current[0].duplicate(true)
	var fogged: Image=await render("01-unexplored")
	var field: Rect2=app.view.playfield_rect()
	var changed: int=0;var samples: int=0
	var points: Array=[]
	for x in [14.0,15.0,16.0,17.0,18.0]:
		for fraction in [.12,.28,.44,.60,.76,.90]:
			var local: Vector2=Vector2(app.view.world_to_screen(x).x,field.position.y+field.size.y*fraction)
			if field.has_point(local):points.append(root.get_final_transform()*app.view.get_global_transform_with_canvas()*local)
	app.sim.config.fog=false;app.sim.visibility.refresh()
	var clear: Image=await render("02-debug-clear")
	for p in points:
		samples+=1
		if difference(fogged,clear,p)>.05:changed+=1
	verify(samples>=24 and float(changed)/maxi(1,samples)>=.80,"unknown scene is obscured across stage height",{"samples":samples,"changed":changed})
	var mini: Vector2=root.get_final_transform()*app.view.get_global_transform_with_canvas()*(app.view.minimap_point(18,app.sim.map.ground_y_at(18))+Vector2(0,3))
	verify(difference(fogged,clear,mini)>.025,"minimap presents the same fog",{"pixel_delta":difference(fogged,clear,mini)})
	app.sim.config.fog=true;app.sim.visibility.refresh()
	app.view.camera_x=app.sim.map.length-8;app.view.target_camera=app.view.camera_x
	await render("03-hidden-enemy-base")
	verify(app.sim.visibility.current[0]==vision,"camera navigation never scouts")
	verify(not app.sim.visible_to(0,app.sim.bases[1]),"enemy base remains hidden")
	start_case("map.01.04")
	app.sim.units.clear()
	for base in app.sim.bases:base.hp=0
	var scout=app.sim.spawn("unit.yin.axe",0,22)
	app.sim.map.apply_anchor(scout,app.sim.map.anchor("ground.2",8))
	var ground=app.sim.spawn("unit.mo.giant",1,22)
	app.sim.map.apply_anchor(ground,app.sim.map.anchor("ground.2",9))
	var upper=app.sim.spawn("unit.mo.giant",1,22)
	app.sim.map.apply_anchor(upper,app.sim.map.anchor("bridge",app.sim.map.edges.bridge.length*.5))
	app.sim.visibility.refresh();app.view.camera_x=22;app.view.target_camera=22
	await render("04-lower-road-scout")
	verify(app.sim.visible_to(0,ground) and not app.sim.visible_to(0,upper),"lower route does not reveal upper enemy")
	scout.hp=0;app.sim.visibility.refresh()
	await render("05-scout-lost")
	verify(not app.sim.visible_to(0,ground) and not app.sim.visibility.explored[0].is_empty(),"lost scout retracts live sight and keeps history")
	app.view.player_side=1
	await render("06-east-perspective")
	verify(app.sim.visible_to(1,ground) and app.sim.visible_to(1,upper),"second observer owns both actors")
	var inputs: Dictionary={}
	for file in ["scripts/battle_view","scripts/battle_visibility","scripts/theatre_fog","scripts/map_runtime","scripts/client_battle","scripts/match_projection"]:
		var path: String="res://"+file+(".gd" if FileAccess.file_exists("res://"+file+".gd") else ".gdc")
		if FileAccess.file_exists(path):inputs[path]=FileAccess.get_sha256(path)
	var report: Dictionary={"passed":checks.all(func(c):return c.passed),"version":ProjectSettings.get_setting("application/config/version"),"mobile":app.mobile_ui,"image_size":str(fogged.get_size()),"minimap_pixel":str(mini),"checks":checks,"screenshots":shots,"inputs":inputs,"harness_sha256":FileAccess.get_sha256(get_script().resource_path),"scope":"Native Windows GPU fog fixtures and paired fog/debug-clear pixel observations; injected mobile display metrics. Not Android hardware, human gameplay, original-game timing or full balance."}
	FileAccess.open(folder+"/report.json",FileAccess.WRITE).store_string(JSON.stringify(report,"  "))
	print("FOG_RENDERING ",report.passed," checks=",checks.size())
	for check in checks:
		if not check.passed:print(check)
	quit(0 if report.passed else 1)
