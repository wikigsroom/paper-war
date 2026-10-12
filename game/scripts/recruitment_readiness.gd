extends RefCounted

# Own FIFO only. This estimates exit from base, never arrival at the battlefield.
static func queued_seconds(sim, side: int, index: int) -> float:
	if side<0 or side>=sim.players.size():return -1.0
	var p: Dictionary=sim.players[side]
	if index<0 or index>=p.queue.size():return -1.0
	var seconds: float=-float(p.production)
	for i in range(index+1):
		seconds+=float(sim.db.balance.units[p.queue[i]].get("production_seconds",2.0))
	return maxf(0.0,seconds)

static func queue_notice(sim, side: int, index: int) -> String:
	var seconds: float=queued_seconds(sim,side,index)
	return "约 %.1f 秒出仓"%seconds if seconds>=0 else "队列位置已改变"

# Living own bodies on the currently selected base route, never queue orders.
# A nearby pair is a formation observation, not a survival/arrival guarantee.
static func deployment_group(sim,side: int,gap: float=6.0) -> Dictionary:
	var result: Dictionary={"supported":false,"front_count":0,"members":[]}
	if side<0 or side>=sim.players.size():return result
	if side==1 and not sim.config.get("enemy_entries",[]).is_empty():return result
	result.supported=true
	var map=sim.map
	var west: float=float(map.nodes[map.definition.bases[0].node].position[0])+.1
	var east: float=float(map.nodes[map.definition.bases[1].node].position[0])-.1
	var x: float=clampf(float(sim.bases[side].x)+(.65 if side==0 else -.65),west,east)
	var origin: Dictionary=map.project(Vector2(x,map.ground_y_at(x)))
	var edge_id: String=origin.edge
	var offset: float=-float(origin.s) if side==0 else float(origin.s)-float(map.edges[edge_id].length)
	var offsets: Dictionary={}
	for step in range(32):
		if offsets.has(edge_id):break
		offsets[edge_id]=offset
		var edge: Dictionary=map.edges[edge_id]
		offset+=float(edge.length)
		var node: String=edge.to if side==0 else edge.from
		var next: Array=map.outgoing[node] if side==0 else map.incoming[node]
		if next.is_empty():break
		edge_id=str(map.choices[side].get(node,next[0]))
		if not next.has(edge_id):edge_id=str(next[0])
	var bodies: Array=[]
	for u in sim.units:
		if u.side!=side or u.hp<=0 or not offsets.has(u.edge):continue
		var def: Dictionary=sim.db.balance.units[u.id]
		if def.get("economy",false):continue
		var progress: float=float(offsets[u.edge])+(float(u.s) if side==0 else float(map.edges[u.edge].length)-float(u.s))
		if progress<0:continue
		var front: bool=str(def.get("attack","")).begins_with("melee")
		if front:result.front_count+=1
		bodies.append({"uid":u.uid,"distance":progress,"front":front})
	bodies.sort_custom(func(a,b):return a.distance<b.distance)
	for body in bodies:
		if not body.front:continue
		var members: Array=[]
		for other in bodies:
			if absf(float(body.distance)-float(other.distance))<=maxf(0,gap):members.append(other.uid)
		if members.size()>=2:
			result.members=members;break
	return result

# Farthest living own soldier on the selected route. No enemy intelligence.
static func front_distance(sim, side: int) -> float:
	if side<0 or side>=sim.players.size():return -1.0
	if side==1 and not sim.config.get("enemy_entries",[]).is_empty():return -1.0
	var map=sim.map
	var west: float=float(map.nodes[map.definition.bases[0].node].position[0])+.1
	var east: float=float(map.nodes[map.definition.bases[1].node].position[0])-.1
	var x: float=clampf(float(sim.bases[side].x)+(.65 if side==0 else -.65),west,east)
	var origin: Dictionary=map.project(Vector2(x,map.ground_y_at(x)))
	var own: Dictionary={}
	for u in sim.units:
		if u.side!=side or u.hp<=0 or sim.db.balance.units[u.id].get("economy",false):continue
		var s: float=float(u.s)
		if not own.has(u.edge):own[u.edge]=s
		else:own[u.edge]=maxf(own[u.edge],s) if side==0 else minf(own[u.edge],s)
	var edge_id: String=origin.edge
	var offset: float=-float(origin.s) if side==0 else float(origin.s)-float(map.edges[edge_id].length)
	var visited: Dictionary={}
	var farthest: float=-1.0
	for step in range(32):
		if visited.has(edge_id):break
		visited[edge_id]=true
		var edge: Dictionary=map.edges[edge_id]
		if own.has(edge_id):
			var distance: float=offset+(float(own[edge_id]) if side==0 else float(edge.length)-float(own[edge_id]))
			if distance>=0:farthest=maxf(farthest,distance)
		offset+=float(edge.length)
		var node: String=edge.to if side==0 else edge.from
		var next: Array=map.outgoing[node] if side==0 else map.incoming[node]
		if next.is_empty():break
		edge_id=str(map.choices[side].get(node,next[0]))
		if not next.has(edge_id):edge_id=str(next[0])
	return farthest

