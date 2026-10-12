extends SceneTree
const Data=preload("res://scripts/data_store.gd")
const Simulation=preload("res://scripts/battle_sim.gd")
const Readiness=preload("res://scripts/recruitment_readiness.gd")
const AI=preload("res://scripts/tactical_ai.gd")
func _initialize():call_deferred("run")
func run():
	var args=OS.get_cmdline_user_args()
	var db=Data.new()
	var output: String=args[args.find("--output")+1]
	var report: Dictionary={"scope":"Read-only one-second snapshots after simulation tick, not exact AI decision blockers. Four paid full-AI matches on map.01.04 seed137, both sequential candidates, 150 seconds; no price, gold or fog overrides.","inputs":{},"records":[]}
	for path in ["res://scripts/battle_sim.gd","res://scripts/battle_visibility.gd","res://scripts/unit_abilities.gd","res://scripts/tactical_ai.gd","res://scripts/map_runtime.gd","res://scripts/recruitment_readiness.gd","res://scripts/data_store.gd","res://tests/probe_deployment_windows.gd","res://data/balance-prototype.json","res://data/maps.json","res://data/technology.json","res://data/factions.json"]:
		report.inputs[path]=FileAccess.get_sha256(path)
	for index in [19,51,59,96]:
		var west: String=db.FACTIONS[index/10]
		var east: String=db.FACTIONS[index%10]
		var sim=Simulation.new(db)
		sim.start({"map":"map.01.04","faction":west,"enemy":east,"starting_gold":300,"enemy_starting_gold":300,"ai_warmup":0,"full_tech":false,"seed":137})
		sim.config["experimental_ai_sequential_deployment"]=true
		sim.ai_enabled=[true,true]
		var samples: Array=[]
		for step in range(150*60):
			sim.tick(1.0/60.0)
			sim.drain_events()
			if step%60==0:
				for side in [0,1]:
					var p: Dictionary=sim.players[side]
					var target: String=str(p.get("ai_unit_plan",""))
					if target=="":continue
					var group: Dictionary=Readiness.deployment_group(sim,side)
					var bodies: Array=[]
					var allies: Array=[]
					var enemies: Array=[]
					for u in sim.units:
						if u.hp<=0 or db.balance.units[u.id].get("economy",false):continue
						if u.side==side:allies.append(u)
						elif sim.visible_to(side,u):enemies.append(u)
					var contact_fronts: int=0
					var threatened: bool=AI.uncovered_approach(sim,side,enemies,allies)
					for u in allies:
						if AI.is_frontline(db.balance.units[u.id]) and AI.frontline_near_contact(sim,u,enemies):contact_fronts+=1
					for u in enemies:
						if AI.dist(u,sim.bases[side])<9:threatened=true
					for u in sim.units:
						if u.side!=side or u.hp<=0 or db.balance.units[u.id].get("economy",false):continue
						bodies.append({"uid":u.uid,"id":u.id,"hp":u.hp,"x":u.x,"y":u.y})
					samples.append({"time":sim.time,"side":side,"target":target,"gold":p.gold,"affordable":p.gold>=float(db.balance.units[target].gold),"unlocked":p.unlocked.has(target),"workers_including_orders":sim.population(side,true),"queue":p.queue.duplicate(),"group":group,"bodies":bodies,"visible_enemies":enemies.size(),"contact_fronts":contact_fronts,"front_broken":not enemies.is_empty() and contact_fronts==0,"threatened":threatened,"build_reserve":p.get("ai_build_reserve",0),"research_target":p.ai_research,"remaining_after_target":p.gold-float(db.balance.units[target].gold)})
			if sim.winner!=-2:break
		report.records.append({"index":index,"west":west,"east":east,"winner":sim.winner,"time":sim.time,"samples":samples})
	var stable: bool=true
	for path in report.inputs:
		if FileAccess.get_sha256(path)!=report.inputs[path]:stable=false
	report["source_unchanged"]=stable
	var file=FileAccess.open(output,FileAccess.WRITE)
	if file==null or not stable:push_error("Cannot save stable deployment observation");quit(1);return
	file.store_string(JSON.stringify(report,"\t"));file.close()
	print("deployment windows: ",report.records.size()," matches")
	quit(0)
