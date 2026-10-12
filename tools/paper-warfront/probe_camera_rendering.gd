extends SceneTree
# Native GPU navigation on an authored map, with real paid recruitment.
const App=preload("res://scripts/main.gd")
const Duel=preload("res://scripts/local_duel.gd")
const Client=preload("res://scripts/client_battle.gd")
const MatchProjection=preload("res://scripts/match_projection.gd")
var app
var folder: String
var checks: Array=[]
var shots: Array=[]
var payments: Array=[]
func verify(value: bool,note: String,details: Dictionary={}):
	checks.append({"passed":value,"name":note,"details":details})
func _initialize():call_deferred("run")
func front(battle,side: int) -> float:
	for method in battle.get_method_list():
		if method.name=="front":return battle.call("front",side) if method.args.size()==1 else battle.call("front")
	return -1
func render(name_value: String):
	await process_frame;await process_frame;await RenderingServer.frame_post_draw
	var img: Image=root.get_texture().get_image();var path: String=folder+"/"+name_value+".png"
	verify(img.save_png(path)==OK,"save "+name_value)
	shots.append({"path":path,"sha256":FileAccess.get_sha256(path)})
func simulate(seconds: float) -> int:
	var hits: int=0
	for step in range(int(seconds*60)):
		app.sim.tick(1.0/60)
		for event in app.sim.drain_events():
			if event.kind=="hit":hits+=1
			if app.sim.event_visible(0,event):app.view.on_event(event)
	return hits
func focus(view):
	view.update(1);view.queue_redraw()
