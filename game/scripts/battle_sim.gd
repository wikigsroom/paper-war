extends RefCounted
const UnitProjectile=preload("res://scripts/unit_projectile.gd")
# Rendering and UI never change these rules. All participants share command APIs.
const SpellRules = preload("res://scripts/manual_spell_rules.gd")
const CommandRules=preload("res://scripts/battle_command_rules.gd")
const ChallengeRules = preload("res://scripts/challenge_rules.gd")
const Visibility = preload("res://scripts/battle_visibility.gd")
var visibility
const MapRuntime = preload("res://scripts/map_runtime.gd")
var db
var map: MapRuntime
var protected_uid: int = 0
var escort_uid: int = 0
var intercept_uid: int = 0
var intercept_crossed: bool = false
var result_reason: String = ""
const Abilities = preload("res://scripts/unit_abilities.gd")
const TacticalAI = preload("res://scripts/tactical_ai.gd")
var config: Dictionary = {}
var players: Array = []
var units: Array = []
var buildings: Array = []
var bases: Array = []
var corpses: Array = []
var projectiles: Array = []
var scheduled: Array = []
var spell_areas: Array = []
var events: Array = []

# Tick snapshots and survivor buffers are reused across frames. They preserve
# the old duplicate/filter phase boundaries while avoiding per-tick Array churn.
var tick_units_snapshot: Array = []
var tick_projectiles_snapshot: Array = []
var tick_scheduled_snapshot: Array = []
var tick_corpses_snapshot: Array = []
var alive_units_buffer: Array = []
var alive_buildings_buffer: Array = []
var next_uid: int = 1
var time: float = 0.0
var winner: int = -2
var ai_clock: Array = [0.0,0.0]
var ai_enabled: Array = [false,true]
var rng = RandomNumberGenerator.new()
var ai_rng: Array=[RandomNumberGenerator.new(),RandomNumberGenerator.new()]
var stats: Array = []
var tick_count: int = 0
# UID lookups are on the hot path for projectiles, events, visibility and UI.
# The cache is rebuilt only when the live actor collection changes; hp is still
# checked on every hit so a death processed inside the current tick cannot be
# resurrected by a stale reference.
var actor_lookup_cache: Dictionary = {}
var actor_lookup_units_size: int = -1
var actor_lookup_buildings_size: int = -1
var actor_lookup_bases_size: int = -1
var collecting_attacks: bool=false
var attack_intents: Array=[]
var collecting_combat_hits: bool=false
var combat_hits: Array=[]
var resolving_combat_hits: bool=false
var combat_deaths: Array=[]
var formation_ranges: Dictionary={}
var movement_side_units: Array=[[],[]]
var movement_sides_active: bool=false
var movement_current_uid: int=0
var movement_current_anchor: Dictionary={}
var blocker_roads: Array=[{},{}]
var blocker_roads_dirty: bool=true
var blocker_roads_valid: bool=true
var melee_query_roads: Array=[{},{}]
var melee_query_revision: int=-1
var melee_query_valid: bool=true
var melee_neighbor_edges: Dictionary={}
var ranged_query_records: Array=[[],[]]
var ranged_query_revision: int=-1
var ranged_query_valid: bool=true
# Sorted query pools may survive a phase only after every source reference,
# physical road offset, native point and support classification matches.
# Actor dictionaries remain live: hp/side filtering is never cached.
var target_snapshot_revision: int=-1
var target_snapshot_generation: int=0
var target_snapshot_ready: bool=false
var target_snapshots: Array=[]
var melee_snapshot_generation: int=-1
var ranged_snapshot_generation: int=-1
var target_snapshot_reuses: int=0
var target_snapshot_rebuilds: int=0

# Answers are used only inside tick's dense simultaneous unit phase.
# Geometry comes from the exact existing snapshots; eligibility is separate.
var target_answers_active: bool=false
var target_answers: Dictionary={}
var target_answers_generation: int=-1
var target_answers_revision: int=-1
var target_answers_eligibility: Array=[]
var target_answer_hits: int=0
var target_answer_misses: int=0

# Marching answers are confined to the dense simultaneous unit phase.
# The exact ordered blocker geometry and eligibility are checked each phase.
var marching_answers_active: bool=false
var marching_answers_ready: bool=false
var marching_answers: Dictionary={}
var marching_snapshot: MarchingSnapshot
var marching_answer_hits: int=0
var marching_answer_misses: int=0
var marching_snapshot_reuses: int=0
var marching_snapshot_rebuilds: int=0

class MarchingAnswer:
	extends RefCounted
	var source: Dictionary={}
	var uid
	var side: int=0
	var edge: String=""
	var offset: float=0
	var reach: float=0
	var giant: bool=false
	var sees_enemy: bool=false
	var forward: float=0
	var requested: float=0
	var limit: float=0

class MarchingSnapshot:
	extends RefCounted
	var roads: Array=[{},{}]
	var valid: bool=true
	var actors: Array[Dictionary]=[]
	var uids: Array=[]
	var edges: Array[String]=[]
	var offsets: PackedFloat64Array=PackedFloat64Array()
	var sides: PackedInt32Array=PackedInt32Array()
	var eligibility: PackedByteArray=PackedByteArray()
	var ranges: PackedFloat64Array=PackedFloat64Array()
	func flags(a: Dictionary,d: Dictionary) -> int:
		return (1 if a.hp>0 else 0)+(2 if d.get("economy",false) else 0)+(4 if d.get("role","") in ["medic","engineer","necromancer","summoner","oracle","scribe"] else 0)
	func matches(simulation) -> bool:
		var index: int=0;var current_valid: bool=true
		for a in simulation.units:
			var anchor: Dictionary=simulation.movement_current_anchor if int(a.uid)==simulation.movement_current_uid else a
			if not is_finite(float(anchor.s)):current_valid=false
			var d: Dictionary=simulation.db.balance.units[a.id]
			if a.hp<=0 or d.get("economy",false):continue
			if index>=actors.size() or not is_same(a,actors[index]) or a.uid!=uids[index] or int(a.side)!=sides[index]:return false
			if anchor.edge!=edges[index] or float(anchor.s)!=offsets[index]:return false
			if float(d.range)!=ranges[index] or flags(a,d)!=eligibility[index]:return false
			index+=1
		return index==actors.size() and current_valid==valid
	func capture(simulation):
		roads=simulation.blocker_roads;valid=simulation.blocker_roads_valid
		for a in simulation.units:
			var d: Dictionary=simulation.db.balance.units[a.id]
			if a.hp<=0 or d.get("economy",false):continue
			var anchor: Dictionary=simulation.movement_current_anchor if int(a.uid)==simulation.movement_current_uid else a
			actors.append(a);uids.append(a.uid);edges.append(anchor.edge);offsets.append(float(anchor.s));sides.append(int(a.side))
			ranges.append(float(d.range));eligibility.append(flags(a,d))

func prepare_marching_answers():
	if marching_answers_ready:return
	if marching_snapshot!=null and marching_snapshot.matches(self):
		marching_snapshot_reuses+=1;blocker_roads=marching_snapshot.roads;blocker_roads_valid=marching_snapshot.valid;blocker_roads_dirty=false
	else:
		marching_answers.clear()
		if blocker_roads_dirty:prepare_blocker_roads()
		marching_snapshot=MarchingSnapshot.new();marching_snapshot.capture(self);marching_snapshot_rebuilds+=1
	marching_answers_ready=true

class TargetAnswer:
	extends RefCounted
	var source: Dictionary={}
	var target: Dictionary={}
	var edge: String=""
	var offset: float=0
	var point: Vector2=Vector2.ZERO
	var side: int=0
	var melee: bool=false
	var priority: bool=false
	var reach: float=0

func prepare_target_answers():
	if target_answers_revision==visibility.revision:return
	prepare_target_snapshot()
	var eligibility: Array=[]
	for side in [0,1]:
		var flags: PackedInt32Array=PackedInt32Array()
		for a in visibility.enemies[side]:flags.append(int(a.side)*2+(1 if a.hp>0 else 0))
		eligibility.append(flags)
	if target_answers_generation!=target_snapshot_generation or eligibility!=target_answers_eligibility:target_answers.clear()
	target_answers_generation=target_snapshot_generation
	target_answers_eligibility=eligibility;target_answers_revision=visibility.revision

class TargetGeometrySnapshot:
	extends RefCounted
	var actors: Array[Dictionary]=[]
	var edges: Array[String]=[]
	var offsets: PackedFloat64Array=PackedFloat64Array()
	var points: PackedVector2Array=PackedVector2Array()
	var supports: PackedByteArray=PackedByteArray()
	func matches(source_actors: Array,simulation) -> bool:
		if actors.size()!=source_actors.size():return false
		for index in range(actors.size()):
			var a: Dictionary=source_actors[index]
			if not is_same(a,actors[index]):return false
			var anchor: Dictionary=simulation.physical_anchor(a)
			if anchor.edge!=edges[index] or float(anchor.s)!=offsets[index] or Vector2(anchor.x,anchor.y)!=points[index]:return false
			var support: bool=not a.get("building",false) and simulation.db.balance.units[a.id].get("role","") in ["medic","engineer","scribe","necromancer","summoner","illusionist","oracle"]
			if (1 if support else 0)!=supports[index]:return false
		return true
	func capture(source_actors: Array,simulation):
		for a in source_actors:
			var anchor: Dictionary=simulation.physical_anchor(a)
			actors.append(a);edges.append(anchor.edge);offsets.append(float(anchor.s));points.append(Vector2(anchor.x,anchor.y))
			var support: bool=not a.get("building",false) and simulation.db.balance.units[a.id].get("role","") in ["medic","engineer","scribe","necromancer","summoner","illusionist","oracle"]
			supports.append(1 if support else 0)

func prepare_target_snapshot():
	if target_snapshot_revision==visibility.revision:return
	var matches: bool=target_snapshot_ready
	if matches:
		for side in [0,1]:
			var previous: TargetGeometrySnapshot=target_snapshots[side]
			if not previous.matches(visibility.enemies[side],self):matches=false;break
	if matches:target_snapshot_reuses+=1
	else:
		target_snapshots=[TargetGeometrySnapshot.new(),TargetGeometrySnapshot.new()]
		for side in [0,1]:
			var snapshot: TargetGeometrySnapshot=target_snapshots[side]
			snapshot.capture(visibility.enemies[side],self)
		target_snapshot_ready=true;target_snapshot_generation+=1;target_snapshot_rebuilds+=1
	target_snapshot_revision=visibility.revision

class RoadQueryRecords:
	extends RefCounted
	var actors: Array[Dictionary]=[]
	var offsets: PackedFloat64Array=PackedFloat64Array()
	var ranks: PackedInt32Array=PackedInt32Array()
	var supports: PackedByteArray=PackedByteArray()
	var anchors: Array[Dictionary]=[]
	func add(actor_value: Dictionary,offset: float,rank: int,support: bool,edge: String):
		actors.append(actor_value);offsets.append(offset);ranks.append(rank);supports.append(1 if support else 0)
		anchors.append({"edge":edge,"s":offset})
	func order(keep_rank: bool):
		var indices: Array[int]=[]
		for index in range(actors.size()):indices.append(index)
		indices.sort_custom(func(a: int,b: int):return ranks[a]<ranks[b] if keep_rank and offsets[a]==offsets[b] else offsets[a]<offsets[b])
		var sorted_actors: Array[Dictionary]=[];var sorted_offsets: PackedFloat64Array=PackedFloat64Array()
		var sorted_ranks: PackedInt32Array=PackedInt32Array();var sorted_supports: PackedByteArray=PackedByteArray()
		var sorted_anchors: Array[Dictionary]=[]
		for index in indices:
			sorted_actors.append(actors[index]);sorted_offsets.append(offsets[index]);sorted_ranks.append(ranks[index])
			sorted_supports.append(supports[index]);sorted_anchors.append(anchors[index])
		actors=sorted_actors;offsets=sorted_offsets;ranks=sorted_ranks;supports=sorted_supports;anchors=sorted_anchors

class RangedQueryRecords:
	extends RefCounted
	var actors: Array[Dictionary]=[]
	var points: PackedVector2Array=PackedVector2Array()
	var supports: PackedByteArray=PackedByteArray()
	var by_x: PackedInt32Array=PackedInt32Array()
	var support_by_x: PackedInt32Array=PackedInt32Array()
	func order_x():
		var xs: PackedFloat64Array=PackedFloat64Array();var indices: Array[int]=[]
		for index in range(points.size()):xs.append(points[index].x);indices.append(index)
		indices.sort_custom(func(a: int,b: int):return a<b if xs[a]==xs[b] else xs[a]<xs[b])
		by_x=PackedInt32Array(indices);support_by_x=PackedInt32Array()
		for index in indices:
			if supports[index]!=0:support_by_x.append(index)

class BlockerQueryRecords:
	extends RefCounted
	var actors: Array[Dictionary]=[]
	var offsets: PackedFloat64Array=PackedFloat64Array()
	func order():
		var indices: Array[int]=[]
		for index in range(actors.size()):indices.append(index)
		indices.sort_custom(func(a: int,b: int):return offsets[a]<offsets[b])
		var sorted_actors: Array[Dictionary]=[];var sorted_offsets: PackedFloat64Array=PackedFloat64Array()
		for index in indices:sorted_actors.append(actors[index]);sorted_offsets.append(offsets[index])
		actors=sorted_actors;offsets=sorted_offsets

