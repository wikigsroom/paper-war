extends SceneTree
const Ground=preload("res://scripts/theatre_ground.gd")
var checks: Array=[]
var app
func _initialize():call_deferred("run")
func check(name_value: String,passed: bool,details: Dictionary={}):
	checks.append({"name":name_value,"passed":passed,"details":details})
	if not passed:print("PAN_MENU_FAIL ",name_value," ",details)
func buttons(parent: Node) -> Array:
	return parent.find_children("*","Button",true,false).filter(func(b):return b.is_visible_in_tree())
func run():
	var args=OS.get_cmdline_user_args();var folder: String=args[args.find("--output")+1]
	DirAccess.make_dir_recursive_absolute(folder+"/frames")
	app=load("res://main.tscn").instantiate();root.add_child(app);await process_frame
	app.set_process(false);app.main_menu()
	for i in range(3):await process_frame
	var bs: Array=buttons(app.ui);var captions: Array=[]
	for b in bs:captions.append(b.text)
	check("Exactly five main entries",captions==["继续战役","新战役","成就挑战","兵书","设置"],{"labels":captions})
	for i in range(1,bs.size()):
		check("Main menu row "+str(i),absf(bs[i].global_position.x-bs[0].global_position.x)<.1 and bs[i].global_position.y>=bs[i-1].get_global_rect().end.y+7.9)
	await app.qa_snapshot(folder,"menu")
	app.new_battle_menu();for i in range(3):await process_frame
	bs=buttons(app.ui);captions.clear()
	for b in bs:
		if b.text!="返回":captions.append(b.text)
	check("New battle contains two modes",captions==["故事战役","遭遇战"],{"labels":captions})
	await app.qa_snapshot(folder,"new-battle")
	app.start_battle({"title":"纸桥岔口","faction":"yin","enemy":"mo","map":"map.01.04","full_tech":true});app.sim.ai_enabled=[false,false];app.view.follow_front=false
	app.view.update(0,true)
	# All map profiles keep the same world vertex count and positions on pan.
	var max_residual: float=0;var shapes: int=0
	for definition in app.db.maps.values():
		app.sim.start({"faction":definition.region,"enemy":"mo","map":definition.id})
		app.view.camera_x=20;var first: PackedVector2Array=Ground.surface(app.view,app.sim)
		app.view.camera_x=20.127;var second: PackedVector2Array=Ground.surface(app.view,app.sim)
		check(definition.id+" stable surface topology",first.size()==second.size())
		for i in range(mini(first.size(),second.size())):max_residual=maxf(max_residual,(second[i]-first[i]-Vector2(-.127*app.view.PX,0)).length())
		shapes+=1
	check("Terrain vertices translate coherently",max_residual<.001,{"max_px":max_residual,"maps":shapes})
	app.start_battle({"title":"纸桥岔口","faction":"yin","enemy":"mo","map":"map.01.04","full_tech":true});app.sim.ai_enabled=[false,false]
	app.view.follow_front=false;app.view.camera_x=22;app.view.target_camera=31;app.view.update(0,true)
	var start=Vector2(760,460);var press=InputEventMouseButton.new();press.position=start;press.button_index=MOUSE_BUTTON_LEFT;press.pressed=true
	root.push_input(press,true);await process_frame
	check("Pan starts at visible camera",is_equal_approx(app.drag_camera,22) and app.view.direct_pan)
	var delta_step: float=1
	var positions: Array=[]
	for frame in range(48):
		var motion=InputEventMouseMotion.new();motion.position=start+Vector2(-16-frame*delta_step,0);motion.button_mask=MOUSE_BUTTON_MASK_LEFT
		root.push_input(motion,true);app.view.update(1.0/60,true)
		check("Direct drag follows pointer "+str(frame),absf(app.view.camera_x-(22+(16+frame)/app.view.PX))<.0001)
		app.view.queue_redraw();await process_frame;await RenderingServer.frame_post_draw
		root.get_texture().get_image().save_png(folder+"/frames/frame-%04d.png"%frame)
		positions.append(app.view.camera_x)
	var release=InputEventMouseButton.new();release.position=Vector2(20,870);release.button_index=MOUSE_BUTTON_LEFT;release.pressed=false
	root.push_input(release,true);await process_frame
	check("Release over HUD ends mouse capture",not app.dragging and not app.view.direct_pan)
	var camera: float=app.view.camera_x;app.view.update(.2,true)
	check("No post-drag camera chase",absf(app.view.camera_x-camera)<.0001)
	# A shared shake transform keeps surface and actors in the same stage space.
	app.view.shake=5;app.view.direct_pan=true;app.view.update(0,true);await process_frame;await RenderingServer.frame_post_draw
	check("No battle shake during manual drag",app.view.canvas_shift==Vector2.ZERO)
	var failures: Array=checks.filter(func(c):return not c.passed)
	var report={"passed":failures.is_empty(),"checks":checks,"failures":failures,"maps":shapes,"max_vertex_residual_px":max_residual,"camera_positions":positions,"capture_errors":app.capture_errors,"scope":"Native Windows GPU and actual pointer event injection; fixed simulation for translation/pixel inspection. All map geometries sampled. Not Android hardware evidence.","inputs":{}}
	for p in ["res://scripts/main.gd","res://scripts/mobile_ui.gd","res://scripts/mobile_input.gd","res://scripts/battle_view.gd","res://scripts/theatre_ground.gd","res://data/maps.json"]:report.inputs[p]=FileAccess.get_sha256(p)
	var file=FileAccess.open(folder+"/report.json",FileAccess.WRITE);file.store_string(JSON.stringify(report,"\t"));file.close()
	print("PAN_MENU ",JSON.stringify({"passed":report.passed,"checks":checks.size(),"maps":shapes,"residual":max_residual}));quit(0 if report.passed else 1)
