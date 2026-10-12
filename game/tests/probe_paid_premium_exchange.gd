extends SceneTree
const Data=preload("res://scripts/data_store.gd")
const Simulation=preload("res://scripts/battle_sim.gd")
func _initialize():call_deferred("run")
func run():
	var args=OS.get_cmdline_user_args()
	var map_id: String=args[args.find("--map")+1] if args.has("--map") else "map.01.04"
	var formal_db=Data.new()
	var records: Array=[]
	for price in ([float(formal_db.balance.units["unit.qi.executioner"].gold)] if args.has("--formal-price") else [127.0,92.0]):
		for reach in ([.85,1.25] if args.has("--reach-trial") else [float(formal_db.balance.units["unit.qi.executioner"].range)]):
			for side in [0,1]:
				var db=Data.new()
				db.balance.units["unit.qi.executioner"].gold=price
				db.balance.units["unit.qi.executioner"].range=reach
				var sim=Simulation.new(db)
				sim.start({"map":map_id,"faction":"qi","enemy":"qi","starting_gold":300,"enemy_starting_gold":300,"full_tech":false,"ai_warmup":0,"seed":137})
				sim.ai_enabled=[false,false];sim.drain_events()
				var study: Dictionary=db.tech("tech.qi.unit.executioner")
				var escorts: int=int(floor((300.0-float(study.gold)-price)/49.0))
				var paid: Array=[];var errors: Array=[];var actors: Dictionary={};var events: Array=[]
				var request: Dictionary=sim.request(side,"research",{"id":study.id})
				if not request.ok:errors.append(request)
				else:paid.append({"side":side,"kind":"research","id":study.id,"gold":study.gold,"time":sim.time})
				for team in [0,1]:
					for i in range(escorts if team==side else 6):
						request=sim.request(team,"recruit",{"id":"unit.qi.vanguard"})
						if not request.ok:errors.append(request)
						else:paid.append({"side":team,"kind":"recruit","id":"unit.qi.vanguard","gold":49,"time":sim.time})
				var ordered: bool=false;var spawned: bool=false;var stop: String="time_limit"
				var releases: int=0;var hits: int=0;var damage: float=0.0
				for step in range(180*60):
					if not ordered and sim.players[side].studied.has(study.id):
						request=sim.request(side,"recruit",{"id":study.grant})
						if request.ok:ordered=true;paid.append({"side":side,"kind":"recruit","id":study.grant,"gold":price,"time":sim.time})
						else:errors.append(request);break
					sim.tick(1.0/60.0)
					for e in sim.drain_events():
						if e.kind=="spawn":
							actors[int(e.uid)]=str(e.id)
							if e.id==study.grant and int(e.side)==side:spawned=true
						if e.kind in ["research_start","research_done","recruit","spawn","attack","hit","death"]:events.append(e.duplicate(true))
						if e.kind=="attack" and int(e.side)==side and actors.get(int(e.uid),"")==study.grant:releases+=1
						if e.kind=="hit" and int(e.get("attacker_side",-1))==side and actors.get(int(e.get("source_uid",0)),"")==study.grant:hits+=1;damage+=float(e.amount)
					if spawned and sim.players[0].queue.is_empty() and sim.players[1].queue.is_empty() and (sim.population(0,false,false)==0 or sim.population(1,false,false)==0):stop="paid_army_eliminated";break
					if sim.winner!=-2:stop="base_destroyed";break
				var hp: Array=[0.0,0.0]
				for u in sim.units:
					if u.hp>0 and not db.balance.units[u.id].get("economy",false):hp[int(u.side)]+=float(u.hp)
				records.append({"price":price,"reach":reach,"premium_side":side,"escorts":escorts,"planned_purchase_budget":float(study.gold)+price+escorts*49,"basic_purchase_budget":294,"paid":paid,"errors":errors,"stop":stop,"time":sim.time,"survivors":[sim.population(0,false,false),sim.population(1,false,false)],"hp":hp,"premium_attack_releases":releases,"premium_hit_events":hits,"premium_event_damage":damage,"events":events})
	var report: Dictionary={"scope":"Scripted 300-gold paid premium investment versus six basic frontliners. Two original workers retained, real research/production/automarch/fog, no AI/spells/towers/additional recruitment. Isolated recipe exchange, not full faction or normal AI balance. Explicit price/reach overrides are recorded per recipe; research remains89. These observations do not establish any exported build.","map":map_id,"formal_price_only":args.has("--formal-price"),"reach_control":args.has("--reach-trial"),"records":records,"inputs":{}}
	for source in ["res://scripts/battle_sim.gd","res://scripts/battle_command_rules.gd","res://scripts/unit_abilities.gd","res://scripts/battle_visibility.gd","res://scripts/map_runtime.gd","res://data/balance-prototype.json","res://data/technology.json","res://data/maps.json","res://tests/probe_paid_premium_exchange.gd"]:report.inputs[source]=FileAccess.get_sha256(source)
	var file=FileAccess.open(args[0],FileAccess.WRITE)
	if file==null:push_error("Cannot save premium exchange report");quit(1);return
	file.store_string(JSON.stringify(report,"  "));file.close()
	print("PAID_PREMIUM_EXCHANGE: ",records.size()," records")
	quit(0 if records.all(func(r):return r.errors.is_empty()) else 1)
