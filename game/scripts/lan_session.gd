extends Control
const Transport=preload("res://scripts/lan_match.gd")
const Simulation=preload("res://scripts/battle_sim.gd")
const Controls=preload("res://scripts/local_duel.gd")
signal exit_requested
var transport
var controls
var data
var status: Label
var side: int=0
var sequence: int=0
var sound
func initialize(db,options: Dictionary,address: String="",audio=null):
	sound=audio
	data=db;side=0 if address.is_empty() else 1
	status=Label.new();status.position=Vector2(24,24);status.size=Vector2(size.x-48,80);status.text="等待另一位玩家连接" if side==0 else "正在连接房主";add_child(status)
	var back=Button.new();back.text="取消连接 / 返回";back.position=Vector2(24,120);back.size=Vector2(240,48);add_child(back);back.pressed.connect(func():transport.close();exit_requested.emit())
	transport=Transport.new();transport.name="LanMatch";add_child(transport)
	transport.match_ready.connect(show_controls)
	transport.effects_received.connect(func(events):
		if is_instance_valid(controls):
			for event in events:
				controls.consume_event(side,event)
				if sound!=null and transport.sim.event_visible(side,event):sound.battle_event(event,controls.panels[side].view.camera_x))
	transport.command_result.connect(func(_seq,result):
		if is_instance_valid(controls):
			controls.panels[side].message="已执行" if result.ok else str(result.error);controls.panels[side].message_left=3)
	transport.connection_lost.connect(func():
		if is_instance_valid(controls):controls.set_paused(true);controls.network_status="连接中断 · 请返回重新建局"
		else:status.text="连接失败或连接中断，请返回重试")
	var err: Error
	if side==0:
		var battle=Simulation.new(data);battle.start(options);err=transport.host(battle)
	else:
		transport.configure_client(data);err=transport.join(address)
	if err!=OK:status.text="无法建立连接："+str(err)
func show_controls():
	if is_instance_valid(controls):return
	for child in get_children():
		if child!=transport:child.queue_free()
	controls=Controls.new();controls.size=size;controls.theme=theme;add_child(controls)
	controls.initialize_network(data,transport.sim,side,send)
	controls.exit_requested.connect(func():transport.close();exit_requested.emit())
func send(kind: String,args: Dictionary):
	sequence+=1;transport.send_command({"sequence":sequence,"kind":kind,"args":args})
func relayout(dimensions: Vector2):
	size=dimensions
	if is_instance_valid(controls):controls.size=size;controls.build()
func _notification(what: int):
	if what==NOTIFICATION_APPLICATION_PAUSED or (OS.has_feature("android") and what==NOTIFICATION_APPLICATION_FOCUS_OUT):
		if transport!=null:transport.close()
		if is_instance_valid(controls):controls.set_paused(true);controls.network_status="已离开对局 · 返回后请重新建局"
func _process(_delta: float):
	if transport!=null and side==0 and transport.started and not is_instance_valid(controls):show_controls()
func _exit_tree():
	if transport!=null:transport.close()
