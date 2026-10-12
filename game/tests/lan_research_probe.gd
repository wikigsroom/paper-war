extends SceneTree
const Data=preload("res://scripts/data_store.gd")
const Simulation=preload("res://scripts/battle_sim.gd")
const Transport=preload("res://scripts/lan_match.gd")
var transport
var host: bool=false
var began: int=0
var previous: int=0
var node: Dictionary={}
var before_gold: float=0
var accepted: bool=false
var paid: bool=false
var pending_seen: bool=false
var research_started: float=-1
func _initialize():call_deferred("run")
func run():
	var args=OS.get_cmdline_user_args();host=args.has("--host")
	transport=Transport.new();transport.name="LanMatch";root.add_child(transport);transport.set_process(false)
	var db=Data.new();var err: Error
	if host:
		var battle=Simulation.new(db);battle.start({"map":"map.01.01","faction":"yin","enemy":"mo","starting_gold":300,"enemy_starting_gold":300,"full_tech":false})
		err=transport.host(battle,28749)
	else:
		transport.configure_client(db);transport.state_received.connect(on_state)
		transport.command_result.connect(func(_seq,result):accepted=result.ok;print("LAN_RESEARCH_ACK ",result))
		err=transport.join("127.0.0.1",28749)
	if err!=OK:quit(1);return
	began=Time.get_ticks_msec();previous=began
	if host:
		var marker=FileAccess.open(args[args.find("--ready")+1],FileAccess.WRITE);marker.store_string("ready");marker.close()
func on_state(state: Dictionary):
	if node.is_empty():
		for candidate in transport.sim.db.technology.nodes:
			if candidate.faction!="mo" or state.player.studied.has(candidate.id) or state.player.gold<float(candidate.gold):continue
			var valid: bool=true
			for requirement in candidate.requires:
				if not state.player.studied.has(requirement):valid=false
			if valid:node=candidate;break
		if node.is_empty():quit(2);return
		before_gold=float(state.player.gold)
		transport.send_command({"sequence":1,"kind":"research","args":{"id":node.id}})
		return
	if not state.player.research.is_empty() and state.player.research.id==node.id:
		if research_started<0:research_started=float(state.time)
		paid=paid or absf(float(state.player.gold)-(before_gold-float(node.gold)))<.001
		pending_seen=pending_seen or not state.player.unlocked.has(node.grant)
	if state.player.studied.has(node.id):
		var completed: bool=state.player.unlocked.has(node.grant) and state.player.research.is_empty()
		var waited: bool=float(state.time)-research_started>=float(node.seconds)-.15
		print("LAN_RESEARCH_RESULT ",node.id," paid=",paid," pending=",pending_seen," waited=",waited," completed=",completed)
		if accepted and paid and pending_seen and waited and completed:print("LAN_CLIENT_PASS real paid research completed and unlocked")
		transport.close();quit(0 if accepted and paid and pending_seen and waited and completed else 3)
func _process(_delta: float) -> bool:
	if began==0:return false
	var now: int=Time.get_ticks_msec();transport.multiplayer.poll();transport._process((now-previous)/1000.0);previous=now
	if now-began>(12000 if host else 10000):transport.close();print("LAN_RESEARCH_TIMEOUT_OR_HOST_STOP");quit(0 if host else 4)
	return false
