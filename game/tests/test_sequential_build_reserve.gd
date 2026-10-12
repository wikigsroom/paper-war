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
		var sim=Simulation.new(Data.new())
		sim.start({"map":"map.01.04","faction":"bai","enemy":"bai","ai_warmup":0})
		sim.ai_enabled=[false,false];sim.time=100;sim.buildings.clear()
		var p: Dictionary=sim.players[side]
		var target: String="unit.bai.scribe"
		p.gold=122;p.ai_unit_plan=target;p.unlocked.append(target);p.studied.append("tech.bai.unit.scribe")
		var direction: float=1 if side==0 else -1
		sim.spawn("unit.bai.worker",side,sim.bases[side].x)
		sim.spawn("unit.bai.mirror",side,sim.bases[side].x+direction)
		sim.spawn("unit.bai.repeater",side,sim.bases[side].x+2*direction)
		sim.visibility.refresh()
		check(AI.watchpost_slot(sim,side)>=0,"Fixture offers a genuine optional fork watchpost")
		sim.config["experimental_ai_sequential_deployment"]=true
		AI.turn(sim,side)
		check(p.queue==[target] and p.gold==0,"Paid deployment gets actual cash before optional watchpost")
		check(p.ai_build_reserve==0,"Deferred optional building cannot retain a blocking budget")
		check(sim.buildings.is_empty(),"No free facility or extra cash is created")
	print("SEQUENTIAL_BUILD_RESERVE: ",checks," checks; failures=",failures)
	quit(0 if failures.is_empty() else 1)
