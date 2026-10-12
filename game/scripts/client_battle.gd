extends "res://scripts/battle_sim.gd"
# Rendering mirror only. Authority owns all simulation and command execution.
var observer: int=1
var received_tick: int=-1
func mine_state(mine: Dictionary,ignore_uid: int=0) -> Dictionary:
	var assigned: int=0;var active: int=0;var waiting: int=0
	for worker in units:
		if worker.uid==ignore_uid or not db.balance.units[worker.id].get("economy",false):continue
		if int(worker.side)==observer:
			if worker.get("mine","")!=mine.id:continue
		else:
			if worker.edge!=mine.edge or absf(float(worker.s)-float(mine.s))>1:continue
		assigned+=1
		if worker.anim=="mine":active+=1
		if worker.anim=="queue":waiting+=1
	return {"assigned":assigned,"active":active,"waiting":waiting,"capacity":int(mine.capacity)}
func tick(_dt: float):pass
func request(_side: int,_kind: String,_args: Dictionary={}) -> Dictionary:
	return {"ok":false,"error":"客户端操作必须提交服务端"}
func command(_side: int,_sequence: int,_kind: String,_args: Dictionary) -> Dictionary:
	return {"ok":false,"error":"客户端不能执行战斗命令"}
func apply_snapshot(packet: Dictionary) -> bool:
	if int(packet.get("protocol",0))!=1 or int(packet.get("side",-1))!=observer or int(packet.get("tick",-1))<=received_tick:return false
	received_tick=int(packet.tick);tick_count=received_tick;time=float(packet.time);winner=int(packet.winner)
	players[observer]=packet.player.duplicate(true)
	players[1-observer]={"faction":packet.opponent.faction}
	units=[];buildings=[]
	for side in range(2):
		bases[side]=bases[side].duplicate(true);bases[side].hp=0
	visibility.visible_uids=[{},{}];visibility.enemies=[[],[]]
	for source in packet.actors:
		var actor: Dictionary=source.duplicate(true)
		if actor.get("base",false):bases[int(actor.side)]=actor
		elif actor.get("building",false):buildings.append(actor)
		else:
			actor.merge({"statuses":{},"job_time":0.0,"cargo":0,"clone":false},false)
			units.append(actor)
		if int(actor.side)!=observer:
			visibility.visible_uids[observer][actor.uid]=true;visibility.enemies[observer].append(actor)
	visibility.current[observer]=packet.vision.duplicate(true)
	visibility.explored[observer]=packet.explored.duplicate(true)
	visibility.last_seen[observer]=packet.last_seen.duplicate(true)
	projectiles=packet.get("projectiles",[]).duplicate(true)
	for missile in projectiles:missile["observed_only"]=true
	spell_areas=packet.get("spell_areas",[]).duplicate(true)
	corpses=packet.get("corpses",[]).duplicate(true)
	return true
