extends RefCounted
# All participants use this geometry. Curves are deterministic polylines in world units.
var definition: Dictionary
var nodes: Dictionary = {}
var edges: Dictionary = {}
var outgoing: Dictionary = {}
var incoming: Dictionary = {}
var adjacency: Dictionary = {}
var choices: Array = [{}, {}]
var length: float = 56.0
var bounds: Rect2
var shortest_cache: Dictionary = {}
var ground_surface: PackedVector2Array = PackedVector2Array()
# A zero-distance advance still canonicalizes its input the first time. Retain
# only exact finite canonical projections; raw or edited anchors use the old path.
var stationary_projections: Dictionary={}
var stationary_projection_order: Array[int]=[]
const STATIONARY_PROJECTION_LIMIT: int=256
var stationary_projection_hits: int=0

class StationaryProjection:
	extends RefCounted
	var actor_ref: Dictionary
	var edge_id: String
	var offset: float
	var x: float
	var y: float
	var edge_length: float
	var points: Array
	var cumulative: Array
	func _init(actor: Dictionary,edge: Dictionary):
		actor_ref=actor;edge_id=str(actor.edge);offset=float(actor.s);x=float(actor.x);y=float(actor.y)
		edge_length=float(edge.length);points=edge.points.duplicate();cumulative=edge.cumulative.duplicate()
	func matches(actor: Dictionary,edge: Dictionary) -> bool:
		return is_same(actor,actor_ref) and typeof(actor.edge)==TYPE_STRING and typeof(actor.s)==TYPE_FLOAT and typeof(actor.x)==TYPE_FLOAT and typeof(actor.y)==TYPE_FLOAT and actor.edge==edge_id and actor.s==offset and actor.x==x and actor.y==y and float(edge.length)==edge_length and edge.points==points and edge.cumulative==cumulative


func _init(data: Dictionary):
	definition = data.duplicate(true)
	length = float(data.get("length", 56))
	var min_y: float = 0
	var max_y: float = 0
	for node in data.nodes:
		nodes[node.id] = node
		outgoing[node.id] = []
		incoming[node.id] = []
		adjacency[node.id] = []
	for original in data.edges:
		var edge: Dictionary = original.duplicate(true)
		edge.points = []
		edge.cumulative = [0.0]
		var total: float = 0
		for xy in original.points:
			var p = Vector2(float(xy[0]), float(xy[1]))
			if not edge.points.is_empty(): total += p.distance_to(edge.points[-1])
			edge.points.append(p)
			if edge.points.size() > 1: edge.cumulative.append(total)
			min_y = minf(min_y, p.y); max_y = maxf(max_y, p.y)
		edge.length = total
		edges[edge.id] = edge
		outgoing[edge.from].append(edge.id)
		incoming[edge.to].append(edge.id)
		adjacency[edge.from].append({"node":edge.to,"edge":edge.id,"cost":total})
		adjacency[edge.to].append({"node":edge.from,"edge":edge.id,"cost":total})
	bounds = Rect2(0, min_y, length, maxf(1, max_y-min_y))
	var ground_ids: Array = data.get("presentation",{}).get("ground_edges",[])
	for edge_id in ground_ids:
		for p in edges[edge_id].points:
			if ground_surface.is_empty() or p.distance_to(ground_surface[-1])>.00001:ground_surface.append(p)
	for side in range(2):
		for node_id in nodes:
			var available: Array = outgoing[node_id] if side == 0 else incoming[node_id]
			if not available.is_empty(): choices[side][node_id] = available[0]

func point(edge_id: String, distance: float) -> Vector2:
	var e: Dictionary = edges[edge_id]
	var s: float = clampf(distance, 0, e.length)
	for i in range(1, e.points.size()):
		if s <= float(e.cumulative[i]) + 0.000001:
			var segment: float = float(e.cumulative[i])-float(e.cumulative[i-1])
			return e.points[i-1].lerp(e.points[i], (s-float(e.cumulative[i-1])) / maxf(.000001, segment))
	return e.points[-1]

func anchor(edge_id: String, s: float) -> Dictionary:
	var p = point(edge_id, s)
	return {"edge":edge_id,"s":clampf(s,0,edges[edge_id].length),"x":p.x,"y":p.y}

func at_node(node_id: String, side: int = 0) -> Dictionary:
	var list: Array = outgoing[node_id] if side == 0 else incoming[node_id]
	if list.is_empty(): list = incoming[node_id] if side == 0 else outgoing[node_id]
	var edge_id: String = str(list[0])
	return anchor(edge_id, 0.0 if edges[edge_id].from == node_id else float(edges[edge_id].length))

