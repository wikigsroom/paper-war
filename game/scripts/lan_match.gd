extends Node
const Commands=preload("res://scripts/network_commands.gd")
const MatchProjection=preload("res://scripts/match_projection.gd")
const ClientBattle=preload("res://scripts/client_battle.gd")
signal match_ready
signal effects_received(events: Array)
signal state_received(state: Dictionary)
signal command_result(sequence: int,result: Dictionary)
signal connection_lost
var sim
var remote_peer: int=0
var snapshot_clock: float=0
var accumulator: float=0
var started: bool=false
var latest: Dictionary={}
var client_data
var owned_peer: ENetMultiplayerPeer
var pending_effects: Array=[]
func configure_client(data):client_data=data
func host(authority,port: int=28740) -> Error:
	sim=authority;sim.ai_enabled=[false,false]
	var peer=ENetMultiplayerPeer.new()
	var err: Error=peer.create_server(port,1)
	if err!=OK:return err
	multiplayer.multiplayer_peer=peer
	owned_peer=peer
	multiplayer.peer_connected.connect(_connected)
	multiplayer.peer_disconnected.connect(_disconnected)
	return OK
func join(address: String,port: int=28740) -> Error:
	var peer=ENetMultiplayerPeer.new()
	var err: Error=peer.create_client(address,port)
	if err!=OK:return err
	multiplayer.multiplayer_peer=peer
	owned_peer=peer
	multiplayer.server_disconnected.connect(func():started=false;connection_lost.emit())
	multiplayer.connection_failed.connect(func():started=false;connection_lost.emit())
	return OK
func _connected(peer_id: int):
	print("LAN peer connected ",peer_id)
	if remote_peer!=0:return
	remote_peer=peer_id;started=true
	var options: Dictionary={}
	for key in ["map","faction","enemy","seed","full_tech","fog"]:
		if sim.config.has(key):options[key]=sim.config[key]
	_setup.rpc_id(peer_id,options)
func _disconnected(peer_id: int):
	if peer_id==remote_peer:
		remote_peer=0;close();pending_effects.clear();connection_lost.emit()
func _process(delta: float):
	if sim==null or not started or not multiplayer.is_server():return
	accumulator+=minf(delta,.25)
	while accumulator>=1.0/60.0:
		sim.tick(1.0/60.0);accumulator-=1.0/60.0
	var events: Array=sim.drain_events()
	effects_received.emit(MatchProjection.visible_events(sim,0,events))
	pending_effects.append_array(MatchProjection.visible_events(sim,1,events))
	if pending_effects.size()>256:pending_effects=pending_effects.slice(-256)
	snapshot_clock+=delta
	if snapshot_clock>=.05:
		snapshot_clock=0
		_receive_state.rpc_id(remote_peer,MatchProjection.snapshot(sim,1))
		if not pending_effects.is_empty():_receive_effects.rpc_id(remote_peer,pending_effects);pending_effects=[]
func send_command(payload: Dictionary):
	if multiplayer.is_server():
		command_result.emit(int(payload.get("sequence",0)),Commands.submit(sim,0,payload))
	else:_command.rpc_id(1,payload)
@rpc("any_peer","call_remote","reliable",0)
func _command(payload: Dictionary):
	if not multiplayer.is_server() or not started or multiplayer.get_remote_sender_id()!=remote_peer:return
	var result: Dictionary=Commands.submit(sim,1,payload)
	_ack.rpc_id(remote_peer,int(payload.get("sequence",0)),result)
@rpc("authority","call_remote","reliable",0)
func _ack(sequence: int,result: Dictionary):
	command_result.emit(sequence,result)
@rpc("authority","call_remote","reliable",1)
func _setup(options: Dictionary):
	if client_data==null:return
	sim=ClientBattle.new(client_data);sim.observer=1;sim.start(options)
	# Initialization must not expose the local placeholder enemy army.
	sim.units=[];sim.buildings=[]
	for base in sim.bases:base.hp=0
@rpc("authority","call_remote","reliable",1)
func _receive_effects(events: Array):effects_received.emit(events)
@rpc("authority","call_remote","reliable",1)
func _receive_state(state: Dictionary):
	if sim==null or not sim.apply_snapshot(state):return
	var first_state: bool=latest.is_empty()
	latest=state;started=true;state_received.emit(state)
	if first_state:match_ready.emit()
func close():
	started=false
	if owned_peer!=null:owned_peer.close();owned_peer=null
