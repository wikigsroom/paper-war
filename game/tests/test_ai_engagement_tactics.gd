extends SceneTree
const Data=preload("res://scripts/data_store.gd")
const Simulation=preload("res://scripts/battle_sim.gd")
const AI=preload("res://scripts/tactical_ai.gd")
var failures: Array=[]
var checks: int=0
func verify(ok: bool,note: String):
	checks+=1
	if not ok:failures.append(note)
func make(db,faction: String):
	var s=Simulation.new(db)
	s.start({"map":"map.01.04","faction":faction,"enemy":"yin","starting_gold":0,"full_tech":false})
	s.ai_enabled=[false,false];s.units.clear();s.time=20;s.players[0].mana=0
	return s
func run():
	var db=Data.new();var s=make(db,"mu")
	for x in [3,4]:s.spawn("unit.mu.worker",0,x)
	for x in [19,20]:s.spawn("unit.mu.poisoner",0,x)
	s.spawn("unit.yin.axe",1,22);s.players[0].gold=100;s.players[0].ai_research="tech.mu.unit.medic"
	s.visibility.refresh();AI.turn(s,0)
	verify(s.players[0].research.is_empty() and s.players[0].ai_research=="","exposed ranged pair releases research savings")
	verify(s.players[0].queue==["unit.mu.guard"] and s.players[0].gold==30,"real 70-gold front replacement before optional worker or medic")
	s=make(db,"jin")
	for x in [3,4]:s.spawn("unit.jin.worker",0,x)
	for x in [19,20]:s.spawn("unit.jin.archer",0,x)
	s.spawn("unit.yin.axe",1,22);s.players[0].gold=100
	s.visibility.refresh();AI.turn(s,0)
	verify(s.players[0].queue.is_empty() and s.players[0].gold==100,"save for missing expensive front instead of cycling cheaper archers")
	s.players[0].gold=125;AI.turn(s,0)
	verify(s.players[0].queue==["unit.jin.berserker"] and s.players[0].gold==0,"normal 125-gold screen is recruited when the saved budget becomes sufficient")
	s=make(db,"mu")
	for x in [3,4]:s.spawn("unit.mu.worker",0,x)
	s.spawn("unit.mu.poisoner",0,12);s.spawn("unit.yin.axe",1,10);s.players[0].gold=65
	s.visibility.refresh();AI.turn(s,0)
	verify(s.players[0].queue.is_empty() and s.players[0].gold==65,"defensive approach preserves the 70-gold screen budget rather than cycling 62-gold ranged")
	s=make(db,"mu")
	for x in [3,4]:s.spawn("unit.mu.worker",0,x)
	s.spawn("unit.mu.poisoner",0,8);s.spawn("unit.yin.axe",1,4.5);s.players[0].gold=65
	s.visibility.refresh();AI.turn(s,0)
	verify(s.players[0].queue==["unit.mu.poisoner"],"enemy already near workers retains affordable emergency recruitment")
	s=make(db,"mu")
	for x in [3,4]:s.spawn("unit.mu.worker",0,x)
	s.spawn("unit.mu.guard",0,35);s.spawn("unit.mu.poisoner",0,10);s.spawn("unit.yin.axe",1,11)
	s.players[0].gold=100;s.players[0].ai_research="tech.mu.unit.medic"
	s.visibility.refresh();AI.turn(s,0)
	verify(s.players[0].queue==["unit.mu.guard"] and s.players[0].ai_research=="","distant attacking front does not cover an exposed home ranged unit")
	s=make(db,"mu")
	for x in [3,4]:s.spawn("unit.mu.worker",0,x)
	var forward=s.spawn("unit.mu.guard",0,30);s.spawn("unit.yin.axe",1,31)
	var rear=s.spawn("unit.mu.poisoner",0,10);var raider=s.spawn("unit.yin.axe",1,11)
	s.visibility.refresh()
	verify(AI.backline_without_screen(s,[forward,rear],[raider]),"front at another contact does not protect a threatened rear formation")
	var screen=s.spawn("unit.mu.guard",0,10.5)
	verify(not AI.backline_without_screen(s,[forward,rear,screen],[raider]),"nearby front toward the same raider supplies a local screen")
	s.map.apply_anchor(screen,s.map.project(Vector2(12,0)))
	verify(AI.backline_without_screen(s,[forward,rear,screen],[raider]),"front beyond the raider does not count as interception")
	s.players[0].gold=0;s.players[0].ai_research="tech.mu.unit.medic"
	s.players[0].unlocked.erase("building.mu.tower")
	AI.turn(s,0)
	verify(s.players[0].ai_research=="tech.mu.unit.medic","default strategy does not cancel investment solely for the experimental multi-contact signal")
	s=make(db,"bai");s.players[0].unlocked=["spell.bai.clone"];s.players[0].mana=45
	var ally=s.spawn("unit.bai.repeater",0,3);var enemy=s.spawn("unit.yin.axe",1,10)
	s.visibility.refresh();AI.cast_spells(s,0,[enemy],[ally],false)
	verify(s.stats[0].casts==0 and s.players[0].mana==45,"temporary clone is not spent during distant approach")
	s=make(db,"bai");s.players[0].unlocked=["spell.bai.clone"];s.players[0].mana=45
	ally=s.spawn("unit.bai.repeater",0,19);var wounded=s.spawn("unit.bai.mirror",0,20);wounded.hp=20
	enemy=s.spawn("unit.yin.axe",1,21);s.visibility.refresh();AI.cast_spells(s,0,[enemy],[wounded,ally],false)
	var copies: Array=s.units.filter(func(u):return u.clone)
	verify(copies.size()==1 and copies[0].id=="unit.bai.repeater" and copies[0].hp==ally.hp,"clone a healthy engaged burst shooter instead of dying melee")
	verify(s.players[0].mana==0 and copies[0].ttl==14,"clone pays normal 45 mana and retains faction lifetime")
	s=make(db,"bai");s.players[0].unlocked=["spell.bai.protect"];s.players[0].mana=30
	ally=s.spawn("unit.bai.mirror",0,20);enemy=s.spawn("unit.mu.colossus",1,20.7);enemy.windup=.5;enemy.target=ally.uid
	s.visibility.refresh();AI.cast_spells(s,0,[enemy],[ally],false)
	verify(ally.statuses.has("protect") and s.players[0].mana==0,"healthy front is protected before an incoming heavy blow")
	s=make(db,"jin");s.players[0].unlocked=["spell.jin.sacrifice"]
	ally=s.spawn("unit.jin.berserker",0,20);ally.hp=40;var second=s.spawn("unit.jin.leech",0,19)
	enemy=s.spawn("unit.mu.colossus",1,20.7);enemy.windup=.5;enemy.target=ally.uid
	s.visibility.refresh();AI.cast_spells(s,0,[enemy],[ally,second],false)
	verify(ally.hp==40 and s.stats[0].casts==0,"preserve a last-stand fighter even when critically wounded")
	s=make(db,"mu");s.players[0].unlocked=["spell.mu.sacrifice"]
	ally=s.spawn("unit.mu.guard",0,20);ally.hp=35;second=s.spawn("unit.mu.poisoner",0,19)
	enemy=s.spawn("unit.mu.colossus",1,20.7);enemy.windup=.5;enemy.target=ally.uid
	s.visibility.refresh();AI.cast_spells(s,0,[enemy],[ally,second],false)
	verify(ally.hp==35 and s.stats[0].casts==0,"do not sacrifice the last front screening ranged troops")
	s=make(db,"mo");s.players[0].unlocked=["spell.mo.sacrifice"]
	ally=s.spawn("unit.mo.giant",0,20);ally.hp=60;second=s.spawn("unit.mo.blade",0,19)
	enemy=s.spawn("unit.mu.colossus",1,20.7);enemy.windup=.5;enemy.target=ally.uid
	s.visibility.refresh();AI.cast_spells(s,0,[enemy],[ally,second],false)
	verify(ally.hp<=0 and s.players[0].mana==10,"doomed expendable unit can still fund normal sacrifice economy")
	s=make(db,"mu");s.players[0].mana=40
	ally=s.spawn("unit.mu.guard",0,20);enemy=s.spawn("unit.yin.axe",1,21)
	second=s.spawn("unit.yin.axe",1,21.5);s.visibility.refresh()
	AI.cast_spells(s,0,[enemy,second],[ally],false)
	verify(s.stats[0].spell_counts.get("spell.mu.poison",0)==1 and s.spell_areas.size()==1,"cluster receives the faction root-and-poison field instead of routine bind")
	verify(s.players[0].mana==0 and enemy.hp==enemy.max_hp,"field pays 40 mana without inventing instant damage")
	s=make(db,"mu");s.players[0].unlocked=["spell.mu.bind"];s.players[0].mana=60
	ally=s.spawn("unit.mu.guard",0,20);enemy=s.spawn("unit.mu.colossus",1,21)
	s.set_status(enemy,"bind",2,0,0);s.visibility.refresh();AI.cast_spells(s,0,[enemy],[ally],false)
	verify(s.players[0].mana==60 and s.stats[0].casts==0,"already immobilized target does not consume another bind")
	print("AI_ENGAGEMENT_TACTICS: ",checks," checks; failures=",failures)
	quit(0 if failures.is_empty() else 1)
func _initialize():call_deferred("run")