func run():
	var args=OS.get_cmdline_user_args();folder=args[args.find("--output")+1];DirAccess.make_dir_recursive_absolute(folder)
	app=App.new();root.add_child(app);await process_frame;app.set_process(false)
	app.audio.silent=true;app.audio.set_background(true);app.mode="skirmish"
	app.start_battle({"title":"前线导航核验","map":"map.01.04","faction":"yin","enemy":"yin","seed":137})
	app.sim.ai_enabled=[false,false];app.accumulator=-100000
	var key=InputEventKey.new();key.keycode=KEY_SPACE;key.pressed=true;app._unhandled_input(key);focus(app.view)
	var home: float=clampf(float(app.sim.bases[0].x)+5,minf(app.view.width/app.view.PX*.5,app.sim.map.length*.5),app.sim.map.length-minf(app.view.width/app.view.PX*.5,app.sim.map.length*.5))
	verify(app.view.follow_front and is_equal_approx(app.view.target_camera,home),"Space follows own opening instead of unexplored center",{"target":app.view.target_camera,"expected":home})
	await render("01-opening")
	for side in range(2):
		var gold: float=app.sim.players[side].gold;var cost: float=app.db.balance.units["unit.yin.axe"].gold
		var result: Dictionary=app.sim.request(side,"recruit",{"id":"unit.yin.axe"})
		payments.append({"side":side,"id":"unit.yin.axe","time":app.sim.time,"gold_before":gold,"gold_after":app.sim.players[side].gold,"cost":cost,"ok":result.ok})
		verify(result.ok and is_equal_approx(gold-app.sim.players[side].gold,cost),"recruitment really pays side "+str(side))
	simulate(8);app.update_hud();focus(app.view)
	var lead: Dictionary={}
	for actor in app.sim.units:
		if actor.side==0 and actor.id=="unit.yin.axe":lead=actor
	verify(not lead.is_empty(),"paid west fighter leaves production")
	verify(is_equal_approx(front(app.sim,0),float(lead.get("x",-1))),"west camera follows its march before enemy contact",{"camera_front":front(app.sim,0),"lead_x":lead.get("x",-1)})
	await render("02-west-paid-march")
	var mirror=Client.new(app.db);mirror.start(app.sim.config);mirror.observer=1
	verify(mirror.apply_snapshot(MatchProjection.snapshot(app.sim,1)),"real east snapshot accepted")
	var duel=Duel.new();duel.size=app.ui.size;duel.scale=app.ui.scale;duel.theme=app.theme;app.add_child(duel)
	duel.initialize_network(app.db,mirror,1,func(_kind,_args):return {});duel.set_process(false)
	app.ui.hide();app.view.hide();await process_frame
	duel._process(0)
	var panel: Dictionary=duel.panels[1];var view=panel.view;view.follow_front=true;focus(view)
	var east: Dictionary={}
	for actor in mirror.units:
		if actor.side==1 and actor.id=="unit.yin.axe":east=actor
	verify(not east.is_empty(),"paid east fighter is available in its own projection")
	verify(is_equal_approx(front(mirror,1),float(east.get("x",-1))),"LAN east uses its own advance",{"camera_front":front(mirror,1),"own_lead_x":east.get("x",-1)})
	verify(is_equal_approx(view.target_camera,clampf(float(east.get("x",-1)),minf(view.width/view.PX*.5,mirror.map.length*.5),mirror.map.length-minf(view.width/view.PX*.5,mirror.map.length*.5))),"LAN view consumes east front")
	await render("03-east-paid-march")
	var sight: Dictionary=mirror.visibility.current[1].duplicate(true)
	var touch=InputEventScreenTouch.new();touch.index=2;touch.pressed=true;touch.position=(view.minimap_rect().position+view.minimap_rect().size*Vector2(.4,.5))*view.scale
	duel.field_input(1,touch);focus(view)
	verify(not view.follow_front and panel.finger==-1,"native minimap touch exits automatic follow and releases finger")
	verify(mirror.visibility.current[1]==sight,"manual LAN camera does not create sight")
	await render("04-east-manual-navigation")
	duel.open_sheet(1,"orders");await process_frame
	var button: Button=null
	var pending: Array=[panel.overlay]
	while not pending.is_empty():
		var node: Node=pending.pop_back()
		if node is Button and node.text=="追踪交锋":button=node;break
		pending.append_array(node.get_children())
	verify(button!=null,"real orders sheet contains follow action")
	if button!=null:button.pressed.emit()
	focus(view)
	verify(view.follow_front and is_equal_approx(view.target_camera,clampf(float(east.get("x",-1)),minf(view.width/view.PX*.5,mirror.map.length*.5),mirror.map.length-minf(view.width/view.PX*.5,mirror.map.length*.5))),"orders resumes the correct east follow")
	await render("05-east-follow-resumed")
	duel.queue_free();await process_frame;app.ui.show();app.view.show()
	var impacts: int=0
	for step in range(45):
		impacts+=simulate(1)
		if impacts>0:break
	app.update_hud();focus(app.view)
	verify(impacts>0,"paid troops reach actual damaging combat",{"simulation_time":app.sim.time,"damage_hits":impacts})
	var combatants: Array=app.sim.units.filter(func(actor):return actor.hp>0 and actor.id=="unit.yin.axe")
	verify(combatants.size()==2,"both paid combatants survive first observed contact")
	if combatants.size()==2:
		var midpoint: float=(float(combatants[0].x)+float(combatants[1].x))*.5
		verify(is_equal_approx(front(app.sim,0),midpoint),"camera centers legally observed contact",{"expected":midpoint,"front":front(app.sim,0)})
	await render("06-paid-contact")
	var inputs: Dictionary={}
	for name_value in ["battle_sim","battle_view","local_duel","main","mobile_ui","battle_visibility","map_runtime","client_battle","match_projection"]:
		var path: String="res://scripts/"+name_value+(".gd" if FileAccess.file_exists("res://scripts/"+name_value+".gd") else ".gdc")
		inputs[path]=FileAccess.get_sha256(path)
	var report: Dictionary={"passed":checks.all(func(c):return c.passed),"version":ProjectSettings.get_setting("application/config/version"),"mobile":app.mobile_ui,"checks":checks,"payments":payments,"screenshots":shots,"inputs":inputs,"observer_sha256":FileAccess.get_sha256(get_script().resource_path),"scope":"Native Windows GPU, actual paid units on an authored map, KEY_SPACE handler, projected east Control UI and native ScreenTouch. AI disabled for reproducible timing; no free fighters, altered HP/resources, Android hardware or original-game timing claims."}
	FileAccess.open(folder+"/report.json",FileAccess.WRITE).store_string(JSON.stringify(report,"  "))
	print("CAMERA_RENDERING ",report.passed," checks=",checks.size())
	for check in checks:
		if not check.passed:print(check)
	quit(0 if report.passed else 1)
