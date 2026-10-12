extends SceneTree
const Data=preload("res://scripts/data_store.gd")
const Simulation=preload("res://scripts/battle_sim.gd")
const Transport=preload("res://scripts/lan_match.gd")
const AI=preload("res://scripts/tactical_ai.gd")
var transport
var host: bool=false
var began: int=0
var previous: int=0
var decision: float=0
var sequence: int=0
var effect_counts: Dictionary={}
var accepted: int=0
var reported: int=-1
var connected_once: bool=false
var recruitment_step: int=0
func _initialize():call_deferred("run")
func run():
	var args=OS.get_cmdline_user_args();host=args.has("--host")
	transport=Transport.new();transport.name="LanMatch";root.add_child(transport);transport.set_process(false)
	var db=Data.new();var err: Error
	if host:
		var battle=Simulation.new(db);battle.start({"map":"map.01.01","faction":"yin","enemy":"mo","starting_gold":300,"enemy_starting_gold":300,"full_tech":true})
		err=transport.host(battle,28749)
	else:
		transport.configure_client(db);transport.state_received.connect(on_state)
		transport.command_result.connect(func(_seq,result):
			if result.ok:accepted+=1)
		transport.effects_received.connect(func(events):
			for event in events:effect_counts[event.kind]=int(effect_counts.get(event.kind,0))+1)
		err=transport.join("127.0.0.1",28749)
	if err!=OK:quit(1);return
	began=Time.get_ticks_msec();previous=began
	if host:
		var marker=FileAccess.open(args[args.find("--ready")+1],FileAccess.WRITE);marker.store_string("ready");marker.close()
func issue(kind: String,args: Dictionary):
	sequence+=1;transport.send_command({"sequence":sequence,"kind":kind,"args":args})
func on_state(state: Dictionary):
	if state.winner!=-2:
		var passed: bool=accepted>=5 and int(effect_counts.get("attack",0))>0 and int(effect_counts.get("hit",0))>0
		print("LAN_FULL_MATCH winner=",state.winner," time=",state.time," accepted=",accepted," effects=",effect_counts)
		if passed:print("LAN_CLIENT_PASS complete paid accelerated match and winner synchronization")
		transport.close();quit(0 if passed else 2);return
	if float(state.time)>=300:print("LAN_MATCH_OBSERVATION_LIMIT bases=",transport.sim.bases," effects=",effect_counts," accepted=",accepted);transport.close();quit(3);return
	if float(state.time)<decision:return
	decision=float(state.time)+.5
	if state.player.queue.size()<2:
		var plan: Array=["blade","blade","needle","giant","priest","leech"]
		var id: String="unit.mo."+plan[recruitment_step%plan.size()]
		if float(state.player.gold)>=float(transport.sim.db.balance.units[id].gold):issue("recruit",{"id":id});recruitment_step+=1
	if state.player.mana>=40 and float(state.player.cooldowns.get("spell.mo.poison",0))<=0:
		for enemy in transport.sim.units:
			if int(enemy.side)==0 and enemy.x<transport.sim.bases[1].x-.1 and enemy.x>transport.sim.bases[0].x+.1:
				issue("cast",{"id":"spell.mo.poison","x":enemy.x,"y":enemy.y});break
func _process(_delta: float) -> bool:
	if began==0:return false
	var now: int=Time.get_ticks_msec();transport.multiplayer.poll()
	# Eight-times wall rate is QA-only; production, costs and movement remain normal.
	transport._process((now-previous)/1000.0*8);previous=now
	if host and transport.started:
		connected_once=true
		if transport.sim.time>=decision:AI.turn(transport.sim,0);decision=transport.sim.time+.35
		var phase: int=int(transport.sim.time/30)
		if phase!=reported:reported=phase;print("LAN_MATCH_PROGRESS ",transport.sim.time)
	if host and connected_once and not transport.started:print("LAN_MATCH_HOST_DISCONNECTED");quit(0)
	if now-began>65000:transport.close();quit(0 if host else 4)
	return false
