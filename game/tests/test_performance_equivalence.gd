extends SceneTree
const Data=preload("res://scripts/data_store.gd")
const Simulation=preload("res://scripts/battle_sim.gd")
var checks: int=0
var failures: Array=[]
func canonical(s) -> String:
	var comparable_stats: Array=s.stats.duplicate(true)
	# New income telemetry is observational; compare every pre-existing gameplay/stat field.
	for side in comparable_stats:side.erase("mana_income")
	return JSON.stringify({"time":s.time,"players":s.players,"units":s.units,"buildings":s.buildings,"bases":s.bases,"corpses":s.corpses,"projectiles":s.projectiles,"areas":s.spell_areas,"scheduled":s.scheduled,"events":s.events,"stats":comparable_stats,"choices":s.map.choices,"winner":s.winner,"protected":s.protected_uid,"escort":s.escort_uid,"intercept":s.intercept_uid})
func run():
	var db=Data.new()
	var args=OS.get_cmdline_user_args()
	var path: String=args[args.find("--baseline")+1]
	var baseline=GDScript.new();baseline.source_code=FileAccess.get_file_as_string(path)
	if baseline.reload()!=OK:quit(1);return
	for faction in db.FACTIONS:
		for map_id in ["map.01.01","map.01.04","map.01.11"]:
			var a=baseline.new(db);var b=Simulation.new(db)
			for s in [a,b]:
				s.start({"map":map_id,"faction":faction,"enemy":"mo","full_tech":true,"starting_gold":1000})
				s.ai_enabled=[false,false]
				for side in range(2):
					for i in range(12):
						var id: String=s.players[side].roster[i%6]
						var u=s.spawn(id,side,18+i*.16+side*4)
						if i%3==0:u["speed_override"]=0.0
						if i%4==0:u.hp=u.max_hp*.7
				s.visibility.refresh()
			for i in range(240):
				a.tick(1.0/60.0);b.tick(1.0/60.0)
				checks+=1
				if canonical(a)!=canonical(b):
					failures.append(faction+" "+map_id+" tick "+str(i));break
				a.drain_events();b.drain_events()
	if args.has("--output"):
		var report={"checks":checks,"failures":failures,"baseline_sha256":FileAccess.get_sha256(path),"current_simulation_sha256":FileAccess.get_sha256("res://scripts/battle_sim.gd"),"scope":"Exact gameplay state and events each 60Hz step, ten factions across short/branched/long maps, stationary and moving mixed forces. Excludes only the added observational mana_income dictionary."}
		var file=FileAccess.open(args[args.find("--output")+1],FileAccess.WRITE);file.store_string(JSON.stringify(report,"  "));file.close()
	print("PERFORMANCE_EQUIVALENCE: ",checks," checks; failures=",failures)
	quit(0 if failures.is_empty() else 1)
func _initialize():call_deferred("run")
