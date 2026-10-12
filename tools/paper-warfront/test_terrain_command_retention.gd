extends SceneTree
# The oracle is loaded from the frozen, unmodified RC30 terrain and mesh helper.
# Compare ordered native drawing parameters, including actual mesh surface arrays.
const Data=preload("res://scripts/data_store.gd")
const Map=preload("res://scripts/map_runtime.gd")
const Candidate=preload("res://scripts/theatre_ground_cache.gd")
var checks: int=0
var failures: Array=[]
var mesh_geometry_present: bool=false
var original_ground: GDScript
var original_cache: GDScript
var draw_calls: int=0

class Scenario:
	extends RefCounted
	var map
	var bases: Array=[]
	func _init(value):
		map=value
		for base in map.definition.bases:
			bases.append({"x":float(map.nodes[base.node].position[0])})

class TraceDB:
	extends RefCounted
	var assets: Dictionary={}
	var textures: Dictionary={}
	var loaded: Dictionary={}
	var blocked: Dictionary={}
	var events: Array=[]
	var texture_clock: int=0
	func _init(definitions: Dictionary):
		for id in definitions:
			if id.begins_with("material.common.") or (id.begins_with("prop.") and id.ends_with(".terrain")):
				assets[id]=definitions[id].duplicate(true)
				var path: String=str(assets[id].path)
				loaded[path]=ImageTexture.create_from_image(Image.create(512,512,false,Image.FORMAT_RGBA8))
	func art(id: String,portrait: bool=false) -> Texture2D:
		events.append(["art",id,portrait]);texture_clock+=1
		if not assets.has(id) or blocked.get(id,false):return null
		var path: String=str(assets[id].path)
		if not textures.has(path):textures[path]=loaded[path]
		return textures[path]

class TraceCanvas:
	extends RefCounted
	var width: float=1280
	var height: float=720
	var floor: float=525
	var camera_x: float=8.173
	var PX: float=112
	var PY: float=64
	var events: Array=[]
	var db
	var ground_mesh_cache
	func _init(data,cache):db=data;ground_mesh_cache=cache
	func floor_y() -> float:return floor
	func point_to_screen(x: float,y: float) -> Vector2:
		return Vector2(width*.5+(x-camera_x)*PX,floor_y()+y*PY)
	func screen_to_world(x: float) -> float:return (x-width*.5)/PX+camera_x
	func draw_colored_polygon(points: PackedVector2Array,color: Color,uv: PackedVector2Array=PackedVector2Array(),texture: Texture2D=null):events.append(["polygon",points,color,uv,texture])
	func draw_polyline(points: PackedVector2Array,color: Color,line_width: float=-1,antialiased: bool=false):events.append(["polyline",points,color,line_width,antialiased])
	func draw_line(from: Vector2,to: Vector2,color: Color,line_width: float=-1,antialiased: bool=false):events.append(["line",from,to,color,line_width,antialiased])
	func draw_circle(position: Vector2,radius: float,color: Color):events.append(["circle",position,radius,color])
	func draw_texture_rect(texture: Texture2D,rect: Rect2,tile: bool,modulate: Color=Color.WHITE,transpose: bool=false):events.append(["texture_rect",texture,rect,tile,modulate,transpose])
	func draw_mesh(mesh: Mesh,texture: Texture2D=null,transform: Transform2D=Transform2D.IDENTITY,modulate: Color=Color.WHITE):
		var arrays: Array=[]
		for index in range(mesh.get_surface_count()):arrays.append(mesh.surface_get_arrays(index))
		events.append(["mesh",arrays,texture,transform,modulate])

func _initialize():call_deferred("run")
func verify(value: bool,note: String):
	checks+=1
	if not value and failures.size()<30:failures.append(note)

