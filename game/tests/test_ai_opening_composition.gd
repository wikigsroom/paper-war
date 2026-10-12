extends SceneTree
const Data=preload("res://scripts/data_store.gd")
const Simulation=preload("res://scripts/battle_sim.gd")
const AI=preload("res://scripts/tactical_ai.gd")
var failures: Array=[]
var checks: int=0
func verify(ok: bool,note: String):
	checks+=1
	if not ok:failures.append(note)
func run():
	var db=Data.new();var s=Simulation.new(db)
	s.start({"map":"map.01.01","faction":"yin","enemy":"mo","starting_gold":70,"full_tech":true,"player_ai_style":"rush"})
	s.ai_enabled=[false,false];AI.turn(s,0)
	verify(s.players[0].queue==["unit.yin.axe"],"rush pays for front before optional third worker")
	verify(s.players[0].gold==25,"opening uses real 45-gold cost")
	s.start({"map":"map.01.01","faction":"yin","enemy":"mo","starting_gold":45,"full_tech":true})
	s.ai_enabled=[false,false];s.time=20
	s.spawn("unit.yin.axe",0,3);s.spawn("unit.yin.spear",0,4)
	s.spawn("unit.mo.giant",1,5);s.visibility.refresh();AI.turn(s,0)
	verify(s.players[0].queue==["unit.yin.axe"] and s.players[0].gold==0,"visible emergency selects an affordable fighter, not an unaffordable preferred heavy")
	s.start({"map":"map.01.01","faction":"yin","enemy":"mo","starting_gold":1000,"full_tech":true,"seed":137})
	s.ai_enabled=[false,false];s.units=s.units.filter(func(u):return u.side==0);s.spawn("unit.yin.axe",0,10)
	s.players[0].queue=["unit.yin.axe"]
	var before: int=s.players[0].queue.size();AI.turn(s,0)
	verify(s.players[0].queue.size()==before+1 and s.players[0].queue[0]=="unit.yin.axe" and s.players[0].queue[-1]!="unit.yin.axe","queued front-line bodies contribute to composition and avoid another redundant axe")
	print("AI_OPENING_COMPOSITION: ",checks," checks; failures=",failures)
	quit(0 if failures.is_empty() else 1)
func _initialize():call_deferred("run")
