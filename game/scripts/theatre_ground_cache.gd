extends RefCounted
# Cache only static terrain fills. Camera translation and the live fog remain
# separate; no unit, hit effect, mining pose or visibility decision is cached.
var geometry_key: int=0
var meshes: Array=[]
var cursor: int=0
var rebuilds: int=0
var hits: int=0

const Terrain = preload("res://scripts/theatre_ground.gd")
enum Operation { BEGIN, FILL, ART, POLYGON, POLYLINE, LINE, CIRCLE, TEXTURE_RECT, MESH }
var terrain_commands: Array=[]
var terrain_ready: bool=false
var terrain_owner: WeakRef
var terrain_map: WeakRef
var terrain_db: WeakRef
var terrain_scalars: Array=[]
var terrain_shapes: Dictionary={}
var terrain_assets: Dictionary={}
var terrain_textures: Dictionary={}
var terrain_texture_sizes: Dictionary={}
var terrain_reuses: int=0
var terrain_rebuilds: int=0
var terrain_bypasses: int=0
var terrain_mesh_key: int=0
var terrain_meshes: Array=[]
var pending_ready: bool=false
var pending_owner: WeakRef
var pending_map: WeakRef
var pending_db: WeakRef
var pending_scalars: Array=[]

class TextureRelay:
	extends RefCounted
	var source
	var commands: Array
	var assets:
		get:return source.assets
	func _init(value,output: Array):source=value;commands=output
	func art(id: String,portrait: bool=false) -> Texture2D:
		var texture: Texture2D=source.art(id,portrait)
		commands.append([Operation.ART,id,portrait,texture])
		return texture

class MeshRelay:
	extends RefCounted
	var source
	var commands: Array
	func _init(value,output: Array):source=value;commands=output
	func begin(view,sim):
		commands.append([Operation.BEGIN])
		source.begin(view,sim)
	func draw_fill(view,points: PackedVector2Array,color: Color,uv: PackedVector2Array,texture):
		commands.append([Operation.FILL])
		source.draw_fill(view,points,color,uv,texture)

class RecordingCanvas:
	extends RefCounted
	var owner_ref: WeakRef
	var commands: Array=[]
	var db
	var ground_mesh_cache
	var owner:
		get:return owner_ref.get_ref()
	var width:
		get:return owner.width
	var height:
		get:return owner.height
	var camera_x:
		get:return owner.camera_x
	var PX:
		get:return owner.PX
	var PY:
		get:return owner.PY
	func _init(view,cache):
		owner_ref=weakref(view)
		db=TextureRelay.new(view.db,commands)
		ground_mesh_cache=MeshRelay.new(cache,commands)
	func floor_y() -> float:return owner.floor_y()
	func point_to_screen(x: float,y: float) -> Vector2:return owner.point_to_screen(x,y)
	func screen_to_world(x: float) -> float:return owner.screen_to_world(x)
	func draw_colored_polygon(points: PackedVector2Array,color: Color,uv: PackedVector2Array=PackedVector2Array(),texture: Texture2D=null):
		commands.append([Operation.POLYGON,points,color,uv,texture])
		owner.draw_colored_polygon(points,color,uv,texture)
	func draw_polyline(points: PackedVector2Array,color: Color,width_value: float=-1,antialiased: bool=false):
		commands.append([Operation.POLYLINE,points,color,width_value,antialiased])
		owner.draw_polyline(points,color,width_value,antialiased)
	func draw_line(from: Vector2,to: Vector2,color: Color,width_value: float=-1,antialiased: bool=false):
		commands.append([Operation.LINE,from,to,color,width_value,antialiased])
		owner.draw_line(from,to,color,width_value,antialiased)
	func draw_circle(position: Vector2,radius: float,color: Color):
		commands.append([Operation.CIRCLE,position,radius,color])
		owner.draw_circle(position,radius,color)
	func draw_texture_rect(texture: Texture2D,rect: Rect2,tile: bool,modulate: Color=Color.WHITE,transpose: bool=false):
		commands.append([Operation.TEXTURE_RECT,texture,rect,tile,modulate,transpose])
		owner.draw_texture_rect(texture,rect,tile,modulate,transpose)
	func draw_mesh(mesh: Mesh,texture: Texture2D=null,transform: Transform2D=Transform2D.IDENTITY,modulate: Color=Color.WHITE):
		commands.append([Operation.MESH,mesh,texture,transform,modulate])
		owner.draw_mesh(mesh,texture,transform,modulate)

func scalars(view,sim) -> Array:
	return [view.width,view.height,view.floor_y(),view.PX,view.PY,view.camera_x,sim.map.length]

func shapes(sim) -> Dictionary:
	var base_x: PackedFloat64Array=PackedFloat64Array()
	for base in sim.bases:base_x.append(float(base.x))
	return {"definition":sim.map.definition,"nodes":sim.map.nodes,"edges":sim.map.edges,
		"outgoing":sim.map.outgoing,"incoming":sim.map.incoming,"choices":sim.map.choices,
		"surface":sim.map.ground_surface,"base_x":base_x}

