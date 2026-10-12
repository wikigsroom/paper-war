extends SceneTree
const Data=preload("res://scripts/data_store.gd")
const Session=preload("res://scripts/lan_session.gd")
var session
var start_ms: int=0
var last_ms: int=0
var host: bool=false
var finished: bool=false
func _initialize():call_deferred("run")
func run():
	var args=OS.get_cmdline_user_args();host=args.has("--host")
	session=Session.new();session.name="LanSession";session.size=root.get_visible_rect().size;root.add_child(session)
	session.initialize(Data.new(),{"map":"map.01.01","faction":"yin","enemy":"mo","starting_gold":300,"enemy_starting_gold":300,"full_tech":true},"" if host else "127.0.0.1")
	session.set_process(false);session.transport.set_process(false)
	start_ms=Time.get_ticks_msec();last_ms=start_ms
	if host:
		var file=FileAccess.open(args[args.find("--ready")+1],FileAccess.WRITE);file.store_string("ready");file.close();return
	while session.transport.latest.is_empty():
		if Time.get_ticks_msec()-start_ms>12000:quit(1);return
		await process_frame
	await process_frame
	var panel: Dictionary=session.controls.panels[1]
	var before: float=session.transport.sim.players[1].gold
	var card=panel.cards["unit.mo.blade"]
	var container=panel.viewport.get_parent();var window=container.get_viewport()
	var point: Vector2=window.get_final_transform()*(container.get_global_transform()*card.get_global_rect().get_center())
	var motion=InputEventMouseMotion.new();motion.position=point;window.push_input(motion,false);await process_frame
	for pressed in [true,false]:
		var event=InputEventMouseButton.new();event.position=point;event.button_index=MOUSE_BUTTON_LEFT;event.pressed=pressed;window.push_input(event,false);await process_frame
	while session.transport.sim.players[1].sequence<1:
		if Time.get_ticks_msec()-start_ms>12000:quit(2);return
		await process_frame
	var paid: bool=session.transport.sim.players[1].gold<before and session.sequence==1
	while not session.controls.halted:
		if Time.get_ticks_msec()-start_ms>15000:quit(3);return
		await process_frame
	await process_frame
	var disabled: bool=card.disabled
	print("LAN_SESSION_QA paid=",paid," disconnect_disabled=",disabled," own_panel_only=",session.controls.panels[0].is_empty())
	finished=true;quit(0 if paid and disabled and session.controls.panels[0].is_empty() else 4)
func _process(_delta: float) -> bool:
	if session==null or start_ms==0:return false
	var now: int=Time.get_ticks_msec();var dt: float=(now-last_ms)/1000.0;last_ms=now
	session.transport.multiplayer.poll();session.transport._process(dt);session._process(dt)
	if is_instance_valid(session.controls):session.controls.set_process(false);session.controls._process(dt)
	if host and now-start_ms>8000:session.transport.close();print("LAN_SESSION_HOST_STOP");quit(0)
	return false
