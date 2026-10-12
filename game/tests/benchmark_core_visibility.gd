extends SceneTree
const Data=preload("res://scripts/data_store.gd")
const Simulation=preload("res://scripts/battle_sim.gd")
func _initialize():call_deferred("run")
func run():
	var args=OS.get_cmdline_user_args()
	var moving: bool=args.has("--moving")
	var db=Data.new()
	var s=Simulation.new(db)
	s.start({"map":"map.01.04","faction":"yin","enemy":"mo","full_tech":true})
	s.units.clear();s.ai_enabled=[false,false]
	for side in range(2):
		for i in range(60):
			var ids: Array=s.players[side].roster
			var u=s.spawn(ids[i%ids.size()],side,18+float(i%12)*.25+side*7)
			u.hp=100000;u.max_hp=u.hp;u["speed_override"]=float(db.balance.units[u.id].speed) if moving else 0.0
	s.visibility.refresh()
	var refresh_start: int=Time.get_ticks_usec()
	for i in range(30):s.visibility.refresh()
	var refresh_mean: float=float(Time.get_ticks_usec()-refresh_start)/30
	var scan_start: int=Time.get_ticks_usec()
	for i in range(10):
		for unit in s.units:s.nearest_enemy(unit)
	var scan_mean: float=float(Time.get_ticks_usec()-scan_start)/10
	var samples: Array=[]
	for i in range(120):
		var before: int=Time.get_ticks_usec()
		s.tick(1.0/60.0)
		samples.append(Time.get_ticks_usec()-before)
	samples.sort()
	var total: int=0
	for sample in samples:total+=sample
	var report={"scope":"Windows native headless CPU simulation, 120 live combat units, branched map, formal fog. No rendered FPS or Android hardware claim.","visibility_refresh_mean_us":refresh_mean,"all_units_target_scan_mean_us":scan_mean,"marching":moving,"live_units":s.units.size(),"samples":samples.size(),"mean_us":float(total)/samples.size(),"median_us":samples[samples.size()/2],"p95_us":samples[int(samples.size()*.95)],"max_us":samples[-1]}
	report["inputs"]={}
	for path in ["res://scripts/battle_sim.gd","res://scripts/unit_abilities.gd","res://scripts/battle_visibility.gd","res://scripts/map_runtime.gd","res://data/balance-prototype.json","res://data/maps.json","res://tests/benchmark_core_visibility.gd"]:report.inputs[path]=FileAccess.get_sha256(path)
	if args.has("--output"):
		var file=FileAccess.open(args[args.find("--output")+1],FileAccess.WRITE);file.store_string(JSON.stringify(report,"  "));file.close()
	print(JSON.stringify(report))
	quit()
