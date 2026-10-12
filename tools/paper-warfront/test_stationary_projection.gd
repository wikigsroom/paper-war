extends SceneTree
const Data=preload("res://scripts/data_store.gd")
const Map=preload("res://scripts/map_runtime.gd")
const OriginalMap=preload("dense_reference_map_runtime.gd")
var checks: int=0
var failures: Array=[]
func _initialize():call_deferred("run")
func verify(value: bool,note: String):
	checks+=1
	if not value and failures.size()<30:failures.append(note)
func compare(actual_map,original_map,a: Dictionary,b: Dictionary,distance: float,side: int,note: String):
	var expected: Array=original_map.advance(b,distance,side)
	var actual: Array=actual_map.advance(a,distance,side)
	verify(actual==expected and a==b and PackedFloat64Array([a.s,a.x,a.y]).to_byte_array()==PackedFloat64Array([b.s,b.x,b.y]).to_byte_array(),note)
func run():
	var db=Data.new();var args=OS.get_cmdline_user_args()
	var original_script: GDScript=load(args[args.find("--baseline-map")+1]) if args.has("--baseline-map") else OriginalMap
	for definition in db.maps.values():
		var actual_map=Map.new(definition);var original_map=original_script.new(definition)
		var uid: int=1
		for edge_id in actual_map.edges:
			var length: float=float(actual_map.edges[edge_id].length)
			for side in [0,1]:
				for proportion in [0.0,.25,.5,1.0]:
					var a: Dictionary=actual_map.anchor(edge_id,length*proportion);a.uid=uid;uid+=1
					var b: Dictionary=a.duplicate(true)
					compare(actual_map,original_map,a,b,0,side,"first canonical zero "+definition.id)
					var hits: int=actual_map.stationary_projection_hits
					compare(actual_map,original_map,a,b,0,side,"retained canonical zero "+definition.id)
					verify(actual_map.stationary_projection_hits>hits,"actual retained projection "+definition.id)
					compare(actual_map,original_map,a,b,-1,side,"negative travel clamps to zero "+definition.id)
					a.x+=.01;b.x+=.01
					compare(actual_map,original_map,a,b,0,side,"edited Cartesian point canonicalized "+definition.id)
					a=a.duplicate(true);b=b.duplicate(true)
					compare(actual_map,original_map,a,b,0,side,"replacement uid keeps actual actor identity "+definition.id)
					a.s=-1.0;b.s=-1.0
					compare(actual_map,original_map,a,b,0,side,"invalid negative arc normalized "+definition.id)
					a.s=length+1;b.s=length+1
					compare(actual_map,original_map,a,b,0,side,"overshoot normalized "+definition.id)
					compare(actual_map,original_map,a,b,.02,side,"positive boundary crossing remains original "+definition.id)
		var edge_id: String=actual_map.edges.keys()[0]
		var edge: Dictionary=actual_map.edges[edge_id];var original: Dictionary=original_map.edges[edge_id]
		var a: Dictionary=actual_map.anchor(edge_id,float(edge.length)*.2);a.uid=100000
		var b: Dictionary=a.duplicate(true)
		compare(actual_map,original_map,a,b,0,0,"prime edited geometry "+definition.id)
		edge.points[1]+=Vector2(0,.01);original.points[1]+=Vector2(0,.01)
		compare(actual_map,original_map,a,b,0,0,"changed edge point "+definition.id)
		edge.cumulative[1]+=.01;original.cumulative[1]+=.01
		compare(actual_map,original_map,a,b,0,0,"changed cumulative length "+definition.id)
		edge.length+=.01;original.length+=.01
		compare(actual_map,original_map,a,b,0,0,"changed edge length "+definition.id)
		for i in range(270):
			var actor: Dictionary=actual_map.anchor(edge_id,float(edge.length)*.3);actor.uid=200000+i
			actual_map.advance(actor,0,0)
		verify(actual_map.stationary_projections.size()<=256 and actual_map.stationary_projection_order.size()<=256,"projection retention bounded "+definition.id)
	print("STATIONARY_PROJECTION: ",checks," checks; failures=",failures)
	if args.has("--output"):
		var source_path: String="res://scripts/map_runtime.gd" if FileAccess.file_exists("res://scripts/map_runtime.gd") else "res://scripts/map_runtime.gdc"
		FileAccess.open(args[args.find("--output")+1],FileAccess.WRITE).store_string(JSON.stringify({"passed":failures.is_empty(),"checks":checks,"failures":failures,"source_sha256":FileAccess.get_sha256(source_path),"baseline_sha256":FileAccess.get_sha256(original_script.resource_path),"observer_sha256":FileAccess.get_sha256(get_script().resource_path),"scope":"Exact values and float64 bytes against full original map advance, all200 maps, every road, both directions and ends/interiors; actual reuse, negative/zero/positive travel, invalid/replaced actors, mutated geometry and bounded retention."},"  "))
	quit(0 if failures.is_empty() else 1)
