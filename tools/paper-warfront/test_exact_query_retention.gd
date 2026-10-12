extends SceneTree
const Data=preload("res://scripts/data_store.gd")
const Simulation=preload("res://scripts/battle_sim.gd")
const Reference=preload("dense_reference_target_search.gd")
var checks: int=0
var failures: Array=[]
func _initialize():call_deferred("run")
func verify(value: bool,note: String):
	checks+=1
	if not value and failures.size()<30:failures.append(note)
func compare(s,reference,source: Dictionary,note: String):
	reference.map=s.map;reference.visibility=s.visibility
	var expected: Dictionary=reference.nearest_enemy(source)
	var actual: Dictionary=s.nearest_enemy(source)
	verify(actual.is_empty() if expected.is_empty() else is_same(actual,expected),note)
func phase(s):
	s.visibility.refresh();s.prepare_movement_sides();s.movement_sides_active=true
func run():
	var db=Data.new()
	for definition in db.maps.values():
		for side in [0,1]:
			var s=Simulation.new(db);var reference=Reference.new(db)
			s.start({"map":definition.id,"faction":"yin","enemy":"mo","fog":false,"full_tech":true})
			s.ai_enabled=[false,false];s.units.clear()
			var edge_id: String=s.map.edges.keys()[0]
			var length: float=float(s.map.edges[edge_id].length)
			var sources: Array=[];var enemies: Array=[]
			for id in s.players[side].roster:
				var source: Dictionary=s.spawn(id,side,3)
				s.map.apply_anchor(source,s.map.anchor(edge_id,length*.43));sources.append(source)
			for id in s.players[1-side].roster:
				var enemy: Dictionary=s.spawn(id,1-side,3)
				s.map.apply_anchor(enemy,s.map.anchor(edge_id,length*.5));enemies.append(enemy)
			phase(s)
			for source in sources:compare(s,reference,source,"initial "+definition.id)
			var rebuilt: int=s.target_snapshot_rebuilds
			phase(s)
			for source in sources:compare(s,reference,source,"retained "+definition.id)
			verify(s.target_snapshot_rebuilds==rebuilt and s.target_snapshot_reuses>0,"unchanged geometry retained "+definition.id)
			enemies[0].hp=0
			for source in sources:compare(s,reference,source,"live death without refresh "+definition.id)
			enemies[0].hp=enemies[0].max_hp;enemies[1].side=side
			for source in sources:compare(s,reference,source,"live conversion without refresh "+definition.id)
			enemies[1].side=1-side
			var replaced: Dictionary=enemies[0].duplicate(true)
			s.units[s.units.find(enemies[0])]=replaced;enemies[0]=replaced
			phase(s)
			for source in sources:compare(s,reference,source,"same uid different actor reference "+definition.id)
			verify(s.target_snapshot_rebuilds>rebuilt,"replacement invalidates identity "+definition.id)
			rebuilt=s.target_snapshot_rebuilds
			enemies[0].s+=0.000000000001
			phase(s)
			for source in sources:compare(s,reference,source,"float64 offset changed with same native point "+definition.id)
			verify(s.target_snapshot_rebuilds>rebuilt,"double arc invalidates geometry "+definition.id)
			s.units.reverse();phase(s)
			for source in sources:compare(s,reference,source,"sight-list rank changed "+definition.id)
			var enemy_def: Dictionary=db.balance.units[enemies[0].id]
			var role: String=str(enemy_def.get("role",""));enemy_def.role="medic" if role!="medic" else "frontline"
			phase(s)
			for source in sources:compare(s,reference,source,"support class changed "+definition.id)
			enemy_def.role=role
			var worker: Dictionary=s.spawn("unit."+s.players[1-side].faction+".worker",1-side,3)
			s.map.apply_anchor(worker,s.map.anchor(edge_id,length*.6));worker.body_anchor=s.map.anchor(edge_id,length*.44)
			phase(s)
			for source in sources:compare(s,reference,source,"new visible physical worker body "+definition.id)
			worker.body_anchor=s.map.anchor(edge_id,length*.42);phase(s)
			for source in sources:compare(s,reference,source,"worker body moved without service anchor move "+definition.id)
			s.start({"map":definition.id,"faction":"yin","enemy":"mo","fog":false})
			verify(not s.target_snapshot_ready and s.target_snapshots.is_empty(),"battle restart clears retained actor references "+definition.id)
	print("EXACT_QUERY_RETENTION: ",checks," checks; failures=",failures)
	var args=OS.get_cmdline_user_args()
	if args.has("--output"):
		var source_path: String="res://scripts/battle_sim.gd" if FileAccess.file_exists("res://scripts/battle_sim.gd") else "res://scripts/battle_sim.gdc"
		var reference_script: GDScript=Reference
		FileAccess.open(args[args.find("--output")+1],FileAccess.WRITE).store_string(JSON.stringify({"passed":failures.is_empty(),"checks":checks,"failures":failures,"source_sha256":FileAccess.get_sha256(source_path),"reference_sha256":FileAccess.get_sha256(reference_script.resource_path),"observer_sha256":FileAccess.get_sha256(get_script().resource_path),"scope":"Independent original linear targeting across all200 maps and both sides, actual cache reuse, live death/ownership, actor replacement, float64 arc changes, rank and support changes, physical worker anchors and battle reset."},"  "))
	quit(0 if failures.is_empty() else 1)
