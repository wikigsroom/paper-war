extends SceneTree
const Data=preload("res://scripts/data_store.gd")
const Simulation=preload("res://scripts/battle_sim.gd")
const AI=preload("res://scripts/tactical_ai.gd")
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
	var faction: String="mu"
	var symmetric_start: bool=args.has("--symmetric-start")
	var deployment_trial: bool=args.has("--deployment-trial")
	var arrival_trial: bool=args.has("--arrival-trial")
	var policy: String=args[args.find("--policy")+1] if args.has("--policy") else "full_ai"
	assert(policy in ["investment_only","replace_front","replace_front_spells","screen_first_spells","full_ai"])
	var recipes: Dictionary={"yuan":{"tech":["tech.yuan.unit.artillery"],"units":["unit.yuan.vanguard","unit.yuan.artillery","unit.yuan.archer","unit.yuan.archer"]},"bai":{"tech":["tech.bai.unit.scribe"],"units":["unit.bai.mirror","unit.bai.scribe","unit.bai.repeater","unit.bai.repeater"]},"mu":{"tech":["tech.mu.unit.warden","tech.mu.unit.medic"],"units":["unit.mu.guard","unit.mu.warden","unit.mu.medic","unit.mu.poisoner"]}}
	assert(recipes.has(faction))
	var report={"scope":"Paid opening-order comparison with opposing three-axe waves scheduled at 18/43/68 seconds, independent of defender investment. Replacement and paid spell policies are explicitly recorded. Normal 300 gold, two workers, real research/production, formal fog; full defender TacticalAI against scripted paid waves, not human or full faction-balance evidence.","scripted_policy":policy,"defender_full_tactical_ai":policy=="full_ai","wave_protocol":"fixed_18_43_68","spell_threat_gate":"same visible-base-distance and uncovered approach as formal TacticalAI","scripted_formation":faction,"experimental_legacy_formation":legacy,"inputs":{},"records":[]}
	for path in ["res://scripts/battle_sim.gd","res://scripts/battle_visibility.gd","res://scripts/unit_abilities.gd","res://scripts/manual_spell_rules.gd","res://scripts/tactical_ai.gd","res://scripts/map_runtime.gd","res://data/balance-prototype.json","res://data/technology.json","res://data/maps.json","res://tests/probe_sustained_ai_waves.gd","res://tests/reference_homogeneous_formation.gd"]:report.inputs[path]=FileAccess.get_sha256(path)
	report["symmetric_start"]=symmetric_start
	report.inputs["res://scripts/recruitment_readiness.gd"]=FileAccess.get_sha256("res://scripts/recruitment_readiness.gd")
	report["experimental_ai_research_deployment"]=deployment_trial
	report["experimental_ai_support_arrival"]=arrival_trial
	for map_id in ["map.01.01","map.01.04","map.01.11"]:
		for side in [0,1]:
			var s=Legacy.new(db) if legacy else Simulation.new(db)
			s.start({"map":map_id,"faction":faction if side==0 else "yin","enemy":"yin" if side==0 else faction,"starting_gold":300,"enemy_starting_gold":300,"full_tech":false,"seed":271})
			if symmetric_start:s.config["ai_warmup"]=0.0
			if deployment_trial:s.config["experimental_ai_research_deployment"]=true
			if arrival_trial:s.config["experimental_ai_support_arrival"]=true
			s.ai_enabled=[false,false];s.ai_enabled[side]=policy=="full_ai";s.drain_events()
			var chain: Array=[];var seen: Array=[]
			for id in recipes[faction].tech:chain.append_array(tech_chain(db,id,seen))
			var orders: Array=recipes[faction].units.duplicate()
			if policy=="screen_first_spells":orders=["unit.mu.guard","unit.mu.poisoner","unit.mu.warden","unit.mu.medic"]
			var paid: Array=[];var releases: Dictionary={};var hits: Dictionary={};var building_hits: Dictionary={};var created: Dictionary={}
			var medic_trace: Array=[];var purchase_context: Array=[]
			var worker_ids: Dictionary={};var economy_trace: Array=[];var route_trace: Array=[]
			for unit in s.units:
				if unit.side==side and db.balance.units[unit.id].get("economy",false):worker_ids[unit.uid]=true
			var enemy_orders: int=0;var wave_triggered: bool=false;var wave_at: float=18.0;var enemy_paid: Array=[];var spells: Array=[];var first_contact=null;var first_building_hit=null
			for step in range(180*60):
				var known: Array=[];var allies: Array=[]
				for unit in s.units:
					if unit.side==side and db.balance.units[unit.id].get("economy",false):worker_ids[unit.uid]=true
					if unit.hp<=0 or db.balance.units[unit.id].get("economy",false):continue
					if unit.side==side:allies.append(unit)
					elif s.visible_to(side,unit):known.append(unit)
				if policy!="full_ai":
					var guard_needed: bool=policy!="investment_only" and not known.is_empty() and not allies.any(func(u):return AI.is_frontline(db.balance.units[u.id])) and not s.players[side].queue.has("unit.mu.guard")
					if guard_needed:
						if s.request(side,"recruit",{"id":"unit.mu.guard"}).ok:paid.append({"kind":"recruit","id":"unit.mu.guard","time":s.time,"gold":db.balance.units["unit.mu.guard"].gold,"replacement":true})
					if policy in ["replace_front_spells","screen_first_spells"] and step%30==0:
						var threatened: bool=AI.uncovered_approach(s,side,known,allies)
						for enemy in known:
							if AI.dist(enemy,s.bases[side])<9:threatened=true
						AI.cast_spells(s,side,known,allies,threatened)
					if s.players[side].research.is_empty():
						for id in chain:
							if s.players[side].studied.has(id):continue
							var result: Dictionary=s.request(side,"research",{"id":id})
							if result.ok:paid.append({"kind":"research","id":id,"time":s.time,"gold":db.tech(id).gold})
							break
					if not guard_needed and not orders.is_empty() and (chain.all(func(id):return s.players[side].studied.has(id)) or (policy=="screen_first_spells" and orders[0] in ["unit.mu.guard","unit.mu.poisoner"])):
						var id: String=orders[0]
						var result: Dictionary=s.request(side,"recruit",{"id":id})
						if result.ok:orders.pop_front();paid.append({"kind":"recruit","id":id,"time":s.time,"gold":db.balance.units[id].gold})
				wave_triggered=s.time>=wave_at
				if wave_triggered and enemy_orders<mini(9,3*(1+int((s.time-wave_at)/25))):
					if s.request(1-side,"recruit",{"id":"unit.yin.axe"}).ok:
						enemy_orders+=1;enemy_paid.append({"time":s.time,"id":"unit.yin.axe","gold":db.balance.units["unit.yin.axe"].gold})
				s.tick(1.0/60.0)
				if step%60==0:
					for medic in s.units:
						if medic.side!=side or medic.hp<=0 or medic.id!="unit.mu.medic":continue
						var nearest: float=INF;var hurt_count: int=0;var eligible: int=0
						for ally in s.units:
							if ally.side!=side or ally.hp<=0 or ally.uid==medic.uid or db.balance.units[ally.id].get("economy",false) or ally.hp>=ally.max_hp-.01:continue
							hurt_count+=1
							var distance: float=s.physical_point(medic).distance_to(s.physical_point(ally))
							nearest=minf(nearest,distance)
							if distance<=float(db.balance.units[medic.id].heal_radius):eligible+=1
						medic_trace.append({"time":s.time,"uid":medic.uid,"x":medic.x,"hp":medic.hp,"hurt_allies":hurt_count,"nearest_hurt_distance":nearest if nearest<INF else -1,"eligible":eligible,"healed_total":s.stats[side].healed,"silenced":medic.statuses.has("silence")})
				for unit in s.units:
					if unit.side==side and not db.balance.units[unit.id].get("economy",false) and not created.has(unit.uid):created[unit.uid]={"id":unit.id,"time":s.time}
				for e in s.drain_events():
					if e.kind=="route_changed" and e.side==side:route_trace.append({"time":s.time,"node":e.node,"edge":e.edge})
					if e.kind=="hit" and worker_ids.has(int(e.uid)):
						var attacker: Dictionary=s.actor(int(e.get("source_uid",0)))
						var defenders: Array=[]
						for ally in s.units:
							if ally.side==side and ally.hp>0 and not db.balance.units[ally.id].get("economy",false):defenders.append({"uid":ally.uid,"id":ally.id,"hp":ally.hp,"x":ally.x,"edge":ally.edge})
						economy_trace.append({"time":s.time,"kind":"hit","worker_uid":e.uid,"x":e.x,"damage":e.amount,"source_uid":e.get("source_uid",0),"source_x":attacker.get("x",null),"source_edge":attacker.get("edge",""),"source_visible":not attacker.is_empty() and s.visible_to(side,attacker),"gold":s.players[side].gold,"mana":s.players[side].mana,"cooldowns":s.players[side].cooldowns.duplicate(),"queue":s.players[side].queue.duplicate(),"defenders":defenders})
					if e.kind=="death" and e.side==side and db.balance.units[e.id].get("economy",false):economy_trace.append({"time":s.time,"kind":"death","worker_uid":e.uid,"x":e.x})
					if policy=="full_ai" and int(e.get("side",-1))==side:
						if e.kind=="recruit" and e.id=="unit.mu.medic":
							var context: Array=[]
							for ally in s.units:
								if ally.side==side and ally.hp>0 and not db.balance.units[ally.id].get("economy",false):context.append({"uid":ally.uid,"id":ally.id,"hp":ally.hp,"max_hp":ally.max_hp,"x":ally.x,"edge":ally.edge,"s":ally.s})
							purchase_context.append({"time":s.time,"allies":context})
						if e.kind=="recruit":paid.append({"kind":"recruit","id":e.id,"time":s.time,"gold":db.balance.units[e.id].gold})
						elif e.kind=="research_start":paid.append({"kind":"research","id":e.id,"time":s.time,"gold":db.tech(e.id).gold})
						elif e.kind=="build":paid.append({"kind":"build","id":e.id,"time":s.time,"gold":db.balance.buildings[e.id].gold})
					if e.kind=="cast" and e.side==side:spells.append({"time":s.time,"id":e.id})
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
			report["economy_trace_scope"]="Read-only own worker hit/death snapshots, defender state and own route changes; not gameplay intelligence. Visibility sampled after tick."
			report["medic_trace_sampling_seconds"]=1
			for uid in created:members.append({"uid":uid,"id":created[uid].id,"created_at":created[uid].time,"releases":int(releases.get(uid,0)),"hits":int(hits.get(uid,0)),"building_hits":int(building_hits.get(uid,0))})
			var economy_record: Dictionary={"map":map_id,"side":side,"incidents":economy_trace,"routes":route_trace}
			if not report.has("economy_traces"):report["economy_traces"]=[]
			report.economy_traces.append(economy_record)
			report.records.append({"medic_trace":medic_trace,"medic_purchase_context":purchase_context,"map":map_id,"side":side,"paid":paid,"remaining_orders":orders,"enemy_orders":enemy_orders,"enemy_paid":enemy_paid,"wave_at":wave_at,"enemy_gold":s.players[1-side].gold,"enemy_delivered":s.stats[1-side].gold_delivered,"spells":spells,"first_contact":first_contact,"first_building_hit":first_building_hit,"members":members,"winner":s.winner,"time":s.time,"gold":s.players[side].gold,"delivered":s.stats[side].gold_delivered,"enemy_base_hp":s.bases[1-side].hp,"workers":s.population(side,true),"stats":s.stats[side]})
	var file=FileAccess.open(args[args.find("--output")+1],FileAccess.WRITE);file.store_string(JSON.stringify(report,"  "));file.close()
	print("SUSTAINED_AI_WAVES ",report.records.size());quit()
