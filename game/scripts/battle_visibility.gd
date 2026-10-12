extends RefCounted
# Road-distance sight is independent of camera, display size and screen zoom.
var owner_ref: WeakRef
var revision: int=0
var sim:
	get:return owner_ref.get_ref()
var current: Array = [{},{}]
var explored: Array = [{},{}]
var last_seen: Array = [{},{}]
var visible_uids: Array = [{},{}]
var enemies: Array = [[],[]]
var node_budgets: Array = [{},{}]
var spotted: Array=[{},{}]
var alert_at: Array=[-8.0,-8.0]
const FIRING_REVEAL_SECONDS: float=1.5
const FIRING_REVEAL_RADIUS: float=.35
var firing_reveals: Array=[{},{}]
var dirty: bool=true
var last_refresh_time: float=-INF

func reveal_attack(source: Dictionary,target: Dictionary):
	var battle=sim
	if source.is_empty() or target.is_empty() or float(source.get("hp",0))<=0 or float(target.get("hp",0))<=0:return
	if int(source.side)==int(target.side):return
	var anchor: Dictionary=battle.physical_anchor(source)
	firing_reveals[int(target.side)][int(source.uid)]={"until":battle.time+FIRING_REVEAL_SECONDS,"anchor":{"edge":anchor.edge,"s":anchor.s,"x":anchor.x,"y":anchor.y}}
	dirty=true

func _init(owner):
	owner_ref=weakref(owner)

func mark_dirty():
	# Geometry, ownership and timed reveal changes are explicit. A non-forced
	# refresh can reuse the last result when none of those inputs changed.
	dirty=true

func refresh_needed() -> bool:
	if dirty:return true
	var battle=sim
	for side in range(2):
		for flash in firing_reveals[side].values():
			if battle.time>=float(flash.until):return true
	for field in battle.spell_areas:
		if float(field.get("vision",0))<=0 or float(field.get("left",0))<=0:continue
		var start_at: float=float(field.get("start_at",0))
		if last_refresh_time<start_at and battle.time>=start_at:return true
	return false

func radius(a: Dictionary) -> float:
	var battle=sim
	if a.get("building",false):
		return 8.0 if a.get("state","active")=="active" and float(a.get("disabled",0))<=0 else 2.0
	var d: Dictionary=battle.db.balance.units[a.id]
	return 3.2 if d.get("economy",false) else maxf(6.0,float(d.get("range",0))+2.0)

func add_span(side: int,edge: String,lo: float,hi: float):
	if hi<lo:return
	if not current[side].has(edge):current[side][edge]=[]
	current[side][edge].append(Vector2(lo,hi))

func merge(spans: Array) -> Array:
	spans.sort_custom(func(a,b):return a.x<b.x)
	var result: Array=[]
	for span in spans:
		if result.is_empty() or span.x>result[-1].y+.0001:result.append(span)
		else:result[-1].y=maxf(result[-1].y,span.y)
	return result

func reveal(side: int,a: Dictionary,r: float):
	var battle=sim
	var source: Dictionary=battle.physical_anchor(a)
	var edge: Dictionary=battle.map.edges[source.edge]
	add_span(side,source.edge,maxf(0,float(source.s)-r),minf(edge.length,float(source.s)+r))
	for endpoint in [edge.from,edge.to]:
		var remaining: float=r-(float(source.s) if endpoint==edge.from else float(edge.length)-float(source.s))
		if remaining>=0:node_budgets[side][endpoint]=maxf(remaining,float(node_budgets[side].get(endpoint,-1)))

func propagate(side: int):
	var battle=sim
	var pending: Array=node_budgets[side].keys()
	while not pending.is_empty():
		var node: String=str(pending.pop_back())
		var budget: float=float(node_budgets[side][node])
		for link in battle.map.adjacency[node]:
			var e: Dictionary=battle.map.edges[link.edge]
			if node==e.from:add_span(side,link.edge,0,minf(e.length,budget))
			else:add_span(side,link.edge,maxf(0,e.length-budget),e.length)
			var remaining: float=budget-float(link.cost)
			if remaining>=0 and remaining>float(node_budgets[side].get(link.node,-1))+.00001:
				node_budgets[side][link.node]=remaining;pending.append(link.node)

