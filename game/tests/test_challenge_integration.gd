extends SceneTree
const Data=preload("res://scripts/data_store.gd")
const Simulation=preload("res://scripts/battle_sim.gd")
var failures: Array=[]
var checks: int=0
func verify(ok: bool,note: String):
	checks+=1
	if not ok:failures.append(note)
func run():
	var db=Data.new()
	for c in db.read_json("res://data/campaign.json").challenges:
		var s=Simulation.new(db);s.start(c);s.ai_enabled=[false,false]
		verify(s.objective_text().contains(c.challenge_rule.label),c.id+" HUD goal")
		s.bases[1].hp=0;s.evaluate_objective()
		verify(s.winner==-2,c.id+" base destruction does not substitute objective")
		var metric: String=c.challenge_rule.metric
		if metric=="time":s.time=c.challenge_rule.target
		elif metric=="facility_mana":s.stats[0].mana_income.facility=c.challenge_rule.target
		else:s.stats[0][metric]=c.challenge_rule.target
		s.evaluate_objective();verify(s.winner==0,c.id+" goal finishes real simulation")
		s.start(c);s.bases[0].hp=0
		if metric=="time":s.time=c.challenge_rule.target
		elif metric=="facility_mana":s.stats[0].mana_income.facility=c.challenge_rule.target
		else:s.stats[0][metric]=c.challenge_rule.target
		s.evaluate_objective();verify(s.winner==1,c.id+" losing own base overrides goal")
	print("CHALLENGE_INTEGRATION: ",checks," checks; failures=",failures)
	quit(0 if failures.is_empty() else 1)
func _initialize():call_deferred("run")