func _init(data):
	db = data

func start(options: Dictionary):
	config = options.duplicate(true)
	map = MapRuntime.new(db.map_definition(str(config.get("map","stamp-plain"))))
	protected_uid=0;escort_uid=0;intercept_uid=0;intercept_crossed=false;result_reason=""
	players.clear(); units.clear(); buildings.clear(); bases.clear(); corpses.clear()
	actor_lookup_cache.clear();actor_lookup_units_size=-1;actor_lookup_buildings_size=-1;actor_lookup_bases_size=-1
	projectiles.clear(); scheduled.clear(); spell_areas.clear(); events.clear(); stats.clear()
	tick_units_snapshot.clear(); tick_projectiles_snapshot.clear(); tick_scheduled_snapshot.clear(); tick_corpses_snapshot.clear()
	alive_units_buffer.clear(); alive_buildings_buffer.clear()
	attack_intents.clear();combat_hits.clear();combat_deaths.clear()
	formation_ranges.clear();movement_side_units=[[],[]];movement_sides_active=false;movement_current_uid=0;movement_current_anchor={}
	melee_query_roads=[{},{}];melee_query_revision=-1;melee_neighbor_edges.clear()
	ranged_query_records=[[],[]];ranged_query_revision=-1
	target_snapshot_revision=-1;target_snapshot_generation=0;target_snapshot_ready=false;target_snapshots=[]
	melee_snapshot_generation=-1;ranged_snapshot_generation=-1;target_snapshot_reuses=0;target_snapshot_rebuilds=0
	target_answers.clear();target_answers_active=false;target_answers_generation=-1;target_answers_revision=-1;target_answers_eligibility=[];target_answer_hits=0;target_answer_misses=0
	marching_answers.clear();marching_answers_active=false;marching_answers_ready=false;marching_snapshot=null;marching_answer_hits=0;marching_answer_misses=0;marching_snapshot_reuses=0;marching_snapshot_rebuilds=0
	collecting_attacks=false;collecting_combat_hits=false;resolving_combat_hits=false
	winner = -2; time = 0; next_uid = 1; tick_count = 0
	ai_clock = [0.0,0.0]; ai_enabled = [false,true]
	rng.seed = int(config.get("seed",137))
	# Separate streams prevent one player's decisions consuming the other's noise.
	# Equal seeds give equal random preferences under mirrored conditions.
	for stream in ai_rng:stream.seed=int(config.get("seed",137))
	for side in range(2):
		var faction = config.get("faction","yin") if side == 0 else config.get("enemy","mo")
		var unlocked = db.technology.starting_unlocked[faction].duplicate()
		var extra = config.get("initial_unlocked",[]) if side == 0 else config.get("enemy_unlocked",[])
		for id in extra:
			if not unlocked.has(id): unlocked.append(id)
		var studied = []
		if config.get("full_tech",false):
			for node in db.technology.nodes:
				if node.faction == faction:
					studied.append(node.id)
					if not unlocked.has(node.grant): unlocked.append(node.grant)
		else:
			for node in db.technology.nodes:
				if node.faction == faction and unlocked.has(node.grant): studied.append(node.id)
		var starting_gold = config.get("starting_gold",160) if side == 0 else config.get("enemy_starting_gold",160)
		var slots: int = int(config.get("combat_slots",config.get("default_roster",db.factions[config.get("faction","yin")].default_roster).size()))
		var requested: Array = config.get("player_roster",config.get("default_roster",db.factions[faction].default_roster)) if side==0 else config.get("enemy_roster",db.factions[faction].default_roster)
		var roster: Array = db.normalize_roster(faction,requested,config.get("available_roster",[]) if side==0 else [],slots)
		var quick_roster: Array=roster.duplicate()
		if not config.get("restrict_roster",false):roster=db.all_unit_ids(faction).duplicate()
		# Quick slots arrange controls; they never grant advanced technology for free.
		for node in db.technology.nodes:
			if node.faction==faction and unlocked.has(node.grant) and not studied.has(node.id):studied.append(node.id)
		players.append({"faction":faction,"roster":roster,"quick_roster":quick_roster,"gold":float(starting_gold),"mana":40.0,"unlocked":unlocked,"studied":studied,"queue":[],"queue_revision":0,"production":0.0,"research":{},"cooldowns":{},"sequence":0,"ai_order":"","ai_research":"","ai_research_at":15.0,"ai_route_at":0.0})
		var base = {"uid":-(side+1),"id":"building."+faction+".base","building":true,"base":true,"side":side,"hp":1100.0,"max_hp":1100.0,"hurt":0.0,"cooldown":0.0,"state":"active","construction":0.0,"disabled":0.0}
		map.apply_anchor(base,map.at_node(map.definition.bases[side].node,side))
		bases.append(base)
		stats.append({"recruited":0,"killed":0,"lost":0,"gold_delivered":0,"mana_spent":0,"casts":0,"healed":0,"buildings":0,"reflections":0,"interrupts":0,"summons":0,"spell_counts":{},"build_counts":{},"mana_income":{}})
		for i in range(2):
			var worker = spawn("unit."+faction+".worker",side,bases[side].x+(0.4+i*.45)*(1 if side==0 else -1))
			worker.job = "mine"
	visibility=Visibility.new(self)
	setup_objective()
	setup_opening_forces()
	visibility.refresh()
	event("start",{})

func setup_opening_forces():
	for opening in config.get("opening_forces",[]):
		var side: int = int(opening.get("side",1));var id: String = str(opening.get("id",""))
		if side not in [0,1] or not db.balance.units.has(id) or id.get_slice(".",1)!=players[side].faction:continue
		var cost: float = float(db.balance.units[id].gold)
		if players[side].gold<cost:continue
		players[side].gold-=cost
		var unit: Dictionary = spawn(id,side,float(opening.x));map.apply_anchor(unit,opening)
		if opening.get("stationary",false):unit["speed_override"]=0.0
		unit["display_name"]=str(opening.get("label",""));stats[side].recruited+=1

func event(kind: String, values: Dictionary):
	if not values.has("y"):
		var source = actor(int(values.get("uid",0)))
		values["y"] = source.get("y",map.ground_y_at(float(values.get("x",0)))) if map!=null else 0.0
	values["kind"] = kind
	values["time"] = time
	events.append(values)

func drain_events() -> Array:
	var out = events
	events = []
	return out

func actor(uid: int) -> Dictionary:
	if actor_lookup_units_size!=units.size() or actor_lookup_buildings_size!=buildings.size() or actor_lookup_bases_size!=bases.size():
		actor_lookup_cache.clear()
		for a in units:
			actor_lookup_cache[int(a.uid)]=a
		for a in buildings:
			actor_lookup_cache[int(a.uid)]=a
		for a in bases:
			actor_lookup_cache[int(a.uid)]=a
		actor_lookup_units_size=units.size();actor_lookup_buildings_size=buildings.size();actor_lookup_bases_size=bases.size()
	var cached: Dictionary=actor_lookup_cache.get(uid,{})
	if not cached.is_empty():
		if float(cached.get("hp",0))>0:return cached
		actor_lookup_cache.erase(uid)
	for a in units:
		if a.uid == uid and a.hp>0: return a
	for a in buildings:
		if a.uid == uid and a.hp>0: return a
	for a in bases:
		if a.uid == uid and a.hp>0: return a
	return {}

func spawn(id: String, side: int, x: float, clone: bool = false, owner: int = 0, origin: String = "scripted") -> Dictionary:
	var def = db.balance.units[id]
	var west: float = float(map.nodes[map.definition.bases[0].node].position[0])+.1
	var east: float = float(map.nodes[map.definition.bases[1].node].position[0])-.1
	var u = {"uid":next_uid,"id":id,"side":side,"x":clampf(x,west,east),"hp":float(def.hp),"max_hp":float(def.hp),"age":0.0,"cooldown":.2,"windup":0.0,"target":0,"hurt":0.0,"anim":"idle","anim_t":0.0,"walk":0.0,"facing":1 if side==0 else -1,"statuses":{},"special_cd":1.2,"summon_cd":1.0,"owner":owner,"clone":clone,"ttl":10.0 if clone else float(def.get("lifetime_seconds",-1.0)),"cargo":0,"job":"mine","job_time":0.0,"mine":"","ability_clock":1.0,"control_clock":0.0,"crossed_nodes":[]}
	map.apply_anchor(u,map.project(Vector2(u.x,map.ground_y_at(u.x))))
	next_uid+=1; units.append(u)
	actor_lookup_cache[int(u.uid)]=u
	actor_lookup_units_size=units.size()
	if visibility!=null:visibility.mark_dirty()
	if movement_sides_active:
		movement_side_units[side].append(u);blocker_roads_dirty=true;marching_answers_ready=false
	event("spawn",{"uid":u.uid,"id":id,"side":side,"x":u.x,"origin":"clone" if clone else "summon" if def.get("summoned",false) else origin})
	return u

func population(side: int, workers: bool = false, include_queue: bool = true) -> int:
	var n = 0
	for u in units:
		if u.side==side and u.hp>0 and bool(db.balance.units[u.id].get("economy",false))==workers: n+=1
	if include_queue:
		for id in players[side].queue:
			if bool(db.balance.units[id].get("economy",false))==workers: n+=1
	return n

func production_ids(side: int) -> Array:
	return players[side].roster+["unit."+players[side].faction+".worker"]

func mana_rate(side: int) -> float:
	var p = players[side]
	var rate = .5
	for id in p.unlocked:
		if db.balance.upgrades.has(id): rate+=float(db.balance.upgrades[id].mana_per_second_add)
	for b in buildings:
		if b.side==side and b.hp>0 and b.state=="active" and b.disabled<=0:
			rate+=float(db.balance.buildings[b.id].get("mana_per_second",0))
	return rate

func request(side: int, kind: String, args: Dictionary = {}) -> Dictionary:
	return command(side,players[side].sequence+1,kind,args)

func command(side: int, sequence: int, kind: String, args: Dictionary) -> Dictionary:
	if winner!=-2: return {"ok":false,"error":"对局已结束"}
	visibility.refresh()
	var p = players[side]
	if sequence<=p.sequence: return {"ok":false,"error":"重复指令"}
	p.sequence=sequence
	var error = "未知指令"
	match kind:
		"recruit": error = recruit(side,args.get("id",""))
		"cancel_queue":
			var index: int = int(args.get("index",-1))
			if args.has("queue_revision") and int(args.queue_revision)!=int(p.queue_revision):error="队列已更新，请重新选择"
			elif args.has("id") and index>=0 and index<p.queue.size() and p.queue[index]!=args.id:error="队列位置已改变，请重新选择"
			else:error=cancel_queue(side,index)
		"research": error = research(side,args.get("id",""))
		"build": error = build(side,args.get("id",""),int(args.get("slot",-1)))
		"cast": error = cast(side,args.get("id",""),float(args.get("x",0)),int(args.get("target",0)),float(args.get("y",NAN)))
		"route":
			error = "" if map.set_route(side,str(args.get("node","")),str(args.get("edge",""))) else "请选择有效分岔出口"
			if error=="":
				if visibility!=null:visibility.mark_dirty()
				event("route_changed",{"side":side,"node":args.node,"edge":args.edge})
		"mine_priority":
			error="未知矿点"
			for mine in map.definition.mines:
				if mine.id==args.get("mine","") and int(mine.owner)==side:
					p["preferred_mine"]=mine.id;error="";event("mine_priority",{"side":side,"mine":mine.id,"x":mine.x,"y":mine.y});break
	return {"ok":error=="","error":error}

func recruit(side: int, id: String) -> String:
	var p = players[side]
	if bases[side].hp<=0:return "纸城已失守，无法继续招募"
	if not db.balance.units.has(id) or not p.unlocked.has(id): return "需要先研究此兵种"
	var def = db.balance.units[id]
	if id.get_slice(".",1)!=p.faction or not def.get("manual_recruit",true): return "无法招募此单位"
	if p.queue.size()>=6: return "招募队列已满，可点击排队图标取消"
	var worker = bool(def.get("economy",false))
	if not production_ids(side).has(id):return "本局仅能生产当前编组与工人，共3–5项"
	if population(side,worker)>= (int(config.get("worker_limit",db.balance.simulation.max_workers_per_side)) if worker else 60): return "纸工或军团人数达到上限"
	if p.gold<float(def.gold): return "金币不足"
	p.gold-=float(def.gold)
	p.queue.append(id)
	p.queue_revision+=1
	stats[side].recruited+=1
	event("recruit",{"side":side,"id":id})
	return ""

func cancel_queue(side: int, index: int) -> String:
	var p = players[side]
	if index<0 or index>=p.queue.size(): return "队列位置已改变"
	var id = p.queue[index]
	p.gold+=float(db.balance.units[id].gold)
	p.queue.remove_at(index)
	p.queue_revision+=1
	if index==0: p.production=0.0
	event("cancel",{"side":side})
	return ""

