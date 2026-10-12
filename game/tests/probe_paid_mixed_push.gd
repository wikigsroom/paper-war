extends SceneTree
const Data=preload("res://scripts/data_store.gd")
const Simulation=preload("res://scripts/battle_sim.gd")
const Legacy=preload("res://tests/reference_homogeneous_formation.gd")
func _initialize():call_deferred("run")
func tech_chain(db,id: String,seen: Array)->Array:
	var node: Dictionary=db.tech(id);var result: Array=[]
	for required in node.requires:
		if not seen.has(required):
			result.append_array(tech_chain(db,required,seen));seen.append(required)
	if not seen.has(id):result.append(id);seen.append(id)
	return result
func run():
	var db=Data.new();var args=OS.get_cmdline_user_args();var legacy: bool=args.has("--legacy")
	var faction: String=args[args.find("--formation")+1] if args.has("--formation") else "yuan"
	var recipes: Dictionary={"yuan":{"tech":["tech.yuan.unit.artillery"],"units":["unit.yuan.vanguard","unit.yuan.artillery","unit.yuan.archer","unit.yuan.archer"]},"bai":{"tech":["tech.bai.unit.scribe"],"units":["unit.bai.mirror","unit.bai.scribe","unit.bai.repeater","unit.bai.repeater"]},"mu":{"tech":["tech.mu.unit.warden","tech.mu.unit.medic"],"units":["unit.mu.guard","unit.mu.warden","unit.mu.medic","unit.mu.poisoner"]}}
	assert(recipes.has(faction))
	var report={"scope":"Paid scripted formation investment and opposing melee wave. Normal 300 gold, two workers, real research/production, formal fog; no AI or human/faction-balance claim.","scripted_formation":faction,"experimental_legacy_formation":legacy,"inputs":{},"records":[]}
	for path in ["res://scripts/battle_sim.gd","res://scripts/battle_visibility.gd","res://scripts/unit_abilities.gd","res://scripts/manual_spell_rules.gd","res://scripts/map_runtime.gd","res://data/balance-prototype.json","res://data/technology.json","res://data/maps.json","res://tests/probe_paid_mixed_push.gd","res://tests/reference_homogeneous_formation.gd"]:report.inputs[path]=FileAccess.get_sha256(path)
	for map_id in ["map.01.01","map.01.04","map.01.11"]:
		for side in [0,1]:
			var s=Legacy.new(db) if legacy else Simulation.new(db)
			s.start({"map":map_id,"faction":faction if side==0 else "yin","enemy":"yin" if side==0 else faction,"starting_gold":300,"enemy_starting_gold":300,"full_tech":false,"seed":271})
			s.ai_enabled=[false,false];s.drain_events()
			var chain: Array=[];var seen: Array=[]
			for id in recipes[faction].tech:chain.append_array(tech_chain(db,id,seen))
			var orders: Array=recipes[faction].units.duplicate()
			var paid: Array=[];var releases: Dictionary={};var hits: Dictionary={};var building_hits: Dictionary={};var created: Dictionary={}
			var enemy_orders: int=0;var wave_triggered: bool=false;var first_contact=null;var first_building_hit=null
			for step in range(180*60):
				if s.players[side].research.is_empty():
					for id in chain:
						if s.players[side].studied.has(id):continue
						var result: Dictionary=s.request(side,"research",{"id":id})
						if result.ok:paid.append({"kind":"research","id":id,"time":s.time,"gold":db.tech(id).gold})
						break
				if chain.all(func(id):return s.players[side].studied.has(id)) and not orders.is_empty():
					var id: String=orders[0]
					var result: Dictionary=s.request(side,"recruit",{"id":id})
					if result.ok:orders.pop_front();paid.append({"kind":"recruit","id":id,"time":s.time,"gold":db.balance.units[id].gold})
				for unit in s.units:
					if unit.side==side and unit.id==recipes[faction].units[1]:wave_triggered=true
				if wave_triggered and enemy_orders<3:
					if s.request(1-side,"recruit",{"id":"unit.yin.axe"}).ok:enemy_orders+=1
				s.tick(1.0/60.0)
				for unit in s.units:
					if unit.side==side and not db.balance.units[unit.id].get("economy",false) and not created.has(unit.uid):created[unit.uid]={"id":unit.id,"time":s.time}
				for e in s.drain_events():
					if e.kind=="attack" and e.side==side:
						releases[e.uid]=int(releases.get(e.uid,0))+1
						if first_contact==null:first_contact=s.time
					if e.kind=="hit" and int(e.get("attacker_side",-1))==side and int(e.get("source_uid",0))!=0:
						hits[e.source_uid]=int(hits.get(e.source_uid,0))+1
						if e.get("building",false):
							building_hits[e.source_uid]=int(building_hits.get(e.source_uid,0))+1
							if first_building_hit==null:first_building_hit=s.time
				if s.winner!=-2:break
			var members: Array=[]
			for uid in created:members.append({"uid":uid,"id":created[uid].id,"created_at":created[uid].time,"releases":int(releases.get(uid,0)),"hits":int(hits.get(uid,0)),"building_hits":int(building_hits.get(uid,0))})
			report.records.append({"map":map_id,"side":side,"paid":paid,"remaining_orders":orders,"enemy_orders":enemy_orders,"first_contact":first_contact,"first_building_hit":first_building_hit,"members":members,"winner":s.winner,"time":s.time,"gold":s.players[side].gold,"delivered":s.stats[side].gold_delivered,"enemy_base_hp":s.bases[1-side].hp,"workers":s.population(side,true),"stats":s.stats[side]})
	var file=FileAccess.open(args[args.find("--output")+1],FileAccess.WRITE);file.store_string(JSON.stringify(report,"  "));file.close()
	print("PAID_MIXED_PUSH ",report.records.size());quit()
