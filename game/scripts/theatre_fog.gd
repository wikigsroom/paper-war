extends RefCounted
# Presentation of authoritative road sight. No camera or pixel reveals vision.
# A full-height wash follows each road's own intervals, including split levels.
const STEP: float=.24
const FEATHER: float=.9
const UNKNOWN_ALPHA: float=.90
const REMEMBERED_ALPHA: float=.56
var columns: Array=[]
var geometry_key: int=0
var mesh_key: int=0
var mesh: ArrayMesh

static func interval_depth(spans: Array,s: float,length: float) -> float:
	var depth: float=-1
	for span in spans:
		if s<span.x-.0001 or s>span.y+.0001:continue
		var left: float=INF if span.x<=.0001 else maxf(0,s-span.x)
		var right: float=INF if span.y>=length-.0001 else maxf(0,span.y-s)
		depth=maxf(depth,minf(left,right))
	return depth

static func opacity(visibility,side: int,anchor: Dictionary,length: float) -> float:
	var live: float=interval_depth(visibility.current[side].get(anchor.edge,[]),float(anchor.s),length)
	var known: float=interval_depth(visibility.explored[side].get(anchor.edge,[]),float(anchor.s),length)
	var memory: float=smoothstep(0,FEATHER,maxf(0,known))
	var clear: float=smoothstep(0,FEATHER,maxf(0,live))
	return lerpf(UNKNOWN_ALPHA,REMEMBERED_ALPHA,memory)*(1-clear)

static func road_section(map,edge_id: String,x: float) -> Dictionary:
	var edge: Dictionary=map.edges[edge_id]
	for i in range(1,edge.points.size()):
		var a: Vector2=edge.points[i-1];var b: Vector2=edge.points[i]
		if x<minf(a.x,b.x)-.0001 or x>maxf(a.x,b.x)+.0001 or absf(b.x-a.x)<.00001:continue
		var t: float=clampf((x-a.x)/(b.x-a.x),0,1)
		return {"edge":edge_id,"s":float(edge.cumulative[i-1])+a.distance_to(b)*t,"x":x,"y":lerpf(a.y,b.y,t)}
	return {}

func prepare(map):
	var key: int=map.definition.hash()
	if key==geometry_key and not columns.is_empty():return
	geometry_key=key;mesh_key=0;columns.clear()
	var cuts: Array=[0.0,float(map.length)]
	for n in range(1,int(ceilf(map.length/STEP))):cuts.append(n*STEP)
	for edge in map.edges.values():
		for point in edge.points:cuts.append(float(point.x))
	cuts.sort()
	for i in range(cuts.size()-1):
		var lo: float=cuts[i];var hi: float=cuts[i+1]
		if hi-lo<.00001:continue
		var roads: Array=[]
		for id in map.edges:
			var center: Dictionary=road_section(map,id,(lo+hi)*.5)
			if not center.is_empty():roads.append(center)
		roads.sort_custom(func(a,b):return float(a.y)<float(b.y))
		var samples: Array=[]
		for road in roads:
			samples.append({"left":road_section(map,road.edge,lo),"right":road_section(map,road.edge,hi)})
		if samples.is_empty():
			# The stage includes paper margins beyond the first/last road node.
			# They inherit the endpoint's sight, instead of leaving a bright hole.
			var endpoint: Dictionary=map.project(Vector2((lo+hi)*.5,0))
			if not endpoint.is_empty():samples.append({"left":endpoint,"right":endpoint.duplicate()})
		if not samples.is_empty():columns.append({"lo":lo,"hi":hi,"roads":samples})

static func mist_color(region: String,x: float,y: float,alpha: float) -> Color:
	var hue: Color=Color("99948a")
	if region in ["mo","bai"]:hue=Color("97929e")
	elif region=="shuang":hue=Color("a3b2b6")
	elif region in ["mu","qi"]:hue=Color("969d8b")
	# World-fixed fibers, not a moving screen pattern or a field of dark blocks.
	var grain: float=(sin(x*1.17+y*.53)+sin(x*3.09-y*.71))*.012
	hue=hue.lightened(maxf(0,grain)) if grain>=0 else hue.darkened(-grain)
	hue.a=alpha
	return hue