func research(side: int, id: String) -> String:
	var error: String=CommandRules.research_error(self,side,id)
	if not error.is_empty():return error
	var p = players[side]
	var node = db.tech(id)
	p.gold-=float(node.gold)
	p.research={"id":id,"left":float(node.seconds),"total":float(node.seconds)}
	event("research_start",{"side":side,"id":id})
	return ""

func slot_x(side: int, slot: int) -> float:
	return float(slot_anchor(side,slot).x)

func side_sites(side: int) -> Array:
	return map.definition.build_sites.filter(func(site):return int(site.owner)==side)

func slot_anchor(side: int, slot: int) -> Dictionary:
	return side_sites(side)[slot]

func build(side: int, id: String, slot: int, mission_setup: bool=false) -> String:
	var error: String=CommandRules.build_error(self,side,id,slot,mission_setup)
	if not error.is_empty():return error
	var p = players[side]
	var def = db.balance.buildings[id]
	p.gold-=float(def.gold)
	var duration: float = float(def.get("construction_seconds",4))
	var b = {"uid":next_uid,"id":id,"building":true,"base":false,"side":side,"slot":slot,"hp":float(def.hp),"max_hp":float(def.hp),"hurt":0.0,"cooldown":.8,"state":"constructing" if duration>0 else "active","construction":duration,"construction_total":duration,"disabled":0.0}
	map.apply_anchor(b,slot_anchor(side,slot))
	next_uid+=1; buildings.append(b)
	actor_lookup_cache[int(b.uid)]=b
	actor_lookup_buildings_size=buildings.size()
	if visibility!=null:visibility.mark_dirty()
	stats[side].buildings+=1
	stats[side].build_counts[id]=int(stats[side].build_counts.get(id,0))+1
	event("build",{"id":id,"side":side,"x":b.x})
	return ""

func spell_error(side: int, id: String, x: float, target_uid: int, y: float = NAN) -> String:
	var p = players[side]
	if not db.balance.spells.has(id) or not p.unlocked.has(id) or id.get_slice(".",1)!=p.faction: return "需要先研究此法术"
	var def = db.balance.spells[id]
	if p.mana<float(def.mana): return "法力不足"
	if p.cooldowns.get(id,0.0)>0: return "法术正在冷却"
	var tail = id.get_slice(".",2)
	var target = actor(target_uid)
	if tail in ["repair","fury","sacrifice","protect","clone","lightning","bind","convert","root"]:
		if target.is_empty() or target.get("building",false): return "请选择一名战斗单位"
		if not visible_to(side,target):return "目标不在当前视野中"
		var is_friendly = tail in ["repair","fury","sacrifice","protect","clone"]
		if (target.side==side)!=is_friendly: return "请选择友军" if is_friendly else "请选择敌军"
		var unit_def = db.balance.units[target.id]
		if unit_def.get("economy",false): return "纸工不可作为此法术目标"
		if target.get("objective_unit",false) and tail in ["sacrifice","convert","clone"]:return "任务对象携带唯一证据，不可献弃、夺印或复印"
		if tail in ["sacrifice","convert","clone"]:
			if unit_def.get("summoned",false) or target.clone: return "召唤物或复制体不可作为目标"
			if tail=="clone" and unit_def.get("giant",false): return "巨人不可复印"
			if tail in ["clone","convert"] and population(side)>=60: return "军团人数达到上限"
		if tail=="repair" and target.hp>=target.max_hp: return "这名友军没有受伤"
	else:
		if not location_visible(side,x,map.ground_y_at(x) if is_nan(y) else y):return "落点不在当前视野中"
		if x<bases[0].x+.1 or x>bases[1].x-.1: return "请在战场内选择落点"
		if not is_nan(y) and float(map.project(Vector2(x,y)).distance)>2.0: return "请靠近可走纸面选择落点"
		if tail=="guardian":
			if absf(x-bases[1-side].x)<2.5: return "不能把纸卫直接放入敌基地"
			if population(side)>=60: return "军团人数达到上限"
			var guardians=0
			for u in units:
				if u.side==side and u.id=="unit.deng.guardian" and u.hp>0: guardians+=1
			if guardians>=2: return "最多同时存在两名纸卫"
	return ""

func cast(side: int, id: String, x: float, target_uid: int, y: float = NAN) -> String:
	melee_query_revision=-1
	var error = spell_error(side,id,x,target_uid,y)
	if error!="": return error
	var def = db.balance.spells[id]
	var p = players[side]
	p.mana-=float(def.mana); p.cooldowns[id]=float(def.cooldown)
	stats[side].mana_spent+=int(def.mana); stats[side].casts+=1
	stats[side].spell_counts[id]=stats[side].spell_counts.get(id,0)+1
	var tail = id.get_slice(".",2)
	var target = actor(target_uid)
	if tail in ["repair","fury","sacrifice","protect","clone","lightning","bind","convert","root"]: x=target.x; y=target.y
	elif is_nan(y): y=map.ground_y_at(x)
	if not SpellRules.override_cast(self,side,id,x,y,target,def):
		match tail:
			"repair":
				var heal = minf(float(def.heal),target.max_hp-target.hp)
				target.hp+=heal; stats[side].healed+=int(heal)
				event("heal",{"x":x,"uid":target_uid,"amount":heal,"side":side})
			"lightning": damage(target,float(def.damage),side,false)
			"cold":
				for u in area_units(x,float(def.radius),1-side,y): set_status(u,"cold",float(def.duration),0,side)
			"fury":
				# A manual initiative window: accelerate the selected formation, not just damage.
				for ally in area_units(x,2.4,side,y):
					if db.balance.units[ally.id].get("economy",false):continue
					set_status(ally,"fury",float(def.duration))
					ally.cooldown=minf(float(ally.cooldown),.08)
					if float(ally.windup)>0:ally.windup=minf(float(ally.windup),.08)
			"stamp": scheduled.append({"at":time+float(def.delay),"side":side,"x":x,"y":y,"radius":float(def.radius),"damage":float(def.damage),"fx":"stamp"})
			"sacrifice":
				var mana = floorf(target.hp*.18)
				var received: float=gain_mana(side,mana,"sacrifice")
				die(target,false)
				event("mana_gain",{"side":side,"x":x,"amount":received})
			"bind": set_status(target,"bind",float(def.duration),0,side); interrupt(target,side)
			"poison":
				spell_areas.append({"id":id,"side":side,"x":x,"y":y,"radius":float(def.radius),"left":float(def.duration),"pulse":0.0,"period":.25,"status":"poison","potency":float(def.damage_per_second)})
			"convert":
				target.side=side; target.facing=1 if side==0 else -1
				if movement_sides_active:prepare_movement_sides()
				target.target=0; target.windup=0.0; target.owner=0
				# Pending attacks revalidate independently. New allies shed damage-over-time
				# originating from their new team, rather than retaining friendly poison.
				for key in ["cold","bind","root","stun","silence","poison","burn"]:
					if target.statuses.has(key) and int(target.statuses[key].source)==side:target.statuses.erase(key)
				# A converted caster cannot leave hostile projectiles and attached
				# weapon effects attacking its new teammates under an old team flag.
				for projectile in projectiles.duplicate():
					if int(projectile.source)==int(target.uid) or (int(projectile.target)==int(target.uid) and int(projectile.side)==side):projectiles.erase(projectile)
				for ally in units:
					if ally.side!=side:continue
					for key in ally.statuses.keys():
						if int(ally.statuses[key].get("source_uid",0))==int(target.uid) and key in ["cold","bind","root","stun","silence","poison","burn"]:ally.statuses.erase(key)
			"burst": area_damage(x,float(def.radius),float(def.damage),side,false,y)
			"protect": set_status(target,"protect",float(def.duration))
			"clone":
				var copy = spawn(target.id,side,x-(.45 if side==0 else -.45),true)
				map.apply_anchor(copy,map.anchor(target.edge,clampf(float(target.s)+(-.45 if side==0 else .45),0,map.edges[target.edge].length)))
				copy.hp=target.hp; copy.max_hp=target.max_hp
				copy.ttl=float(def.get("clone_lifetime",10))
				if def.has("clone_haste"):set_status(copy,"haste",copy.ttl,float(def.clone_haste),side)
				if def.get("clone_reset",false):SpellRules.reset_reload(copy)
				stats[side].summons+=1
			"fire":
				for pulse in range(3): scheduled.append({"at":time+float(pulse)*float(def.pulse_interval),"side":side,"x":x,"y":y,"radius":float(def.radius),"damage":float(def.damage_per_pulse),"fx":"fire"})
			"root": set_status(target,"root",float(def.duration),0,side)
			"guardian":
				var guard = spawn("unit.deng.guardian",side,x)
				map.apply_anchor(guard,map.project(Vector2(x,y))); stats[side].summons+=1
				guard.ttl=float(def.get("guardian_lifetime",8))
				if def.has("guardian_haste"):set_status(guard,"haste",guard.ttl,float(def.guardian_haste),side)
	SpellRules.after_cast(self,side,id,x,y,target,def)
	visibility.refresh()
	if db.factions[p.faction].mana=="control" and tail in ["cold","bind","root"]:
		var controlled: int = 1 if not target.is_empty() else area_units(x,float(def.get("radius",2)),1-side,y).size()
		if controlled>0:gain_mana(side,minf(4,controlled*1.5),"control")
	event("cast",{"id":id,"side":side,"x":x,"y":y,"uid":target_uid,"radius":float(def.get("radius",.8))})
	return ""

func set_status(u: Dictionary, key: String, duration: float, potency: float = 0.0, source: int = -1, source_uid: int=0):
	if u.is_empty() or u.hp<=0 or duration<=0: return
	if key in ["cold","bind","root","stun","silence","poison","burn"] and source in [0,1] and not hostile_target(u,source,source_uid):return
	if key in ["poison","burn"] and source not in [0,1]:return
	var old = u.statuses.get(key,{"left":0.0,"potency":0.0})
	var replace_source: bool=potency>=float(old.potency)
	u.statuses[key]={"left":maxf(old.left,duration),"potency":maxf(old.potency,potency),"source":source if replace_source else int(old.source),"source_uid":source_uid if replace_source else int(old.get("source_uid",0)),"clock":float(old.get("clock",0.0))}

func interrupt(u: Dictionary, by: int):
	if u.get("windup",0)>0:
		u.windup=0; u.anim="hurt"; u.anim_t=0
		u.cooldown=maxf(u.cooldown,.3)
		stats[by].interrupts+=1
		event("interrupt",{"x":u.x,"uid":u.uid,"side":by})

func area_units(x: float, radius: float, side: int, y: float = NAN) -> Array:
	var out=[]
	if is_nan(y): y=map.ground_y_at(x)
	for u in units:
		if u.hp>0 and u.side==side and physical_point(u).distance_to(Vector2(x,y))<=radius: out.append(u)
	return out

func area_damage(x: float, radius: float, amount: float, side: int, physical: bool, y: float = NAN, source_uid: int=0):
	if is_nan(y): y=map.ground_y_at(x)
	for u in area_units(x,radius,1-side,y): damage(u,amount,side,physical,source_uid)
	for b in buildings+bases:
		if b.hp>0 and b.side!=side and Vector2(b.x,b.y).distance_to(Vector2(x,y))<=radius: damage(b,amount,side,physical,source_uid)

func hostile_target(target: Dictionary,side: int,source_uid: int=0) -> bool:
	if target.is_empty() or side not in [0,1] or int(target.side)!=1-side or float(target.hp)<=0:return false
	var source: Dictionary=actor(source_uid) if source_uid!=0 else {}
	return source.is_empty() or int(source.side)==side

func damage(target: Dictionary, amount: float, side: int, physical: bool = true, source_uid: int = 0) -> float:
	if not hostile_target(target,side,source_uid) or not is_finite(amount) or amount<=0:return 0.0
	amount=damage_after_defense(target,amount,side,physical)
	var actual: float=minf(float(target.hp),maxf(0.0,amount))
	if actual<=0:return 0.0
	target.hp=maxf(0.0,target.hp-actual)
	if target_answers_active and target.hp<=0:target_answers.clear();marching_answers.clear()
	record_damage_hit(target,actual,side,physical,source_uid)
	if not target.get("building",false):Abilities.on_damaged(self,target,db.balance.units[target.id],source_uid,physical)
	process_damage_death(target,side)
	return actual

func damage_after_defense(target: Dictionary,amount: float,side: int,physical: bool) -> float:
	if not target.get("building",false):
		if target.statuses.has("protect"):
			event("blocked",{"x":target.x,"uid":target.uid,"side":target.side})
			return 0.0
		var def: Dictionary = db.balance.units[target.id]
		amount=Abilities.defense(self,target,def,amount,physical)
		if physical and target.statuses.has("brace"):amount*=1-clampf(float(target.statuses.brace.potency),0,.6)
		if physical: amount*=float(def.get("physical_damage_multiplier",1.0))
		else: amount*=float(def.get("magic_damage_multiplier",1.0))
		if not physical and db.factions[players[target.side].faction].trait=="ward":
			for lamp in buildings:
				if lamp.side==target.side and lamp.id.ends_with(".mana") and lamp.state=="active" and lamp.disabled<=0 and physical_point(lamp).distance_to(physical_point(target))<=3.5:
					amount*=.8;break
		if def.get("economy",false):
			var body: Vector2=physical_point(target)
			for guard in area_units(body.x,3.0,target.side,body.y):
				var guardian: Dictionary = db.balance.units[guard.id]
				if guardian.has("worker_guard_reduction") and melee_distance(target,guard)<=float(guardian.worker_guard_radius):
					amount*=1-float(guardian.worker_guard_reduction);break
	return maxf(0.0,amount)

