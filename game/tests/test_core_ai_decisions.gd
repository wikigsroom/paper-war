extends SceneTree
const Data=preload("res://scripts/data_store.gd")
const Simulation=preload("res://scripts/battle_sim.gd")
const AI=preload("res://scripts/tactical_ai.gd")
var checks: int=0
var failures: Array=[]
func verify(value: bool,note: String):
	checks+=1
	if not value:failures.append(note)
func make(db,faction: String):
	var s=Simulation.new(db);s.start({"map":"map.01.01","faction":faction,"enemy":"mo","full_tech":true,"starting_gold":1000})
	s.ai_enabled=[false,false];s.units.clear();s.events.clear();return s
func run():
	var db=Data.new()
	var s=make(db,"shuang")
	var ally=s.spawn("unit.shuang.shield",0,20);ally.hp=ally.max_hp*.45
	var giant=s.spawn("unit.mo.giant",1,20.7);giant.windup=.55;giant.target=ally.uid
	s.players[0].mana=100;s.visibility.refresh()
	AI.cast_spells(s,0,[giant],[ally],false)
	verify(giant.windup==0 and giant.statuses.has("stun"),"AI freezes giant before healing")
	verify(s.stats[0].spell_counts.get("spell.shuang.lightning",0)==1,"priority uses real freeze command")
	s=make(db,"shuang");ally=s.spawn("unit.shuang.shield",0,3);ally.hp=ally.max_hp*.4
	giant=s.spawn("unit.mo.giant",1,s.bases[1].x-1);giant.windup=.55;giant.target=ally.uid
	s.players[0].mana=100;s.visibility.refresh();s.time=20
	AI.turn(s,0)
	verify(giant.statuses.is_empty() and giant.windup==.55,"AI cannot interrupt hidden giant")
	s=make(db,"deng");s.config.player_ai_style="economy";s.time=20;s.players[0].gold=60
	for x in [13,14]:s.spawn("unit.deng.mirror",0,x)
	for x in [3,4]:s.spawn("unit.deng.worker",0,x)
	s.visibility.refresh();AI.turn(s,0)
	verify(s.players[0].ai_build_reserve>0 and s.players[0].queue.is_empty(),"facility investment prevents competing recruitment")
	s.players[0].gold=80;AI.turn(s,0)
	verify(s.buildings.size()==1 and s.buildings[0].id=="building.deng.mana","saved budget buys real facility")
	verify(s.players[0].gold==25,"facility pays normal 55 gold")
	s=make(db,"mo");ally=s.spawn("unit.mo.blade",0,20);ally.hp=10;s.players[0].mana=5;s.visibility.refresh()
	AI.cast_spells(s,0,[],[ally],false)
	verify(ally.hp==10 and s.stats[0].casts==0,"AI does not trade a soldier for one mana")
	s=make(db,"yin");s.time=20;s.players[0].gold=float(db.balance.units["unit.yin.worker"].gold)
	s.spawn("unit.yin.axe",0,3);s.spawn("unit.yin.spear",0,4);s.visibility.refresh()
	AI.turn(s,0)
	verify(s.players[0].queue==["unit.yin.worker"] and s.players[0].gold==0,"AI pays for last-worker recovery below former 70 threshold")
	print("CORE_AI_DECISIONS: ",checks," checks; failures=",failures)
	quit(0 if failures.is_empty() else 1)
func _initialize():call_deferred("run")
