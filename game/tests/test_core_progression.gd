extends SceneTree
const Data=preload("res://scripts/data_store.gd")
const Simulation=preload("res://scripts/battle_sim.gd")
var checks: int=0
var failures: Array=[]
func verify(value: bool,note: String):
	checks+=1
	if not value:failures.append(note)
func advance(s,seconds: float):
	for i in range(roundi(seconds*60)):s.tick(1.0/60.0)
func run():
	var db=Data.new()
	for faction in db.FACTIONS:
		var s=Simulation.new(db)
		s.start({"map":"map.01.01","faction":faction,"enemy":"mo","starting_gold":5000,"player_roster":db.all_unit_ids(faction).slice(2,6)})
		s.ai_enabled=[false,false]
		verify(s.players[0].roster.size()==6,"all six available "+faction)
		var known: Array=s.players[0].studied.duplicate()
		var remaining: Array=[]
		for node in db.technology.nodes:
			if node.faction!=faction:continue
			if not known.has(node.id):remaining.append(node)
		for attempt in range(20):
			for node in remaining.duplicate():
				var eligible: bool=true
				for prerequisite in node.requires:
					verify(not db.tech(prerequisite).is_empty(),"prerequisite exists "+node.id)
					if not known.has(prerequisite):eligible=false
				if eligible:known.append(node.id);remaining.erase(node)
			if remaining.is_empty():break
		verify(remaining.is_empty(),"technology reachable without dependency cycle "+faction)
		for id in db.all_unit_ids(faction):
			verify(float(db.balance.units[id].production_seconds)>0,"positive production "+id)
			if not db.technology.starting_unlocked[faction].has(id):verify(not s.players[0].unlocked.has(id),"quick loadout does not grant advanced unit "+id)
	var s=Simulation.new(db)
	s.start({"map":"map.01.01","faction":"yin","enemy":"mo","starting_gold":5000})
	s.ai_enabled=[false,false]
	var before: float=s.players[0].gold
	verify(not s.request(0,"research",{"id":"tech.yin.unit.cannon"}).ok,"heavy prerequisite enforced")
	verify(s.players[0].gold==before,"rejected research no debit")
	verify(s.request(0,"research",{"id":"tech.yin.unit.hammer"}).ok,"intermediate investment accepted")
	advance(s,5.1)
	verify(s.request(0,"research",{"id":"tech.yin.unit.cannon"}).ok,"heavy research available after investment")
	advance(s,8.1)
	verify(s.request(0,"recruit",{"id":"unit.yin.cannon"}).ok,"recruit researched heavy")
	advance(s,3.5)
	verify(s.units.filter(func(u):return u.id=="unit.yin.cannon").is_empty(),"heavy not produced prematurely")
	advance(s,.4)
	verify(s.units.filter(func(u):return u.id=="unit.yin.cannon").size()==1,"heavy completes after 3.8 seconds")
	print("CORE_PROGRESSION: ",checks," checks; failures=",failures)
	quit(0 if failures.is_empty() else 1)
func _initialize():call_deferred("run")

