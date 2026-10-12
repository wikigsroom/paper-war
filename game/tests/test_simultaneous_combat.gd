extends SceneTree
const Data=preload("res://scripts/data_store.gd")
const Simulation=preload("res://scripts/battle_sim.gd")
const DT: float=1.0/60.0
var db
var checks: int=0
var failures: Array=[]
var observations: Array=[]
func _initialize():call_deferred("run")
func verify(value: bool,label: String):
	checks+=1
	if not value:failures.append(label)
func make(west: String="qi",east: String="qi"):
	var s=Simulation.new(db)
	s.start({"map":"map.01.04","faction":west,"enemy":east,"full_tech":true})
	s.ai_enabled=[false,false];s.units.clear();s.buildings.clear();s.drain_events()
	return s
func body(s,id: String,side: int,offset: float=0.0) -> Dictionary:
	var u=s.spawn(id,side,22)
	var anchor=s.map.project(Vector2(22,s.map.ground_y_at(22)))
	s.map.apply_anchor(u,s.map.anchor(anchor.edge,float(anchor.s)+offset))
	u.cooldown=1000;u.special_cd=1000;u.summon_cd=1000;u.ability_clock=1000;u.speed_override=0.0
	return u
func ready(u: Dictionary,target: Dictionary,left: float=.001):
	u.target=target.uid;u.windup=left
func advance(s,steps: int=1,first: int=0):
	for i in range(steps):
		s.units.sort_custom(func(u,v):return int(u.side)==first if u.side!=v.side else int(u.uid)<int(v.uid))
		s.visibility.refresh();s.tick(DT)
func events_of(events: Array,kind: String) -> Array:
	return events.filter(func(e):return e.kind==kind)
func pair_death(first: int,id: String,faction: String):
	var s=make(faction,faction)
	var a=body(s,id,0);var b=body(s,id,1,.4)
	a.hp=1;b.hp=1;ready(a,b);ready(b,a)
	var gold: Array=[s.players[0].gold,s.players[1].gold]
	advance(s,1,first)
	var events=s.drain_events()
	verify(a.hp==0 and b.hp==0,"both released lethal melee hits land: "+id+" first="+str(first))
	verify(events_of(events,"attack").size()==2,"both attack releases emitted")
	verify(events_of(events,"hit").size()==2,"both lethal hits recorded")
	verify(events_of(events,"death").size()==2 and s.corpses.size()==2,"two deaths and two corpses exactly once")
	verify(s.stats[0].killed==1 and s.stats[1].killed==1 and s.stats[0].lost==1 and s.stats[1].lost==1,"mutual kills/losses counted once")
	if faction=="qi":verify(s.players[0].gold==gold[0]+3 and s.players[1].gold==gold[1]+3,"each released lethal attack earns its own bounty")
	advance(s,1,first)
	verify(a.hp==0 and b.hp==0 and s.units.is_empty(),"lifesteal cannot revive a lethal attacker")
	verify(events_of(s.drain_events(),"death").is_empty() and s.corpses.size()==2,"no duplicate deaths on next tick")
	observations.append({"case":"mutual melee","id":id,"first":first,"hp":[a.hp,b.hp]})
func shared_kill(first: int):
	var s=make("qi","yin")
	var a=body(s,"unit.qi.vanguard",0);var b=body(s,"unit.qi.executioner",0,-.1)
	var target=body(s,"unit.yin.axe",1,.4);target.hp=1
	ready(a,target);ready(b,target)
	var gold: int=int(s.players[0].gold)
	advance(s,1,first)
	var hits=events_of(s.drain_events(),"hit");var total: float=0
	for hit in hits:total+=float(hit.amount)
	verify(target.hp==0 and hits.size()==2,"both same-frame attacks contribute to one lethal target")
	verify(is_equal_approx(total,1.0),"overkill attribution cannot exceed target's remaining health")
	verify(s.stats[0].killed==1 and s.stats[1].lost==1 and s.corpses.size()==1,"shared kill counted once")
	verify(s.players[0].gold==gold+7,"one bounty goes to largest mitigated contributor")
func control_windows(first: int):
	var s=make("yin","qi")
	var hammer=body(s,"unit.yin.hammer",0);var foe=body(s,"unit.qi.vanguard",1,.4)
	hammer.hp=1000;hammer.max_hp=1000;foe.hp=1000;foe.max_hp=1000
	ready(hammer,foe);ready(foe,hammer)
	advance(s,1,first)
	verify(hammer.hp<1000 and foe.hp<1000,"same-frame stun does not revoke already released counterattack")
	verify(foe.statuses.has("stun"),"released hammer still applies stun")
	verify(events_of(s.drain_events(),"attack").size()==2,"both release events precede control consequence")
	ready(foe,hammer,.2)
	advance(s,1,first)
	verify(foe.windup==0 and foe.anim=="bound","existing stun blocks a later windup")
	verify(events_of(s.drain_events(),"attack").is_empty(),"existing control produces no attack")
	s=make("yin","qi");hammer=body(s,"unit.yin.hammer",0);foe=body(s,"unit.qi.vanguard",1,.4)
	ready(hammer,foe);ready(foe,hammer,.2)
	advance(s,1,first)
	verify(foe.windup==0 and hammer.hp==hammer.max_hp,"stun interrupts unfinished opposing windup")
	verify(s.stats[0].interrupts==1,"unfinished attack interruption counted once")