func record_damage_hit(target: Dictionary,actual: float,side: int,physical: bool,source_uid: int):
	if not target.get("building",false):
		var def: Dictionary=db.balance.units[target.id]
		if db.factions[players[target.side].faction].mana=="damage" and not def.get("economy",false) and not def.get("summoned",false) and not target.clone and side!=target.side:
			var p: Dictionary = players[target.side]
			if time-float(p.get("reward_at",-1))>=1: p["reward_at"]=time; p["reward_used"]=0.0
			var reward: float = minf(maxf(0,3-float(p.get("reward_used",0))),actual*.06)
			gain_mana(target.side,reward,"damage");p["reward_used"]=float(p.get("reward_used",0))+reward
	target.hurt=.30
	if not target.get("building",false) and target.windup<=0 and target.anim!="attack": target.anim="hurt"; target.anim_t=0.0
	var hit_point: Vector2=physical_point(target)
	event("hit",{"x":hit_point.x,"y":hit_point.y,"uid":target.uid,"source_uid":source_uid,"side":target.side,"attacker_side":side,"amount":actual,"heavy":actual>=34,"physical":physical,"building":target.get("building",false)})
	if not target.get("building",false) and db.balance.units[target.id].get("economy",false):
		var defender: Dictionary=players[int(target.side)]
		if time-float(defender.get("economy_alarm_at",-8.0))>=8.0:
			defender["economy_alarm_at"]=time
			# Owned damage is known even if this hit kills the last local observer.
			event("economy_alarm",{"observer":target.side,"side":target.side,"uid":target.uid,"x":hit_point.x,"y":hit_point.y})

func process_damage_death(target: Dictionary,side: int):
	if target.hp>0 or target.get("death_processed",false) or target.get("death_queued",false):return
	target["death_queued"]=true
	if not target.get("building",false):
		stats[side].killed+=1;stats[target.side].lost+=1
	if resolving_combat_hits:combat_deaths.append(target)
	else:finish_damage_death(target)

func finish_damage_death(target: Dictionary):
	if target.get("building",false):
		target["death_processed"]=true
		if visibility!=null:visibility.mark_dirty()
		event("building_death",{"x":target.x,"y":target.y,"side":target.side,"id":target.id})
	else:die(target,true)

func die(u: Dictionary, create_corpse: bool):
	if u.get("death_processed",false): return
	u["death_processed"]=true
	u.hp=0.0
	if visibility!=null:visibility.mark_dirty()
	if target_answers_active:target_answers.clear();marching_answers.clear()
	var def = db.balance.units[u.id]
	if create_corpse and not u.clone and def.get("creates_corpse",true) and not def.get("economy",false):
		corpses.append({"uid":next_uid,"x":u.x,"y":u.y,"edge":u.edge,"s":u.s,"left":8.0})
		next_uid+=1
	var foot: Vector2=physical_point(u)
	event("death",{"x":foot.x,"y":foot.y,"id":u.id,"side":u.side,"uid":u.uid,"facing":u.facing,"puppet":u.duplicate(true)})
	Abilities.on_death(self,u,def)

# The unit phase restores every movement intent before the next actor runs.
# Query records therefore share one physical geometry. They retain live actors
# for immediate death/ownership filtering and the original sight-list rank.
func prepare_melee_queries():
	if melee_query_revision==visibility.revision:return
	prepare_target_snapshot()
	if melee_snapshot_generation==target_snapshot_generation:
		melee_query_revision=visibility.revision;return
	melee_snapshot_generation=target_snapshot_generation
	melee_query_revision=visibility.revision;melee_query_roads=[{},{}];melee_query_valid=true
	if melee_neighbor_edges.is_empty():
		for edge_id in map.edges:
			var source: Dictionary=map.edges[edge_id]
			var neighbors: Dictionary={}
			for node_id in [source.from,source.to]:
				for link in map.adjacency[node_id]:
					if link.edge==edge_id:continue
					var edge: Dictionary=map.edges[link.edge]
					if not neighbors.has(link.edge):neighbors[link.edge]=[]
					neighbors[link.edge].append(0.0 if node_id==edge.from else float(edge.length))
			melee_neighbor_edges[edge_id]=neighbors
	for side in [0,1]:
		var rank: int=0
		for actor_value in visibility.enemies[side]:
			var body: Dictionary=physical_anchor(actor_value)
			var offset: float=float(body.s)
			if not is_finite(offset) or offset<0 or offset>float(map.edges[body.edge].length):melee_query_valid=false
			if not melee_query_roads[side].has(body.edge):melee_query_roads[side][body.edge]={"all":RoadQueryRecords.new(),"support":RoadQueryRecords.new()}
			var support: bool=not actor_value.get("building",false) and db.balance.units[actor_value.id].get("role","") in ["medic","engineer","scribe","necromancer","summoner","illusionist","oracle"]
			var road: Dictionary=melee_query_roads[side][body.edge]
			var all_records: RoadQueryRecords=road.all
			all_records.add(actor_value,offset,rank,support,body.edge)
			if support:
				var support_records: RoadQueryRecords=road.support
				support_records.add(actor_value,offset,rank,true,body.edge)
			rank+=1
		for road in melee_query_roads[side].values():
			for records in [road.all,road.support]:records.order(true)

# Arc offsets stay float64, including the rounded-junction tie fixtures.
func nearest_road_records(records: RoadQueryRecords,offset: float,side: int) -> PackedInt32Array:
	var lo: int=0;var hi: int=records.actors.size()
	while lo<hi:
		var middle: int=(lo+hi)/2
		if records.offsets[middle]<offset:lo=middle+1
		else:hi=middle
	var candidates: PackedInt32Array=PackedInt32Array();var distance: float=INF
	for direction in [-1,1]:
		var index: int=lo-1 if direction<0 else lo
		while index>=0 and index<records.actors.size():
			var next_distance: float=absf(records.offsets[index]-offset)
			if next_distance>distance+0.000000001:break
			var candidate: Dictionary=records.actors[index]
			if candidate.hp>0 and int(candidate.side)!=side:
				distance=minf(distance,next_distance)
				var same: int=-1
				for i in range(candidates.size()):
					if records.offsets[candidates[i]]==records.offsets[index]:same=i;break
				if same<0:candidates.append(index)
				elif records.ranks[index]<records.ranks[candidates[same]]:candidates[same]=index
			index+=direction
	return candidates

func nearest_melee_query(anchor: Dictionary,side: int,priority: bool,reach: float) -> Dictionary:
	var roads: Dictionary=melee_query_roads[side]
	var requests: Dictionary=melee_neighbor_edges[anchor.edge].duplicate(false)
	requests[anchor.edge]=[float(anchor.s)]
	var best: Dictionary={};var distance: float=10000.0;var rank: int=2147483647
	for edge_id in requests:
		if not roads.has(edge_id):continue
		var road: Dictionary=roads[edge_id]
		var pools: Array[RoadQueryRecords]=[road.all]
		if priority:pools.append(road.support)
		for offset in requests[edge_id]:
			for records in pools:
				for index in nearest_road_records(records,float(offset),side):
					var d: float=map.melee_distance(anchor,records.anchors[index])
					var score: float=d*.35 if priority and records.supports[index]!=0 and d<=reach else d
					if score<distance or (not best.is_empty() and score==distance and records.ranks[index]<rank):
						best=records.actors[index];distance=score;rank=records.ranks[index]
	return best

func prepare_ranged_queries():
	if ranged_query_revision==visibility.revision:return
	prepare_target_snapshot()
	if ranged_snapshot_generation==target_snapshot_generation:
		ranged_query_revision=visibility.revision;return
	ranged_snapshot_generation=target_snapshot_generation
	ranged_query_records=[RangedQueryRecords.new(),RangedQueryRecords.new()];ranged_query_valid=true
	for observer in [0,1]:
		var records: RangedQueryRecords=ranged_query_records[observer]
		for actor_value in visibility.enemies[observer]:
			var anchor: Dictionary=physical_anchor(actor_value)
			var point: Vector2=Vector2(anchor.x,anchor.y)
			if not is_finite(point.x) or not is_finite(point.y):ranged_query_valid=false
			var support: bool=not actor_value.get("building",false) and db.balance.units[actor_value.id].get("role","") in ["medic","engineer","scribe","necromancer","summoner","illusionist","oracle"]
			records.actors.append(actor_value);records.points.append(point);records.supports.append(1 if support else 0)
	if ranged_query_valid:
		for records in ranged_query_records:records.order_x()
	ranged_query_revision=visibility.revision

func nearest_ranged_query(origin: Vector2,side: int,priority: bool,reach: float) -> Dictionary:
	var records: RangedQueryRecords=ranged_query_records[side]
	var actors: Array[Dictionary]=records.actors
	var points: PackedVector2Array=records.points
	var best_index: int=-1;var distance: float=10000.0
	# Pass0 finds the raw nearest actor. Pass1 separately finds weighted
	# supports in range, so a weighted best never prunes another support.
	for pass_index in range(2 if priority else 1):
		var indices: PackedInt32Array=records.by_x if pass_index==0 else records.support_by_x
		if pass_index==1 and best_index>=0 and records.supports[best_index]!=0 and distance<=reach:distance*=.35
		var lo: int=0;var hi: int=indices.size()
		while lo<hi:
			var middle: int=(lo+hi)/2
			if points[indices[middle]].x<origin.x:lo=middle+1
			else:hi=middle
		for direction in [-1,1]:
			var at: int=lo-1 if direction<0 else lo
			while at>=0 and at<indices.size():
				var index: int=indices[at];var point: Vector2=points[index]
				# Use the same native Vector2 length arithmetic as distance_to.
				# A scalar float64 abs(dx) can exceed the rounded float32 full
				# distance and incorrectly discard an equal-score earlier rank.
				var lower: float=Vector2(origin.x-point.x,0).length()
				if lower>distance if pass_index==0 else (lower>reach or lower*.35>distance):break
				at+=direction
				var actor_value: Dictionary=actors[index]
				if int(actor_value.side)==side or actor_value.hp<=0:continue
				var d: float=origin.distance_to(point)
				if pass_index==1 and d>reach:continue
				var score: float=d if pass_index==0 else d*.35
				if score<distance or (best_index>=0 and score==distance and index<best_index):best_index=index;distance=score
	return {} if best_index<0 else actors[best_index]

func nearest_enemy(u: Dictionary) -> Dictionary:
	if not target_answers_active:return nearest_enemy_uncached(u)
	prepare_target_answers()
	var def: Dictionary=db.balance.buildings[u.id] if u.get("building",false) else db.balance.units[u.id]
	var anchor: Dictionary=physical_anchor(u)
	var melee: bool=str(def.get("attack","projectile")).begins_with("melee")
	var priority: bool=bool(def.get("support_priority",false)) and not u.get("building",false)
	var reach: float=float(def.range) if priority else 0.0
	var point: Vector2=Vector2.ZERO if melee else Vector2(anchor.x,anchor.y)
	var side: int=int(u.side)
	var memo: TargetAnswer=target_answers.get(u.uid)
	if memo!=null and is_same(memo.source,u) and memo.side==side and memo.melee==melee and memo.priority==priority and memo.reach==reach and memo.edge==anchor.edge and memo.offset==float(anchor.s) and memo.point==point:
		if memo.target.is_empty() or (memo.target.hp>0 and int(memo.target.side)!=side):
			target_answer_hits+=1;return memo.target
	var result: Dictionary=nearest_enemy_uncached(u)
	memo=TargetAnswer.new();memo.source=u;memo.target=result;memo.side=side;memo.melee=melee;memo.priority=priority;memo.reach=reach;memo.edge=anchor.edge;memo.offset=float(anchor.s);memo.point=point
	# At most256 source references, regardless of a long match's UID growth.
	if target_answers.size()>=256 and not target_answers.has(u.uid):target_answers.clear()
	target_answers[u.uid]=memo;target_answer_misses+=1
	return result

func nearest_enemy_uncached(u: Dictionary) -> Dictionary:
	var best={}; var distance=10000.0
	var def: Dictionary = db.balance.buildings[u.id] if u.get("building",false) else db.balance.units[u.id]
	var anchor: Dictionary=physical_anchor(u)
	var melee: bool=str(def.get("attack","projectile")).begins_with("melee")
	var origin: Vector2=Vector2.ZERO if melee else Vector2(anchor.x,anchor.y)
	var edge: String=anchor.edge if melee else ""
	var offset: float=float(anchor.s) if melee else 0.0
	var priority: bool=bool(def.get("support_priority",false)) and not u.get("building",false)
	var reach: float=float(def.range) if priority else 0.0
	var side: int=int(u.side)
	if melee and movement_sides_active:
		prepare_melee_queries()
		if melee_query_valid and offset>=0 and offset<=float(map.edges[edge].length):
			return nearest_melee_query(anchor,side,priority,reach)
	if not melee and movement_sides_active:
		prepare_ranged_queries()
		if ranged_query_valid:
			return nearest_ranged_query(origin,side,priority,reach)
	for e in visibility.enemies[side]:
		if e.side==side or e.hp<=0:continue
		var destination: Dictionary=physical_anchor(e)
		var d: float
		if melee and edge==destination.edge:d=absf(offset-float(destination.s))
		elif melee:d=map.melee_distance(anchor,destination)
		else:d=origin.distance_to(Vector2(destination.x,destination.y))
		var score: float = d
		if priority and not e.get("building",false) and d<=reach:
			if db.balance.units[e.id].get("role","") in ["medic","engineer","scribe","necromancer","summoner","illusionist","oracle"]:score*=.35
		if score<distance:best=e;distance=score
	return best