func compare(actual,reference,scenario,note: String):
	reference.events=[];reference.db.events=reference.events
	var clock: int=reference.db.texture_clock
	original_ground.ground(reference,scenario)
	original_ground.decorations(reference,scenario)
	var expected_clock: int=reference.db.texture_clock-clock
	actual.events=[];actual.db.events=actual.events;clock=actual.db.texture_clock
	actual.ground_mesh_cache.draw_terrain(actual,scenario)
	verify(actual.events==reference.events,note+" ordered native parameters")
	verify(actual.db.texture_clock-clock==expected_clock,note+" identical texture touches")
	for event in actual.events:
		if event[0]=="mesh" and not event[1].is_empty() and not event[1][0][Mesh.ARRAY_INDEX].is_empty():mesh_geometry_present=true
	draw_calls+=1

func triple(actual,reference,scenario,note: String):
	for frame in range(3):compare(actual,reference,scenario,note+" frame "+str(frame))

func run():
	var args=OS.get_cmdline_user_args()
	assert(args.has("--baseline-ground") and args.has("--baseline-cache") and args.has("--output"))
	original_ground=load(args[args.find("--baseline-ground")+1]);original_cache=load(args[args.find("--baseline-cache")+1])
	var data=Data.new();var db=TraceDB.new(data.assets)
	for definition in data.maps.values():
		for display in ["desktop","phone"]:
			var scenario=Scenario.new(Map.new(definition))
			var actual=TraceCanvas.new(db,Candidate.new());var reference=TraceCanvas.new(db,original_cache.new())
			if display=="phone":
				actual.width=1136;actual.height=640;actual.floor=480
				reference.width=actual.width;reference.height=actual.height;reference.floor=actual.floor
			for fraction in [.321,.673]:
				actual.camera_x=scenario.map.length*fraction+.173;reference.camera_x=actual.camera_x
				var hits: int=actual.ground_mesh_cache.terrain_reuses
				triple(actual,reference,scenario,definition.id+" "+display+" "+str(fraction))
				verify(actual.ground_mesh_cache.terrain_reuses>hits,definition.id+" actual retained native commands "+display)
	# Independent mutations exercise validity, rather than deriving expected
	# commands from the cached plan. Both views always use the same current map.
	var scenario=Scenario.new(Map.new(data.maps["map.01.04"]))
	var cache=Candidate.new()
	var actual=TraceCanvas.new(db,cache);var reference=TraceCanvas.new(db,original_cache.new())
	triple(actual,reference,scenario,"prime mutation fixture")
	for field in ["camera_x","width","height","floor","PX","PY"]:
		actual.set(field,float(actual.get(field))+.00000001);reference.set(field,actual.get(field))
		var hits: int=cache.terrain_reuses
		compare(actual,reference,scenario,"changed exact scalar "+field)
		verify(cache.terrain_reuses==hits,"no stale scalar reuse "+field)
		triple(actual,reference,scenario,"settled scalar "+field)
	for i in range(12):
		actual.camera_x+=.03173;reference.camera_x=actual.camera_x
		var rebuilds: int=cache.terrain_rebuilds;var bypasses: int=cache.terrain_bypasses
		compare(actual,reference,scenario,"moving camera "+str(i))
		verify(cache.terrain_rebuilds==rebuilds and cache.terrain_bypasses>bypasses,"moving camera bypass without recording "+str(i))
	triple(actual,reference,scenario,"camera stopped")
	for mutation in ["surface","edge_points","edge_length","base","mine","region","node","choices","outgoing","incoming"]:
		var edge: Dictionary=scenario.map.edges.values()[0]
		var node_id: String=scenario.map.nodes.keys()[0]
		match mutation:
			"surface":scenario.map.ground_surface[0]+=Vector2(.003,.013)
			"edge_points":edge.points[1]+=Vector2(.011,.023)
			"edge_length":edge.length+=.001
			"base":scenario.bases[0].x+=.25
			"mine":scenario.map.definition.mines[0].x+=.7
			"region":scenario.map.definition.region="shuang"
			"node":scenario.map.nodes[node_id].position[0]+=.02
			"choices":scenario.map.choices[0]["diagnostic-only"]="changed"
			"outgoing":scenario.map.outgoing["diagnostic-only"]=[]
			"incoming":scenario.map.incoming["diagnostic-only"]=[]
		var hits: int=cache.terrain_reuses
		compare(actual,reference,scenario,"mutated live "+mutation)
		verify(cache.terrain_reuses==hits,"live mutation invalidates "+mutation)
		triple(actual,reference,scenario,"settled live "+mutation)
	var cap: String="material.common.edge.ice"
	var metadata: Dictionary=db.assets[cap].duplicate(true)
	db.assets.erase(cap);triple(actual,reference,scenario,"missing cap asset")
	db.assets[cap]=metadata;triple(actual,reference,scenario,"added previously missing cap asset")
	db.assets[cap].walk_y+=3;triple(actual,reference,scenario,"edited edge metadata")
	var path: String=str(db.assets[cap].path)
	db.loaded[path]=ImageTexture.create_from_image(Image.create(512,512,false,Image.FORMAT_RGBA8));db.textures[path]=db.loaded[path]
	triple(actual,reference,scenario,"replaced texture resource")
	db.loaded[path].set_image(Image.create(512,640,false,Image.FORMAT_RGBA8))
	triple(actual,reference,scenario,"changed texture dimensions")
	db.blocked[cap]=true;db.textures.erase(path);triple(actual,reference,scenario,"transient failed texture load")
	db.blocked[cap]=false;triple(actual,reference,scenario,"texture recovered after failed load")
	cache.meshes.clear();reference.ground_mesh_cache.meshes.clear()
	triple(actual,reference,scenario,"native mesh pool cleared")
	cache.clear_terrain();triple(actual,reference,scenario,"battle reset clears command plan")
	scenario.map=Map.new(data.maps["map.01.04"])
	triple(actual,reference,scenario,"replacement map same identifier")
	actual=TraceCanvas.new(db,cache)
	reference=TraceCanvas.new(db,original_cache.new())
	triple(actual,reference,scenario,"replacement owner")
	var new_db=TraceDB.new(data.assets);actual.db=new_db;reference.db=new_db
	triple(actual,reference,scenario,"replacement data store")
	cache.clear_terrain()
	verify(cache.terrain_commands.is_empty() and cache.terrain_meshes.is_empty() and cache.pending_scalars.is_empty(),"clear releases retained plan resources")
	triple(actual,reference,scenario,"prime weak ownership")
	var owner_ref: WeakRef=weakref(actual);var map_ref: WeakRef=weakref(scenario.map);var db_ref: WeakRef=weakref(new_db)
	actual=null;reference=null;scenario=null;new_db=null
	verify(owner_ref.get_ref()==null and map_ref.get_ref()==null and db_ref.get_ref()==null,"plan does not retain view, map or database")
	verify(mesh_geometry_present,"native mesh surface arrays were present in comparison")
	var report={"passed":failures.is_empty(),"checks":checks,"failures":failures,"maps":data.maps.size(),"native_draw_comparisons":draw_calls,"mesh_geometry_present":mesh_geometry_present,
		"source_sha256":FileAccess.get_sha256("res://scripts/theatre_ground_cache.gd" if FileAccess.file_exists("res://scripts/theatre_ground_cache.gd") else "res://scripts/theatre_ground_cache.gdc"),"ground_sha256":FileAccess.get_sha256("res://scripts/theatre_ground.gd" if FileAccess.file_exists("res://scripts/theatre_ground.gd") else "res://scripts/theatre_ground.gdc"),"reference_ground_sha256":FileAccess.get_sha256(original_ground.resource_path),"reference_cache_sha256":FileAccess.get_sha256(original_cache.resource_path),"observer_sha256":FileAccess.get_sha256(get_script().resource_path),
		"scope":"Exact ordered native command and mesh surface parameters against frozen RC30 helpers across 200 maps, two layouts and two fractional cameras with actual cache reuse. Independent geometry, metadata, missing/added assets, failed/recovered texture, dimensions, replacement owners and resets. Synthetic textures isolate native parameters; actual raster equivalence and natural FPS are separate checks. Not Android hardware or full balance."}
	FileAccess.open(args[args.find("--output")+1],FileAccess.WRITE).store_string(JSON.stringify(report,"  "))
	print("TERRAIN_COMMAND_RETENTION ",checks," checks; draw comparisons=",draw_calls," failures=",failures)
	quit(0 if failures.is_empty() else 1)
