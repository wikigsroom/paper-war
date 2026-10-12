extends SceneTree
const Data=preload("res://scripts/data_store.gd")
const Reference=preload("reference_target_search.gd")
class ComparedSimulation:
	extends "res://scripts/battle_sim.gd"
	var reference
	var queries: int=0
	var phase_queries: int=0
	var failures: Array=[]
	var mutation: String=""
	var mutation_done: bool=false
	func _init(data):
		super(data);reference=Reference.new(data)
	func nearest_enemy(u: Dictionary) -> Dictionary:
		# Changes are diagnostic fixtures. No paid-gameplay claim is made.
		if queries==3 and not mutation_done and not mutation.is_empty():
			for enemy in visibility.enemies[int(u.side)]:
				if enemy.get("building",false) or enemy.hp<=0:continue
				if mutation=="death":enemy.hp=0
				else:
					map.apply_anchor(enemy,map.anchor(enemy.edge,float(map.edges[enemy.edge].length)*.73))
					visibility.refresh()
				mutation_done=true;break
		var actual: Dictionary=super.nearest_enemy(u)
		reference.map=map;reference.visibility=visibility
		var expected: Dictionary=reference.nearest_enemy(u)
		queries+=1
		if bool(get("movement_sides_active")):phase_queries+=1
		if actual.get("uid",0)!=expected.get("uid",0) and failures.size()<20:
			failures.append({"map":config.map,"source":u.uid,"actual":actual.get("uid",0),
				"expected":expected.get("uid",0),"source_anchor":physical_anchor(u).duplicate(true)})
		return actual

var checks: int=0
var failures: Array=[]
var queries: int=0
var phase_queries: int=0
var cases: int=0
var mutations: int=0
func _initialize():call_deferred("run")
func verify(value: bool,note: String):
	checks+=1
	if not value and failures.size()<20:failures.append(note)
func collect(s):
	queries+=s.queries;phase_queries+=s.phase_queries
	checks+=s.queries
	for failure in s.failures:
		if failures.size()<20:failures.append(failure)

func precision_boundary(db):
	var s=ComparedSimulation.new(db)
	s.start({"map":"map.01.04","faction":"yin","enemy":"mo","full_tech":true,"fog":false})
	s.ai_enabled=[false,false];s.units.clear()
	var source=s.spawn("unit.yin.axe",0,6)
	s.map.apply_anchor(source,s.map.anchor("ground.1",0))
	var far=s.spawn(s.players[1].roster[0],1,15)
	var near=s.spawn(s.players[1].roster[0],1,15)
	s.map.apply_anchor(far,s.map.anchor("ground.2",1.0+2.220446049250313e-16))
	s.map.apply_anchor(near,s.map.anchor("ground.2",1.0))
	s.visibility.refresh();s.prepare_movement_sides();s.movement_sides_active=true
	verify(far.s!=near.s,"fixture retains distinct double-precision arc offsets")
	verify(s.map.melee_distance(source,far)==s.map.melee_distance(source,near),"junction addition rounds both distances to the same value")
	verify(s.nearest_enemy(source).get("uid",0)==far.uid,"rounded junction tie keeps the first sight-list actor")
	s.map.apply_anchor(source,s.map.anchor("ground.2",0));s.visibility.refresh()
	verify(s.nearest_enemy(source).get("uid",0)==near.uid,"distinct same-road distance keeps the closer actor despite broad candidate tolerance")
	far.side=0
	verify(s.nearest_enemy(source).get("uid",0)==near.uid,"cached actor ownership is rechecked")
	near.hp=0
	verify(s.nearest_enemy(source).is_empty(),"cached dead actor is skipped and distant unconnected base is unreachable")
	near.hp=100;near.s=float(s.map.edges[near.edge].length)+1
	s.visibility.refresh()
	var selected=s.nearest_enemy(source)
	verify(not s.melee_query_valid,"out-of-bounds diagnostic target uses the linear fallback")
	verify(selected.get("uid",0)==near.uid,"fallback preserves the original raw-anchor query")
	s.movement_sides_active=false;collect(s)

func run():
	var db=Data.new()
	precision_boundary(db)
	var args=OS.get_cmdline_user_args()
	var limit: int=int(args[args.find("--map-limit")+1]) if args.has("--map-limit") else db.maps.size()
	var definitions: Array=db.maps.values()
	for map_index in range(mini(limit,db.maps.size())):
		var definition: Dictionary=definitions[map_index]
		for fog in [false,true]:
			var s=ComparedSimulation.new(db)
			var west: String=str(definition.region)
			var east: String=["mo","deng","bai"][map_index%3]
			s.start({"map":definition.id,"faction":west,"enemy":east,"full_tech":true,"fog":fog})
			s.ai_enabled=[false,false];s.units.clear();s.buildings.clear()
			var serial: int=0
			for side in [0,1]:
				for edge in s.map.edges.values():
					for fraction in [.1,.5,.5,.9]:
						var roster: Array=s.players[side].roster
						var id: String=roster[serial%roster.size()]
						if serial%9==0:id="unit."+s.players[side].faction+".worker"
						var u=s.spawn(id,side,18)
						s.map.apply_anchor(u,s.map.anchor(edge.id,float(edge.length)*fraction))
						u.hp=10000;u.max_hp=u.hp
						if db.balance.units[id].get("economy",false):
							u["body_anchor"]=s.map.anchor(edge.id,maxf(0,float(u.s)-.35))
						if serial%7==0:u["speed_override"]=0.0
						serial+=1
			s.visibility.refresh();s.drain_events()
			s.mutation="death" if fog else "refresh"
			for step in range(4):s.tick(1.0/60.0);s.drain_events()
			collect(s);cases+=1
			if s.mutation_done:mutations+=1
	verify(cases==mini(limit,db.maps.size())*2,"every selected map is checked with fog enabled and disabled")
	verify(phase_queries>0,"comparison executes inside the actual simultaneous unit phase")
	verify(mutations>0,"comparison includes same-phase death and visibility/position refresh")
	var inputs: Dictionary={}
	for path in ["res://scripts/battle_sim.gd","res://scripts/battle_visibility.gd","res://scripts/map_runtime.gd",
		"res://tests/reference_target_search.gd","res://data/maps.json","res://data/balance-prototype.json"]:
		inputs[path]=FileAccess.get_sha256(path)
	var report: Dictionary={"passed":failures.is_empty(),"checks":checks,"queries":queries,"phase_queries":phase_queries,
		"map_cases":cases,"mutated_cases":mutations,"failures":failures,"inputs":inputs,"observer_sha256":FileAccess.get_sha256(get_script().resource_path),
		"scope":"Exact target UID against the pre-existing independent linear query during real 60Hz unit phases, all selected authored maps with fog on/off, ten native faction rosters, duplicate positions, mining body anchors, current death/ownership filtering and visibility/position refresh. Explicit double-precision junction tie and invalid-anchor fallback. Spawn/HP/tech fixtures; not paid normal gameplay, performance, full balance or Android hardware."}
	if args.has("--output"):
		FileAccess.open(args[args.find("--output")+1],FileAccess.WRITE).store_string(JSON.stringify(report,"  "))
	print("ROAD_TARGET_EQUIVALENCE: ",checks," checks; cases=",cases," failures=",failures)
	quit(0 if report.passed else 1)