func combat_distance(a: Dictionary, b: Dictionary, def: Dictionary) -> float:
	if str(def.get("attack","projectile")).begins_with("melee"):
		return melee_distance(a,b)
	return physical_point(a).distance_to(physical_point(b))

func physical_anchor(a: Dictionary) -> Dictionary:
	if not a.has("body_anchor"):return a
	return a.get("body_anchor",a) if a.has("id") and db.balance.units.has(a.id) and not a.get("building",false) and db.balance.units[a.id].get("economy",false) else a

func physical_point(a: Dictionary) -> Vector2:
	var anchor: Dictionary=physical_anchor(a)
	return Vector2(float(anchor.x),float(anchor.y))

func melee_distance(a: Dictionary,b: Dictionary) -> float:
	return map.melee_distance(physical_anchor(a),physical_anchor(b))

func update_worker_body(u: Dictionary,dt: float):
	# The service location stays at the mine. The worker's actual body stands at
	# its FIFO station on the same road, shared by targeting, AoE and rendering.
	var target_offset: float=0
	if u.job=="mine" and u.mine!="":
		for mine in map.definition.mines:
			if mine.id!=u.mine:continue
			if u.edge!=mine.edge:break
			var distance: float=absf(float(u.s)-float(mine.s))
			if distance<1.25:
				var incoming: Array=units.filter(func(w):return w.hp>0 and w.side==u.side and w.mine==u.mine and w.job=="mine")
				incoming.sort_custom(func(a,b):
					var aa: float=float(a.get("mine_arrived_at",-1));var bb: float=float(b.get("mine_arrived_at",-1))
					if aa>=0 and bb<0:return true
					if bb>=0 and aa<0:return false
					return int(a.uid)<int(b.uid) if aa==bb else aa<bb)
				var slot: int=int(u.get("work_slot",incoming.find(u))) if float(u.get("mine_arrived_at",-1))>=0 else incoming.find(u)
				var forward: float=1 if u.side==0 else -1
				target_offset=-forward*(.60+maxi(0,slot)*.86)*(1-smoothstep(.05,1.25,distance))
			break
	u["body_offset"]=lerpf(float(u.get("body_offset",0)),target_offset,1-exp(-dt*12))
	u["body_anchor"]=map.anchor(u.edge,clampf(float(u.s)+float(u.body_offset),0,float(map.edges[u.edge].length)))

func tick(dt: float):
	if winner!=-2: return
	time+=dt; tick_count+=1
	for side in range(2):
		var p = players[side]
		var rate: float=mana_rate(side)
		var generated: float=minf(100.0-p.mana,rate*dt)
		p.mana=minf(100.0,p.mana+rate*dt)
		if generated>0 and rate>0:
			var sources: Dictionary=mana_rate_sources(side)
			for source in sources:record_mana_income(side,source,generated*float(sources[source])/rate)
		for key in p.cooldowns: p.cooldowns[key]=maxf(0.0,p.cooldowns[key]-dt)
		if not p.queue.is_empty() and bases[side].hp>0:
			p.production+=dt
			var production_time: float = float(db.balance.units[p.queue[0]].get("production_seconds",2.0))
			if p.production>=production_time:
				p.production-=production_time
				var id=p.queue.pop_front()
				p.queue_revision+=1
				var entrance: Dictionary = {}
				if side==1:
					for candidate in config.get("enemy_entries",[]):
						if time>=float(candidate.get("unlock_time",0)):entrance=candidate
				var unit: Dictionary = spawn(id,side,float(entrance.get("x",bases[side].x+(0.65 if side==0 else -.65))),false,0,"production")
				if not entrance.is_empty():map.apply_anchor(unit,entrance)
		if not p.research.is_empty():
			p.research.left-=dt
			if p.research.left<=0:
				var node=db.tech(p.research.id)
				p.studied.append(node.id)
				if not p.unlocked.has(node.grant): p.unlocked.append(node.grant)
				p.research={}
				var mana_reward: float=0.0
				if db.factions[p.faction].mana=="research":mana_reward=gain_mana(side,8,"research")
				event("research_done",{"side":side,"id":node.grant,"mana_reward":mana_reward})
	for b in bases+buildings:
		b.hurt=maxf(0,b.hurt-dt)
		if b.get("base",false) or b.hp<=0: continue
		var def=db.balance.buildings[b.id]
		var previous_disabled: float=float(b.disabled)
		b.disabled=maxf(0,b.disabled-dt)
		if visibility!=null and previous_disabled>0 and float(b.disabled)<=0:visibility.mark_dirty()
		if b.state=="constructing":
			b.construction=maxf(0,b.construction-dt)
			if b.construction<=0:
				b.state="active"; event("building_completed",{"uid":b.uid,"side":b.side,"x":b.x,"id":b.id})
				if visibility!=null:visibility.mark_dirty()
				if db.factions[players[b.side].faction].mana=="construction": gain_mana(b.side,12,"construction")
			continue
		if b.disabled>0: continue
		b.cooldown-=dt
		if def.has("damage") and b.cooldown<=0:
			var target=nearest_enemy(b)
			if not target.is_empty() and combat_distance(b,target,def)<=float(def.range):
				launch(b,target,float(def.damage),0.0,1.0,0.0)
				b.cooldown=float(def.attack_interval)
	update_ranged_formations()
	var movement_intents: Array=[]
	prepare_movement_sides();movement_sides_active=true;target_answers_active=units.size()>=40;marching_answers_active=target_answers_active
	collecting_attacks=true
	tick_units_snapshot.clear()
	tick_units_snapshot.append_array(units)
	for u in tick_units_snapshot:
		if u.hp<=0: continue
		var original_anchor: Dictionary=movement_anchor(u)
		movement_current_uid=int(u.uid);movement_current_anchor=original_anchor
		tick_unit(u,dt)
		if u.hp>0 and db.balance.units[u.id].get("economy",false):update_worker_body(u,dt)
		# Bound, recovering and blocked actors often do not move. Avoid a second
		# anchor allocation and two sets of writes when the position is unchanged.
		if u.edge!=original_anchor.edge or u.s!=original_anchor.s or u.x!=original_anchor.x or u.y!=original_anchor.y or u.get("body_anchor",{})!=original_anchor.get("body_anchor",{}):
			movement_intents.append({"actor":u,"anchor":movement_anchor(u)})
			apply_movement_anchor(u,original_anchor)
	movement_current_uid=0;movement_current_anchor={}
	collecting_attacks=false;movement_sides_active=false;target_answers_active=false;marching_answers_active=false
	collecting_combat_hits=true
	release_attack_intents()
	# All actors perceive the same pre-movement positions during this phase.
	for intent in movement_intents:
		if intent.actor.hp>0:apply_movement_anchor(intent.actor,intent.anchor)
	if visibility!=null and not movement_intents.is_empty():visibility.mark_dirty()
	tick_projectiles_snapshot.clear()
	tick_projectiles_snapshot.append_array(projectiles)
	for p in tick_projectiles_snapshot:
		p.left-=dt
		var tracked: Dictionary=actor(int(p.target))
		if not tracked.is_empty() and not hostile_target(tracked,int(p.side),int(p.source)):
			projectiles.erase(p);continue
		if tracked.is_empty() and float(p.radius)<=0:projectiles.erase(p);continue
		if not tracked.is_empty():
			var body: Vector2=physical_point(tracked)
			p.end_x=body.x;p.end_y=body.y
		p.x=lerpf(p.start_x,p.end_x,clampf(1.0-p.left/p.total,0,1))
		p.y=lerpf(p.start_y,p.end_y,clampf(1.0-p.left/p.total,0,1))
		if p.left<=0:
			projectiles.erase(p)
			projectile_hit(p)
	collecting_combat_hits=false
	resolve_combat_hits()
	tick_scheduled_snapshot.clear()
	tick_scheduled_snapshot.append_array(scheduled)
	for action in tick_scheduled_snapshot:
		if action.at<=time:
			scheduled.erase(action)
			area_damage(action.x,action.radius,action.damage,action.side,false,action.y)
			event("impact",{"x":action.x,"y":action.y,"side":action.side,"fx":action.fx,"radius":action.radius})
	SpellRules.tick_zones(self,dt)
	tick_corpses_snapshot.clear()
	tick_corpses_snapshot.append_array(corpses)
	for c in tick_corpses_snapshot:
		c.left-=dt
		if c.left<=0: corpses.erase(c)
	alive_units_buffer.clear()
	for u in units:
		if u.hp>0:alive_units_buffer.append(u)
	var previous_units: Array=units
	units=alive_units_buffer
	alive_units_buffer=previous_units
	alive_buildings_buffer.clear()
	for b in buildings:
		if b.hp>0:alive_buildings_buffer.append(b)
	var previous_buildings: Array=buildings
	buildings=alive_buildings_buffer
	alive_buildings_buffer=previous_buildings
	evaluate_objective()
	visibility.refresh(false)
	if winner!=-2:
		event("result",{"winner":winner}); return
	for side in range(2):
		if not ai_enabled[side]: continue
		ai_clock[side]-=dt
		if ai_clock[side]<=0:
			ai_clock[side]=[1.25,.65,.35][int(config.get("difficulty",1))]
			ai_turn(side)
	# AI commands can change routes, spawn actors or create vision fields after
	# the simulation phase's first refresh. Publish those changes in the same
	# tick so the renderer and the next command observe current fog immediately.
	visibility.refresh(false)

# Used only during the simultaneous unit phase. Keep live actor references:
# movement, death and a just-born summon remain visible to later blockers.
func prepare_movement_sides():
	blocker_roads_dirty=true;target_answers_revision=-1;marching_answers_ready=false
	melee_query_revision=-1;ranged_query_revision=-1
	movement_side_units=[[],[]]
	for unit in units:movement_side_units[int(unit.side)].append(unit)

func prepare_blocker_roads():
	blocker_roads=[{},{}];blocker_roads_valid=true
	for ally in units:
		var anchor: Dictionary=movement_current_anchor if int(ally.uid)==movement_current_uid else ally
		var offset: float=float(anchor.s)
		if not is_finite(offset):blocker_roads_valid=false
		if ally.hp<=0 or db.balance.units[ally.id].get("economy",false):continue
		var roads: Dictionary=blocker_roads[int(ally.side)]
		if not roads.has(anchor.edge):roads[anchor.edge]=BlockerQueryRecords.new()
		var records: BlockerQueryRecords=roads[anchor.edge]
		records.actors.append(ally);records.offsets.append(offset)
	for roads in blocker_roads:
		for records in roads.values():records.order()
	blocker_roads_dirty=false

func marching_step(u: Dictionary,def: Dictionary,enemy: Dictionary,step: float,forward: float) -> float:
	if not marching_answers_active or not movement_sides_active or step<=0 or not is_finite(step) or forward not in [-1.0,1.0]:return marching_step_uncached(u,def,enemy,step,forward)
	if blocker_roads_dirty and marching_answers_ready:marching_answers_ready=false
	prepare_marching_answers()
	if not blocker_roads_valid or not is_finite(float(u.s)):return marching_step_uncached(u,def,enemy,step,forward)
	var side: int=int(u.side);var edge: String=u.edge;var offset: float=float(u.s)
	var reach: float=float(def.range);var giant: bool=def.get("role","")=="colossus";var sees_enemy: bool=not enemy.is_empty()
	var memo: MarchingAnswer=marching_answers.get(u.uid)
	if memo!=null and is_same(memo.source,u) and memo.uid==u.uid and memo.side==side and memo.edge==edge and memo.offset==offset and memo.reach==reach and memo.giant==giant and memo.sees_enemy==sees_enemy and memo.forward==forward:
		if memo.limit<memo.requested or step<=memo.requested:
			marching_answer_hits+=1;return minf(step,memo.limit) if memo.limit<memo.requested else step
	var result: float=marching_step_uncached(u,def,enemy,step,forward)
	memo=MarchingAnswer.new();memo.source=u;memo.uid=u.uid;memo.side=side;memo.edge=edge;memo.offset=offset;memo.reach=reach;memo.giant=giant;memo.sees_enemy=sees_enemy;memo.forward=forward;memo.requested=step;memo.limit=result
	if marching_answers.size()>=256 and not marching_answers.has(u.uid):marching_answers.clear()
	marching_answers[u.uid]=memo;marching_answer_misses+=1
	return result

