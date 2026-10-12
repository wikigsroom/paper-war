extends SceneTree
const Data=preload("res://scripts/data_store.gd")
const Simulation=preload("res://scripts/battle_sim.gd")
const Reference=preload("res://tests/reference_target_search.gd")
var checks: int=0
var failures: Array=[]
func _initialize():call_deferred("run")
func verify(value: bool,note: String):
	checks+=1
	if not value:failures.append(note)
func setup():
	var db=Data.new();var s=Simulation.new(db)
	s.start({"map":"map.01.04","faction":"yin","enemy":"mu","fog":false,"full_tech":true})
	s.ai_enabled=[false,false];s.units.clear();s.buildings.clear();s.bases[1].hp=0
	var u=s.spawn("unit.yin.spear",0,5);u.x=0;u.y=0
	s.prepare_movement_sides();s.movement_sides_active=true
	return {"db":db,"sim":s,"source":u}
func body(f,id: String,x: float,y: float=0.0):
	var u=f.sim.spawn(id,1,5);u.x=x;u.y=y
	return u
func compare(f,note: String,expected_uid: int=-1):
	var ref=Reference.new(f.db);ref.map=f.sim.map;ref.visibility=f.sim.visibility
	var expected: Dictionary=ref.nearest_enemy(f.source)
	var actual: Dictionary=f.sim.nearest_enemy(f.source)
	verify(actual.get("uid",0)==expected.get("uid",0),note+" agrees with independent full scan")
	if expected_uid>=0:verify(actual.get("uid",0)==expected_uid,note+" keeps intended sentinel/rank")
func run():
	var f=setup();f.source.x=20
	var earlier=body(f,"unit.mu.guard",21);body(f,"unit.mu.poisoner",19)
	f.sim.visibility.refresh();compare(f,"equal X-neighbor distance retains original order",earlier.uid)
	f=setup();f.source.x=.1
	earlier=body(f,"unit.mu.guard",20.2);body(f,"unit.mu.poisoner",-20)
	f.sim.visibility.refresh()
	var origin: Vector2=f.sim.physical_point(f.source);var point: Vector2=f.sim.physical_point(earlier)
	verify(absf(float(origin.x)-float(point.x))>origin.distance_to(point),"scalar64 lower bound exceeds rounded native full distance")
	compare(f,"native-rounded boundary keeps earlier right candidate",earlier.uid)
	f=setup();f.db.balance.units[f.source.id].support_priority=true;f.db.balance.units[f.source.id].range=30000.0
	body(f,"unit.mu.guard",14000);var support=body(f,"unit.mu.medic",26000)
	f.sim.visibility.refresh();compare(f,"weighted support still qualifies when all raw distances exceed10000",support.uid)
	f=setup();f.db.balance.units[f.source.id].support_priority=true;f.db.balance.units[f.source.id].range=4.0
	var close=body(f,"unit.mu.guard",2);support=body(f,"unit.mu.medic",3.5)
	f.sim.visibility.refresh();compare(f,"weighted support beats closer raw body",support.uid)
	support.hp=0;compare(f,"cached dead support is skipped",close.uid)
	support.hp=100;support.side=0;compare(f,"cached converted support is skipped",close.uid)
	support.side=1;support.x=5;f.sim.visibility.refresh();compare(f,"support outside reach retains raw score",close.uid)
	f=setup();var worker=body(f,"unit.mu.worker",9)
	worker.body_anchor={"edge":worker.edge,"s":worker.s,"x":.5,"y":0.0}
	body(f,"unit.mu.guard",2);f.sim.visibility.refresh();compare(f,"mining body controls query geometry",worker.uid)
	f=setup();var invalid=body(f,"unit.mu.guard",2);invalid.x=NAN
	close=body(f,"unit.mu.poisoner",4);f.sim.visibility.refresh();compare(f,"nonfinite target uses original fallback",close.uid)
	verify(not f.sim.ranged_query_valid,"invalid query avoids sorting nonfinite points")
	var args=OS.get_cmdline_user_args();var output: String=args[args.find("--output")+1]
	FileAccess.open(output,FileAccess.WRITE).store_string(JSON.stringify({"passed":failures.is_empty(),"checks":checks,"failures":failures,"simulation_sha256":FileAccess.get_sha256("res://scripts/battle_sim.gd"),"observer_sha256":FileAccess.get_sha256(get_script().resource_path),"scope":"Exact independent linear ranged selection at native-float bounds, rank ties, weighted support,10000 sentinel, live death/conversion, mining body and invalid-point fallback. Deliberate coordinate/definition fixtures; not paid games or FPS."},"  "))
	print("AXIS_TARGET_BOUNDARIES: ",checks," checks; failures=",failures)
	quit(0 if failures.is_empty() else 1)
