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
	var db=Data.new();var a=Simulation.new(db);var b=Simulation.new(db)
	var options={"map":"map.01.04","faction":"yin","enemy":"yin","starting_gold":300,"enemy_starting_gold":300,"full_tech":true,"ai_warmup":0,"seed":137}
	a.start(options);b.start(options)
	for i in range(100):a.ai_rng[0].randf()
	verify(a.ai_rng[1].state==b.ai_rng[1].state,"opponent draws do not change own random stream")
	AI.turn(a,1);AI.turn(b,1)
	verify(a.players[1].queue==b.players[1].queue and a.players[1].gold==b.players[1].gold,"paid enemy recruitment unchanged by opponent RNG consumption")
	a.start(options);b.start(options)
	for i in range(16):verify(a.ai_rng[0].randf()==b.ai_rng[1].randf(),"mirrored seeded preferences "+str(i))
	a.start(options);var draw: float=a.ai_rng[0].randf();a.start(options)
	verify(a.ai_rng[0].randf()==draw,"restart restores deterministic preference stream")
	options.seed=271;b.start(options)
	verify(b.ai_rng[0].randf()!=draw,"different seed retains varied preferences")
	print("AI_RANDOM_STREAMS ",checks," failures=",failures);quit(0 if failures.is_empty() else 1)
func _initialize():call_deferred("run")