func project(position: Vector2, edge_filter: String = "") -> Dictionary:
	var best: Dictionary = {}
	var nearest: float = INF
	for edge_id in edges:
		if edge_filter != "" and edge_id != edge_filter: continue
		var e: Dictionary = edges[edge_id]
		for i in range(1, e.points.size()):
			var a: Vector2 = e.points[i-1]; var b: Vector2 = e.points[i]
			var delta: Vector2 = b-a
			var t: float = clampf((position-a).dot(delta) / maxf(delta.length_squared(),.000001),0,1)
			var q: Vector2 = a + delta*t
			var d: float = position.distance_squared_to(q)
			if d < nearest:
				nearest = d
				best = {"edge":edge_id,"s":float(e.cumulative[i-1])+a.distance_to(b)*t,"x":q.x,"y":q.y,"distance":sqrt(d)}
	return best

func apply_anchor(actor: Dictionary, placement: Dictionary):
	for key in ["edge","s","x","y"]: actor[key] = placement[key]

func advance(actor: Dictionary, distance: float, side: int) -> Array:
	var stationary: bool=is_finite(distance) and distance<=0 and actor.has("uid") and int(actor.uid)>0
	if stationary and stationary_projections.has(int(actor.uid)):
		var previous: StationaryProjection=stationary_projections[int(actor.uid)]
		if previous.matches(actor,edges[actor.edge]):stationary_projection_hits+=1;return []
	var crossed: Array = []
	var remaining: float = maxf(0,distance)
	var direction: float = 1.0 if side == 0 else -1.0
	for safety in range(32):
		var e: Dictionary = edges[actor.edge]
		var available: float = float(e.length)-float(actor.s) if side == 0 else float(actor.s)
		var step: float = minf(remaining, available)
		actor.s = clampf(float(actor.s)+step*direction,0,e.length)
		remaining -= step
		if available-step > .000001 or remaining <= .000001: break
		var node_id: String = e.to if side == 0 else e.from
		crossed.append(node_id)
		var next_edges: Array = outgoing[node_id] if side == 0 else incoming[node_id]
		if next_edges.is_empty(): break
		var chosen: String = str(choices[side].get(node_id,next_edges[0]))
		if not next_edges.has(chosen): chosen = next_edges[0]
		actor.edge = chosen
		actor.s = 0.0 if side == 0 else float(edges[chosen].length)
	apply_anchor(actor,anchor(actor.edge,float(actor.s)))
	if stationary and is_finite(float(actor.s)) and is_finite(float(actor.x)) and is_finite(float(actor.y)):
		var uid: int=int(actor.uid)
		if not stationary_projections.has(uid):
			if stationary_projection_order.size()>=STATIONARY_PROJECTION_LIMIT:stationary_projections.erase(stationary_projection_order.pop_front())
			stationary_projection_order.append(uid)
		stationary_projections[uid]=StationaryProjection.new(actor,edges[actor.edge])
	return crossed

func move_to(actor: Dictionary, destination: Dictionary, distance: float) -> bool:
	var remaining: float = maxf(0,distance)
	for safety in range(32):
		if actor.edge == destination.edge:
			var delta: float = float(destination.s)-float(actor.s)
			actor.s = float(actor.s)+signf(delta)*minf(absf(delta),remaining)
			apply_anchor(actor,anchor(actor.edge,float(actor.s)))
			return absf(float(actor.s)-float(destination.s)) < .025
		var plan: Dictionary = route_to(actor,destination)
		if plan.is_empty(): return false
		var e: Dictionary = edges[actor.edge]
		var endpoint: float = 0.0 if plan.exit == e.from else float(e.length)
		var delta: float = endpoint-float(actor.s)
		var step: float = minf(absf(delta),remaining)
		actor.s = float(actor.s)+signf(delta)*step
		remaining -= step
		if absf(endpoint-float(actor.s)) > .000001 or remaining <= .000001:
			apply_anchor(actor,anchor(actor.edge,float(actor.s)))
			return false
		var next_edge: String = str(plan.next_edge)
		actor.edge = next_edge
		actor.s = 0.0 if edges[next_edge].from == plan.exit else float(edges[next_edge].length)
	apply_anchor(actor,anchor(actor.edge,float(actor.s)))
	return false

func shortest_nodes(start: String, goal: String) -> Dictionary:
	if start == goal: return {"distance":0.0,"edges":[]}
	var key: String = start+"|"+goal
	if shortest_cache.has(key): return shortest_cache[key]
	var distances: Dictionary = {start:0.0}
	var previous: Dictionary = {}
	var visited: Dictionary = {}
	for iteration in range(nodes.size()):
		var current: String = ""; var best: float = INF
		for node_id in distances:
			if not visited.has(node_id) and float(distances[node_id]) < best:
				current = node_id; best = float(distances[node_id])
		if current == "": break
		if current == goal: break
		visited[current] = true
		for link in adjacency[current]:
			var proposed: float = best+float(link.cost)
			if proposed < float(distances.get(link.node,INF)):
				distances[link.node] = proposed
				previous[link.node] = {"node":current,"edge":link.edge}
	if not distances.has(goal): return {}
	var path: Array = []; var cursor: String = goal
	while cursor != start:
		var link: Dictionary = previous[cursor]
		path.push_front(link.edge); cursor = link.node
	var result: Dictionary = {"distance":float(distances[goal]),"edges":path}
	shortest_cache[key] = result
	return result