func ranged_pair(first: int):
	var s=make()
	var a=body(s,"unit.qi.javelin",0);var b=body(s,"unit.qi.javelin",1,.4)
	a.hp=1;b.hp=1
	s.launch(a,b,20,0,1,0);s.launch(b,a,20,0,1,0)
	for p in s.projectiles:p.left=.001
	if first==1:s.projectiles.reverse()
	var gold: Array=[s.players[0].gold,s.players[1].gold]
	advance(s,1,first)
	var events=s.drain_events()
	verify(a.hp==0 and b.hp==0,"simultaneous projectile impacts are order independent")
	verify(events_of(events,"hit").size()==2 and events_of(events,"death").size()==2,"both projectile impacts and deaths emitted")
	verify(s.players[0].gold==gold[0]+5 and s.players[1].gold==gold[1]+5,"both projectile kills earn one bounty")
	verify(s.projectiles.is_empty() and s.corpses.size()==2,"projectiles consumed and two corpses created")
func shooter_death(first: int):
	var s=make()
	var shooter=body(s,"unit.qi.javelin",0);var melee=body(s,"unit.qi.vanguard",1,.4)
	shooter.hp=1;melee.hp=1;ready(shooter,melee);ready(melee,shooter)
	var gold: int=int(s.players[0].gold)
	advance(s,1,first)
	verify(shooter.hp==0 and melee.hp>0 and s.projectiles.size()==int(db.balance.units[shooter.id].burst_count),"lethal melee cannot cancel concurrently released burst shots")
	advance(s,15,first)
	verify(melee.hp==0 and shooter.hp==0,"released shot hits after its shooter dies without reviving it")
	verify(s.players[0].gold==gold+5 and s.stats[0].killed==1,"dead shooter retains projectile kill ownership and bounty")