static func travel_notice(sim, id: String, distance: float) -> String:
	var def: Dictionary=sim.db.balance.units[id]
	if def.get("economy",false):return "纸工出仓后执行采矿运输"
	if distance<0:return "当前选路没有可估算的己方前线"
	return "出仓后基础行军约 %.1f 秒至当前己方前线\n不含阻挡、控制或战线变化"%(distance/maxf(.001,float(def.speed)))

# Same own-route geometry as the existing travel notice. This is a stationary
# reference position, never a prediction of enemy contact or future survival.
static func reinforcement_seconds(sim,side: int,id: String,distance: float=-2.0) -> float:
	var investment: Dictionary=first_investment(sim,side,id)
	if investment.is_empty() or sim.db.balance.units[id].get("economy",false):return -1.0
	if distance==-2.0:distance=front_distance(sim,side)
	if distance<0:return -1.0
	return float(investment.exit_seconds)+distance/maxf(.001,float(sim.db.balance.units[id].speed))

static func reinforcement_notice(sim,side: int,id: String,distance: float=-2.0) -> String:
	if not sim.db.balance.units.has(id):return "本局不可招募此兵种"
	if sim.db.balance.units[id].get("economy",false):return "纸工出仓后执行采矿运输"
	var seconds: float=reinforcement_seconds(sim,side,id,distance)
	if seconds<0:return "当前选路没有可估算的己方前线"
	return "到当前前线位置约 %.1f 秒（研究＋出仓＋行军）\n按足额金币估算；未计战线移动、阻挡或控制"%seconds

# A cash requirement, not predicted income. Research and existing production run
# in parallel; a new locked unit enters FIFO only after all prerequisites finish.
static func pending_research(sim,side: int,id: String,seen: Dictionary,result: Array):
	if seen.has(id) or sim.players[side].studied.has(id):return
	seen[id]=true
	var node: Dictionary=sim.db.tech(id)
	if node.is_empty():return
	for required in node.requires:pending_research(sim,side,str(required),seen,result)
	result.append(node)

static func first_investment(sim,side: int,id: String) -> Dictionary:
	if side<0 or side>=sim.players.size() or not sim.db.balance.units.has(id):return {}
	var def: Dictionary=sim.db.balance.units[id]
	if not def.get("manual_recruit",true) or not sim.production_ids(side).has(id):return {}
	var p: Dictionary=sim.players[side]
	var pending: Array=[]
	if not p.unlocked.has(id):
		var node: Dictionary=sim.db.tech_for(id)
		if node.is_empty():return {}
		pending_research(sim,side,str(node.id),{},pending)
	var gold: float=float(def.gold)
	var study_time: float=0
	var active: String=str(p.research.get("id",""))
	var active_needed: bool=false
	for node in pending:
		if node.id==active:
			study_time+=float(p.research.left);active_needed=true
		else:
			gold+=float(node.gold);study_time+=float(node.seconds)
	if not pending.is_empty() and active!="" and not active_needed:study_time+=float(p.research.left)
	var fifo: float=queued_seconds(sim,side,p.queue.size()-1) if not p.queue.is_empty() else 0.0
	return {"gold":gold,"research_seconds":study_time,"production_seconds":float(def.get("production_seconds",2)),"exit_seconds":maxf(study_time,fifo)+float(def.get("production_seconds",2)),"research_count":pending.size()}

static func investment_notice(sim,side: int,id: String) -> String:
	var estimate: Dictionary=first_investment(sim,side,id)
	if estimate.is_empty():return "本局不可招募此兵种"
	return "首次投入还需 %d 金（研究＋招募）\n最早约 %.1f 秒出仓 · 尚有 %d 项研究\n按现有队列、足额金币与连续研究估算"%[int(ceil(estimate.gold)),estimate.exit_seconds,estimate.research_count]