func route_to(actor: Dictionary, destination: Dictionary) -> Dictionary:
	if actor.edge == destination.edge:
		return {"distance":absf(float(actor.s)-float(destination.s)),"exit":"","next_edge":""}
	var a: Dictionary = edges[actor.edge]; var b: Dictionary = edges[destination.edge]
	var best: Dictionary = {}; var nearest: float = INF
	for exit in [a.from,a.to]:
		var first: float = float(actor.s) if exit == a.from else float(a.length)-float(actor.s)
		for entry in [b.from,b.to]:
			var last: float = float(destination.s) if entry == b.from else float(b.length)-float(destination.s)
			var path: Dictionary = shortest_nodes(exit,entry)
			if path.is_empty(): continue
			# A route from an edge interior must leave that edge once and enter
			# the destination once. Endpoint ties otherwise select the actor's
			# edge again and make move_to repeatedly transition to itself.
			if not path.edges.is_empty() and (path.edges[0]==actor.edge or path.edges[-1]==destination.edge):continue
			var d: float = first+float(path.distance)+last
			if d < nearest:
				nearest = d
				best = {"distance":d,"exit":exit,"next_edge":destination.edge if path.edges.is_empty() else path.edges[0]}
	return best

func selected_route_distance(actor: Dictionary, destination: Dictionary, side: int) -> float:
	# Mission HUD and objective checks must follow the route currently selected
	# at each fork. A shortest-path distance can silently choose the other road
	# and make a long bridge or a guarded ground lane look equally close.
	if not edges.has(actor.get("edge", "")) or not edges.has(destination.get("edge", "")):
		return INF
	var direction: float = 1.0 if side == 0 else -1.0
	var edge_id: String = str(actor.edge)
	var offset: float = float(actor.s)
	var total: float = 0.0
	var visited: Dictionary = {}
	for safety in range(64):
		var edge: Dictionary = edges[edge_id]
		if edge_id == str(destination.edge):
			var delta: float = (float(destination.s)-offset)*direction
			if delta >= -0.0001:
				return total+maxf(0.0,delta)
		if visited.has(edge_id):
			return INF
		visited[edge_id]=true
		var node_id: String = str(edge.to if side == 0 else edge.from)
		var available: float = float(edge.length)-offset if side == 0 else offset
		total+=maxf(0.0,available)
		var options: Array = outgoing[node_id] if side == 0 else incoming[node_id]
		if options.is_empty():
			return INF
		var next_edge: String = str(choices[side].get(node_id,options[0]))
		if not options.has(next_edge):
			return INF
		edge_id=next_edge
		offset=0.0 if side == 0 else float(edges[edge_id].length)
	return INF

func objective_reached(actor: Dictionary, destination: Dictionary, side: int) -> bool:
	if not edges.has(actor.get("edge", "")) or not edges.has(destination.get("edge", "")):
		return false
	var direction: float = 1.0 if side == 0 else -1.0
	if actor.edge == destination.edge and (float(actor.s)-float(destination.s))*direction >= -0.025:
		return true
	var distance: float = selected_route_distance(actor,destination,side)
	return is_finite(distance) and distance <= 0.025

func melee_distance(a: Dictionary, b: Dictionary) -> float:
	if a.edge == b.edge: return absf(float(a.s)-float(b.s))
	var ea: Dictionary = edges[a.edge]; var eb: Dictionary = edges[b.edge]
	var best: float = INF
	for node_id in [ea.from,ea.to]:
		if node_id != eb.from and node_id != eb.to: continue
		var da: float = float(a.s) if node_id == ea.from else float(ea.length)-float(a.s)
		var db: float = float(b.s) if node_id == eb.from else float(eb.length)-float(b.s)
		best = minf(best, da+db)
	return best

func set_route(side: int, node_id: String, edge_id: String) -> bool:
	if not nodes.has(node_id): return false
	var options: Array = outgoing[node_id] if side == 0 else incoming[node_id]
	if options.size()<2 or not options.has(edge_id): return false
	choices[side][node_id] = edge_id
	return true

func fork_nodes(side: int) -> Array:
	var result: Array = []
	for node_id in nodes:
		var options: Array = outgoing[node_id] if side == 0 else incoming[node_id]
		if options.size()>1: result.append({"node":node_id,"position":nodes[node_id].position,"options":options,"selected":choices[side][node_id]})
	return result

func ground_y_at(x: float) -> float:
	# Sample the authored main surface at this X. Nearest-point projection
	# changes X on slopes and can accidentally pick a raised parallel road.
	if ground_surface.is_empty():return float(project(Vector2(x,0)).y)
	if x<=ground_surface[0].x:return ground_surface[0].y
	for i in range(1,ground_surface.size()):
		var a: Vector2 = ground_surface[i-1];var b: Vector2 = ground_surface[i]
		if x<=b.x and b.x>a.x:
			return lerpf(a.y,b.y,(x-a.x)/(b.x-a.x))
	return ground_surface[-1].y
