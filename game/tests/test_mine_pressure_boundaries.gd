extends SceneTree
const Data=preload("res://scripts/data_store.gd")
const Simulation=preload("res://scripts/battle_sim.gd")
const AI=preload("res://scripts/tactical_ai.gd")
var failures: Array=[]
var checks: int=0
func check(ok: bool,note: String):
	checks+=1
	if not ok:failures.append(note)
func _initialize():call_deferred("run")
func run():
	for side in [0,1]:
		var s=Simulation.new(Data.new())
		s.start({"map":"map.01.04","faction":"mu","enemy":"mu"})
		s.ai_enabled=[false,false]
		var mine: Dictionary={}
		for entry in s.map.definition.mines:
			if entry.owner==side:mine=entry;break
		var raider=s.spawn("unit.mu.guard",1-side,float(mine.x)+1)
		s.visibility.refresh()
		check(raider.edge!=mine.edge and s.visible_to(side,raider),"Visible raider is across mine road endpoint")
		check(AI.mine_under_visible_pressure(s,side,mine,[raider]),"Adjacent connected road cannot hide a mine threat")
		s.map.apply_anchor(raider,s.map.anchor(str(mine.edge),maxf(0,float(mine.s)-1)))
		s.visibility.refresh()
		check(AI.mine_under_visible_pressure(s,side,mine,[raider]),"Same-road mine threat remains recognized")
		s.map.apply_anchor(raider,s.map.at_node(s.map.definition.bases[1-side].node,1-side));s.visibility.refresh()
		check(not AI.mine_under_visible_pressure(s,side,mine,[raider]),"Remote hidden raider cannot trigger mine defense")
		raider.hp=0
		check(not AI.mine_under_visible_pressure(s,side,mine,[raider]),"Dead raider cannot trigger mine defense")
		s.units.clear()
		var branch_mine: Dictionary=s.map.anchor("bridge",float(s.map.edges.bridge.length)*.5)
		var separated=s.spawn("unit.mu.guard",1-side,22)
		s.spawn("unit.mu.worker",side,22);s.visibility.refresh()
		check(s.visible_to(side,separated) and AI.dist(separated,branch_mine)<6,"Parallel-road fixture is visibly close in screen space")
		check(not AI.mine_under_visible_pressure(s,side,branch_mine,[separated]),"Separated branch uses connected path distance instead of screen proximity")
	print("MINE_PRESSURE_BOUNDARIES: ",checks," checks; failures=",failures)
	quit(0 if failures.is_empty() else 1)
