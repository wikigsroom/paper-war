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
	var db=Data.new()
	for level in db.campaign:
		var s=Simulation.new(db);s.start(level);s.ai_enabled=[false,false]
		var previous: float=-1
		for phase in level.ai_phases:
			verify(float(phase.at)>previous,level.id+" phase order")
			previous=float(phase.at)
			for id in phase.prefer_units:verify(s.players[1].roster.has(id),level.id+" reachable preference")
			s.time=float(phase.at)
			var gold: float=s.players[1].gold
			var mana: float=s.players[1].mana
			var actors: int=s.units.size()
			verify(AI.campaign_phase(s,1).id==phase.id,level.id+" active phase")
			verify(s.players[1].gold==gold and s.players[1].mana==mana and s.units.size()==actors,level.id+" no free assets")
			verify(AI.campaign_phase(s,0).is_empty(),level.id+" player unaffected")
			var preferred={"grant":phase.prefer_units[0]}
			verify(AI.research_priority(preferred,phase)>AI.research_priority({"grant":"spell.test"},phase),level.id+" phase investment priority")
	print("CAMPAIGN_DIRECTOR: ",checks," checks; failures=",failures)
	quit(0 if failures.is_empty() else 1)
func _initialize():call_deferred("run")
