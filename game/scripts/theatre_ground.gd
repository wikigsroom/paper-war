extends RefCounted
# Geometry follows the simulation; material and paper layers only stage that geometry.
const PALETTES={
	"yin":["c8b18a","7f9464","8e704f"],"mo":["a99fac","8d9d79","645a73"],
	"deng":["cfb88d","ad9e73","917650"],"ji":["b6afa3","899b90","766d62"],
	"yuan":["c0b597","8eaa95","7c8167"],"qi":["afba93","7f9b60","657658"],
	"mu":["b4af88","799452","706c4e"],"shuang":["c6d5d8","e2f0ea","8ba8b1"],
	"jin":["c8b095","bc976c","8c675b"],"bai":["c7c1ac","b1bba3","848777"]}

static func surface(view,sim) -> PackedVector2Array:
	var top=PackedVector2Array()
	# A world-fixed lattice and the actual road vertices. Camera-dependent end
	# points changed triangulation/UVs every frame and made slopes visibly swim.
	var samples: Array=[0.0,float(sim.map.length)]
	for i in range(1,int(ceilf(sim.map.length/.42))):samples.append(float(i)*.42)
	for edge in sim.map.edges.values():
		for p in edge.points:samples.append(clampf(p.x,0,sim.map.length))
	samples.sort()
	var last: float=-INF
	for x in samples:
		if absf(float(x)-last)<.0001:continue
		top.append(view.point_to_screen(x,sim.map.ground_y_at(x)));last=x
	return top

static func textured(view,points: PackedVector2Array,color: Color):
	var texture=view.db.art("material.common.earth")
	var uv=PackedVector2Array()
	if texture!=null:
		for p in points:uv.append(Vector2((p.x+view.camera_x*view.PX-view.width*.5)/512.0,p.y/512.0))
	view.ground_mesh_cache.draw_fill(view,points,color,uv,texture)

static func ground(view,sim):
	view.ground_mesh_cache.begin(view,sim)
	var top: PackedVector2Array=surface(view,sim)
	if top.size()<2:return
	var palette: Array=PALETTES.get(sim.map.definition.region,PALETTES.yin)
	var soil=Color(palette[0]);var sod=Color(palette[1]);var stone=Color(palette[2])
	var base=top.duplicate();base.append(Vector2(top[-1].x,view.height));base.append(Vector2(top[0].x,view.height))
	textured(view,base,soil)
	# Uneven laminations and their paper shadows replace broad uniform bands.
	var previous=top
	for layer in [28.0,67.0,112.0,168.0,234.0,308.0]:
		var edge=PackedVector2Array()
		for p in top:
			var wx: float=view.screen_to_world(p.x)
			var ripple: float=sin(wx*.72+layer*.09)*5+sin(wx*2.8+layer)*2
			edge.append(p+Vector2(0,layer+ripple))
		var band=previous.duplicate()
		for i in range(edge.size()-1,-1,-1):band.append(edge[i])
		var tint: Color=soil.lerp(stone,clampf(layer/580.0,0,.6))
		textured(view,band,tint)
		view.draw_polyline(edge,Color(stone,.26),3.0,true)
		var highlight=edge.duplicate()
		for i in range(highlight.size()):highlight[i]+=Vector2(0,-1.5)
		view.draw_polyline(highlight,Color("e9dcc3") if sim.map.definition.region!="shuang" else Color("eff7f2"),1,true)
		previous=edge
	cap_layer(view,sim,top)
	var seam=PackedVector2Array();var lip=PackedVector2Array()
	for p in top:seam.append(p+Vector2(0,11));lip.append(p+Vector2(0,5))
	view.draw_polyline(seam,stone.darkened(.10),12.0,true)
	view.draw_polyline(lip,sod,9.0,true)
	view.draw_polyline(top,Color("f7e8c9") if sim.map.definition.region!="shuang" else Color("f5fcf8"),3.0,true)
	var first: int=maxi(0,int(view.screen_to_world(-150)/1.35))
	var last: int=mini(int(sim.map.length/1.35)+1,int(view.screen_to_world(view.width+150)/1.35)+1)
	for n in range(first,last):
		var x: float=.5+n*1.35
		var p: Vector2=view.point_to_screen(x,sim.map.ground_y_at(x))
		var deterministic: float=sin(n*13.83)*.5+.5
		# Fragments lie below the road; they never imply an extra traversable ledge.
		var chip=p+Vector2(0,39+deterministic*42)
		var shard=PackedVector2Array([chip+Vector2(-14,1),chip+Vector2(-3,-5),chip+Vector2(19,-2),chip+Vector2(12,6),chip+Vector2(-8,8)])
		view.draw_colored_polygon(shard,soil.lerp(stone,.13+deterministic*.18))
		view.draw_line(chip+Vector2(-13,1),chip+Vector2(17,-2),Color("e4d2b5"),1,true)
		if n%3==1:
			var root=p+Vector2(0,17)
			var roots=PackedVector2Array([root,root+Vector2(5,15),root+Vector2(-2,24),root+Vector2(3,39)])
			view.draw_polyline(roots,Color(stone,.24),1.3,true)
			view.draw_line(root+Vector2(5,15),root+Vector2(14,22),Color(stone,.22),1,true)
		if clear_object(sim,x,.8) and n%2==0:
			var leaf=PackedVector2Array([p+Vector2(-10,5),p+Vector2(-6,-5),p+Vector2(-2,1),p+Vector2(2,-10),p+Vector2(5,1),p+Vector2(11,-4),p+Vector2(8,6)])
			view.draw_colored_polygon(leaf,sod)
			view.draw_line(p+Vector2(-4,4),p+Vector2(3,-3),sod.lightened(.22),1,true)
	for id in sim.map.edges:
		var e: Dictionary=sim.map.edges[id]
		if e.get("route_role","")=="bridge":bridge(view,sim,e,id,stone)

