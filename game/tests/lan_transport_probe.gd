extends SceneTree
const Data=preload("res://scripts/data_store.gd")
const Simulation=preload("res://scripts/battle_sim.gd")
const LanMatch=preload("res://scripts/lan_match.gd")
var match_node
var elapsed: float=0
var sent: bool=false
var acknowledged: bool=false
var observed: bool=false
var is_host: bool=false
var begin_ms: int=0
var previous_ms: int=0
var initial_gold: float=0
var stage: int=0
var results: Dictionary={}
func _initialize():call_deferred("run")
func run():
	begin_ms=Time.get_ticks_msec()
	is_host=OS.get_cmdline_user_args().has("--host")
	match_node=LanMatch.new();match_node.name="LanMatch";root.add_child(match_node)
	# This custom SceneTree probe drives the transport explicitly.
	match_node.set_process(false)
	var err: Error
	if is_host:
		var s=Simulation.new(Data.new());s.start({"map":"map.01.01","faction":"yin","enemy":"mo","starting_gold":300,"full_tech":true})
		err=match_node.host(s,28749)
	else:
		match_node.configure_client(Data.new())
		match_node.state_received.connect(on_state)
		match_node.command_result.connect(func(sequence,result):
			print("LAN_ACK ",sequence," ",result)
			results[sequence]=result
			if sequence==1 and result.ok:acknowledged=true)
		err=match_node.join("127.0.0.1",28749)
	if err!=OK:print("LAN_PROBE_ERROR ",err);quit(1)
	else:
		begin_ms=Time.get_ticks_msec()
		previous_ms=begin_ms
		print("LAN_READY ","host" if is_host else "client")
		var args=OS.get_cmdline_user_args()
		if is_host and args.has("--ready"):
			var marker=FileAccess.open(args[args.find("--ready")+1],FileAccess.WRITE)
			marker.store_string("ready");marker.close()
func on_state(state: Dictionary):
	if state.side!=1 or state.opponent.keys()!=["faction"]:quit(2);return
	if match_node.sim==null or match_node.sim.tick_count!=int(state.tick) or match_node.sim.players[1].gold!=state.player.gold:quit(3);return
	if not sent:
		initial_gold=float(state.player.gold)
		print("LAN_FIRST_STATE ",state.player.faction," ",state.player.gold)
		sent=true
		match_node.send_command({"sequence":1,"kind":"recruit","args":{"id":"unit.mo.blade"}})
	if state.player.sequence==1 and float(state.player.gold)<initial_gold and (not state.player.queue.is_empty() or state.actors.any(func(a):return a.id=="unit.mo.blade" and a.side==1)):
		observed=true
	if stage==0 and acknowledged and observed:
		stage=1;match_node.send_command({"sequence":2,"kind":"cancel_queue","args":{"index":0,"id":"unit.mo.blade"}})
	elif stage==1 and results.has(2) and state.player.sequence==2:
		if not results[2].ok or not state.player.queue.is_empty() or state.player.gold<initial_gold:quit(4);return
		var slot: int=-1
		for i in range(match_node.sim.side_sites(1).size()):
			var site: Dictionary=match_node.sim.slot_anchor(1,i)
			if site.get("types",[]).has("mana") and match_node.sim.visibility.point_visible(1,site):slot=i
		if slot<0:quit(5);return
		stage=2;match_node.send_command({"sequence":3,"kind":"build","args":{"id":"building.mo.mana","slot":slot}})
	elif stage==2 and results.has(3) and state.player.sequence==3:
		if not results[3].ok or not match_node.sim.buildings.any(func(b):return b.id=="building.mo.mana") or state.player.gold>initial_gold-55:quit(6);return
		stage=3;match_node.send_command({"sequence":4,"kind":"cast","args":{"id":"spell.mo.poison","x":match_node.sim.bases[0].x,"y":match_node.sim.bases[0].y}})
	elif stage==3 and results.has(4) and state.player.sequence==4:
		if results[4].ok:quit(7);return
		var x: float=float(match_node.sim.bases[1].x)-2
		stage=4;match_node.send_command({"sequence":5,"kind":"cast","args":{"id":"spell.mo.poison","x":x,"y":match_node.sim.map.ground_y_at(x)}})
	elif stage==4 and results.has(5) and state.player.sequence==5:
		if not results[5].ok or match_node.sim.spell_areas.is_empty():quit(8);return
		print("LAN_CLIENT_PASS paid recruit, refund, building, hidden cast denial and visible zone cast observed");match_node.close();quit(0)
func _process(delta: float) -> bool:
	if match_node!=null:
		match_node.multiplayer.poll()
		var now: int=Time.get_ticks_msec()
		match_node._process((now-previous_ms)/1000.0)
		previous_ms=now
	elapsed=(Time.get_ticks_msec()-begin_ms)/1000.0
	if is_host and elapsed>10:
		print("LAN_HOST_STOP tick=",match_node.sim.tick_count," started=",match_node.started," clock=",match_node.snapshot_clock);match_node.close();quit(0)
	elif not is_host and elapsed>8:print("LAN_CLIENT_TIMEOUT");match_node.close();quit(1)
	return false
