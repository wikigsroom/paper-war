extends SceneTree
const Data=preload("res://scripts/data_store.gd")
const Simulation=preload("res://scripts/battle_sim.gd")
const AI=preload("res://scripts/tactical_ai.gd")
var failures: Array=[]
var checks: int=0
func verify(ok: bool,note: String):
	checks+=1
	if not ok:failures.append(note)
func make(db):
	var s=Simulation.new(db)
	s.start({"map":"map.01.01","faction":"mo","enemy":"yin","enemy_starting_gold":50,"ai_phases":[{"id":"invest","at":0,"style":"economy","workers":3,"prefer_units":["unit.yin.cannon"]}]})
	s.ai_enabled=[false,false];s.time=20
	s.spawn("unit.yin.axe",1,s.bases[1].x-1);s.spawn("unit.yin.spear",1,s.bases[1].x-2);s.visibility.refresh()
	return s
func run():
	var db=Data.new();var s=make(db)
	AI.turn(s,1)
	verify(s.players[1].ai_research=="tech.yin.unit.hammer","select prerequisite toward desired cannon")
	verify(s.players[1].queue.is_empty() and s.players[1].gold==50,"save budget instead of buying another basic soldier")
	s.players[1].gold=70;AI.turn(s,1)
	verify(s.players[1].research.id=="tech.yin.unit.hammer" and s.players[1].gold==4,"spend normal 66-gold research cost before optional third worker")
	verify(s.players[1].queue.is_empty(),"optional worker did not consume research budget")
	for i in range(301):s.tick(1.0/60.0);s.drain_events()
	verify(s.players[1].unlocked.has("unit.yin.hammer"),"real research timer completes")
	s=make(db);AI.turn(s,1);s.players[1].gold=60
	var enemy=s.spawn("unit.mo.blade",0,s.bases[1].x-3);s.visibility.refresh();AI.turn(s,1)
	verify(s.players[1].ai_research=="" and not s.players[1].queue.is_empty(),"visible base threat releases savings for defense")
	verify(s.players[1].gold<60 and s.players[1].research.is_empty(),"defense pays normal recruitment instead of forced technology")
	s=make(db);AI.turn(s,1)
	s.spawn("unit.mo.giant",0,s.bases[0].x+1);s.visibility.refresh();AI.turn(s,1)
	verify(s.players[1].ai_research=="tech.yin.unit.hammer" and s.players[1].queue.is_empty(),"hidden giant does not change investment behavior")
	print("AI_INVESTMENT: ",checks," checks; failures=",failures)
	quit(0 if failures.is_empty() else 1)
func _initialize():call_deferred("run")
