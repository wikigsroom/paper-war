extends SceneTree
const Data=preload("res://scripts/data_store.gd")
const Simulation=preload("res://scripts/battle_sim.gd")
const Abilities=preload("res://scripts/unit_abilities.gd")
const MatchProjection=preload("res://scripts/match_projection.gd")
var checks: int=0
var failures: Array=[]
var db
func check(ok: bool,note: String):
	checks+=1
	if not ok:failures.append(note)
func make(faction: String):
	var s=Simulation.new(db)
	s.start({"map":"map.01.04","faction":faction,"enemy":faction,"full_tech":true,"starting_gold":900,"enemy_starting_gold":900})
	s.ai_enabled=[false,false];s.units.clear();s.buildings.clear();s.drain_events()
	return s
func bridge(s,u,offset: float=0):
	s.map.apply_anchor(u,s.map.anchor("bridge",7.0+offset))
func _initialize():call_deferred("run")
func run():
	db=Data.new()
	for side in [0,1]:
		var tag: String="side "+str(side)+": "
		var s=make("mu")
		var medic=s.spawn("unit.mu.medic",side,20);bridge(s,medic)
		var guard=s.spawn("unit.mu.guard",side,20);bridge(s,guard,.3);guard.hp-=30
		var healthy=s.spawn("unit.mu.guard",side,20);bridge(s,healthy,.6)
		var enemy=s.spawn("unit.mu.guard",1-side,20);bridge(s,enemy,.5);enemy.hp=30
		s.drain_events();medic.ability_clock=0;medic.summon_cd=0
		Abilities.tick(s,medic,db.balance.units[medic.id],.01)
		var events: Array=s.drain_events();var heals: Array=events.filter(func(e):return e.kind=="heal")
		check(is_equal_approx(guard.hp,guard.max_hp-7),tag+"healer restores real wounded health")
		check(enemy.hp==30 and healthy.hp==healthy.max_hp,tag+"hostile and full-health bodies are untouched")
		check(heals.size()==1 and heals[0].uid==guard.uid and heals[0].amount==23,tag+"one capped positive heal names its target")
		check(heals.size()==1 and is_equal_approx(float(heals[0].y),float(guard.y)) and absf(guard.y)>1,tag+"bridge feedback uses elevated target paper")
		check(heals.size()==1 and heals[0].source_uid==medic.uid,tag+"heal attribution names the real medic")
		check(s.stats[side].healed==23,tag+"statistics equal restored health")
		s.visibility.refresh()
		var public: Array=MatchProjection.visible_events(s,side,events).filter(func(e):return e.kind=="heal")
		check(public.size()==1 and public[0].y==guard.y and not public[0].has("source_uid"),tag+"projected feedback retains paper height without private provenance")
		guard.hp=guard.max_hp;s.set_status(guard,"poison",3,4,1-side);s.stats[side].healed=0
		medic.ability_clock=0;medic.summon_cd=0;Abilities.tick(s,medic,db.balance.units[medic.id],.01)
		events=s.drain_events()
		check(not events.any(func(e):return e.kind=="heal"),tag+"full-health cleanse has no zero-value heal event")
		check(not guard.statuses.has("poison") and medic.summon_cd>0 and events.any(func(e):return e.kind=="unit_special" and e.fx=="heal"),tag+"cleanse still consumes cooldown and has its ability animation")
		check(s.stats[side].healed==0 and guard.hp==guard.max_hp,tag+"cleanse invents no healing score")
		s=make("ji")
		check(s.build(side,"building.ji.tower",0,true)=="",tag+"repair fixture builds a real paid facility")
		var tower: Dictionary=s.buildings[0];tower.hp=tower.max_hp-5
		var engineer=s.spawn("unit.ji.engineer",side,tower.x);s.map.apply_anchor(engineer,s.map.anchor(tower.edge,tower.s))
		var hostile: Dictionary=tower.duplicate(true);hostile.uid=990;hostile.side=1-side;hostile.hp=20;s.buildings.append(hostile)
		s.drain_events();engineer.ability_clock=0;engineer.summon_cd=0;Abilities.tick(s,engineer,db.balance.units[engineer.id],.01)
		events=s.drain_events();heals=events.filter(func(e):return e.kind=="heal")
		check(tower.hp==tower.max_hp and s.stats[side].healed==5,tag+"repair is capped and counted as effective restoration")
		check(heals.size()==1 and heals[0].amount==5 and heals[0].uid==tower.uid and heals[0].source_uid==engineer.uid and heals[0].y==tower.y,tag+"repair has the actual source and target paper")
		check(hostile.hp==20,tag+"repair never restores an overlapping enemy facility")
		s=make("mu")
		var moth=s.spawn("unit.mu.phoenix",side,20);bridge(s,moth)
		guard=s.spawn("unit.mu.guard",side,20);bridge(s,guard,.3);guard.hp=guard.max_hp-40
		healthy=s.spawn("unit.mu.guard",side,20);bridge(s,healthy,.6)
		enemy=s.spawn("unit.mu.guard",1-side,20);bridge(s,enemy,.5);enemy.hp=30
		s.drain_events();moth.hp=0;Abilities.on_death(s,moth,db.balance.units[moth.id]);events=s.drain_events();heals=events.filter(func(e):return e.kind=="heal")
		check(guard.hp==guard.max_hp and enemy.hp==30 and healthy.hp==healthy.max_hp,tag+"death restoration affects only wounded allies")
		check(heals.size()==1 and heals[0].source_uid==moth.uid and heals[0].uid==guard.uid and heals[0].amount==40 and heals[0].y==guard.y,tag+"death restoration names its dead source and elevated target")
		check(s.stats[side].healed==40,tag+"death restoration score matches actual missing health")
		Abilities.on_death(s,moth,db.balance.units[moth.id])
		check(not s.drain_events().any(func(e):return e.kind=="heal"),tag+"healthy survivors emit no empty restoration feedback")
		guard.hp-=40;moth.clone=true;Abilities.on_death(s,moth,db.balance.units[moth.id])
		check(guard.hp==guard.max_hp-40 and s.drain_events().is_empty(),tag+"copied moth does not duplicate the death ability")
		s.visibility.refresh();public=MatchProjection.visible_events(s,side,events).filter(func(e):return e.kind=="heal")
		check(public.size()==1 and public[0].y==guard.y and not public[0].has("source_uid"),tag+"visible death healing does not serialize private dead-source provenance")
	print("HEALING_EVENTS: ",checks," checks; failures=",failures)
	quit(0 if failures.is_empty() else 1)
