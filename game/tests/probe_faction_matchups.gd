extends SceneTree
const Data=preload("res://scripts/data_store.gd")
const Simulation=preload("res://scripts/battle_sim.gd")
func _initialize():call_deferred("run")
func run():
	var db=Data.new();var args=OS.get_cmdline_user_args()
	if args.has("--unit-overrides"):push_error("The rooted-unit trial was retired; it is not a shipping mechanic. Use --price-overrides only for explicit price pilots.");quit(1);return
	var start: int=int(args[args.find("--start")+1]) if args.has("--start") else 0
	var count: int=int(args[args.find("--count")+1]) if args.has("--count") else 100
	var output: String=args[args.find("--output")+1]
	var map_id: String=args[args.find("--map")+1] if args.has("--map") else "map.01.04"
	var seed_value: int=int(args[args.find("--seed")+1]) if args.has("--seed") else 137
	var sample_seconds: int=maxi(1,int(args[args.find("--sample-seconds")+1])) if args.has("--sample-seconds") else 15
	var duration_seconds: int=int(args[args.find("--duration-seconds")+1]) if args.has("--duration-seconds") else 150
	var starting_gold: int=int(args[args.find("--starting-gold")+1]) if args.has("--starting-gold") else 300
	if starting_gold<0 or starting_gold>300:
		push_error("Paid observation starting stock must be 0..300; stock is explicit in the report");quit(1);return
	var paid_opening_side: int=int(args[args.find("--paid-opening-side")+1]) if args.has("--paid-opening-side") else -1
	var budget_side: int=int(args[args.find("--budget-planner-side")+1]) if args.has("--budget-planner-side") else -1
	if args.has("--budget-planner-side") and (not args.has("--budget-planner-trial") or budget_side not in [0,1]):
		push_error("Budget planner side requires --budget-planner-trial and side 0 or 1");quit(1);return
	if args.has("--budget-planner-trial") and args.has("--paid-opening-trial"):
		push_error("Compare one budget policy at a time");quit(1);return
	if (args.has("--paid-opening-side") or args.has("--paid-opening-faction")) and not args.has("--paid-opening-trial"):
		push_error("Paid opening selectors require --paid-opening-trial");quit(1);return
	if args.has("--paid-opening-side") and (paid_opening_side not in [0,1] or args.has("--paid-opening-faction")):
		push_error("Paid opening side must be 0 or 1 and cannot be combined with a faction selector");quit(1);return
	var combat_trace_seconds: int=int(args[args.find("--combat-trace-seconds")+1]) if args.has("--combat-trace-seconds") else 60
	if duration_seconds<1 or duration_seconds>900 or combat_trace_seconds<0 or combat_trace_seconds>duration_seconds:
		push_error("Observation duration must be 1..900 seconds; combat trace must fit within it");quit(1);return
	var removed_edges: Array=[]
	if args.has("--remove-edge"):
		var edge_id: String=args[args.find("--remove-edge")+1]
		var control: Dictionary=db.map_definition(map_id).duplicate(true)
		for anchor in control.mines+control.build_sites+[control.objective_anchor]:
			if anchor.edge==edge_id:push_error("Cannot remove an edge with authored objects");quit(1);return
		var original_count: int=control.edges.size()
		control.edges=control.edges.filter(func(edge):return edge.id!=edge_id)
		if control.edges.size()==original_count:push_error("Requested experimental edge does not exist");quit(1);return
		control.erase("route_lengths");control.erase("geometry_sha256")
		db.maps[control.id]=control;removed_edges.append(edge_id)
	var price_overrides: Dictionary={}
	var research_scale: float=0.0
	var research_costs: Dictionary={}
	if args.has("--unit-research-scale-trial"):
		var scale_text: String=args[args.find("--unit-research-scale-trial")+1]
		if not scale_text.is_valid_float():push_error("Unit research scale must be a number in (0,1]");quit(1);return
		research_scale=float(scale_text)
		if not is_finite(research_scale) or research_scale<=0 or research_scale>1:
			push_error("Unit research scale must be in (0,1]");quit(1);return
		# Runtime-only price experiment. Both sides pay the same explicit costs;
		# prerequisites, research duration, unit price and production are intact.
		for node in db.technology.nodes:
			if not node.requires.is_empty() and db.balance.units.has(node.grant):
				node.gold=maxi(1,ceili(float(node.gold)*research_scale));research_costs[node.id]=node.gold
	if args.has("--price-overrides"):
		var override_path: String=args[args.find("--price-overrides")+1]
		price_overrides=JSON.parse_string(FileAccess.get_file_as_string(override_path))
		for id in price_overrides:
			if not db.balance.units.has(id) or float(price_overrides[id])<=0:
				push_error("Invalid experimental price override: "+str(id));quit(1);return
			db.balance.units[id].gold=float(price_overrides[id])
	if args.has("--executioner-reach-trial"):db.balance.units["unit.qi.executioner"].range=1.25
	if args.has("--executioner-short-reach-control"):
		if args.has("--executioner-reach-trial"):push_error("Conflicting executioner reach controls");quit(1);return
		db.balance.units["unit.qi.executioner"].range=.85
	var report={"scope":"Paid AI-vs-AI baseline, explicit duration_seconds ceiling, normal research and formal fog. Includes mirrored side assignments; not human skill balance or all-map evidence.","map":map_id,"seed":seed_value,"inputs":{},"records":[]}
	report["starting_gold_per_side"]=starting_gold
	report["experimental_price_overrides"]=price_overrides
	report["experimental_unit_research_scale"]=research_scale
	report["experimental_unit_research_costs"]=research_costs
	report["experimental_ai_budget_planner"]=args.has("--budget-planner-trial")
	report["experimental_ai_budget_planner_side"]=budget_side
	report["experimental_executioner_range"]=.85 if args.has("--executioner-short-reach-control") else (1.25 if args.has("--executioner-reach-trial") else 0.0)
	report["sample_seconds"]=sample_seconds
	report["duration_seconds"]=duration_seconds
	report["combat_trace_seconds"]=combat_trace_seconds
	report["observe_ai_deployment"]=args.has("--deployment-decision-trace")
	report["observe_ai_recruitment"]=args.has("--recruitment-decision-trace")
	report["experimental_ai_paid_opening"]=args.has("--paid-opening-trial")
	report["experimental_paid_opening_faction"]=args[args.find("--paid-opening-faction")+1] if args.has("--paid-opening-faction") else ("both" if args.has("--paid-opening-trial") else "")
	report["experimental_paid_opening_side"]=paid_opening_side
	report["experimental_legacy_area_aim"]=args.has("--legacy-area-aim")
	report["experimental_ai_area_threat_weight"]=args.has("--area-threat-trial")
	report["experimental_ai_research_arrival"]=args.has("--research-arrival-trial")
	report["experimental_ai_funded_deployment"]=args.has("--funded-deployment-trial")
	report["experimental_ai_staged_deployment"]=args.has("--staged-deployment-trial")
	report["experimental_ai_deployment_commitment"]=args.has("--deployment-commitment-trial")
	report["experimental_ai_sequential_deployment"]=args.has("--sequential-deployment-trial")
	report["experimental_ai_sequential_funded_start"]=args.has("--sequential-funded-start-trial")
	report["experimental_ai_role_deployment"]=args.has("--role-deployment-trial")
	report["experimental_ai_context_research"]=args.has("--context-research-trial")
	report["experimental_ai_demand_research"]=args.has("--demand-research-trial")
	report["experimental_ai_demand_deployment"]=args.has("--demand-deployment-trial")
	report["experimental_demand_deployment_faction"]=args[args.find("--demand-deployment-faction")+1] if args.has("--demand-deployment-faction") else ("both" if args.has("--demand-deployment-trial") else "")
	report["experimental_demand_research_faction"]=args[args.find("--demand-research-faction")+1] if args.has("--demand-research-faction") else ("both" if args.has("--demand-research-trial") else "")
	report["experimental_ai_visible_counter_deployment"]=args.has("--visible-counter-trial")
	report["experimental_visible_counter_faction"]=args[args.find("--visible-counter-faction")+1] if args.has("--visible-counter-faction") else ("both" if args.has("--visible-counter-trial") else "")
	report["experimental_context_research_faction"]=args[args.find("--context-research-faction")+1] if args.has("--context-research-faction") else ("both" if args.has("--context-research-trial") else "")
	report["experimental_role_policy_faction"]=args[args.find("--role-trial-faction")+1] if args.has("--role-trial-faction") else ("both" if args.has("--role-deployment-trial") else "")
	report["experimental_ai_research_screen_budget"]=args.has("--research-screen-budget-trial")
	report["experimental_policy_faction"]=args[args.find("--trial-faction")+1] if args.has("--trial-faction") else ("both" if args.has("--funded-deployment-trial") or args.has("--staged-deployment-trial") or args.has("--deployment-commitment-trial") or args.has("--sequential-deployment-trial") else "")
	report["experimental_map_removed_edges"]=removed_edges
	if not removed_edges.is_empty():
		report["experimental_map_sha256"]=JSON.stringify(db.map_definition(map_id)).sha256_text()
		report.scope="Experimental branch removal on the same map; actual road geometry is recorded by experimental_map_sha256. NOT a shipping map. Paid AI-vs-AI with normal research/fog, 150s observation ceiling."
	if not price_overrides.is_empty():report.scope="Experimental paid price pilot: runtime unit costs explicitly overridden below; NOT shipped balance or human acceptance. 150s observation ceiling, normal research and formal fog."
	if research_scale>0:report.scope="Experimental unit research costs explicitly recorded; both sides pay these fees. Unit prices, prerequisites, study/production times and formal fog retained. NOT shipped balance or human acceptance. 150s observation ceiling."
	report.scope=report.scope.replace("150s observation ceiling",str(duration_seconds)+"s observation ceiling")
	for path in ["res://scripts/battle_sim.gd","res://scripts/battle_visibility.gd","res://scripts/unit_abilities.gd","res://scripts/tactical_ai.gd","res://scripts/map_runtime.gd","res://tests/probe_faction_matchups.gd","res://data/balance-prototype.json","res://data/maps.json","res://data/technology.json"]:
		if FileAccess.file_exists(path):report.inputs[path]=FileAccess.get_sha256(path)
	report.inputs["res://scripts/recruitment_readiness.gd"]=FileAccess.get_sha256("res://scripts/recruitment_readiness.gd")
	report.inputs["res://scripts/ai_budget_planner.gd"]=FileAccess.get_sha256("res://scripts/ai_budget_planner.gd")
	for index in range(start,mini(100,start+count)):
		if args.has("--indices") and not args[args.find("--indices")+1].split(",").has(str(index)):continue
		if args.has("--mirrors") and index/10!=index%10:continue
		var west: String=db.FACTIONS[index/10];var east: String=db.FACTIONS[index%10]
		var battle=Simulation.new(db)
		battle.start({"map":map_id,"faction":west,"enemy":east,"starting_gold":starting_gold,"enemy_starting_gold":starting_gold,"ai_warmup":0,"full_tech":false,"seed":seed_value})
		if args.has("--research-arrival-trial"):battle.config["experimental_ai_research_arrival"]=true
		if args.has("--sequential-funded-start-trial"):battle.config["experimental_ai_sequential_funded_start"]=true
		if args.has("--role-deployment-trial"):
			battle.config["experimental_ai_role_deployment"]=true
			if args.has("--role-trial-faction"):
				var role_faction: String=args[args.find("--role-trial-faction")+1]
				battle.config["experimental_ai_role_deployment_side"]=0 if west==role_faction else (1 if east==role_faction else -1)
		if args.has("--sequential-deployment-trial"):
			battle.config["experimental_ai_sequential_deployment"]=true
			if args.has("--trial-faction"):
				var sequential_faction: String=args[args.find("--trial-faction")+1]
				battle.config["experimental_ai_sequential_deployment_side"]=0 if west==sequential_faction else (1 if east==sequential_faction else -1)
		if args.has("--research-screen-budget-trial"):
			battle.config["experimental_ai_research_screen_budget"]=true
			if args.has("--trial-faction"):
				var budget_faction: String=args[args.find("--trial-faction")+1]
				battle.config["experimental_ai_research_screen_budget_side"]=0 if west==budget_faction else (1 if east==budget_faction else -1)
		if args.has("--deployment-commitment-trial"):
			battle.config["experimental_ai_deployment_commitment"]=true
			if args.has("--trial-faction"):
				var commitment_faction: String=args[args.find("--trial-faction")+1]
				battle.config["experimental_ai_deployment_commitment_side"]=0 if west==commitment_faction else (1 if east==commitment_faction else -1)
		if args.has("--funded-deployment-trial"):
			battle.config["experimental_ai_funded_deployment"]=true
			if args.has("--trial-faction"):
				var selected_faction: String=args[args.find("--trial-faction")+1]
				battle.config["experimental_ai_funded_deployment_side"]=0 if west==selected_faction else (1 if east==selected_faction else -1)
		if args.has("--staged-deployment-trial"):
			battle.config["experimental_ai_staged_deployment"]=true
			if args.has("--trial-faction"):
				var chosen_faction: String=args[args.find("--trial-faction")+1]
				battle.config["experimental_ai_staged_deployment_side"]=0 if west==chosen_faction else (1 if east==chosen_faction else -1)
		if args.has("--legacy-area-aim"):battle.config["experimental_legacy_area_aim"]=true
		if args.has("--area-threat-trial"):battle.config["experimental_ai_area_threat_weight"]=true
		battle.ai_enabled=[true,true]
		if args.has("--budget-planner-trial"):
			battle.config["experimental_ai_budget_planner"]=true
			if budget_side>=0:battle.config["experimental_ai_budget_planner_side"]=budget_side
		battle.config["observe_ai_budget"]=args.has("--budget-decision-trace")
		if args.has("--paid-opening-trial"):
			battle.config["experimental_ai_paid_opening"]=true
			if paid_opening_side>=0:battle.config["experimental_ai_paid_opening_side"]=paid_opening_side
			if args.has("--paid-opening-faction"):
				var paid_faction: String=args[args.find("--paid-opening-faction")+1]
				battle.config["experimental_ai_paid_opening_side"]=0 if west==paid_faction else (1 if east==paid_faction else -1)
		if args.has("--demand-deployment-trial"):
			battle.config["experimental_ai_demand_deployment"]=true
			if args.has("--demand-deployment-faction"):
				var demand_deploy_faction: String=args[args.find("--demand-deployment-faction")+1]
				battle.config["experimental_ai_demand_deployment_side"]=0 if west==demand_deploy_faction else (1 if east==demand_deploy_faction else -1)
		if args.has("--demand-research-trial"):
			battle.config["experimental_ai_demand_research"]=true
			if args.has("--demand-research-faction"):
				var demand_faction: String=args[args.find("--demand-research-faction")+1]
				battle.config["experimental_ai_demand_research_side"]=0 if west==demand_faction else (1 if east==demand_faction else -1)
		if args.has("--visible-counter-trial"):
			battle.config["experimental_ai_visible_counter_deployment"]=true
			if args.has("--visible-counter-faction"):
				var counter_faction: String=args[args.find("--visible-counter-faction")+1]
				battle.config["experimental_ai_visible_counter_deployment_side"]=0 if west==counter_faction else (1 if east==counter_faction else -1)
		if args.has("--context-research-trial"):
			battle.config["experimental_ai_context_research"]=true
			if args.has("--context-research-faction"):
				var context_faction: String=args[args.find("--context-research-faction")+1]
				battle.config["experimental_ai_context_research_side"]=0 if west==context_faction else (1 if east==context_faction else -1)
		battle.config["observe_ai_deployment"]=args.has("--deployment-decision-trace")
		battle.config["observe_ai_recruitment"]=args.has("--recruitment-decision-trace")
		var timeline: Array=[]
		var investment_trace: Array=[]
		var combat_trace: Array=[]
		var actor_ids: Dictionary={}
		for u in battle.units+battle.bases:actor_ids[u.uid]=u.id
		for step in range(duration_seconds*60):
			battle.tick(1.0/60.0)
			var emitted: Array=battle.drain_events()
			if args.has("--combat-trace") and battle.time<=combat_trace_seconds:
				for event in emitted:
					if event.kind=="spawn":actor_ids[event.uid]=event.id
					if event.kind not in ["spawn","hit","death","heal","cast","unit_special"]:continue
					var record: Dictionary={}
					for key in ["kind","time","id","uid","source_uid","target_uid","side","attacker_side","amount","physical","building","x","y","fx","origin"]:
						if event.has(key):record[key]=event[key]
					record["actor_id"]=actor_ids.get(int(event.get("uid",0)),"")
					record["source_id"]=actor_ids.get(int(event.get("source_uid",0)),"")
					if event.kind=="cast":
						record["observed_units"]=[]
						for u in battle.units:
							if u.hp>0 and (u.side==event.side or battle.visible_to(int(event.side),u)):
								record.observed_units.append({"uid":u.uid,"id":u.id,"side":u.side,"x":u.x,"y":u.y,"hp":u.hp,"statuses":u.statuses.duplicate(true)})
					combat_trace.append(record)
			if args.has("--investment-trace"):
				for event in emitted:
					if event.kind not in ["recruit","research_start","research_done"]:continue
					var side: int=int(event.get("side",-1))
					if side not in [0,1]:continue
					var allies: Array=[]
					for u in battle.units:
						if u.side==side and u.hp>0 and not db.balance.units[u.id].get("economy",false):allies.append({"uid":u.uid,"id":u.id,"edge":u.edge,"s":u.s,"hp":u.hp,"max_hp":u.max_hp})
					var spent: float=float(db.tech(event.id).gold) if event.kind=="research_start" else (float(db.balance.units[event.id].gold) if event.kind=="recruit" else 0.0)
					investment_trace.append({"kind":event.kind,"id":event.get("id",""),"time":event.time,"side":side,"gold":battle.players[side].gold,"gold_spent":spent,"queue":battle.players[side].queue.duplicate(),"own_combat":allies})
			if args.has("--timeline") and step%(sample_seconds*60)==sample_seconds*60-1:
				var sample={"time":battle.time,"sides":[]}
				for side in range(2):
					var army: Dictionary={};var worker_hp: float=0;var known_enemies: Array=[]
					for unit in battle.units:
						if unit.side!=side and unit.hp>0 and battle.visible_to(side,unit):known_enemies.append({"uid":unit.uid,"id":unit.id,"x":unit.x,"y":unit.y,"edge":unit.edge,"s":unit.s})
						if unit.side!=side or unit.hp<=0:continue
						if db.balance.units[unit.id].get("economy",false):worker_hp+=unit.hp
						else:
							if not army.has(unit.id):army[unit.id]={"count":0,"hp":0.0,"x":[],"actors":[]}
							army[unit.id].count+=1;army[unit.id].hp+=unit.hp;army[unit.id].x.append(unit.x)
							army[unit.id].actors.append({"uid":unit.uid,"x":unit.x,"y":unit.y,"edge":unit.edge,"s":unit.s,"hp":unit.hp,"target":unit.target,"windup":unit.windup})
					var player: Dictionary=battle.players[side]
					sample.sides.append({"army":army,"worker_hp":worker_hp,"workers":battle.population(side,true),"gold":player.gold,"mana":player.mana,"base_hp":battle.bases[side].hp,"route_choices":battle.map.choices[side].duplicate(true),"known_enemies":known_enemies,"studied":player.studied.duplicate(),"research":player.research.duplicate(true),"saving":player.ai_research,"deployment_plan":player.get("ai_unit_plan",""),"deployment_plan_until":player.get("ai_unit_plan_until",0),"queue":player.queue.duplicate(),"stats":battle.stats[side].duplicate(true)})
				timeline.append(sample)
			if battle.winner!=-2:break
		var sides: Array=[]
		for side in range(2):
			var player: Dictionary=battle.players[side]
			sides.append({"base_hp":battle.bases[side].hp,"gold":player.gold,"mana":player.mana,"workers":battle.population(side,true,true),"combat":battle.population(side,false,true),"studied":player.studied.duplicate(),"queue":player.queue.duplicate(),"stats":battle.stats[side].duplicate(true)})
		var row={"index":index,"west":west,"east":east,"winner":battle.winner,"time":battle.time,"sides":sides}
		if args.has("--timeline"):row["timeline"]=timeline
		if args.has("--investment-trace"):row["investment_trace"]=investment_trace
		if args.has("--combat-trace"):row["combat_trace"]=combat_trace
		if args.has("--deployment-decision-trace"):row["deployment_decisions"]=battle.config.get("ai_deployment_trace",[])
		if args.has("--recruitment-decision-trace"):row["recruitment_decisions"]=battle.config.get("ai_recruitment_trace",[])
		if args.has("--budget-decision-trace"):row["budget_decisions"]=battle.config.get("ai_budget_trace",[])
		report.records.append(row)
		var file=FileAccess.open(output,FileAccess.WRITE)
		if file==null:
			push_error("Cannot write observation report: "+output);quit(1);return
		file.store_string(JSON.stringify(report,"  "));file.close()
		print("FACTION_MATCHUP ",index," ",west,"/",east," winner=",battle.winner," time=",battle.time)
	quit()