func same_inputs(view,sim,values: Array) -> bool:
	if not terrain_ready or terrain_owner.get_ref()!=view or terrain_map.get_ref()!=sim.map or terrain_db.get_ref()!=view.db:return false
	for i in range(values.size()):
		if not is_finite(float(values[i])) or values[i]!=terrain_scalars[i]:return false
	if geometry_key!=terrain_mesh_key or meshes!=terrain_meshes:return false
	if shapes(sim)!=terrain_shapes:return false
	for id in terrain_assets:
		if terrain_assets[id]==null:
			if view.db.assets.has(id):return false
			continue
		if not view.db.assets.has(id) or view.db.assets[id]!=terrain_assets[id]:return false
		# Failed loads can become available later; never freeze a null resource.
		if terrain_textures[id]==null:return false
		var path: String=str(view.db.assets[id].path)
		# After eviction, a new load can fail or resolve to another resource.
		# Draw through the original loader until the exact texture is resident.
		if not view.db.textures.has(path) or not is_same(view.db.textures[path],terrain_textures[id]):return false
		var texture: Texture2D=terrain_textures[id]
		if texture!=null and texture.get_size()!=terrain_texture_sizes[id]:return false
	return true

func draw_terrain(view,sim):
	var values: Array=scalars(view,sim)
	if not same_inputs(view,sim,values):
		var finite: bool=true
		for value in values:
			if not is_finite(float(value)):finite=false;break
		var settled: bool=finite and pending_ready and pending_owner.get_ref()==view and pending_map.get_ref()==sim.map and pending_db.get_ref()==view.db and pending_scalars==values
		if not settled:
			# Moving cameras should not pay the cost of recording a plan that is
			# invalid on the next frame. The unchanged renderer draws this frame.
			pending_ready=finite;pending_owner=weakref(view);pending_map=weakref(sim.map);pending_db=weakref(view.db);pending_scalars=values
			terrain_bypasses+=1
			Terrain.ground(view,sim)
			Terrain.decorations(view,sim)
			return
		pending_ready=false
		var recorder=RecordingCanvas.new(view,self)
		Terrain.ground(recorder,sim)
		Terrain.decorations(recorder,sim)
		terrain_commands=recorder.commands
		terrain_owner=weakref(view);terrain_map=weakref(sim.map);terrain_db=weakref(view.db)
		terrain_scalars=values;terrain_shapes=shapes(sim).duplicate(true)
		terrain_assets.clear();terrain_textures.clear();terrain_texture_sizes.clear()
		for command in terrain_commands:
			if command[0]==Operation.ART:
				terrain_assets[command[1]]=view.db.assets[command[1]].duplicate(true) if view.db.assets.has(command[1]) else null
				terrain_textures[command[1]]=command[3]
				terrain_texture_sizes[command[1]]=Vector2.ZERO if command[3]==null else command[3].get_size()
		terrain_mesh_key=geometry_key;terrain_meshes=meshes.duplicate()
		terrain_ready=true;terrain_rebuilds+=1
		return
	pending_ready=false
	terrain_reuses+=1
	for command in terrain_commands:
		match command[0]:
			Operation.BEGIN:begin(view,sim)
			Operation.FILL:cursor+=1;hits+=1
			Operation.ART:view.db.art(command[1],command[2])
			Operation.POLYGON:view.draw_colored_polygon(command[1],command[2],command[3],command[4])
			Operation.POLYLINE:view.draw_polyline(command[1],command[2],command[3],command[4])
			Operation.LINE:view.draw_line(command[1],command[2],command[3],command[4],command[5])
			Operation.CIRCLE:view.draw_circle(command[1],command[2],command[3])
			Operation.TEXTURE_RECT:view.draw_texture_rect(command[1],command[2],command[3],command[4],command[5])
			Operation.MESH:view.draw_mesh(command[1],command[2],command[3],command[4])

func clear_terrain():
	terrain_ready=false;terrain_commands.clear();terrain_scalars.clear();terrain_shapes.clear()
	terrain_assets.clear();terrain_textures.clear();terrain_texture_sizes.clear()
	terrain_owner=null;terrain_map=null;terrain_db=null
	terrain_meshes.clear();pending_ready=false;pending_scalars.clear()
	pending_owner=null;pending_map=null;pending_db=null

func begin(view,sim):
	var key: int=[sim.map.definition.hash(),view.width,view.height,view.floor_y(),view.PX,view.PY].hash()
	if key!=geometry_key:
		geometry_key=key;meshes.clear();rebuilds+=1
	cursor=0

func draw_fill(view,points: PackedVector2Array,color: Color,uv: PackedVector2Array,texture):
	var index: int=cursor;cursor+=1
	if index>=meshes.size():
		var triangles: PackedInt32Array=Geometry2D.triangulate_polygon(points)
		if triangles.is_empty():
			meshes.append(null)
		else:
			var vertices=PackedVector3Array();var colors=PackedColorArray()
			for p in points:
				vertices.append(Vector3(p.x+view.camera_x*view.PX-view.width*.5,p.y,0))
				colors.append(color)
			var arrays: Array=[];arrays.resize(Mesh.ARRAY_MAX)
			arrays[Mesh.ARRAY_VERTEX]=vertices;arrays[Mesh.ARRAY_COLOR]=colors;arrays[Mesh.ARRAY_INDEX]=triangles
			if not uv.is_empty():arrays[Mesh.ARRAY_TEX_UV]=uv
			var mesh=ArrayMesh.new();mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES,arrays)
			meshes.append(mesh)
	else:hits+=1
	if meshes[index]==null:
		view.draw_colored_polygon(points,color,uv,texture)
	else:
		view.draw_mesh(meshes[index],texture,Transform2D(0,Vector2(view.width*.5-view.camera_x*view.PX,0)))
