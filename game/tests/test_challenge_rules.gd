extends SceneTree
const Rules=preload("res://scripts/challenge_rules.gd")
class Fixture:
	var config: Dictionary={}
	var stats: Array=[{"healed":0,"interrupts":0,"summons":0,"reflections":0,"lost":0,"mana_income":{"facility":0}}]
	var bases: Array=[{"hp":1100.0,"max_hp":1100.0}]
	var time: float=0
	var winner: int=-2
	var result_reason: String=""
var failures: Array=[]
var checks: int=0
func verify(ok: bool,note: String):
	checks+=1
	if not ok:failures.append(note)
func run():
	for metric in ["time","healed","interrupts","summons","reflections","facility_mana"]:
		var s=Fixture.new();s.config={"challenge_rule":{"metric":metric,"target":10,"deadline":30,"label":"test"}}
		verify(not Rules.evaluate(s),metric+" cannot win without effective progress")
		if metric=="time":s.time=10
		elif metric=="facility_mana":s.stats[0].mana_income.facility=10
		else:s.stats[0][metric]=10
		verify(Rules.evaluate(s) and s.winner==0,metric+" effective target wins")
		verify(Rules.score(s)>0,metric+" victory scores")
		var early: int=Rules.score(s);s.time+=1
		verify(Rules.score(s)<early,metric+" time affects high score")
		s.bases[0].hp=550
		verify(Rules.score(s)<early-10,metric+" damage affects high score")
		if metric=="time":s.config.challenge_rule.target=40
		elif metric=="facility_mana":s.stats[0].mana_income.facility=0
		else:s.stats[0][metric]=0
		s.winner=-2;s.time=30
		verify(Rules.evaluate(s) and s.winner==1 and Rules.score(s)==0,metric+" deadline fails unmet target")
	print("CHALLENGE_RULES: ",checks," checks; failures=",failures)
	quit(0 if failures.is_empty() else 1)
func _initialize():call_deferred("run")
