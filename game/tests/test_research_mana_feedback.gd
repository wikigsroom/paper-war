extends SceneTree
const Data=preload("res://scripts/data_store.gd")
const Simulation=preload("res://scripts/battle_sim.gd")
const MatchProjection=preload("res://scripts/match_projection.gd")
var checks: int=0
var failures: Array=[]
func check(ok: bool,note: String):
	checks+=1
	if not ok:failures.append(note)
func _initialize():call_deferred("run")
func run():
	for side in [0,1]:
		for initial_mana in [10.0,93.0,100.0]:
			var s=Simulation.new(Data.new())
			s.start({"map":"map.01.01","faction":"bai" if side==0 else "yin","enemy":"yin" if side==0 else "bai","starting_gold":300,"enemy_starting_gold":300,"full_tech":false})
			s.ai_enabled=[false,false];s.players[side].mana=initial_mana;s.drain_events()
			var result: Dictionary=s.request(side,"research",{"id":"tech.bai.unit.scribe"})
			check(result.ok and s.players[side].gold==215,"Research requires real 85 gold")
			check(not s.players[side].unlocked.has("unit.bai.scribe"),"Research is not instantly unlocked")
			var completed: Dictionary={}
			for step in range(301):
				s.tick(1.0/60.0)
				for e in s.drain_events():
					if e.kind=="research_done" and e.side==side:completed=e
			check(not completed.is_empty() and s.players[side].unlocked.has("unit.bai.scribe"),"Real research duration completes the unlock")
			var reward: float=float(completed.get("mana_reward",-1))
			check(is_equal_approx(reward,float(s.stats[side].mana_income.get("research",0))),"Feedback reports actual attributed gain")
			if initial_mana==10:
				check(reward==8 and s.db.research_notice(completed).contains("研究回法 +8"),"Normal research has explicit eight mana notice")
			elif initial_mana==93:
				check(reward>0 and reward<8 and not s.db.research_notice(completed).contains("+8"),"Near cap reports partial gain")
			else:
				check(reward==0 and not s.db.research_notice(completed).contains("研究回法"),"Full mana never claims phantom reward")
			var events: Array=MatchProjection.visible_events(s,side,[completed])
			check(events.size()==1 and is_equal_approx(float(events[0].mana_reward),reward),"Owner network feedback preserves actual amount")
			check(MatchProjection.visible_events(s,1-side,[completed]).is_empty(),"Research reward does not leak to opponent")
	var db=Data.new()
	check(not db.research_notice({"id":"unit.bai.scribe"}).contains("研究回法"),"Older packets without reward remain compatible")
	print("RESEARCH_MANA_FEEDBACK: ",checks," checks; failures=",failures)
	quit(0 if failures.is_empty() else 1)