static func cap_layer(view,sim,top: PackedVector2Array):
	var region: String=sim.map.definition.region
	var type: String="ice" if region=="shuang" else "forest" if region in ["qi","mu"] else "slate" if region in ["mo","ji","bai"] else "grass"
	var id: String="material.common.edge."+type
	var tex=view.db.art(id)
	if tex==null:return
	var walk: float=float(view.db.assets[id].walk_y)
	var depth: float=minf(190,float(tex.get_height())-walk-1)
	# Each UV row uses the local real surface height. Grass never creates a
	# second road and the cut-earth skin follows hills without flattening them.
	# Each fixed world strip has its own four vertices. Ear-clipping one large
	# concave cap changed diagonal connections and interpolated unrelated hills.
	for i in range(top.size()-1):
		var p: Vector2=top[i];var q: Vector2=top[i+1]
		if q.x<-200 or p.x>view.width+200:continue
		var u: float=view.screen_to_world(p.x)*view.PX/512.0
		var v: float=view.screen_to_world(q.x)*view.PX/512.0
		var a: float=(walk-25)/float(tex.get_height());var b: float=(walk+depth)/float(tex.get_height())
		var points=PackedVector2Array([p+Vector2(0,-25),q+Vector2(0,-25),q+Vector2(0,depth),p+Vector2(0,depth)])
		view.draw_colored_polygon(points,Color(1,1,1,.90),PackedVector2Array([Vector2(u,a),Vector2(v,a),Vector2(v,b),Vector2(u,b)]),tex)

static func clear_object(sim,x: float,radius: float) -> bool:
	for m in sim.map.definition.mines+sim.map.definition.build_sites:
		if absf(float(m.x)-x)<radius:return false
	for b in sim.bases:
		if absf(float(b.x)-x)<radius:return false
	for side in range(2):
		for fork in sim.map.fork_nodes(side):
			if absf(float(fork.position[0])-x)<radius:return false
	return true

static func bridge(view,sim,e: Dictionary,id: String,stone: Color):
	var upper=PackedVector2Array()
	var divisions: int=maxi(2,int(ceilf(e.length/.44)))
	for i in range(divisions+1):
		var pp: Vector2=sim.map.point(id,float(e.length)*i/divisions)
		upper.append(view.point_to_screen(pp.x,pp.y))
	var slab=upper.duplicate()
	for i in range(upper.size()-1,-1,-1):slab.append(upper[i]+Vector2(0,19))
	view.draw_polyline(upper,Color(stone,.22),29,true)
	textured(view,slab,Color("b9966a"))
	view.draw_polyline(upper,Color("fff1d2"),5,true)
	var underside=PackedVector2Array()
	for p in upper:underside.append(p+Vector2(0,19))
	view.draw_polyline(underside,Color("5b5146"),3,true)
	for i in range(1,upper.size()-1):
		var p: Vector2=upper[i]
		view.draw_line(p+Vector2(0,3),p+Vector2(0,16),Color("846744"),1.2,true)
		view.draw_line(p+Vector2(2,4),p+Vector2(2,15),Color("dbc8a0"),1,true)
	for t in [.25,.5,.75]:
		var pp: Vector2=sim.map.point(id,float(e.length)*t)
		var p: Vector2=view.point_to_screen(pp.x,pp.y)
		var bottom: Vector2=view.point_to_screen(pp.x,sim.map.ground_y_at(pp.x))
		if bottom.y-p.y<26:continue
		var support=PackedVector2Array([p+Vector2(-9,18),p+Vector2(9,18),bottom+Vector2(16,11),bottom+Vector2(-15,11)])
		textured(view,support,Color("9b815e"))
		view.draw_line(p+Vector2(-6,22),bottom+Vector2(-11,7),Color("e4cf9c"),2,true)
		view.draw_line(p+Vector2(8,28),bottom+Vector2(37,0),Color("816b4e"),5,true)
		view.draw_line(bottom+Vector2(-22,9),bottom+Vector2(27,9),Color("b6a281"),7,true)
	var rope=PackedVector2Array()
	for i in range(upper.size()):rope.append(upper[i]+Vector2(0,-17+sin(float(i)*.7)*2))
	view.draw_polyline(rope,Color("a58b63"),2,true)
	for i in range(0,upper.size(),4):
		var p: Vector2=upper[i]
		view.draw_line(p+Vector2(0,-20),p+Vector2(0,6),Color("6c5c47"),4,true)
		view.draw_circle(p+Vector2(0,-20),3,Color("dbc5a0"))

static func decorations(view,sim):
	var tex=view.db.art("prop."+sim.map.definition.region+".terrain")
	if tex==null:return
	for n in range(int(sim.map.length/5.7)):
		var x: float=4.6+float(n)*5.7
		if not clear_object(sim,x,2.2):continue
		var p: Vector2=view.point_to_screen(x,sim.map.ground_y_at(x))
		if p.x<-150 or p.x>view.width+150:continue
		var variant: float=.72+float(n%3)*.13
		var size=Vector2(97,105)*variant
		view.draw_texture_rect(tex,Rect2(p-Vector2(size.x*.5,size.y*476.0/512.0)+Vector2(0,-3),size),false,Color(1,1,1,.87))
