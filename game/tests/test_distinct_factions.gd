extends SceneTree
const Data=preload("res://scripts/data_store.gd")
const Simulation=preload("res://scripts/battle_sim.gd")
const Ability=preload("res://scripts/unit_abilities.gd")
var db
var checks: Array=[]
var failures: Array=[]
var observations: Dictionary={}
func _initialize():call_deferred("run")
func check(ok: bool,note: String):
	checks.append({"name":note,"passed":ok})
	if not ok:failures.append(note)
func make(f: String="yin",enemy: String="yin"):
	var s=Simulation.new(db);s.start({"map":"map.01.01","faction":f,"enemy":enemy,"full_tech":true,"starting_gold":900,"enemy_starting_gold":900})
	s.ai_enabled=[false,false];s.units.clear();s.events.clear();return s
func advance(s,seconds: float):
	for i in range(ceili(seconds*60)):s.tick(1.0/60)
func pair(s,id: String):
	var a=s.spawn(id,0,20);var b=s.spawn("unit.yin.axe",1,20.4)
	a.cooldown=999;b.cooldown=999;b.speed_override=0;b.hp=5000;b.max_hp=5000
	return [a,b]
func hit(s,a,b):
	s.attack(a,b);advance(s,.55)
func run():
	db=Data.new();check(db.balance.units.size()==72,"72 curated definitions, no active palette expansion")
	var total: int=0;var shapes: Array=[]
	for f in db.FACTIONS:
		var ids: Array=db.all_unit_ids(f);check(ids.size()==6,f+" six curated combat units");total+=ids.size()
		var roles: Array=[]
		for uid in ids:
			var d: Dictionary=db.balance.units[uid];roles.append(d.get("role",""));check(d.get("manual_recruit",false) and not d.get("summoned",false),uid+" real recruit definition")
			var paid=Simulation.new(db);paid.start({"map":"map.01.01","faction":f,"enemy":"yin","player_roster":[uid,ids[0]],"full_tech":true,"starting_gold":900})
			paid.ai_enabled=[false,false];var treasury: float=paid.players[0].gold
			check(paid.request(0,"recruit",{"id":uid}).ok and is_equal_approx(treasury-paid.players[0].gold,float(d.gold)),uid+" public recruit spends exact treasury")
			# Production is intentionally asymmetric: artillery/giants can take 3.8–4.8s.
			# Wait for the authored production interval instead of imposing a shorter
			# fixture timeout that falsely reports slow but legal units as missing.
			advance(paid,float(d.get("production_seconds",2.0))+.2);check(paid.units.any(func(actor):return actor.id==uid and actor.side==0),uid+" paid production actually creates actor")
			var s=make(f);var actors=pair(s,uid);var a: Dictionary=actors[0];var b: Dictionary=actors[1]
			var w=s.spawn("unit."+f+".worker",0,20.3);var own_hp: float=w.hp;var before: float=b.hp
			hit(s,a,b)
			check(b.hp<before,uid+" real hostile attack causes damage")
			check(is_equal_approx(w.hp,own_hp),uid+" overlapping own miner remains unharmed")
			for e in s.drain_events():
				if e.kind=="hit":check(int(e.side)!=int(e.attacker_side),uid+" every actual damage event remains hostile")
			var bound: float=w.hp;s.attack(a,w);s.damage(w,999,0,true,int(a.uid));check(is_equal_approx(w.hp,bound),uid+" stale friendly target rejected")
		shapes.append(roles)
	check(total==60,"60 selected combat kits")
	for i in range(shapes.size()):
		for j in range(i+1,shapes.size()):check(shapes[i]!=shapes[j],"factions %d/%d have different role compositions"%[i,j])
	for level in db.campaign:
		for field in ["available_roster","default_roster","enemy_roster"]:
			for id in level.get(field,[]):check(db.balance.units.has(id),str(level.id)+" curated "+field+" "+id)
	check(db.normalize_roster("yin",["unit.yin.pike","unit.yin.duelist"]).size()>=2,"old loadout IDs migrate to playable roster")
	# Distinct behavior is exercised on actual simulation actors, not tags or colors.
	var s=make("ji");var p=pair(s,"unit.ji.vanguard");s.attack(p[0],p[1]);s.attack(p[0],p[1]);check(not p[1].statuses.has("stun"),"spring punch first two hits do not stun");s.attack(p[0],p[1]);check(p[1].statuses.has("stun"),"spring punch third real hit stuns")
	s=make("ji");p=pair(s,"unit.ji.javelin");s.attack(p[0],p[1]);s.attack(p[0],p[1]);check(not p[0].get("reload_pending",false),"nail magazine first two rounds");s.attack(p[0],p[1]);check(p[0].get("reload_pending",false),"nail magazine third round needs reload")
	p[0].anim_t=1;s.tick_unit(p[0],1.0/60);check(p[0].anim=="reload" and p[0].reload_left>0,"reload owns a real firing lockout")
	s=make("yuan");p=pair(s,"unit.yuan.vanguard");var basic: float=Ability.attack_amount(s,p[0],p[1],db.balance.units[p[0].id]);p[0]["charge_walk"]=3;check(Ability.attack_amount(s,p[0],p[1],db.balance.units[p[0].id])>basic*1.6,"actual traveled charge increases strike");s.attack(p[0],p[1]);check(p[0].charge_walk==0,"charged strike consumes charge")
	s=make("yuan");p=pair(s,"unit.yuan.archer");s.attack(p[0],p[1]);p[0].anim="attack";p[0].anim_t=1;var road: float=p[0].s;s.tick_unit(p[0],1.0/60);check(p[0].s<road and p[0].backpedal,"archer really retreats on current road after release")
	s=make("yuan");p=pair(s,"unit.yuan.harrier");road=p[1].s;s.attack(p[0],p[1]);check(p[1].s<road,"kite hook really pulls target along road")
	s=make("qi");p=pair(s,"unit.qi.vanguard");s.players[0].gold=0;basic=Ability.attack_amount(s,p[0],p[1],db.balance.units[p[0].id]);s.players[0].gold=400;check(Ability.attack_amount(s,p[0],p[1],db.balance.units[p[0].id])>basic*1.23,"mercenary power trades against spending treasury")
	s=make("qi");p=pair(s,"unit.qi.javelin");p[1].hp=1;var gold: float=s.players[0].gold;hit(s,p[0],p[1]);check(s.players[0].gold==gold+5,"contract tokens pay real combat kill bounty")
	var thrall=s.spawn("unit.mo.thrall",1,20.4);thrall.hp=1;gold=s.players[0].gold;hit(s,p[0],thrall);check(s.players[0].gold==gold,"summoned skeleton cannot farm contract bounty")
	s=make("mo");p=pair(s,"unit.mo.needle");for i in range(3):hit(s,p[0],p[1])
	check(p[1].statuses.has("poison") and is_equal_approx(float(p[1].statuses.poison.potency),12),"bone poison accumulates three real layers")
	s=make("mu");p=pair(s,"unit.mu.poisoner");for i in range(3):hit(s,p[0],p[1])
	check(p[1].statuses.has("root"),"third seed grows actual root control")
	s=make("mu");p=pair(s,"unit.mu.medic");var ally=s.spawn("unit.mu.guard",0,20.1);ally.hp=40;s.set_status(ally,"poison",3,4,1,int(p[1].uid));p[0].summon_cd=0;p[0].ability_clock=0;Ability.tick(s,p[0],db.balance.units[p[0].id],.01)
	check(ally.hp>40 and not ally.statuses.has("poison"),"flower healer restores and cleanses real ally")
	s=make("mu");p=pair(s,"unit.mu.phoenix");ally=s.spawn("unit.mu.guard",0,20.1);ally.hp=40;s.die(p[0],true);check(ally.hp>40,"leaf moth death heals allied actor instead of damaging it")
	s=make("shuang");p=pair(s,"unit.shuang.javelin");for i in range(3):hit(s,p[0],p[1])
	check(p[1].statuses.has("stun"),"third frost wedge causes actual freeze")
	s=make("shuang");p=pair(s,"unit.shuang.shield");basic=p[1].hp;s.attack(p[1],p[0]);check(p[1].hp<basic,"snow shield retaliates against actual melee")
	s=make("shuang");p=pair(s,"unit.shuang.mortar");basic=Ability.attack_amount(s,p[0],p[1],db.balance.units[p[0].id]);s.set_status(p[1],"root",2,0,0,int(p[0].uid));check(Ability.attack_amount(s,p[0],p[1],db.balance.units[p[0].id])>basic*1.44,"snow mortar rewards control combination")
	s=make("jin");p=pair(s,"unit.jin.leech");p[0].hp=40;s.attack(p[0],p[1]);check(is_equal_approx(p[0].hp,40),"fire hook cannot steal from a previously unburned enemy");s.attack(p[0],p[1]);check(p[0].hp>40,"fire hook steals only after burn setup")
	s=make("bai");p=pair(s,"unit.bai.mirror");basic=p[0].hp;s.damage(p[0],40,1,false,int(p[1].uid));check(p[0].hp==basic,"empty frame absorbs first hostile spell");s.damage(p[0],40,1,false,int(p[1].uid));check(p[0].hp<basic,"empty frame cooldown allows next spell through")
	s=make("bai");p=pair(s,"unit.bai.repeater");s.set_status(p[1],"protect",3,0,1);s.attack(p[0],p[1]);check(not p[1].statuses.has("protect"),"letter repeater actually removes protective buff")
	s=make("bai");p=pair(s,"unit.bai.illusionist");s.launch(p[1],p[0],10,0,1,0);s.projectiles[0].x=p[0].x;s.projectiles[0].y=p[0].y;p[0].ability_clock=0;p[0].summon_cd=0;Ability.tick(s,p[0],db.balance.units[p[0].id],.01);check(s.projectiles.is_empty(),"blank eraser removes actual enemy missile")
	s=make("deng");p=pair(s,"unit.deng.effigy");ally=s.spawn("unit.deng.worker",0,20.1);basic=ally.hp;s.damage(ally,40,1,false,int(p[1].uid));check(is_equal_approx(basic-ally.hp,30),"lamp effigy aura protects a real nearby ally")
	var inputs={}
	for path in ["res://scripts/unit_abilities.gd","res://scripts/battle_sim.gd","res://scripts/data_store.gd","res://data/balance-prototype.json","res://data/factions.json","res://data/campaign.json","res://data/unit-id-migration.json","res://tests/test_distinct_factions.gd"]:inputs[path]=FileAccess.get_sha256(path)
	var args=OS.get_cmdline_user_args();var out: String=args[args.find("--report")+1] if args.has("--report") else "user://factions.json"
	FileAccess.open(out,FileAccess.WRITE).store_string(JSON.stringify({"passed":failures.is_empty(),"checks":checks,"failures":failures,"units":72,"combat_units":60,"factions":10,"inputs":inputs,"scope":"Real simulation attacks, friendly ownership, curated campaign IDs and distinctive ability outcomes. Controlled fixtures; ordinary economy/AI gameplay is verified separately."},"\t"))
	print("DISTINCT_FACTIONS: ",checks.size()," checks; failures=",JSON.stringify(failures));quit(0 if failures.is_empty() else 1)
