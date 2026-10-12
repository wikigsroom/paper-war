extends SceneTree
const Data=preload("res://scripts/data_store.gd")
const Simulation=preload("res://scripts/battle_sim.gd")
const Sight=preload("res://scripts/battle_visibility.gd")
func _initialize():call_deferred("run")
func run():
	var db=Data.new();var s=Simulation.new(db)
	s.start({"map":"map.01.04","faction":"mo","enemy":"mu","starting_gold":300,"enemy_starting_gold":300,"ai_warmup":0,"seed":137})
	s.ai_enabled=[true,true]
	var report={"scope":"90-second normal paid AI opening; observe tower construction, independent tower road sight and actual bridge sightings. Not a full balance or rendering check.","inputs":{},"building_events":[],"bridge_sightings":[],"samples":[]}
	for path in ["res://scripts/battle_sim.gd","res://scripts/tactical_ai.gd","res://scripts/battle_visibility.gd","res://scripts/map_runtime.gd","res://data/maps.json","res://data/balance-prototype.json","res://tests/probe_watchpost_vision.gd"]:report.inputs[path]=FileAccess.get_sha256(path)
	report["scope"]="150-second normal paid AI observation; link bridge discovery to actual infrastructure/economy hits. Observation only, not full balance or rendering evidence."
	report["bridge_target_hits"]=[]
	report["bridge_deaths"]=[]
	report["economic_hits"]=[]
	var seen: Dictionary={};var first_damage: Dictionary={};var catalog: Dictionary={};var bridge_traversed: Dictionary={}
	for step in range(150*60):
		for a in s.units+s.buildings:
			if a.edge=="bridge":bridge_traversed[a.uid]=true
			catalog[a.uid]={"id":a.id,"edge":a.edge,"x":a.x,"traversed_bridge":bridge_traversed.has(a.uid),"building":a.get("building",false),"economy":db.balance.units.get(a.id,{}).get("economy",false)}
		s.tick(1.0/60.0)
		for e in s.drain_events():
			if e.kind=="death" and seen.has(int(e.get("uid",0))):report.bridge_deaths.append({"time":s.time,"uid":e.uid,"since_discovery":s.time-float(seen[e.uid].time)})
			if e.kind in ["build","building_completed"]:report.building_events.append(e)
			if e.kind=="hit":
				var source: int=int(e.get("source_uid",0));var target: Dictionary=catalog.get(int(e.get("uid",0)),{})
				if target.get("building",false) or target.get("economy",false):report.economic_hits.append({"time":s.time,"source_uid":source,"source":catalog.get(source,{}),"target_uid":e.uid,"target":target,"side":e.side,"amount":e.amount})
				if seen.has(source) and (target.get("building",false) or target.get("economy",false)):
					var discovery: Dictionary=seen[source]
					report.bridge_target_hits.append({"time":s.time,"source_uid":source,"target_uid":e.uid,"target":target,"amount":e.amount,"since_discovery":s.time-float(discovery.time),"tower_sight_at_discovery":discovery.tower_sight_alone})
				var actor: Dictionary=s.actor(int(e.get("uid",0)))
				if actor.get("building",false) and not first_damage.has(actor.uid):first_damage[actor.uid]=s.time
		var sight=Sight.new(s)
		for b in s.buildings:
			if b.hp>0 and b.state=="active" and b.disabled<=0:sight.reveal(b.side,b,s.visibility.radius(b))
		for side in [0,1]:sight.propagate(side)
		for enemy in s.units:
			var side: int=1-int(enemy.side)
			if enemy.hp<=0 or enemy.edge!="bridge" or seen.has(enemy.uid) or not s.visible_to(side,enemy):continue
			var discovery={"time":s.time,"observer":side,"uid":enemy.uid,"x":enemy.x,"y":enemy.y,"s":enemy.s,"tower_sight_alone":sight.point_visible(side,s.physical_anchor(enemy))}
			seen[enemy.uid]=discovery
			report.bridge_sightings.append(discovery)
		if step%300==299:
			var buildings: Array=[]
			for b in s.buildings:buildings.append({"uid":b.uid,"side":b.side,"hp":b.hp,"state":b.state,"remaining_construction":b.construction,"edge":b.edge,"x":b.x,"y":b.y,"first_damage":first_damage.get(b.uid,-1)})
			var players: Array=[]
			for side in [0,1]:
				var p: Dictionary=s.players[side]
				players.append({"side":side,"gold":p.gold,"mana":p.mana,"research":p.research.duplicate(true),"saving":p.ai_research,"queue":p.queue.duplicate(),"workers":s.population(side,true),"army":s.population(side,false)})
			report.samples.append({"time":s.time,"buildings":buildings,"players":players})
	report["end_state"]={"time":s.time,"winner":s.winner}
	var args=OS.get_cmdline_user_args();var file=FileAccess.open(args[0],FileAccess.WRITE)
	file.store_string(JSON.stringify(report,"  "));file.close()
	print("WATCHPOST_VISION_OBSERVATION buildings=",report.building_events.size()," bridge_sightings=",report.bridge_sightings.size())
	quit()
