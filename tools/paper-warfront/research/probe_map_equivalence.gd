extends SceneTree
# Research probe: compare shipped rules, without changing the game runtime.
const Store = preload("res://scripts/data_store.gd")
const Simulation = preload("res://scripts/battle_sim.gd")

func _init():
	var reports: Array = []
	for map_id in ["stamp-plain", "ink-marsh", "lantern-ridge"]:
		reports.append(observe(map_id))
	var reference: Dictionary = reports[0]
	var identical: bool = true
	for report in reports:
		if report.trace_sha256 != reference.trace_sha256:
			identical = false
	var output: Dictionary = {
		"purpose": "Research measurement of current map-dependent simulation",
		"date": "2026-10-08",
		"engine": Engine.get_version_info().string,
		"conditions": {"seed":137,"fixed_dt":1.0/60.0,"requested_ticks":7200,"both_sides_ai":true,"faction":"yin","enemy":"mo","starting_gold_each":420,"full_tech":true,"difficulty":1,"ai_style":"counter"},
		"maps": reports,
		"all_simulation_traces_identical": identical,
		"scope": "Includes state and events at every tick. Excludes config.map and rendering. Does not establish benchmark fidelity, human play quality, or all possible matches."
	}
	var args: PackedStringArray = OS.get_cmdline_user_args()
	if args.is_empty():
		push_error("Pass an absolute output JSON path after --")
		quit(2)
		return
	var file: FileAccess = FileAccess.open(args[0], FileAccess.WRITE)
	if file == null:
		push_error("Cannot open probe output")
		quit(2)
		return
	file.store_string(JSON.stringify(output, "\t"))
	file.close()
	print("MAP_RESEARCH: ", JSON.stringify({"identical":identical,"maps":reports.size(),"output":args[0]}))
	quit(0 if identical else 1)

func observe(map_id: String) -> Dictionary:
	var data = Store.new()
	var sim = Simulation.new(data)
	sim.start({"map":map_id,"seed":137,"faction":"yin","enemy":"mo","difficulty":1,"full_tech":true,"starting_gold":420,"enemy_starting_gold":420,"ai_style":"counter"})
	sim.ai_enabled = [true, true]
	var initial: Dictionary = {"bases":sim.bases.duplicate(true),"workers":sim.units.duplicate(true),"build_slots":[[sim.slot_x(0,0),sim.slot_x(0,1)],[sim.slot_x(1,0),sim.slot_x(1,1)]]}
	var hash_context = HashingContext.new()
	hash_context.start(HashingContext.HASH_SHA256)
	var first_damage_time: float = -1.0
	var executed_ticks: int = 0
	for tick_index in range(7200):
		sim.tick(1.0/60.0)
		executed_ticks += 1
		var events: Array = sim.drain_events()
		if first_damage_time < 0:
			for event in events:
				if event.kind == "hit":
					first_damage_time = sim.time
					break
		var state: Dictionary = {"time":sim.time,"ticks":sim.tick_count,"uid":sim.next_uid,"winner":sim.winner,"rng_state":sim.rng.state,"ai_clock":sim.ai_clock,"players":sim.players,"units":sim.units,"buildings":sim.buildings,"bases":sim.bases,"corpses":sim.corpses,"projectiles":sim.projectiles,"scheduled":sim.scheduled,"stats":sim.stats,"events":events}
		hash_context.update(JSON.stringify(state).to_utf8_buffer())
		if sim.winner != -2:
			break
	return {"map":map_id,"initial":initial,"executed_ticks":executed_ticks,"simulation_seconds":sim.time,"first_damage_seconds":first_damage_time,"winner":sim.winner,"stats":sim.stats.duplicate(true),"base_hp":[sim.bases[0].hp,sim.bases[1].hp],"trace_sha256":hash_context.finish().hex_encode()}