func refresh(force: bool=true) -> bool:
	var battle=sim
	if not force and not refresh_needed():
		# Observing an unchanged live building still advances its historical
		# timestamp. Hidden buildings retain the time of their last observation.
		for side in range(2):
			for uid in last_seen[side]:
				if visible_uids[side].has(uid):last_seen[side][uid].seen_at=battle.time
		return false
	# Ordered live references are local to this refresh, never retained across ticks.
	var actors: Array=battle.units+battle.buildings+battle.bases
	var actors_by_uid: Dictionary={}
	var indexed: bool=firing_reveals[0].size()+firing_reveals[1].size()+last_seen[0].size()+last_seen[1].size()>=4
	if indexed:
		for a in actors:
			# Preserve the original scalar comparison for non-integer public fixture IDs.
			if typeof(a.uid)!=TYPE_INT:indexed=false;break
			if a.hp>0 and not actors_by_uid.has(a.uid):actors_by_uid[a.uid]=a
	revision+=1
	current=[{},{}]
	visible_uids=[{},{}];enemies=[[],[]];node_budgets=[{},{}]
	for a in actors:
		if a.hp>0:reveal(int(a.side),a,radius(a))
	for field in battle.spell_areas:
		if field.left>0 and float(field.get("vision",0))>0 and battle.time>=float(field.get("start_at",0)):reveal(int(field.side),field,float(field.vision))
	for side in range(2):
		for uid in firing_reveals[side].keys():
			var flash: Dictionary=firing_reveals[side][uid]
			var source: Dictionary=actors_by_uid.get(int(uid),{}) if indexed else battle.actor(int(uid))
			if battle.time>=float(flash.until) or (not source.is_empty() and int(source.side)==side):
				firing_reveals[side].erase(uid)
				continue
			# A released shot remains observable briefly even after its shooter dies.
			reveal(side,source if not source.is_empty() and source.hp>0 else flash.anchor,FIRING_REVEAL_RADIUS)
		propagate(side)
		for edge in current[side]:
			current[side][edge]=merge(current[side][edge])
			explored[side][edge]=merge(explored[side].get(edge,[])+current[side][edge])
		for a in actors:
			if a.hp>0 and int(a.side)!=side and point_visible(side,battle.physical_anchor(a)):
				visible_uids[side][a.uid]=true;enemies[side].append(a)
				if not a.get("building",false) and not battle.db.balance.units[a.id].get("economy",false) and not spotted[side].has(a.uid):
					spotted[side][a.uid]=battle.time
					if battle.time>=1 and battle.time-float(alert_at[side])>=8 and float(battle.db.balance.units[a.id].gold)>=95:
						alert_at[side]=battle.time
						battle.event("scouted",{"observer":side,"side":side,"uid":a.uid,"id":a.id,"x":a.x,"y":a.y})
		for uid in last_seen[side].keys():
			var remembered: Dictionary=last_seen[side][uid]
			if point_visible(side,remembered) and (actors_by_uid.get(int(uid),{}) if indexed else battle.actor(int(uid))).is_empty():last_seen[side].erase(uid)
		for a in battle.buildings+battle.bases:
			if a.side!=side and a.hp>0 and actor_visible(side,a):
				last_seen[side][a.uid]={"id":a.id,"x":a.x,"y":a.y,"edge":a.edge,"s":a.s,"seen_at":battle.time}
	dirty=false
	last_refresh_time=battle.time
	return true

func point_visible(side: int,a: Dictionary) -> bool:
	var battle=sim
	if not battle.config.get("fog",true):return true
	for span in current[side].get(a.get("edge",""),[]):
		if float(a.get("s",-1))>=span.x-.0001 and float(a.get("s",-1))<=span.y+.0001:return true
	return false

func point_explored(side: int,a: Dictionary) -> bool:
	var battle=sim
	if not battle.config.get("fog",true):return true
	for span in explored[side].get(a.get("edge",""),[]):
		if float(a.get("s",-1))>=span.x-.0001 and float(a.get("s",-1))<=span.y+.0001:return true
	return false

func actor_visible(side: int,a: Dictionary) -> bool:
	return not a.is_empty() and (int(a.side)==side or visible_uids[side].has(a.get("uid",0)))
