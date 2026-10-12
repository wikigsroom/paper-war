extends SceneTree
const Data=preload("res://scripts/data_store.gd")
const Simulation=preload("res://scripts/battle_sim.gd")
const View=preload("res://scripts/battle_view.gd")
var checks: int=0
var failures: Array=[]
func _initialize():call_deferred("run")
func ids(actors: Array) -> Array:
	return actors.map(func(a):return int(a.uid))
func run():
	var db=Data.new()
	var view=View.new()
	for definition in db.maps.values():
		for layout in [0,1,2]:
			var s=Simulation.new(db)
			s.start({"map":definition.id,"faction":definition.region,"enemy":"mo","full_tech":true})
			s.ai_enabled=[false,false];s.units.clear()
			var edges: Array=s.map.edges.keys()
			for side in [0,1]:
				var roster: Array=db.all_unit_ids(s.players[side].faction)
				for i in range(36):
					var u=s.spawn(roster[i%roster.size()],side,3)
					var edge: String=edges[(i+side)%edges.size()]
					s.map.apply_anchor(u,s.map.anchor(edge,float(s.map.edges[edge].length)*float(i%7)/7.0))
					if db.balance.units[u.id].get("economy",false):u["body_anchor"]=s.map.anchor(edge,maxf(0,float(u.s)-.47))
					# Includes exact ties and cyclic comparisons near the old .05
					# threshold. The candidate must retain the original sort outcome.
					if layout==1:
						u.y=.0
						if u.has("body_anchor"):u.body_anchor.y=.0
					elif layout==2:
						u.y=float((i*13+side)%11)*.0125
						if u.has("body_anchor"):u.body_anchor.y=u.y-.025
			view.sim=s
			var expected: Array=s.units.duplicate()
			expected.sort_custom(func(a,b):
				var ay: float=s.physical_point(a).y;var by: float=s.physical_point(b).y
				return ay<by if absf(ay-by)>.05 else int(a.uid)%5<int(b.uid)%5)
			var original: Array=ids(s.units)
			var actual: Array=view.ordered_units()
			checks+=1
			if ids(actual)!=ids(expected) and failures.size()<10:failures.append({"map":definition.id,"layout":layout,"expected":ids(expected),"actual":ids(actual)})
			checks+=1
			if ids(s.units)!=original:failures.append({"map":definition.id,"layout":layout,"reason":"Renderer changed simulation actor order"})
	view.free()
	var args=OS.get_cmdline_user_args();var output: String=args[args.find("--output")+1]
	FileAccess.open(output,FileAccess.WRITE).store_string(JSON.stringify({"passed":failures.is_empty(),"checks":checks,"failures":failures,"simulation_sha256":FileAccess.get_sha256("res://scripts/battle_sim.gd"),"view_sha256":FileAccess.get_sha256("res://scripts/battle_view.gd"),"observer_sha256":FileAccess.get_sha256(get_script().resource_path),"scope":"All200 maps,72 legal actor references from both factions, original geometry, duplicate heights, near-threshold comparator cycles, mining body anchors and immutable simulation order. Exact prior comparator output, not FPS or pixel evidence."},"  "))
	print("UNIT_ORDER_EQUIVALENCE: ",checks," checks; failures=",failures)
	quit(0 if failures.is_empty() else 1)
