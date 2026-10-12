extends SceneTree
# Ownership can change between selection, wind-up, flight and status pulses.
const Data=preload("res://scripts/data_store.gd")
const Simulation=preload("res://scripts/battle_sim.gd")
var db
var checks: int = 0
var failures: Array = []
var evidence: Dictionary = {}

func _initialize():call_deferred("run")
func check(ok: bool,note: String):
	checks+=1
	if not ok:failures.append(note)
func make(f: String="yin",enemy: String="mo"):
	var s=Simulation.new(db)
	s.start({"map":"map.01.01","faction":f,"enemy":enemy,"full_tech":true,"starting_gold":500,"enemy_starting_gold":500})
	s.ai_enabled=[false,false];s.events.clear();return s
func advance(s,seconds: float):
	for i in range(int(ceilf(seconds*60))):s.tick(1.0/60.0)
func run():
	db=Data.new()
	# Actual paid recruitment, transport and overlapping road positions.
	var s=make()
	for i in range(4):check(s.request(0,"recruit",{"id":"unit.yin.worker"}).ok,"paid worker order %d"%i)
	advance(s,9)
	for i in range(3):check(s.request(0,"recruit",{"id":"unit.yin.spear"}).ok,"paid spear order %d"%i)
	var own_hits: Array=[];var overlaps: int=0
	for i in range(60*30):
		s.tick(1.0/60.0)
		for a in s.units:
			if a.side!=0 or not a.id.ends_with(".spear"):continue
			for w in s.units:
				if w.side==0 and w.id.ends_with(".worker") and s.melee_distance(a,w)<.5:overlaps+=1
		for e in s.drain_events():
			if e.kind=="hit" and e.side==e.attacker_side:own_hits.append(e)
	check(overlaps>0,"paid spears really pass and overlap friendly workers")
	check(own_hits.is_empty(),"overlap produces no friendly damage events")
	for w in s.units:
		if w.side==0 and w.id.ends_with(".worker"):check(is_equal_approx(w.hp,w.max_hp),"unthreatened passing worker retains HP %d"%w.uid)
	evidence["paid_passage"]={"overlap_ticks":overlaps,"friendly_hits":own_hits,"gold_delivered":s.stats[0].gold_delivered}
	# Every native weapon must reject a stale same-team target at its boundary.
	for f in db.FACTIONS:
		for id in db.all_unit_ids(f):
			s=make(f)
			var a=s.spawn(id,0,20);var w=s.spawn("unit."+f+".worker",0,20.3)
			var hp: float=w.hp;s.events.clear();s.attack(a,w)
			for p in s.projectiles.duplicate():s.projectile_hit(p)
			check(is_equal_approx(w.hp,hp) and w.statuses.is_empty() and s.projectiles.is_empty() and not s.events.any(func(e):return e.kind in ["attack","hit","chain"]),"friendly target rejected by "+id)
			var opponent=s.spawn("unit.mo.worker",1,20.7)
			s.attack(a,opponent)
			for p in s.projectiles.duplicate():s.projectile_hit(p)
			check(opponent.hp<opponent.max_hp,"enemy worker remains vulnerable to "+id)
	# A public conversion during an already-started melee wind-up.
	s=make("mo","yin")
	var a=s.spawn("unit.mo.blade",0,20);var target=s.spawn("unit.yin.axe",1,20.3)
	a.target=target.uid;a.windup=.18;a.anim="windup";target.cooldown=100
	s.players[0].mana=100
	check(s.request(0,"cast",{"id":"spell.mo.convert","target":target.uid,"x":target.x}).ok,"public conversion during wind-up")
	var hp: float=target.hp;advance(s,.3)
	check(is_equal_approx(target.hp,hp),"melee rechecks allegiance after conversion")
	# In-flight projectile has to recheck current target allegiance.
	s=make("mo","yin");a=s.spawn("unit.mo.blade",0,20);target=s.spawn("unit.yin.axe",1,23)
	s.launch(a,target,25,0,1,4);s.players[0].mana=100
	s.request(0,"cast",{"id":"spell.mo.convert","target":target.uid,"x":target.x})
	hp=target.hp;advance(s,.5)
	check(is_equal_approx(target.hp,hp) and not target.statuses.has("poison"),"flight conversion prevents damage and poison")
	# A converted victim cannot keep taking its new team's damage-over-time.
	s=make("mo","yin");target=s.spawn("unit.yin.axe",1,20)
	# Ownership fixture must explicitly reveal its target under formal fog rules.
	s.spawn("unit.mo.blade",0,19)
	s.set_status(target,"poison",3,12,0);s.players[0].mana=100
	s.request(0,"cast",{"id":"spell.mo.convert","target":target.uid,"x":target.x})
	hp=target.hp;advance(s,.6)
	check(is_equal_approx(target.hp,hp) and not target.statuses.has("poison"),"conversion clears new-friendly damage-over-time")
	# A spear changes teams while its old hostile shot is aimed at a gold worker.
	s=make("mo","yin");a=s.spawn("unit.yin.spear",1,22);target=s.units[0]
	# Ownership fixture must explicitly reveal its target under formal fog rules.
	s.spawn("unit.mo.blade",0,19)
	s.launch(a,target,18,0,1,4);s.players[0].mana=100
	s.request(0,"cast",{"id":"spell.mo.convert","target":a.uid,"x":a.x})
	hp=target.hp;advance(s,.6)
	check(target.hp==hp and s.projectiles.is_empty(),"converted spear cannot hit its new friendly gold worker")
	s=make("mo","jin");a=s.spawn("unit.jin.burner",1,22);target=s.units[0]
	# Ownership fixture must explicitly reveal its target under formal fog rules.
	s.spawn("unit.mo.blade",0,19)
	s.set_status(target,"burn",3,12,1,int(a.uid));s.players[0].mana=100
	s.request(0,"cast",{"id":"spell.mo.convert","target":a.uid,"x":a.x})
	hp=target.hp;advance(s,.6)
	check(target.hp==hp and not target.statuses.has("burn"),"converted weapon caster clears damage on new friendly worker")
	# Friendly bodies on a projectile's path never intercept that shot.
	s=make();a=s.spawn("unit.yin.spear",0,20);worker_passage(s,a)
	# Explosion damages enemies while allies, buildings and cargo are untouched.
	s=make();var worker=s.spawn("unit.yin.worker",0,20);target=s.spawn("unit.mo.giant",1,20)
	worker.cargo=8;s.area_damage(20,2,40,0,false,target.y)
	check(is_equal_approx(worker.hp,worker.max_hp) and worker.cargo==8 and target.hp<target.max_hp,"area impact preserves friendly worker and cargo")
	s.damage(s.bases[0],40,0);check(is_equal_approx(s.bases[0].hp,s.bases[0].max_hp),"friendly building damage rejected")
	# A queued body's physical station is shared by range, blast and hit feedback.
	# This is an isolated geometry fixture; the paid passage test above uses real travel.
	s=make();target=s.spawn("unit.mo.worker",1,23);a=s.spawn("unit.yin.axe",0,21.7)
	target.body_anchor=s.map.anchor(target.edge,float(target.s)-1.5)
	var body: Vector2=s.physical_point(target)
	check(s.combat_distance(a,target,db.balance.units[a.id])<.3,"melee range follows visible worker body instead of service anchor")
	s.area_damage(float(target.x),.35,10,0,false,float(target.y))
	check(target.hp==target.max_hp,"explosion at empty service anchor misses displaced worker body")
	s.area_damage(body.x,.35,10,0,false,body.y)
	var hits: Array=s.events.filter(func(e):return e.kind=="hit" and int(e.uid)==int(target.uid))
	check(target.hp<target.max_hp and hits.size()==1 and Vector2(hits[0].x,hits[0].y).distance_to(body)<.001,"body-centered explosion and feedback use same physical point")
	s.launch(a,target,18,0,1,0)
	var shot: Dictionary=s.projectiles.back()
	check(Vector2(shot.end_x,shot.end_y).distance_to(body)<.001,"projectile endpoint follows worker body station")
	s=make("shuang","mo");a=s.spawn("unit.shuang.oracle",0,20);target=s.spawn("unit.mo.worker",1,23)
	var chained: Dictionary=s.spawn("unit.mo.worker",1,23.6)
	target.body_anchor=s.map.anchor(target.edge,float(target.s)-1.5)
	chained.body_anchor=s.map.anchor(chained.edge,float(chained.s)-1.5)
	var from: Vector2=s.physical_point(target);var to: Vector2=s.physical_point(chained)
	s.attack(a,target)
	for projectile in s.projectiles.duplicate():s.projectile_hit(projectile)
	var links: Array=s.events.filter(func(e):return e.kind=="chain" and e.uid==chained.uid)
	check(chained.hp<chained.max_hp and links.size()==1 and Vector2(links[0].x,links[0].y).distance_to(to)<.001 and Vector2(links[0].from,links[0].from_y).distance_to(from)<.001,"chain damage and feedback follow physical worker bodies")
	# Explosive shells still land if another attack kills the primary target in flight.
	s=make();a=s.spawn("unit.yin.spear",0,20);target=s.spawn("unit.mo.blade",1,23)
	var neighbor: Dictionary=s.spawn("unit.mo.giant",1,23.4);neighbor.speed_override=0;neighbor.cooldown=100
	var ally: Dictionary=s.spawn("unit.yin.axe",0,23.2);ally.speed_override=0;ally.cooldown=100;a.cooldown=100
	s.launch(a,target,22,1.2,1,0);s.die(target,true);advance(s,.4)
	check(neighbor.hp<neighbor.max_hp and s.projectiles.is_empty(),"shell explodes at last known point after primary target dies")
	check(ally.hp==ally.max_hp,"late shell splash still rejects friendly unit")
	# Reflection still hits the original enemy exactly once.
	s=make("deng","yin");a=s.spawn("unit.yin.spear",1,23);target=s.spawn("unit.deng.mirror",0,20)
	a.cooldown=100;target.cooldown=100;target.special_cd=0
	s.launch(a,target,14,0,1,0);advance(s,.65)
	check(s.stats[0].reflections==1 and a.hp<a.max_hp and is_equal_approx(target.hp,target.max_hp),"enemy reflection remains functional")
	# Mirror ownership can change before the hostile incoming shot lands.
	s=make("mo","deng");a=s.spawn("unit.mo.blade",0,20);target=s.spawn("unit.deng.mirror",1,23)
	target.special_cd=0;s.launch(a,target,20,0,1,0);s.players[0].mana=100
	s.request(0,"cast",{"id":"spell.mo.convert","target":target.uid,"x":target.x});advance(s,.5)
	check(s.stats[0].reflections==0 and a.hp==a.max_hp and target.hp==target.max_hp,"converted reflector does not bounce a friendly shot")
	# Invalid/negative damage cannot turn into healing or poison side effects.
	s=make();target=s.units[0];hp=target.hp
	s.damage(target,-20,1);s.damage(target,NAN,1);s.damage(target,20,0)
	s.set_status(target,"stun",2,0,0);s.set_status(target,"poison",2,20,0)
	check(target.hp==hp and target.statuses.is_empty(),"invalid damage and friendly hostile statuses rejected")
	var args=OS.get_cmdline_user_args();var out="user://combat-ownership.json"
	if args.has("--output"):out=args[args.find("--output")+1]
	var report={"checks":checks,"failed":failures.size(),"failures":failures,"evidence":evidence,"engine":Engine.get_version_info().string,"simulation_sha256":FileAccess.get_sha256("res://scripts/battle_sim.gd"),"test_sha256":FileAccess.get_sha256("res://tests/test_combat_ownership.gd")}
	DirAccess.make_dir_recursive_absolute(out.get_base_dir());var file=FileAccess.open(out,FileAccess.WRITE);file.store_string(JSON.stringify(report,"  "));file.close()
	print("OWNERSHIP ",checks," checks / ",failures.size()," failures -> ",out)
	quit(0 if failures.is_empty() else 1)

func worker_passage(s,a):
	var friendly=s.spawn("unit.yin.worker",0,21.5)
	var opponent=s.spawn("unit.mo.worker",1,23)
	s.launch(a,opponent,18,0,1,0);advance(s,.6)
	check(friendly.hp==friendly.max_hp and opponent.hp<opponent.max_hp,"projectile passes friendly worker and hits opposing worker")
