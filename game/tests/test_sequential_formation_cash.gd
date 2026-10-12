extends SceneTree
const Data=preload("res://scripts/data_store.gd")
const Simulation=preload("res://scripts/battle_sim.gd")
const AI=preload("res://scripts/tactical_ai.gd")
func _initialize():call_deferred("run")
func run():
	var failures: Array=[]
	var db=Data.new()
	for side in [0,1]:
		for seed_value in range(16):
			var s=Simulation.new(db)
			s.start({"map":"map.01.01","faction":"mu","enemy":"mu","ai_warmup":0,"seed":seed_value})
			s.ai_enabled=[false,false];s.config["experimental_ai_sequential_deployment"]=true
			var p: Dictionary=s.players[side]
			p.ai_unit_plan="unit.mu.medic";p.ai_unit_plan_until=-1;p.gold=110
			p.unlocked.append("unit.mu.medic");p.studied.append("tech.mu.unit.medic")
			s.spawn("unit.mu.guard",side,s.bases[side].x+(1 if side==0 else -1))
			s.visibility.refresh();AI.turn(s,side)
			if p.queue.is_empty() or p.queue.has("unit.mu.medic") or p.ai_unit_plan!="unit.mu.medic":failures.append("Formation gate bypassed by scoring: side %d seed %d"%[side,seed_value])
	print("SEQUENTIAL_FORMATION_CASH: 32 checks; failures=",failures)
	quit(0 if failures.is_empty() else 1)
