extends SceneTree
# Controlled sight and native input checks. No balance or device claims.
const Data=preload("res://scripts/data_store.gd")
const Simulation=preload("res://scripts/battle_sim.gd")
const Client=preload("res://scripts/client_battle.gd")
const MatchProjection=preload("res://scripts/match_projection.gd")
const View=preload("res://scripts/battle_view.gd")
const Duel=preload("res://scripts/local_duel.gd")
var checks: int=0
var failures: Array=[]
func verify(value: bool,note: String):
	checks+=1
	if not value:failures.append(note)
func supports_side(battle) -> bool:
	for method in battle.get_method_list():
		if method.name=="front":return method.args.size()==1
	return false
func observer_front(battle,side: int) -> float:
	# The same observer can demonstrate failures in a previously shipped pack.
	return battle.call("front",side) if supports_side(battle) else battle.call("front")
func _initialize():call_deferred("run")
func run():
	root.size=Vector2i(1600,900)
	var db=Data.new()
	for side in range(2):
		var sim=Simulation.new(db);sim.start({"map":"map.01.04","faction":"yin","enemy":"yin","seed":137})
		sim.ai_enabled=[false,false];sim.units.clear()
		for base in sim.bases:base.hp=0
		sim.visibility.refresh()
		var direction: float=1 if side==0 else -1
		var home: float=float(sim.bases[side].x)+direction*5
		verify(supports_side(sim),"front accepts the actual observer side")
		verify(is_equal_approx(observer_front(sim,side),home),"empty opening stays at own city")
		var hidden=sim.spawn("unit.yin.axe",1-side,float(sim.bases[1-side].x)-direction)
		sim.visibility.refresh()
		verify(not sim.visible_to(side,hidden),"opponent opening is hidden")
		verify(is_equal_approx(observer_front(sim,side),home),"hidden production does not attract camera")
		var worker=sim.spawn("unit.yin.worker",side,22+direction*7)
		sim.visibility.refresh()
		verify(is_equal_approx(observer_front(sim,side),home),"worker route does not become combat front")
		var lead=sim.spawn("unit.yin.axe",side,22)
		sim.map.apply_anchor(lead,sim.map.anchor("ground.2",8))
		sim.visibility.refresh()
		verify(is_equal_approx(observer_front(sim,side),22),"own lead is followed before contact")
		var initial_focus: float=observer_front(sim,side)
		var initial_sight: Dictionary=sim.visibility.current[side].duplicate(true)
		for hidden_x in ([34.0,35.0] if side==0 else [9.0,10.0]):
			sim.map.apply_anchor(hidden,sim.map.project(Vector2(hidden_x,0)));sim.visibility.refresh()
			verify(not sim.visible_to(side,hidden),"hidden movement fixture remains outside observer sight")
			verify(sim.visibility.current[side]==initial_sight,"hidden actor movement does not change observer sight")
			verify(is_equal_approx(observer_front(sim,side),initial_focus),"hidden opponent movement cannot leak through camera position")
		sim.map.apply_anchor(hidden,sim.map.anchor("bridge",sim.map.edges.bridge.length*.5))
		sim.visibility.refresh()
		verify(not sim.visible_to(side,hidden),"parallel route remains hidden")
		verify(is_equal_approx(observer_front(sim,side),22),"hidden parallel enemy cannot move focus")
		var mirror=Client.new(db);mirror.start(sim.config);mirror.observer=side
		verify(mirror.apply_snapshot(MatchProjection.snapshot(sim,side)),"client accepts side snapshot")
		verify(is_equal_approx(observer_front(mirror,side),observer_front(sim,side)),"host and projected client follow the same own front")
		var view=View.new();view.db=db;view.player_side=side;root.add_child(view);view.reset(sim);view.follow_front=true
		view.update(0)
		verify(is_equal_approx(view.target_camera,22),"BattleView passes observer into automatic follow")
		var before: Dictionary=sim.visibility.current[side].duplicate(true)
		var history: Dictionary=sim.visibility.explored[side].duplicate(true)
		view.target_camera=sim.map.length;view.update(.2)
		verify(sim.visibility.current[side]==before and sim.visibility.explored[side]==history,"automatic navigation never expands sight")
		sim.map.apply_anchor(hidden,sim.map.anchor("ground.2",8+direction*2))
		sim.visibility.refresh()
		verify(sim.visible_to(side,hidden),"contact is observed on own road")
		verify(is_equal_approx(observer_front(sim,side),22+direction),"visible contact midpoint is followed")
		view.update(0)
		verify(is_equal_approx(view.target_camera,22+direction),"view follows contact for its own side")
		sim.tick_count+=1
		verify(mirror.apply_snapshot(MatchProjection.snapshot(sim,side)),"client accepts later contact snapshot")
		verify(is_equal_approx(observer_front(mirror,side),observer_front(sim,side)),"host and client agree during observed combat")
		var trailing=sim.spawn("unit.yin.axe",side,22-direction*3)
		var enemy_worker=sim.spawn("unit.yin.worker",1-side,22+direction*.5)
		var corpse=sim.spawn("unit.yin.axe",side,22+direction*7);corpse.hp=0
		sim.visibility.refresh()
		verify(sim.visible_to(side,enemy_worker),"worker exclusion is exercised on visible actor")
		verify(is_equal_approx(observer_front(sim,side),22+direction),"rear troops, dead troops and workers do not steal focus")
		hidden.hp=0;sim.visibility.refresh()
		verify(is_equal_approx(observer_front(sim,side),22),"lost contact returns focus to own lead")
		hidden.hp=hidden.max_hp
		var bridge: Dictionary=sim.map.project(Vector2(24,-3.2),"bridge")
		sim.map.apply_anchor(hidden,bridge);sim.map.apply_anchor(worker,bridge);sim.visibility.refresh()
		verify(sim.visible_to(side,hidden),"another observer legally scouts the parallel road")
		verify(is_equal_approx(observer_front(sim,side),22),"distant connected route is not mistaken for this contact")
		sim.map.apply_anchor(lead,sim.map.anchor("ground.2",15 if side==0 else 1))
		sim.map.apply_anchor(hidden,sim.map.anchor("ground.3" if side==0 else "ground.1",1 if side==0 else 7))
		sim.visibility.refresh()
		verify(sim.visible_to(side,hidden),"contact across a road node is visible")
		verify(is_equal_approx(observer_front(sim,side),30 if side==0 else 14),"adjacent road pieces retain one contact midpoint")
		lead.hp=0;trailing.hp=0;sim.visibility.refresh()
		verify(is_equal_approx(observer_front(sim,side),home),"lost force returns camera toward own city")
		view.queue_free();await process_frame
		# Both local split views and one-panel LAN use this same input handler.
		for network in [false,true]:
			var duel=Duel.new();duel.size=Vector2(1600,900);root.add_child(duel)
			if network:duel.initialize_network(db,sim,side,func(_kind,_args):return {})
			else:duel.initialize(db,sim.config)
			duel.set_process(false);await process_frame
			var panel: Dictionary=duel.panels[side];var screen_view=panel.view
			screen_view.follow_front=true
			var minimap: Rect2=screen_view.minimap_rect()
			var touch=InputEventScreenTouch.new();touch.index=3;touch.pressed=true;touch.position=minimap.get_center()*screen_view.scale
			duel.field_input(side,touch)
			verify(not screen_view.follow_front,"minimap touch stops follow in local/LAN")
			verify(panel.finger==-1,"minimap touch does not retain a battlefield finger")
			screen_view.follow_front=true
			var point: Vector2=panel.stage.get_center()
			touch.position=point;duel.field_input(side,touch)
			var drag=InputEventScreenDrag.new();drag.index=3;drag.position=point+Vector2(40,0);duel.field_input(side,drag)
			verify(not screen_view.follow_front,"field drag stops follow in local/LAN")
			var moved: float=screen_view.target_camera
			screen_view.update(0)
			verify(is_equal_approx(screen_view.target_camera,clampf(moved,minf(screen_view.width/screen_view.PX*.5,sim.map.length*.5),sim.map.length-minf(screen_view.width/screen_view.PX*.5,sim.map.length*.5))),"manual target survives next view update")
			touch.pressed=false;touch.position=drag.position;duel.field_input(side,touch)
			verify(panel.finger==-1 and not panel.pressed,"touch release clears navigation capture")
			duel.queue_free();await process_frame
	print("OBSERVER_CAMERA: ",checks," checks; failures=",failures)
	quit(0 if failures.is_empty() else 1)