func marching_step_uncached(u: Dictionary,def: Dictionary,enemy: Dictionary,step: float,forward: float) -> float:
	if step<=0:return step
	if movement_sides_active:
		if blocker_roads_dirty:prepare_blocker_roads()
		if blocker_roads_valid and is_finite(float(u.s)):
			var roads: Dictionary=blocker_roads[int(u.side)]
			if not roads.has(u.edge):return step
			var records: BlockerQueryRecords=roads[u.edge]
			var actors: Array[Dictionary]=records.actors
			var offsets: PackedFloat64Array=records.offsets
			var lo: int=0;var hi: int=actors.size()
			while lo<hi:
				var middle: int=(lo+hi)/2
				if offsets[middle]<=float(u.s):lo=middle+1
				else:hi=middle
			var index: int=lo if forward>0 else lo-1
			var gap: float=.72 if def.get("role","")=="colossus" else .54
			while index>=0 and index<actors.size():
				var actor_index: int=index
				var ahead: float=(offsets[actor_index]-float(u.s))*forward
				if ahead>step+gap+0.000000001:break
				var ally: Dictionary=actors[actor_index]
				index+=1 if forward>0 else -1
				if ahead<=0 or ally.uid==u.uid or ally.side!=u.side or ally.hp<=0 or ally.edge!=u.edge:continue
				var other: Dictionary=db.balance.units[ally.id]
				if float(def.range)<=1.5 and (float(other.range)>1.5 or other.get("role","") in ["medic","engineer","necromancer","summoner","oracle","scribe"]):continue
				if not enemy.is_empty() and float(def.range)>1.5 and float(other.range)>float(def.range)+.05:continue
				return minf(step,maxf(0,ahead-gap))
			return step
	var blockers: Array=units
	for ally in blockers if step>0 else []:
		if ally.uid==u.uid or ally.side!=u.side or ally.hp<=0 or ally.edge!=u.edge or db.balance.units[ally.id].get("economy",false):continue
		var ally_def: Dictionary = db.balance.units[ally.id]
		if float(def.range)<=1.5 and (float(ally_def.range)>1.5 or ally_def.get("role","") in ["medic","engineer","necromancer","summoner","oracle","scribe"]):continue
		# A short-range shooter/healer may pass a long-range backliner to
		# reach its own firing/support position. Melee screens still block it.
		if not enemy.is_empty() and float(def.range)>1.5 and float(ally_def.range)>float(def.range)+.05:continue
		var ahead: float = (float(ally.s)-float(u.s))*forward
		if ahead>0:
			var gap: float = .72 if def.get("role","")=="colossus" else .54
			step=minf(step,maxf(0,ahead-gap))
			if step==0:break
	return step

func movement_anchor(u: Dictionary) -> Dictionary:
	var anchor: Dictionary={"edge":u.edge,"s":u.s,"x":u.x,"y":u.y}
	if u.has("body_anchor"):anchor["body_anchor"]=u.body_anchor.duplicate(true)
	return anchor

func apply_movement_anchor(u: Dictionary,anchor: Dictionary):
	for key in ["edge","s","x","y"]:u[key]=anchor[key]
	if anchor.has("body_anchor"):u["body_anchor"]=anchor.body_anchor.duplicate(true)
	else:u.erase("body_anchor")

func tick_unit(u: Dictionary, dt: float):
	var def: Dictionary=db.balance.units[u.id]
	var statuses: Dictionary=u.statuses
	mark_objective_crossing(u)
	u.age+=dt; u.anim_t+=dt; u.hurt=maxf(0.0,u.hurt-dt)
	u["visual_special"]=maxf(0,float(u.get("visual_special",0))-dt)
	u["visual_load"]=maxf(0,float(u.get("visual_load",0))-dt)
	u.cooldown-=dt*(1.6 if statuses.has("fury") else 1.0); u.special_cd-=dt; u.summon_cd-=dt; u.control_clock=maxf(0,float(u.control_clock)-dt)
	if u.ttl>0:
		u.ttl-=dt
		if u.ttl<=0: die(u,false); return
	for key in statuses.keys():
		var status: Dictionary=statuses[key]
		if key in ["cold","bind","root","stun","silence","poison","burn","exposed"] and int(status.source) in [0,1] and not hostile_target(u,int(status.source),int(status.get("source_uid",0))):
			statuses.erase(key);continue
		var active_time: float=minf(dt,maxf(0,float(status.left)))
		status.left-=dt
		if key in ["poison","burn"]:
			status.clock+=active_time
			if status.clock>=.25-0.00001 or status.left<=0:
				damage(u,status.potency*status.clock,int(status.source),false,int(status.get("source_uid",0))); status.clock=0.0
		if status.left<=0: statuses.erase(key)
	if u.hp<=0: return
	if def.get("economy",false): tick_worker(u,dt); return
	var weapon_range: float=float(def.range)
	if statuses.has("bind") or statuses.has("stun"):
		interrupt(u,1-u.side); u.anim="bound"; return
	Abilities.tick(self,u,def,dt)
	if def.has("summons") and u.summon_cd<=0 and not statuses.has("silence"):
		var count=0
		for other in units:
			if other.owner==u.uid and other.hp>0: count+=1
		if count<int(def.max_owned_thralls) and population(u.side)<60:
			for c in corpses:
				if melee_distance(c,u)<=float(def.corpse_range):
					var thrall=spawn(def.summons,u.side,c.x,false,u.uid)
					map.apply_anchor(thrall,c)
					corpses.erase(c); u.summon_cd=float(def.summon_interval)
					stats[u.side].summons+=1
					u["visual_special"]=.6;event("unit_special",{"uid":u.uid,"target_uid":thrall.uid,"side":u.side,"x":u.x,"y":u.y,"fx":"soul"})
					event("summon",{"x":thrall.x,"side":u.side}); break
	if u.windup>0:
		u.windup-=dt*(1.6 if statuses.has("fury") else 1.0); u.anim="windup"
		var pending: Dictionary=actor(int(u.target))
		if not hostile_target(pending,int(u.side)):
			u.windup=0;u.target=0;u.anim="idle";return
		if u.windup<=0:
			if combat_distance(u,pending,def)<=weapon_range+.3:
				attack(u,pending);u.cooldown=float(def.attack_interval);u.anim="attack";u.anim_t=0.0
				if not collecting_attacks and u.get("reload_pending",false):u.cooldown+=float(def.get("reload_seconds",0))
			else:u.anim="idle"
			u.target=0
		return
	var recovery: float=float(db.unit_actions[u.id].recovery)
	# Finish the released pose even if the victim died or left weapon range.
	# Control effects above still interrupt; recovery does not block incoming damage.
	if u.anim=="attack" and u.anim_t<recovery:return
	if u.get("reload_pending",false) and u.anim_t>=recovery:
		u["reload_pending"]=false;u["reload_left"]=float(def.reload_seconds);u["reload_duration"]=float(def.reload_seconds)
		event("reload",{"uid":u.uid,"id":u.id,"side":u.side,"x":u.x,"y":u.y})
	if float(u.get("reload_left",0))>0:
		u["reload_left"]=maxf(0,float(u.reload_left)-dt);u.anim="reload";return
	u["backpedal"]=false
	if float(u.get("retreat_left",0))>0 and u.anim_t>=recovery and not statuses.has("root"):
		var movement: float=float(def.skirmish_retreat)/float(def.retreat_seconds)*dt
		var previous: float=float(u.s)
		map.apply_anchor(u,map.anchor(u.edge,float(u.s)-float(u.facing)*movement))
		u.walk+=absf(float(u.s)-previous);u["retreat_left"]=maxf(0,float(u.retreat_left)-dt);u["backpedal"]=true;u.anim="walk";return
	var enemy: Dictionary=nearest_enemy(u)
	var distance: float = INF if enemy.is_empty() else combat_distance(u,enemy,def)
	u.facing=(1 if u.side==0 else -1) if enemy.is_empty() or distance>weapon_range else (1 if physical_point(enemy).x>u.x else -1)
	if not enemy.is_empty() and u.edge==enemy.edge and def.has("crossing_max_distance") and u.special_cd<=0 and distance<float(def.crossing_max_distance) and not enemy.get("building",false) and not statuses.has("root") and not statuses.has("silence"):
		var direction=1.0 if u.side==0 else -1.0
		var landing=float(physical_anchor(enemy).s)+direction*1.25
		if absf(landing-float(u.s))<=float(def.crossing_max_distance):
			var previous=u.x; var old_y=u.y
			map.apply_anchor(u,map.anchor(u.edge,landing))
			u.special_cd=float(def.crossing_cooldown)
			event("dash",{"x":u.x,"from":previous,"from_y":old_y,"side":u.side,"uid":u.uid})
			return
	if not enemy.is_empty() and u.edge==enemy.edge and def.has("leap_max_distance") and u.special_cd<=0 and distance>weapon_range and distance<float(def.leap_max_distance) and not statuses.has("root") and not statuses.has("silence"):
		var landing: float=leap_landing(u,float(physical_anchor(enemy).s)-float(u.facing)*weapon_range*.9)
		if (landing-float(u.s))*float(u.facing)>.05:
			var previous=u.x; var old_y=u.y
			map.apply_anchor(u,map.anchor(u.edge,landing))
			u.special_cd=float(def.leap_cooldown)
			event("dash",{"x":u.x,"from":previous,"from_y":old_y,"side":u.side,"uid":u.uid})
			distance=combat_distance(u,enemy,def)
	var engagement_range: float=ranged_engagement_range(u,enemy,def)
	if distance<=weapon_range and u.cooldown<=0:
		u.target=enemy.uid; u.windup=float(def.windup); u.anim="windup"; u.anim_t=0.0
	elif distance<=engagement_range:
		if u.anim_t>float(db.unit_actions[u.id].recovery):u.anim="idle"
	else:
		if statuses.has("root"): u.anim="idle"; return
		var speed=float(u.get("speed_override",def.speed))*(.45 if statuses.has("cold") else 1.0)*(1+float(statuses.get("haste",{}).get("potency",0)))*(1.35 if statuses.has("fury") else 1.0)
		var step: float = speed*dt
		if not enemy.is_empty() and u.edge==enemy.edge and (physical_point(enemy).x-u.x)*(1 if u.side==0 else -1)>0: step=minf(step,maxf(0,distance-engagement_range*.94))
		# A visible marching line: allies keep real road distance instead of piling
		# every body onto the same target point. Workers can pass their own army.
		var forward: float = 1.0 if u.side==0 else -1.0
		step=marching_step(u,def,enemy,step,forward)
		var before_step: Vector2=physical_point(u)
		for node_id in map.advance(u,step,u.side):
			if not u.crossed_nodes.has(node_id):
				u.crossed_nodes.append(node_id)
				Abilities.node_reached(self,u,def,node_id)
				event("node_reached",{"uid":u.uid,"side":u.side,"node":node_id,"x":u.x})
		mark_objective_crossing(u)
		u["charge_walk"]=float(u.get("charge_walk",0))+physical_point(u).distance_to(before_step)
		u.walk+=step; u.anim="walk" if step>0.00001 else "idle"

func update_ranged_formations():
	formation_ranges.clear()
	var groups: Dictionary={}
	for u in units:
		if u.hp<=0:continue
		var def: Dictionary=db.balance.units[u.id]
		if float(def.range)<=1.5 or not str(def.attack).begins_with("projectile"):continue
		var key: String=str(u.side)+"/"+str(u.edge)
		if not groups.has(key):groups[key]=[]
		groups[key].append(u)
	for members in groups.values():
		var direction: float=1 if int(members[0].side)==0 else -1
		members.sort_custom(func(a,b):return int(a.uid)<int(b.uid) if is_equal_approx(float(a.s),float(b.s)) else float(a.s)*direction>float(b.s)*direction)
		for i in range(members.size()):
			var def: Dictionary=db.balance.units[members[i].id]
			var desired: float=float(def.range)
			var packed_distance: float=0.0
			for j in range(i+1,mini(i+5,members.size())):
				if absf(float(members[i].s)-float(members[j].s))>6:break
				var rear_def: Dictionary=db.balance.units[members[j].id]
				packed_distance+=.72 if rear_def.get("role","")=="colossus" else .54
				# Shorter-range backliners can pass this shooter. Those which cannot
				# pass need a firing slot, even when they belong to another unit type.
				if float(rear_def.range)<float(def.range)-.05:continue
				desired=minf(desired,float(rear_def.range)-packed_distance)
			formation_ranges[members[i].uid]=maxf(minf(1.8,float(def.range)),desired)

func ranged_engagement_range(u: Dictionary,enemy: Dictionary,def: Dictionary) -> float:
	if enemy.is_empty() or float(def.range)<=1.5 or u.edge!=enemy.edge or (float(enemy.s)-float(u.s))*(1 if u.side==0 else -1)<=0:return float(def.range)
	var desired: float=float(formation_ranges.get(u.uid,def.range))
	if def.has("heal_amount"):desired=minf(desired,maxf(1.8,float(def.heal_radius)-.25))
	return desired

