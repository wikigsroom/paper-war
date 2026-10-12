extends SceneTree
const Data=preload("res://scripts/data_store.gd")
const Simulation=preload("res://scripts/battle_sim.gd")
const AI=preload("res://scripts/tactical_ai.gd")
var checks: int=0
var failures: Array=[]
func check(ok: bool,note: String):
	checks+=1
	if not ok:failures.append(note)
func _initialize():call_deferred("run")
func run():
	for side in [0,1]:
		var s=Simulation.new(Data.new())
		s.start({"map":"map.01.04","faction":"mu","enemy":"mu","starting_gold":62,"enemy_starting_gold":62,"ai_warmup":0})
		s.ai_enabled=[false,false];s.time=130
		var enemy=s.spawn("unit.mu.guard",1-side,float(s.bases[side].x)+(.65 if side==0 else -.65))
		s.visibility.refresh()
		check(AI.spawn_camped(s,side,[enemy]),"Visible melee occupies real production outlet")
		AI.turn(s,side)
		check(s.players[side].queue.is_empty() and s.players[side].gold==62,"Camped outlet saves eight more gold for screen instead of fragile ranged recruit")
		s.players[side].gold=70;AI.turn(s,side)
		check(s.players[side].queue==["unit.mu.guard"] and s.players[side].gold==0,"Emergency frontline pays actual seventy gold")
		s.players[side].queue.clear();s.players[side].gold=62
		s.map.apply_anchor(enemy,s.map.project(Vector2(float(s.bases[side].x)+(3 if side==0 else -3),0)));s.visibility.refresh()
		check(not AI.spawn_camped(s,side,[enemy]),"Nearby approach outside outlet is not treated as spawn camping")
		AI.turn(s,side)
		check(s.players[side].queue==["unit.mu.poisoner"],"Uncamped urgent economy threat retains affordable ranged fallback")
		s.map.apply_anchor(enemy,s.map.at_node(s.map.definition.bases[1-side].node,1-side));s.visibility.refresh()
		check(not AI.spawn_camped(s,side,[enemy]),"Hidden remote enemy cannot camp outlet")
		enemy.hp=0
		check(not AI.spawn_camped(s,side,[enemy]),"Dead attacker cannot block emergency recruitment")
	print("SPAWN_CAMP_RECRUITMENT: ",checks," checks; failures=",failures)
	quit(0 if failures.is_empty() else 1)