static func vertical_alpha(roads: Array,alphas: Array,y: float,end: String) -> float:
	for i in range(roads.size()-1):
		var a: float=float(roads[i][end].y);var b: float=float(roads[i+1][end].y)
		var middle: float=(a+b)*.5
		var feather: float=maxf(.015,minf(.65,(b-a)*.4))
		if y<middle-feather:return float(alphas[i])
		if y<=middle+feather:return lerpf(float(alphas[i]),float(alphas[i+1]),smoothstep(middle-feather,middle+feather,y))
	return float(alphas[-1])

static func vertical_cuts(roads: Array,end: String,top: float,bottom: float) -> Array:
	var cuts: Array=[top,lerpf(top,bottom,.25),lerpf(top,bottom,.5),lerpf(top,bottom,.75),bottom]
	for i in range(roads.size()-1):
		var a: float=float(roads[i][end].y);var b: float=float(roads[i+1][end].y)
		var middle: float=(a+b)*.5
		var feather: float=maxf(.015,minf(.65,(b-a)*.4))
		for y in [middle-feather,middle,middle+feather]:cuts.append(clampf(y,top,bottom))
	cuts.sort()
	return cuts

func draw(view):
	var sim=view.sim
	if not sim.config.get("fog",true):return
	prepare(sim.map)
	var field: Rect2=view.playfield_rect()
	if not field.has_area():return
	var top: float=(field.position.y-view.floor_y())/view.PY
	var bottom: float=(field.end.y-view.floor_y())/view.PY
	var side: int=view.player_side
	var first_x: float=floorf(view.screen_to_world(field.position.x)/STEP)*STEP-STEP
	var last_x: float=ceilf(view.screen_to_world(field.end.x)/STEP)*STEP+STEP
	var key: int=[geometry_key,side,sim.visibility.current[side].hash(),sim.visibility.explored[side].hash(),top,bottom,first_x,last_x].hash()
	if mesh==null or key!=mesh_key:
		mesh_key=key
		var vertices=PackedVector3Array();var colors=PackedColorArray();var indices=PackedInt32Array()
		for column in columns:
			if column.hi<first_x or column.lo>last_x:continue
			var roads: Array=column.roads
			var left_alpha: Array=[];var right_alpha: Array=[];var total_alpha: float=0
			for road in roads:
				var length: float=sim.map.edges[road.left.edge].length
				left_alpha.append(opacity(sim.visibility,side,road.left,length));right_alpha.append(opacity(sim.visibility,side,road.right,length))
				total_alpha+=float(left_alpha[-1])+float(right_alpha[-1])
			if total_alpha<.00001:continue
			var left_cuts: Array=vertical_cuts(roads,"left",top,bottom)
			var right_cuts: Array=vertical_cuts(roads,"right",top,bottom)
			for layer in range(left_cuts.size()-1):
				var points: Array=[Vector2(column.lo,left_cuts[layer]),Vector2(column.hi,right_cuts[layer]),Vector2(column.hi,right_cuts[layer+1]),Vector2(column.lo,left_cuts[layer+1])]
				var first: int=vertices.size()
				for j in range(4):
					var point: Vector2=points[j]
					var alpha: float=vertical_alpha(roads,left_alpha if j in [0,3] else right_alpha,point.y,"left" if j in [0,3] else "right")
					var density: float=lerpf(.84,1.0,clampf((point.y-top)/maxf(.001,bottom-top),0,1))
					vertices.append(Vector3(point.x*view.PX,point.y*view.PY,0))
					colors.append(mist_color(str(sim.map.definition.region),point.x,point.y,alpha*density))
				indices.append_array(PackedInt32Array([first,first+1,first+2,first,first+2,first+3]))
		mesh=ArrayMesh.new()
		if not vertices.is_empty():
			var arrays: Array=[];arrays.resize(Mesh.ARRAY_MAX)
			arrays[Mesh.ARRAY_VERTEX]=vertices;arrays[Mesh.ARRAY_COLOR]=colors;arrays[Mesh.ARRAY_INDEX]=indices
			mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES,arrays)
	if mesh.get_surface_count()>0:
		view.draw_mesh(mesh,null,Transform2D(0,Vector2(view.width*.5-view.camera_x*view.PX,view.floor_y())))