func leap_landing(u: Dictionary,desired: float) -> float:
	# A closing leap is not the separate crossing ability. Preserve the same
	# friendly melee screen spacing as walking; workers and backliners pass.
	var direction: float=float(u.facing)
	var travel: float=maxf(0,(desired-float(u.s))*direction)
	var def: Dictionary=db.balance.units[u.id]
	var gap: float=.72 if def.get("role","")=="colossus" else .54
	for ally in units:
		if ally.uid==u.uid or ally.hp<=0 or ally.side!=u.side or ally.edge!=u.edge:continue
		var other: Dictionary=db.balance.units[ally.id]
		if other.get("economy",false) or float(other.range)>1.5 or other.get("role","") in ["medic","engineer","necromancer","summoner","oracle","scribe"]:continue
		var ahead: float=(float(ally.s)-float(u.s))*direction
		if ahead>0:travel=minf(travel,maxf(0,ahead-gap))
	return float(u.s)+direction*travel

func mark_objective_crossing(u: Dictionary):
	if int(u.uid)!=intercept_uid or u.hp<=0:return
	var goal: Dictionary = config.get("objective_anchor",map.definition.objective_anchor)
	if map.objective_reached(u,goal,1):intercept_crossed=true

func tick_worker(u: Dictionary, dt: float):
	var def: Dictionary = db.balance.units[u.id]
	if u.statuses.has("bind") or u.statuses.has("stun"):u.anim="bound";return
	if u.mine=="": u.mine=choose_mine(u)
	var mine: Dictionary = {}
	for entry in map.definition.mines:
		if entry.id==u.mine: mine=entry; break
	if mine.is_empty(): u.anim="idle"; return
	var goal: Dictionary = mine if u.job=="mine" else bases[u.side]
	var old_x: float = float(u.x)
	var speed: float = float(def.speed)*(.45 if u.statuses.has("cold") else 1.0)
	if u.statuses.has("root") and map.route_to(u,goal).distance>.03:u.anim="idle";return
	if not map.move_to(u,goal,speed*dt):
		u.facing=1 if u.x>old_x else -1
		u.walk+=dt*speed; u.anim="walk"; u.job_time=0.0
		return
	if u.job=="mine":
		if int(mine.resource)==0: u.mine=""; u.job_time=0; return
		var miners: Array = []
		if float(u.get("mine_arrived_at",-1))<0:u["mine_arrived_at"]=time
		for worker in units:
			# An approaching worker has arrival=-1. Counting it as FIFO's oldest
			# would briefly steal a live service slot before it actually arrives.
			if worker.hp>0 and worker.mine==mine.id and worker.job=="mine" and worker.edge==mine.edge and float(worker.get("mine_arrived_at",-1))>=0 and absf(float(worker.s)-float(mine.s))<.025: miners.append(worker)
		miners.sort_custom(func(a,b):
			var arrival_a: float = float(a.get("mine_arrived_at",time));var arrival_b: float = float(b.get("mine_arrived_at",time))
			return int(a.uid)<int(b.uid) if is_equal_approx(arrival_a,arrival_b) else arrival_a<arrival_b)
		u["work_slot"]=miners.find(u);u["work_capacity"]=int(mine.capacity)
		if int(u.work_slot)>=int(mine.capacity): u.anim="queue"; return
	u.facing=1 if u.side==0 else -1
	u.anim="mine" if u.job=="mine" else "unload"
	var service: float=float(mine.mine_seconds) if u.job=="mine" else 1.0
	u["work_duration"]=service
	var previous: float=u.job_time
	u.job_time+=dt
	# A service slot strikes on a readable cycle, tied to real work rather than
	# a renderer clock. Queued miners emit no strike or gathering events.
	if u.job=="mine":
		var cycle: float=minf(.95,service)
		if int(floorf((previous/cycle-.57)+1))<int(floorf((float(u.job_time)/cycle-.57)+1)):
			var foot: Vector2=physical_point(u)
			event("mine_strike",{"uid":u.uid,"side":u.side,"x":foot.x,"y":foot.y,"mine":u.mine,"facing":u.facing})
	if u.job_time >= (float(mine.mine_seconds) if u.job=="mine" else 1.0):
		u.job_time=0.0
		if u.job=="mine":
			u.cargo=int(def.get("cargo",8))+int(mine.get("cargo_bonus",0))+Abilities.cargo_bonus(self,u)
			if int(mine.resource)>=0: u.cargo=mini(u.cargo,int(mine.resource)); mine.resource-=u.cargo
			u.job="deliver"
			u.anim="load";u.anim_t=0.0
			u["visual_load"]=.25
			var foot: Vector2=physical_point(u)
			event("cargo_loaded",{"uid":u.uid,"side":u.side,"x":foot.x,"y":foot.y,"amount":u.cargo})
			u["mine_arrived_at"]=-1.0
		else:
			players[u.side].gold+=u.cargo; stats[u.side].gold_delivered+=u.cargo
			if db.factions[players[u.side].faction].mana=="delivery": gain_mana(u.side,float(u.cargo)*.15,"delivery")
			event("gold",{"x":u.x,"uid":u.uid,"side":u.side,"amount":u.cargo,"mine":u.mine})
			u.cargo=0; u.job="mine"; u.mine=""

func choose_mine(worker: Dictionary) -> String:
	var best: String = ""; var best_score: float = -INF
	for mine in map.definition.mines:
		if int(mine.owner)!=int(worker.side) or int(mine.resource)==0: continue
		var path: Dictionary = map.route_to(worker,mine)
		if path.is_empty(): continue
		var estimate: Dictionary = mine_income(worker.side,mine,worker.uid)
		var score: float = float(estimate.marginal_rate)
		# Player preference affects the next trip, while an actually saturated
		# mine cannot earn a new slot merely because it is preferred.
		if players[worker.side].get("preferred_mine","")==mine.id and score>0:score+=1000.0
		score-=float(path.distance)*.0001
		if score>best_score:best_score=score;best=mine.id
	return best

func mine_state(mine: Dictionary,ignore_uid: int = 0) -> Dictionary:
	var assigned: int = 0;var active: int = 0;var waiting: int = 0
	for worker in units:
		if worker.hp<=0 or worker.uid==ignore_uid or worker.mine!=mine.id:continue
		assigned+=1
		if worker.job=="mine" and worker.anim=="mine":active+=1
		if worker.job=="mine" and worker.anim=="queue":waiting+=1
	return {"assigned":assigned,"active":active,"waiting":waiting,"capacity":int(mine.capacity)}

func mine_income(side: int,mine: Dictionary,ignore_uid: int = 0) -> Dictionary:
	var state: Dictionary = mine_state(mine,ignore_uid)
	var worker: Dictionary = db.balance.units["unit."+players[side].faction+".worker"]
	var route: Dictionary = map.route_to(bases[side],mine)
	if route.is_empty():return {"marginal_rate":0.0,"cycle":INF,"total_rate":0.0}
	var cargo: float = float(worker.get("cargo",8))+float(mine.get("cargo_bonus",0))
	var mining_time: float = maxf(.01,float(mine.mine_seconds))
	var cycle: float = float(route.distance)*2.0/float(worker.speed)+mining_time+1.0
	var service_rate: float = float(mine.capacity)*cargo/mining_time
	var old_rate: float = minf(float(state.assigned)*cargo/cycle,service_rate)
	var new_rate: float = minf(float(state.assigned+1)*cargo/cycle,service_rate)
	return {"cycle":cycle,"total_rate":old_rate,"marginal_rate":maxf(0,new_rate-old_rate),"service_rate":service_rate}

func mana_rate_sources(side: int) -> Dictionary:
	var sources: Dictionary={"passive":.5,"upgrade":0.0,"facility":0.0}
	for id in players[side].unlocked:
		if db.balance.upgrades.has(id):sources.upgrade+=float(db.balance.upgrades[id].mana_per_second_add)
	for b in buildings:
		if b.side==side and b.hp>0 and b.state=="active" and b.disabled<=0:sources.facility+=float(db.balance.buildings[b.id].get("mana_per_second",0))
	return sources

func record_mana_income(side: int,source: String,amount: float):
	if amount>0:stats[side].mana_income[source]=float(stats[side].mana_income.get(source,0))+amount

func gain_mana(side: int, amount: float, source: String="ability") -> float:
	if not is_finite(amount):return 0.0
	var received: float=minf(100-float(players[side].mana),maxf(0,amount))
	players[side].mana=minf(100,float(players[side].mana)+maxf(0,amount))
	record_mana_income(side,source,received)
	return received

func setup_objective():
	var win: String = str(config.get("win","destroy_base"))
	if win=="protect":
		var tower_slots: Array=[]
		for i in range(side_sites(0).size()):
			if slot_anchor(0,i).get("types",["tower","mana"]).has("tower"):tower_slots.append(i)
		var slot: int=int(tower_slots[mini(int(config.get("protect_slot",1)),tower_slots.size()-1)])
		var id: String = "building."+players[0].faction+".tower"
		var original_gold: float = players[0].gold
		players[0].gold+=float(db.balance.buildings[id].gold)
		if build(0,id,slot,true)=="":
			var b: Dictionary = buildings[-1]
			b.state="active"; b.construction=0; b["prebuilt"]=true
			protected_uid=int(b.uid)
			stats[0].buildings-=1; stats[0].build_counts[id]-=1
		players[0].gold=original_gold
	elif win=="escort":
		var id: String = str(config.get("escort_id",db.factions[players[0].faction].default_roster[0]))
		var u = spawn(id,0,float(config.get("escort_start_x",float(bases[0].x)+1)))
		u.hp=float(config.get("escort_hp",650));u.max_hp=u.hp
		u["speed_override"]=float(config.get("escort_speed",.55));u["objective_unit"]=true;u["display_name"]="携证者"
		escort_uid=int(u.uid)
	elif win=="intercept":
		var id: String = str(config.get("intercept_id","unit.mo.giant"))
		var u = spawn(id,1,float(config.get("intercept_start_x",float(bases[1].x)-1)))
		u.hp=float(config.get("intercept_hp",420));u.max_hp=u.hp
		u["speed_override"]=float(config.get("intercept_speed",.5));u["objective_unit"]=true;u["display_name"]="覆写巨兵"
		intercept_uid=int(u.uid)

func evaluate_objective():
	var win: String = str(config.get("win","destroy_base"))
	if bases[0].hp<=0:
		winner=-1 if bases[1].hp<=0 else 1; result_reason="双方纸城同毁" if winner==-1 else "我方纸城失守";return
	if win=="challenge":ChallengeRules.evaluate(self);return
	if win=="protect" and actor(protected_uid).is_empty(): winner=1;result_reason="需要保护的前哨被摧毁";return
	if win=="escort":
		var u: Dictionary = actor(escort_uid)
		if u.is_empty():winner=1;result_reason="携证者阵亡";return
		var goal: Dictionary = config.get("objective_anchor",map.definition.objective_anchor)
		var goal_edge: Dictionary=map.edges[goal.edge]
		var reached: bool=map.objective_reached(u,goal,0)
		# A node on the seam belongs to both adjacent road segments. Movement can
		# enter the next edge during this tick; retain the actual node crossing.
		if is_equal_approx(float(goal.s),float(goal_edge.length)) and u.crossed_nodes.has(goal_edge.to):reached=true
		if reached:winner=0;result_reason="携证者抵达交接点";return
	elif win=="intercept":
		var u: Dictionary = actor(intercept_uid)
		if intercept_crossed:winner=1;result_reason="覆写巨兵突破矿线";return
		if u.is_empty():winner=0;result_reason="覆写巨兵已在矿线前被截住";return
		var goal: Dictionary = config.get("objective_anchor",map.definition.objective_anchor)
		if map.objective_reached(u,goal,1):winner=1;result_reason="覆写巨兵突破矿线";return
	elif win=="deliver_gold" and int(stats[0].gold_delivered)>=int(config.get("goal_gold",200)):
		winner=0;result_reason="真实归仓目标完成";return
	elif win in ["survive","protect"] and time>=float(config.get("duration",150)):
		winner=0;result_reason="指定对象守住目标时间";return
	if bases[1].hp<=0 and win=="destroy_base":winner=0;result_reason="敌方纸城被攻破"

func objective_text() -> String:
	if config.get("win","")=="challenge":return ChallengeRules.text(self)
	match str(config.get("win","destroy_base")):
		"escort":
			var u: Dictionary = actor(escort_uid)
			var distance: float=map.selected_route_distance(u,config.get("objective_anchor",map.definition.objective_anchor),0)
			var distance_text: String="需改道" if not is_finite(distance) else "%.1f 步"%maxf(0.0,distance)
			return "携证者 %d 生命 · 距交接 %s"%[int(u.get("hp",0)),distance_text]
		"intercept":
			var u: Dictionary = actor(intercept_uid)
			var distance: float=map.selected_route_distance(u,config.get("objective_anchor",map.definition.objective_anchor),1)
			var distance_text: String="需改道" if not is_finite(distance) else "%.1f 步"%maxf(0.0,distance)
			return "指定巨兵 %d 生命 · 距矿线 %s"%[int(u.get("hp",0)),distance_text]
		"protect": return "保护前哨 %d / %d 秒"%[int(time),int(config.get("duration",150))]
		"deliver_gold": return "真实归仓 %d / %d 金"%[int(stats[0].gold_delivered),int(config.get("goal_gold",200))]
		"survive": return "守城 %d / %d 秒"%[int(time),int(config.get("duration",150))]
	return "保护经济与增援，攻破敌方纸城"