func remaining_contracts():
	var s=make("mo","yin")
	var leech=body(s,"unit.mo.leech",0);var target=body(s,"unit.yin.axe",1,.4)
	leech.hp=50;target.hp=2;ready(leech,target)
	advance(s)
	var hits=events_of(s.drain_events(),"hit")
	verify(hits.size()==1 and is_equal_approx(hits[0].amount,2),"lifesteal uses actual damage instead of overkill")
	verify(is_equal_approx(leech.hp,50+2*.38),"living attacker receives bounded lifesteal")
	s=make("mo","mo");var a=body(s,"unit.mo.leech",0);var b=body(s,"unit.mo.leech",1,.4)
	a.hp=50;b.hp=50;ready(a,b);ready(b,a);advance(s)
	verify(is_equal_approx(a.hp,b.hp) and a.hp>27 and a.hp<50,"nonlethal simultaneous lifesteal is symmetric")
	s=make("mo","shuang");leech=body(s,"unit.mo.blade",0);target=body(s,"unit.shuang.shield",1,.4)
	leech.hp=2;ready(leech,target);advance(s)
	verify(leech.hp==0 and target.hp>0 and s.corpses.size()==1,"retaliation death cannot be undone by attack lifesteal")
	verify(s.stats[1].killed==1 and s.stats[0].lost==1,"retaliation lethal credit counted once")
	s=make("mo","qi");a=body(s,"unit.mo.giant",0);b=body(s,"unit.qi.vanguard",1,.4)
	var neighbor=body(s,"unit.qi.vanguard",1,1.3);neighbor.hp=10
	a.hp=1;b.hp=1;ready(a,b);ready(b,a);advance(s)
	verify(a.hp==0 and b.hp==0 and neighbor.hp==0,"death burst resolves after mutually lethal released attacks")
	verify(s.corpses.size()==3 and events_of(s.drain_events(),"death").size()==3,"death burst creates each corpse once")
	verify(s.stats[0].killed==2 and s.stats[1].killed==1,"death burst does not recount already dead victim")
	s=make("qi","mu");a=body(s,"unit.qi.vanguard",0);b=body(s,"unit.qi.executioner",0,-.1)
	var phoenix=body(s,"unit.mu.phoenix",1,.4);target=body(s,"unit.mu.guard",1,.5)
	var survivor=body(s,"unit.mu.guard",1,1.5);survivor.hp=100;survivor.hurt=1
	phoenix.hp=1;phoenix.hurt=1;target.hp=1;target.hurt=1
	ready(a,phoenix);ready(b,target);advance(s)
	verify(phoenix.hp==0 and target.hp==0,"death healing cannot revive another same-frame lethal victim")
	verify(is_equal_approx(survivor.hp,165) and s.stats[1].healed==65,"death healing still restores living allies")
	s=make("qi","yin");a=body(s,"unit.qi.vanguard",0);target=body(s,"unit.yin.axe",1,3)
	ready(a,target);advance(s)
	verify(target.hp==target.max_hp and events_of(s.drain_events(),"attack").is_empty(),"out-of-range target cancels release")
	s=make("qi","yin");a=body(s,"unit.qi.vanguard",0);target=body(s,"unit.yin.axe",1,.4)
	ready(a,target);target.side=0;advance(s)
	verify(target.hp==target.max_hp and events_of(s.drain_events(),"attack").is_empty(),"converted friendly target rejects release")
	s=make("qi","yin");a=body(s,"unit.qi.vanguard",0);target=body(s,"unit.yin.axe",1,.4)
	ready(a,target);s.set_status(a,"stun",1,0,1,int(target.uid));s.interrupt(a,1);advance(s)
	verify(target.hp==target.max_hp and events_of(s.drain_events(),"attack").is_empty(),"control applied before tick cancels windup")
	s=make("qi","yin");a=body(s,"unit.qi.vanguard",0);target=body(s,"unit.yin.axe",1,.4)
	ready(a,target);s.set_status(a,"root",1,0,1,int(target.uid));advance(s)
	verify(target.hp<target.max_hp,"movement root alone does not cancel a legal released attack")
	s=make("qi","yin");a=body(s,"unit.qi.vanguard",0);b=body(s,"unit.qi.executioner",0,-.1)
	var base: Dictionary=s.bases[1];s.map.apply_anchor(base,s.map.anchor(a.edge,float(a.s)+.4));base.hp=1
	ready(a,base);ready(b,base);advance(s)
	verify(base.hp==0 and events_of(s.drain_events(),"building_death").size()==1,"simultaneous building damage emits one destruction")
	verify(s.corpses.is_empty() and s.stats[0].killed==0,"destroyed building is not a unit kill or corpse")
	s=make("bai","qi");a=body(s,"unit.bai.oracle",0);b=body(s,"unit.qi.vanguard",1,.4)
	a.hp=1;b.hp=1;s.players[0].mana=0;ready(a,b);ready(b,a);advance(s,16)
	verify(a.hp==0 and b.hp==0,"oracle projectile survives its shooter")
	verify(is_equal_approx(s.players[0].mana,s.time*.5+5),"dead oracle earns one kill-mana reward")
	s=make("mo","qi");a=body(s,"unit.mo.needle",0);b=body(s,"unit.qi.vanguard",1,.4)
	a.hp=1;ready(a,b);ready(b,a);advance(s,16)
	verify(a.hp==0 and b.hp>0 and b.statuses.has("poison"),"poison projectile retains status effect after shooter death")
	s=make("qi","yin");a=body(s,"unit.qi.vanguard",0);b=body(s,"unit.yin.axe",1,.4)
	a.hp=1;ready(a,b);s.set_status(a,"poison",1,100,1,int(b.uid));a.statuses.poison.clock=.249;advance(s)
	verify(a.hp==0 and b.hp==b.max_hp and events_of(s.drain_events(),"attack").is_empty(),"status death before release phase cancels attack")
	s=make("qi","yin");a=body(s,"unit.qi.vanguard",0);b=body(s,"unit.yin.axe",1,.4)
	a.ttl=.001;ready(a,b);advance(s)
	verify(a.hp==0 and b.hp==b.max_hp and s.corpses.is_empty(),"lifetime expiry before release cannot create an attack or corpse")
	s=make("ji","qi");a=body(s,"unit.ji.vanguard",0);b=body(s,"unit.qi.vanguard",1,.4)
	a.attack_serial=2;ready(a,b);advance(s)
	verify(a.attack_serial==3 and b.statuses.has("stun"),"third-hit combo uses the released attack serial")
	s=make("mo","bai");a=body(s,"unit.mo.leech",0);b=body(s,"unit.mo.leech",0,-.1);target=body(s,"unit.bai.mirror",1,.4)
	var hp: float=target.hp;ready(a,target);ready(b,target);advance(s)
	verify(is_equal_approx(hp-target.hp,23*.65),"one-shot spell ward absorbs one of two simultaneous magical hits")
	verify(events_of(s.drain_events(),"blocked").size()==1,"one-shot ward emits one block")
func run():
	db=Data.new()
	for first in [0,1]:
		pair_death(first,"unit.qi.vanguard","qi")
		pair_death(first,"unit.mo.leech","mo")
		shared_kill(first);control_windows(first);ranged_pair(first);shooter_death(first)
	remaining_contracts()
	var report={"checks":checks,"failures":failures,"passed":failures.is_empty(),"observations":observations,"scope":"Native controlled 60Hz release, impact and death contracts; not faction balance, GPU or Android evidence.","inputs":{}}
	for path in ["res://scripts/battle_sim.gd","res://scripts/unit_abilities.gd","res://data/balance-prototype.json","res://tests/test_simultaneous_combat.gd"]:report.inputs[path]=FileAccess.get_sha256(path)
	var args=OS.get_cmdline_user_args()
	var out: String=args[args.find("--output")+1] if args.has("--output") else "user://simultaneous-combat.json"
	var file=FileAccess.open(out,FileAccess.WRITE);file.store_string(JSON.stringify(report,"  "));file.close()
	print("SIMULTANEOUS_COMBAT: ",checks," checks; failures=",failures)
	quit(0 if failures.is_empty() else 1)