func attack(u: Dictionary, target: Dictionary):
	if u.is_empty() or u.hp<=0 or not hostile_target(target,int(u.side)):return
	if collecting_attacks:
		attack_intents.append({"source":u,"target":target,"side":int(u.side)})
		return
	prepare_attack(u,target)

func release_attack_intents():
	var valid: Array=[]
	for intent in attack_intents:
		var source: Dictionary=intent.source
		var target: Dictionary=intent.target
		if source.hp<=0 or int(source.side)!=int(intent.side) or not hostile_target(target,int(intent.side),int(source.uid)):continue
		if source.statuses.has("bind") or source.statuses.has("stun"):continue
		var def: Dictionary=db.balance.units[source.id]
		if combat_distance(source,target,def)>float(def.range)+.3:continue
		valid.append(intent)
	# Dispels take effect for the whole release phase before damage is sampled.
	for intent in valid:Abilities.before_attack(self,intent.source,intent.target,db.balance.units[intent.source.id])
	for intent in valid:
		prepare_attack(intent.source,intent.target,true)
		if intent.source.get("reload_pending",false):intent.source.cooldown+=float(db.balance.units[intent.source.id].get("reload_seconds",0))
	attack_intents.clear()

func prepare_attack(u: Dictionary,target: Dictionary,before_done: bool=false):
	visibility.reveal_attack(u,target)
	u["attack_serial"]=int(u.get("attack_serial",0))+1
	var hit_point: Vector2=physical_point(target)
	var def=db.balance.units[u.id]
	if not before_done:Abilities.before_attack(self,u,target,def)
	var amount=Abilities.attack_amount(self,u,target,def)* (1.4 if u.statuses.has("fury") else 1.0)
	var context: Dictionary={"silenced":u.statuses.has("silence"),"attack_serial":int(u.attack_serial)}
	if str(def.attack).begins_with("projectile"):
		var count=int(def.get("burst_count",1))
		for i in range(count): launch(u,target,amount,float(def.get("radius",0)),float(def.get("building_multiplier",1)),float(def.get("poison_damage_per_second",0)),float(i)*.11)
	else:
		if float(def.get("radius",0))>0:
			for victim in units+buildings+bases:
				if victim.side!=u.side and victim.hp>0 and melee_distance(target,victim)<=float(def.radius):
					attack_hit(u,victim,def,amount,not def.get("magic_damage",false),context)
		else:
			attack_hit(u,target,def,amount*float(def.get("building_multiplier",1)) if target.get("building",false) else amount,not def.get("magic_damage",false),context)
	Abilities.after_attack(u,def)
	event("attack",{"uid":u.uid,"target_uid":target.uid,"x":u.x,"target_x":hit_point.x,"target_y":hit_point.y,"side":u.side,"target_side":target.side,"facing":u.facing,"id":u.id,"weapon_role":def.get("role",""),"weapon_gesture":db.unit_actions[u.id].gesture,"heavy":float(def.damage)>=34,"ranged":str(def.attack).begins_with("projectile")})

func attack_hit(source: Dictionary,target: Dictionary,def: Dictionary,amount: float,physical: bool,context: Dictionary,poison: Dictionary={}):
	if collecting_combat_hits:
		combat_hits.append({"ordinal":combat_hits.size(),"source":source,"target":target,"def":def,"amount":amount,"physical":physical,"context":context.duplicate(),"poison":poison})
		return
	var actual: float=damage(target,amount,int(source.side),physical,int(source.uid))
	if not context.get("suppress_on_hit",false):Abilities.on_hit(self,source,target,def,actual,context)
	if actual>0 and not poison.is_empty():Abilities.poison_hit(self,target,poison)

func resolve_combat_hits():
	if combat_hits.is_empty():return
	var groups: Dictionary={}
	# Stable hit ordering only selects which spell a one-shot ward absorbs.
	# Health loss is aggregated, so a lethal hit never cancels another release.
	combat_hits.sort_custom(func(a,b):return int(a.source.uid)<int(b.source.uid) if a.source.uid!=b.source.uid else int(a.target.uid)<int(b.target.uid))
	for hit in combat_hits:
		var source: Dictionary=hit.source
		var target: Dictionary=hit.target
		if not hostile_target(target,int(source.side),int(source.uid)) or not is_finite(float(hit.amount)) or float(hit.amount)<=0:continue
		var mitigated: float=damage_after_defense(target,float(hit.amount),int(source.side),bool(hit.physical))
		if mitigated<=0:continue
		hit["mitigated"]=mitigated
		if not groups.has(target.uid):groups[target.uid]={"target":target,"hits":[],"total":0.0,"credit":hit}
		var group: Dictionary=groups[target.uid]
		group.hits.append(hit);group.total+=mitigated
		if mitigated>float(group.credit.mitigated):group.credit=hit
	resolving_combat_hits=true
	# Commit every target's health before any hit, healing or death callback.
	for group in groups.values():
		var target: Dictionary=group.target
		group["actual"]=minf(float(target.hp),float(group.total))
		target.hp=maxf(0.0,float(target.hp)-float(group.actual))
	for group in groups.values():process_damage_death(group.target,int(group.credit.source.side))
	for group in groups.values():
		for hit in group.hits:
			hit["actual"]=float(group.actual)*float(hit.mitigated)/float(group.total)
			hit.context["kill_credit"]=group.target.hp<=0 and int(hit.ordinal)==int(group.credit.ordinal)
			record_damage_hit(group.target,float(hit.actual),int(hit.source.side),bool(hit.physical),int(hit.source.uid))
	for group in groups.values():
		if not group.target.get("building",false):
			for hit in group.hits:Abilities.on_damaged(self,group.target,db.balance.units[group.target.id],int(hit.source.uid),bool(hit.physical))
	for group in groups.values():
		for hit in group.hits:
			if not hit.context.get("suppress_on_hit",false):Abilities.on_hit(self,hit.source,group.target,hit.def,float(hit.actual),hit.context)
			if not hit.poison.is_empty():Abilities.poison_hit(self,group.target,hit.poison)
	combat_hits.clear()
	# Death bursts may enqueue additional deaths; each actor is processed once.
	var cursor: int=0
	while cursor<combat_deaths.size():
		finish_damage_death(combat_deaths[cursor]);cursor+=1
	combat_deaths.clear();resolving_combat_hits=false

func launch(u: Dictionary, target: Dictionary, amount: float, radius: float, multiplier: float, poison: float, extra: float = 0.0):
	if u.is_empty() or u.hp<=0 or not hostile_target(target,int(u.side)):return
	if u.get("building",false):visibility.reveal_attack(u,target)
	var origin: Vector2=physical_point(u);var goal: Vector2=physical_point(target)
	var duration=maxf(.13,goal.distance_to(origin)/11.0)+extra
	var def: Dictionary = db.balance.buildings[u.id] if u.get("building",false) else db.balance.units[u.id]
	projectiles.append({"uid":next_uid,"side":u.side,"source":u.uid,"source_id":u.id,"source_facing":u.get("facing",1 if u.side==0 else -1),"target":target.uid,"start_x":origin.x,"start_y":origin.y,"end_x":goal.x,"end_y":goal.y,"x":origin.x,"y":origin.y,"left":duration,"total":duration,"delay":extra,"damage":amount,"radius":radius,"building_multiplier":multiplier,"poison":poison,"reflected":false,"reflectable":def.get("reflectable",true),"ability":def,"style":UnitProjectile.projectile(def,u.id)})
	projectiles[-1]["release_context"]={"silenced":u.get("statuses",{}).has("silence"),"attack_serial":int(u.get("attack_serial",0))}
	projectiles[-1]["source_anchor"]={"edge":u.edge,"s":u.s,"x":origin.x,"y":origin.y}
	next_uid+=1

func projectile_source(p: Dictionary) -> Dictionary:
	var source: Dictionary=actor(int(p.source))
	if not source.is_empty():return source
	# Released shots retain abilities and rewards after their shooter dies.
	var anchor: Dictionary=p.get("source_anchor",map.project(Vector2(float(p.start_x),float(p.start_y))))
	source={"uid":int(p.source),"id":str(p.get("source_id","")),"side":int(p.side),"hp":0.0,"max_hp":0.0,"statuses":{},"control_clock":0.0,"building":db.balance.buildings.has(str(p.get("source_id","")))}
	source.merge(anchor,true)
	return source

func projectile_hit(p: Dictionary):
	var owner: Dictionary=actor(int(p.source))
	if not owner.is_empty() and int(owner.side)!=int(p.side):return
	var target=actor(int(p.target))
	if target.is_empty():
		if float(p.radius)>0:
			var source: Dictionary=projectile_source(p)
			var context: Dictionary=p.get("release_context",{}).duplicate()
			context["suppress_on_hit"]=bool(p.reflected)
			var end: Vector2=Vector2(float(p.end_x),float(p.end_y))
			for victim in units+buildings+bases:
				if hostile_target(victim,int(p.side),int(p.source)) and physical_point(victim).distance_to(end)<=float(p.radius):
					var amount: float=float(p.damage)*(float(p.building_multiplier) if victim.get("building",false) else 1.0)
					attack_hit(source,victim,p.ability,amount,not p.ability.get("magic_damage",false),context,p)
			event("impact",{"x":p.end_x,"y":p.end_y,"side":p.side,"fx":"blast","radius":p.radius})
		return
	if not hostile_target(target,int(p.side),int(p.source)): return
	if not target.get("building",false):
		var def=db.balance.units[target.id]
		if def.has("reflection_cooldown") and target.special_cd<=0 and not p.reflected and p.reflectable and not target.statuses.has("silence"):
			var source=actor(int(p.source))
			if hostile_target(source,int(target.side)):
				var origin: Vector2=physical_point(target);var destination: Vector2=physical_point(source)
				var total=maxf(.13,destination.distance_to(origin)/11.0)
				p.reflected=true; p.side=target.side; p.target=source.uid; p.source=target.uid
				p.erase("render_dx");p.erase("render_dy");p["delay"]=0.0;p["source_id"]=target.id
				p.start_x=origin.x; p.start_y=origin.y; p.end_x=destination.x; p.end_y=destination.y; p.x=origin.x; p.y=origin.y; p.total=total; p.left=total
				projectiles.append(p); target.special_cd=float(def.reflection_cooldown)
				stats[target.side].reflections+=1
				event("reflect",{"x":target.x,"side":target.side}); return
	var goal: Vector2=physical_point(target)
	var source: Dictionary=projectile_source(p)
	var context: Dictionary=p.get("release_context",{}).duplicate()
	context["suppress_on_hit"]=bool(p.reflected)
	var victims: Array=[target]
	if p.radius>0:
		victims=(units+buildings+bases).filter(func(v):return hostile_target(v,int(p.side),int(p.source)) and physical_point(v).distance_to(goal)<=float(p.radius))
		event("impact",{"x":goal.x,"y":goal.y,"side":p.side,"fx":"blast","radius":p.radius})
	for victim in victims:
		var hit_amount: float=float(p.damage)*(float(p.building_multiplier) if victim.get("building",false) else 1.0)
		attack_hit(source,victim,p.ability,hit_amount,not p.ability.get("magic_damage",false),context,p)

func front(side: int=0) -> float:
	# Navigation consumes this observer's live information; it never scouts.
	var direction: float=1 if side==0 else -1
	var lead: Dictionary={}
	var progress: float=-INF
	for u in units:
		if int(u.side)!=side or u.hp<=0 or db.balance.units[u.id].get("economy",false):continue
		var candidate: float=physical_point(u).x*direction
		if candidate>progress or (is_equal_approx(candidate,progress) and int(u.uid)<int(lead.get("uid",u.uid+1))):
			lead=u;progress=candidate
	if lead.is_empty():return clampf(float(bases[side].x)+direction*5,0,map.length)
	var contact: Dictionary={}
	var nearest: float=visibility.radius(lead)
	for opponent in units+buildings+bases:
		if int(opponent.side)==side or opponent.hp<=0 or not visible_to(side,opponent):continue
		if not opponent.get("building",false) and db.balance.units[opponent.id].get("economy",false):continue
		var path: Dictionary=map.route_to(physical_anchor(lead),physical_anchor(opponent))
		if path.is_empty():continue
		var distance: float=float(path.distance)
		if distance<nearest or (is_equal_approx(distance,nearest) and int(opponent.uid)<int(contact.get("uid",opponent.uid+1))):
			contact=opponent;nearest=distance
	return physical_point(lead).x if contact.is_empty() else (physical_point(lead).x+physical_point(contact).x)*.5

func ai_turn(side: int):
	TacticalAI.turn(self,side)

func visible_to(side: int,a: Dictionary) -> bool:
	return visibility!=null and visibility.actor_visible(side,a)

func location_visible(side: int,x: float,y: float) -> bool:
	return visibility.point_visible(side,map.project(Vector2(x,y)))

func event_visible(side: int,e: Dictionary) -> bool:
	var owned: bool=int(e.get("side",-1))==side
	if e.get("kind","")=="economy_alarm":return owned and int(e.get("observer",-1))==side
	if e.get("kind","")=="death" and owned:return true
	if e.has("x"):return location_visible(side,float(e.x),float(e.get("y",map.ground_y_at(float(e.x)))))
	return owned or e.get("kind","") in ["start","result"]
