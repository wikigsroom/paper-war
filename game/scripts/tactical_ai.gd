extends RefCounted
const RecruitmentReadiness=preload("res://scripts/recruitment_readiness.gd")
const BudgetPlanner=preload("res://scripts/ai_budget_planner.gd")
# Uses public geometry, army positions and its own resources. Executes the same commands as UI.
static func dist(a: Dictionary,b: Dictionary) -> float:
	return Vector2(a.x,a.y).distance_to(Vector2(b.x,b.y))

static func turn(sim,side: int):
	if sim.time<float(sim.config.get("ai_warmup",4)) and side==1:return
	var p: Dictionary = sim.players[side]
	var style: String = str(sim.config.get("player_ai_style",sim.config.get("ai_style","counter"))) if side==0 else str(sim.config.get("ai_style","counter"))
	var phase: Dictionary = campaign_phase(sim,side)
	if not phase.is_empty():phase=phase.duplicate(true);phase["research_path"]=preferred_research_path(sim,phase)
	if not phase.is_empty():style=str(phase.get("style",style))
	var limit: int = int(sim.config.get("ai_army_limit",60)) if side==1 else 60
	var combat: int = sim.population(side,false,false)
	var planned_combat: int=sim.population(side,false,true)
	var paid_opening: bool=sim.config.get("experimental_ai_paid_opening",false) and int(sim.config.get("experimental_ai_paid_opening_side",side))==side
	var staged_plan: bool=sim.config.get("experimental_ai_staged_deployment",false) and int(sim.config.get("experimental_ai_staged_deployment_side",side))==side
	var enemies: Array = [];var allies: Array = []
	for u in sim.units:
		if u.hp<=0 or sim.db.balance.units[u.id].get("economy",false):continue
		if u.side==side:allies.append(u)
		elif sim.visible_to(side,u):enemies.append(u)
	var threatened: bool = false
	var living_front: int=0
	for ally in allies:
		if is_frontline(sim.db.balance.units[ally.id]) and frontline_near_contact(sim,ally,enemies):living_front+=1
	for enemy in enemies:
		if dist(enemy,sim.bases[side])<9:threatened=true
	if uncovered_approach(sim,side,enemies,allies):threatened=true
	# A pair of exposed archers is not a safe formation for technology savings.
	# Experimental multi-contact recovery changed investment too aggressively
	# in paid observations. Keep opt-in diagnostics out of shipping decisions.
	var exposed_backline: bool=sim.config.get("ai_multi_contact_recovery",false) and backline_without_screen(sim,allies,enemies)
	var front_broken: bool=not enemies.is_empty() and (living_front==0 or exposed_backline)
	if sim.config.get("experimental_ai_budget_planner",false) and int(sim.config.get("experimental_ai_budget_planner_side",side))==side:
		var screen: Dictionary=BudgetPlanner.frontline_offer(sim,side)
		BudgetPlanner.turn(sim,side,phase,style,allies,enemies,threatened,front_broken,immediate_economic_threat(sim,side,enemies,float(screen.get("seconds",2))),spawn_camped(sim,side,enemies))
		if sim.time>=float(p.ai_route_at):
			p.ai_route_at=sim.time+8;choose_routes(sim,side,enemies,allies,style);choose_mine(sim,side,enemies,style)
		cast_spells(sim,side,enemies,allies,threatened)
		return
	if front_broken:p.ai_research=""
	var fielding: bool=not paid_opening and not staged_plan and not legacy_deployment_active(sim,side)
	var grant_goal: String=paid_grant_target(sim,side) if fielding else ""
	var grant_ready: bool=grant_goal!="" and paid_grant_formation(sim,side,grant_goal,allies,threatened,front_broken)
	if grant_goal!="":p.ai_research=""
	# Establish the paid mining crew and basic wave before technology savings.
	# A subsequent study must already fund its first recruit; it must not suspend
	# replacements for an unaffordable second investment.
	var paid_formation: bool=planned_combat>=3 and combat>=2 and sim.population(side,true,true)>=3
	if paid_opening and p.research.is_empty() and str(p.get("ai_unit_plan",""))=="" and not threatened and not front_broken and paid_formation and (not p.get("ai_paid_opened",false) or sim.time>=float(p.ai_research_at)):
		var has_screen: bool=allies.any(func(u):return is_frontline(sim.db.balance.units[u.id])) or p.queue.any(func(id):return is_frontline(sim.db.balance.units[id]))
		if has_screen and p.ai_research=="":
			var opening_candidates: Array=[]
			for node in sim.db.technology.nodes:
				if node.faction!=p.faction or p.studied.has(node.id):continue
				if node.grant.begins_with("unit.") and not p.roster.has(node.grant):continue
				if node.requires.all(func(id):return p.studied.has(id)) and (not p.get("ai_paid_opened",false) or funded_research_affordable(sim,side,node)):opening_candidates.append(node)
			if not opening_candidates.is_empty():p.ai_research=choose_paid_research(sim,side,opening_candidates,phase,allies,enemies).id
	if paid_opening and str(p.get("ai_paid_saving_id",""))!=str(p.ai_research):
		p["ai_paid_saving_id"]=str(p.ai_research);p["ai_paid_saving_at"]=sim.time
	var deployment: String=""
	var demand_deployment: bool=sim.config.get("experimental_ai_demand_deployment",false) and int(sim.config.get("experimental_ai_demand_deployment_side",side))==side
	if demand_deployment:
		deployment=resolve_demand_deployment(sim,side,allies,enemies,threatened or front_broken)
		if deployment!="":p.ai_research=""
	var demand_pending: bool=demand_deployment and deployment!=""
	if sim.config.get("experimental_ai_visible_counter_deployment",false) and int(sim.config.get("experimental_ai_visible_counter_deployment_side",side))==side and not threatened and not front_broken:
		deployment=visible_counter_deployment_target(sim,side,allies,enemies)
		if deployment!="":p.ai_research=""
	if sim.config.get("experimental_ai_research_deployment",false) and not threatened and not front_broken:
		deployment=research_deployment_target(sim,side,allies,phase)
		if deployment!="":p.ai_research=""
	var opening_investment: bool=(staged_plan and not p.get("ai_stage_opened",false) and planned_combat>=2 and enemies.is_empty()) or (paid_opening and p.ai_research!="" and planned_combat>=1 and not threatened and not front_broken)
	if threatened:style="counter"
	var desired_workers: int = 5 if style=="economy" else 3
	if not phase.is_empty():desired_workers=int(phase.get("workers",desired_workers))
	if sim.map.definition.mines.size()>=6 and style!="rush":desired_workers=6
	var resource_build: bool = sim.db.factions[p.faction].mana in ["facility","construction"]
	# Prefer one paid advanced role before an optional opening watchpost.
	# Mandatory mana facilities and visible emergency defense retain priority.
	if fielding and desired_workers>=3 and not p.get("ai_grant_first_ordered",false) and grant_goal=="" and p.ai_research=="" and p.research.is_empty() and sim.time>=float(p.ai_research_at) and combat>=2 and sim.population(side,true,true)>=3 and not threatened and not front_broken and (not resource_build or unbuilt_facility_reserve(sim,side)==0):
		var first_offer: Dictionary=first_grant_offer(sim,side,phase,allies,enemies)
		if not first_offer.is_empty():p.ai_research=first_offer.id;p.ai_build_reserve=0.0
	var tower_cost: float=float(sim.db.balance.buildings["building."+p.faction+".tower"].gold)
	var watch_slot: int=-1
	var sequential_plan: bool=sim.config.get("experimental_ai_sequential_deployment",false) and int(sim.config.get("experimental_ai_sequential_deployment_side",side))==side
	var deployment_pending: bool=grant_goal!="" or (sequential_plan and str(p.get("ai_unit_plan",""))!="") or (paid_opening and (p.ai_research!="" or not p.research.is_empty() or str(p.get("ai_unit_plan",""))!=""))
	if (not fielding or p.ai_research=="") and sim.population(side,true,true)>=mini(3,desired_workers) and not demand_pending and not deployment_pending and not (staged_plan and (opening_investment or str(p.get("ai_unit_plan",""))!="")) and not resource_build and style=="counter" and planned_combat>=2 and not threatened and not front_broken and (not paid_opening or sim.population(side,true,true)>=3):watch_slot=watchpost_slot(sim,side)
	var workers: int=sim.population(side,true)
	var worker_cost: float=float(sim.db.balance.units["unit."+p.faction+".worker"].gold)
	var saved_research: float=0
	if str(p.ai_research)!="" and not threatened:saved_research=float(sim.db.tech(p.ai_research).gold)
	# Reserve known investments before an optional miner can consume their cash.
	# A campaign path carries authored intent; generic research still follows
	# the normal opening crew. These helpers neither pay nor reveal anything.
	var required_facility: float=0
	if not demand_pending and not deployment_pending and resource_build and sim.time>12 and combat>=2 and not threatened and not front_broken and (not paid_opening or workers>=3):
		required_facility=unbuilt_facility_reserve(sim,side)
	if grant_goal=="" and required_facility==0 and not phase.is_empty() and p.ai_research=="" and p.research.is_empty() and combat>=2 and not threatened and not front_broken and sim.time>=float(p.ai_research_at):
		var authored: Dictionary=authored_research_offer(sim,side,phase,allies,enemies)
		if not authored.is_empty():
			p.ai_research=authored.id;saved_research=float(authored.gold)
	if paid_opening and p.ai_research!="" and not threatened:
		var grant: String=str(sim.db.tech(p.ai_research).grant)
		if sim.db.balance.units.has(grant):saved_research+=float(sim.db.balance.units[grant].gold)
	var investment_reserve: float=maxf(saved_research,0.0 if deployment_pending or demand_pending else float(p.get("ai_build_reserve",0)))
	investment_reserve=maxf(investment_reserve,required_facility)
	if grant_ready:investment_reserve=maxf(investment_reserve,float(sim.db.balance.units[grant_goal].gold))
	if paid_opening and workers<3 and not threatened:investment_reserve=0
	if deployment!="":investment_reserve=maxf(investment_reserve,float(sim.db.balance.units[deployment].gold))
	var commitment_plan: bool=paid_opening or sequential_plan or (sim.config.get("experimental_ai_deployment_commitment",false) and int(sim.config.get("experimental_ai_deployment_commitment_side",side))==side)
	var funded_plan: bool=commitment_plan or staged_plan or (sim.config.get("experimental_ai_funded_deployment",false) and int(sim.config.get("experimental_ai_funded_deployment_side",side))==side)
	var planned_unit: String=str(p.get("ai_unit_plan","")) if funded_plan else ""
	if planned_unit!="" and ((not sequential_plan and sim.time>float(p.get("ai_unit_plan_until",0))) or not p.roster.has(planned_unit) or p.queue.has(planned_unit) or allies.any(func(u):return u.id==planned_unit)):
		p.ai_unit_plan="";planned_unit=""
	if planned_unit!="":investment_reserve=maxf(investment_reserve,float(sim.db.balance.units[planned_unit].gold))
	if watch_slot>=0:investment_reserve=maxf(investment_reserve,tower_cost)
	var can_expand_workers: bool=workers<2 or (not front_broken and (combat>=2 or (style=="economy" and planned_combat>=2 and enemies.is_empty())))
	if (not opening_investment or workers<2) and p.queue.size()<2 and workers<desired_workers and can_expand_workers and p.gold>=worker_cost and (not threatened or workers==0) and (workers<2 or p.gold-worker_cost>=investment_reserve):
		sim.request(side,"recruit",{"id":"unit."+p.faction+".worker"})
	if sim.time>=float(p.ai_route_at):
		p.ai_route_at=sim.time+8
		choose_routes(sim,side,enemies,allies,style)
		choose_mine(sim,side,enemies,style)
	p["ai_build_reserve"]=0.0
	var building_budget: float = tower_cost if threatened else (float(sim.db.balance.buildings["building."+p.faction+".mana"].gold)+25 if resource_build else 120)
	if watch_slot>=0:p.ai_build_reserve=tower_cost;building_budget=tower_cost
	if not demand_pending and not deployment_pending and resource_build and sim.time>12 and combat>=2 and not threatened and not front_broken and (not paid_opening or workers>=3):
		var owned_facilities: int=0
		for building in sim.buildings:
			if building.side==side and building.hp>0 and building.id.ends_with(".mana"):owned_facilities+=1
		if owned_facilities==0:
			for slot in range(sim.side_sites(side).size()):
				var site: Dictionary=sim.slot_anchor(side,slot)
				if not site.get("types",["tower","mana"]).has("mana") or not sim.visibility.point_visible(side,site):continue
				var occupied: bool=false
				for building in sim.buildings:
					if building.side==side and building.hp>0 and building.slot==slot:occupied=true;break
				if not occupied:p.ai_build_reserve=building_budget;break
	if (grant_goal=="" or threatened) and (not paid_opening or workers>=3 or threatened) and (not demand_pending or threatened) and (not funded_plan or planned_unit=="" or threatened) and (sim.time>12 or watch_slot>=0 or threatened) and p.gold>=building_budget and ((combat>=2 and not front_broken) or threatened) and (p.ai_research=="" or threatened or float(p.ai_build_reserve)>0):
		for slot in range(sim.side_sites(side).size()):
			if watch_slot>=0 and not threatened and slot!=watch_slot:continue
			var occupied: bool = false
			for b in sim.buildings:
				if b.side==side and b.slot==slot and b.hp>0:occupied=true;break
			if occupied:continue
			var site: Dictionary = sim.slot_anchor(side,slot)
			var unsafe: bool = false
			for enemy in enemies:
				if dist(enemy,site)<4:unsafe=true;break
			if unsafe and not threatened:continue
			var tail: String = "mana" if sim.db.factions[p.faction].mana in ["facility","construction"] and not threatened else "tower"
			var allowed: Array = site.get("types",["tower","mana"])
			if not allowed.has(tail):
				if allowed.has("tower"):tail="tower"
				elif allowed.has("mana") and not threatened and (p.mana<85 or style=="economy"):tail="mana"
				else:continue
			if p.gold<float(sim.db.balance.buildings["building."+p.faction+"."+tail].gold)+(0 if threatened or watch_slot>=0 else 25):continue
			if sim.request(side,"build",{"id":"building."+p.faction+"."+tail,"slot":slot}).ok:p.ai_build_reserve=0.0;break
	if float(p.ai_build_reserve)>0:p.ai_research=""
	var safe_investment: bool=grant_goal=="" and planned_unit=="" and deployment=="" and not front_broken and (combat>=2 or opening_investment or (not phase.is_empty() and style=="economy" and combat>=1 and enemies.is_empty()))
	if paid_opening:safe_investment=safe_investment and paid_formation
	if p.research.is_empty() and safe_investment and not threatened and float(p.ai_build_reserve)==0 and (sim.time>=float(p.ai_research_at) or opening_investment):
		var candidates: Array = []
		for node in sim.db.technology.nodes:
			if node.faction!=p.faction or p.studied.has(node.id):continue
			if node.grant.begins_with("unit.") and not p.roster.has(node.grant):continue
			var valid: bool = true
			for req in node.requires:
				if not p.studied.has(req):valid=false
			if valid and research_arrival_ready(sim,side,node,allies) and (staged_research_affordable(sim,side,node) if staged_plan else (not funded_plan or commitment_plan or funded_research_affordable(sim,side,node))) and (not paid_opening or not p.get("ai_paid_opened",false) or funded_research_affordable(sim,side,node)):candidates.append(node)
		if not candidates.is_empty():
			if p.ai_research!="" and not candidates.any(func(node):return node.id==p.ai_research):p.ai_research=""
			if p.ai_research=="":
				# Unlock one of the selected army roles before unrelated late spells.
				# A stable safe front can save a real budget, instead of perpetually
				# replacing its two starting units and starving every research grant.
				p.ai_research=(choose_paid_research(sim,side,candidates,phase,allies,enemies) if paid_opening or fielding else choose_research(sim,side,candidates,phase,allies,enemies)).id
			if p.gold>=float(sim.db.tech(p.ai_research).gold) and (not paid_opening or funded_research_affordable(sim,side,sim.db.tech(p.ai_research))) and screen_budget_ready(sim,side,sim.db.tech(p.ai_research)) and sequential_purchase_ready(sim,side,sim.db.tech(p.ai_research)):
				var selected: Dictionary=sim.db.tech(p.ai_research)
				if sim.request(side,"research",{"id":p.ai_research}).ok:
					if fielding and sim.db.balance.units.has(selected.grant) and not sim.db.balance.units[selected.grant].get("economy",false):
						p["ai_grant_goal"]=selected.grant;grant_goal=str(selected.grant)
						grant_ready=paid_grant_formation(sim,side,grant_goal,allies,threatened,front_broken)
					if paid_opening:p["ai_paid_opened"]=true
					if staged_plan:p["ai_stage_opened"]=true
					if funded_plan and sim.db.balance.units.has(selected.grant):
						p["ai_unit_plan"]=selected.grant;p["ai_unit_plan_until"]=sim.time+float(selected.seconds)+30
						planned_unit=str(selected.grant)
					p.ai_research="";p.ai_research_at=sim.time+18
		else:p.ai_research=""
	if threatened:p.ai_research=""
	var research_formation_recovery: bool=false
	var research_needs_screen: bool=false
	var opening_wait: bool=false
	if paid_opening and p.ai_research!="" and planned_combat==1 and enemies.is_empty() and not threatened and not front_broken and sim.time-float(p.get("ai_paid_saving_at",0))<=12:
		var node: Dictionary=sim.db.tech(p.ai_research)
		if sim.db.balance.units.has(node.grant):
			var shortfall: float=float(node.gold)+float(sim.db.balance.units[node.grant].gold)-float(p.gold)
			# A bounded savings decision, not spendable forecast income. Payment
			# still requires the full cash budget after real workers unload gold.
			opening_wait=shortfall>0 and shortfall<=float(sim.db.balance.economy.worker_cargo)*mini(2,sim.population(side,true,false))
	if sequential_plan and sim.config.get("experimental_ai_sequential_funded_start",false) and p.ai_research!="":
		var grant: String=str(sim.db.tech(p.ai_research).grant)
		if sim.db.balance.units.has(grant) and requires_deployment_group(sim,side,sim.db.balance.units[grant]):
			var study_group: Dictionary=RecruitmentReadiness.deployment_group(sim,side)
			research_formation_recovery=bool(study_group.supported) and study_group.members.is_empty()
			research_needs_screen=research_formation_recovery and int(study_group.front_count)==0
	if p.queue.size()<2 and sim.population(side,false)<limit:
		var best: String = "";var best_score: float = -INF
		var recruitment_scores: Array=[]
		var front: int = 0;var supports: int = 0;var own_counts: Dictionary = {}
		var enemy_fast: int = 0;var enemy_ranged: int = 0
		for ally in allies:
			var def: Dictionary = sim.db.balance.units[ally.id]
			if is_frontline(def) and (not front_broken or frontline_near_contact(sim,ally,enemies)):front+=1
			if def.get("role","") in ["medic","engineer","scribe","summoner","necromancer","illusionist","oracle"]:supports+=1
			own_counts[ally.id]=int(own_counts.get(ally.id,0))+1
		for id in p.queue:
			var queued: Dictionary=sim.db.balance.units[id]
			if queued.get("economy",false):continue
			own_counts[id]=int(own_counts.get(id,0))+1
			if is_frontline(queued):front+=1
			if queued.get("role","") in ["medic","engineer","scribe","summoner","necromancer","illusionist","oracle"]:supports+=1
		for enemy in enemies:
			var def: Dictionary = sim.db.balance.units[enemy.id]
			if float(def.speed)>=1.2:enemy_fast+=1
			if float(def.range)>1.5:enemy_ranged+=1
		var replacement_front: String=""
		var queued_front: bool=false
		for id in p.queue:
			if is_frontline(sim.db.balance.units[id]):queued_front=true
		var planned_needs_group: bool=planned_unit!="" and requires_deployment_group(sim,side,sim.db.balance.units[planned_unit])
		var local_group: Dictionary=RecruitmentReadiness.deployment_group(sim,side) if sequential_plan and planned_needs_group else {}
		var group_supported: bool=bool(local_group.get("supported",false))
		var deployment_needs_screen: bool=commitment_plan and planned_needs_group and (int(local_group.front_count)==0 if group_supported else front==0)
		var deployment_needs_formation: bool=sequential_plan and planned_needs_group and (local_group.members.is_empty() if group_supported else planned_combat<2)
		if (front_broken or deployment_needs_screen or research_needs_screen) and (front==0 or exposed_backline or deployment_needs_screen or research_needs_screen) and not queued_front:
			for id in p.roster:
				if not p.unlocked.has(id) or not is_frontline(sim.db.balance.units[id]):continue
				if replacement_front=="" or float(sim.db.balance.units[id].gold)<float(sim.db.balance.units[replacement_front].gold):replacement_front=id
		for id in p.roster:
			if not p.unlocked.has(id):continue
			if sequential_plan and id==planned_unit and (deployment_needs_screen or deployment_needs_formation):continue
			var def: Dictionary = sim.db.balance.units[id]
			if (threatened or front_broken or planned_combat<2) and float(def.gold)>p.gold:continue
			var score: float = 1.0+sim.ai_rng[side].randf()*.5-int(own_counts.get(id,0))*.3
			if not threatened and phase.get("prefer_units",[]).has(id):score+=2.0
			if is_frontline(def) and front<maxi(1,(planned_combat+1)/3):score+=4 if front_broken else 2
			if def.has("anti_fast_multiplier"):score+=enemy_fast*.35
			if def.has("support_priority"):score+=enemy_ranged*.25
			if def.has("heal_amount") and combat>=3 and supports<2:score+=1.5
			if def.get("role","") in ["medic","engineer","summoner","necromancer","illusionist","oracle"] and supports>=maxi(1,combat/4):score-=4
			if threatened:score+=float(def.hp)/maxf(1,float(def.gold))*.25-float(def.gold)*.006
			if style=="rush":score+=float(def.speed)-float(def.gold)*.008
			if enemies.is_empty() and combat>=4:score+=float(def.get("building_multiplier",1))*.5
			if float(def.gold)>p.gold:score-=1.3
			if sim.config.get("observe_ai_recruitment",false):recruitment_scores.append({"id":id,"score":score,"gold":def.gold,"own_count":int(own_counts.get(id,0))})
			if score>best_score:best=id;best_score=score
		# Do not perpetually buy cheap backliners and make the missing screen
		# unaffordable. Emergency defense can still use any affordable fighter.
		if replacement_front!="" and (not threatened or p.gold>=float(sim.db.balance.units[replacement_front].gold) or spawn_camped(sim,side,enemies) or not immediate_economic_threat(sim,side,enemies,float(sim.db.balance.units[replacement_front].get("production_seconds",2)))):best=replacement_front
		if deployment!="" and replacement_front=="":best=deployment
		if planned_unit!="" and p.unlocked.has(planned_unit) and not deployment_needs_screen and not deployment_needs_formation and (not front_broken or is_frontline(sim.db.balance.units[planned_unit])) and (not threatened or is_frontline(sim.db.balance.units[planned_unit])):best=planned_unit
		if grant_ready:best=grant_goal if p.unlocked.has(grant_goal) else ""
		var counter: String=contact_ranged_offer(sim,side,allies,enemies) if fielding and int(sim.config.get("contact_counter_side",-1)) in [-1,side] else ""
		if counter!="" and float(sim.db.balance.units[counter].gold)<=p.gold:
			best=counter;p.ai_research="";p.ai_build_reserve=0.0
		var deployment_cash: float=p.gold
		var deployment_choice: String=best
		var recruitment_result: Dictionary={}
		if not opening_wait and best!="" and p.gold>=float(sim.db.balance.units[best].gold) and (p.ai_research=="" or threatened or planned_combat<2 or research_formation_recovery) and (threatened or planned_combat<2 or p.gold-float(sim.db.balance.units[best].gold)>=float(p.ai_build_reserve)):
			if planned_unit!="" and best!=planned_unit and not threatened and not front_broken and not deployment_needs_screen and not deployment_needs_formation and p.gold-float(sim.db.balance.units[best].gold)<float(sim.db.balance.units[planned_unit].gold):best=""
			if best!="":
				recruitment_result=sim.request(side,"recruit",{"id":best})
				if fielding and best==grant_goal and recruitment_result.ok:
					p["ai_grant_goal"]="";p["ai_grant_first_ordered"]=true
		if sim.config.get("observe_ai_recruitment",false):
			if not sim.config.has("ai_recruitment_trace"):sim.config["ai_recruitment_trace"]=[]
			sim.config.ai_recruitment_trace.append({"time":sim.time,"side":side,"gold_before":deployment_cash,"gold_after":p.gold,"scores":recruitment_scores,"selected":deployment_choice,"final_choice":best,"request":recruitment_result,"deployment_target":deployment,"research_target":p.ai_research,"build_reserve":p.ai_build_reserve,"front_broken":front_broken,"threatened":threatened,"planned_combat":planned_combat,"queue":p.queue.duplicate(),"unlocked":p.unlocked.duplicate()})
			var trace: Dictionary=sim.config.ai_recruitment_trace.back()
			trace["own_alive_ids"]=allies.map(func(u):return str(u.id))
			trace["visible_enemy_ids"]=enemies.map(func(u):return str(u.id))
			trace["counter_eligible"]=visible_counter_deployment_target(sim,side,allies,enemies)
			trace["grant_goal"]=grant_goal;trace["grant_ready"]=grant_ready
		if sim.config.get("observe_ai_deployment",false) and planned_unit!="":
			if not sim.config.has("ai_deployment_trace"):sim.config["ai_deployment_trace"]=[]
			sim.config.ai_deployment_trace.append({"time":sim.time,"side":side,"target":planned_unit,"gold_before_recruit":deployment_cash,"unlocked":p.unlocked.has(planned_unit),"needs_screen":deployment_needs_screen,"needs_formation":deployment_needs_formation,"front_broken":front_broken,"threatened":threatened,"group":local_group.duplicate(true),"scored_choice":deployment_choice,"final_choice":best,"research_target":p.ai_research,"build_reserve":p.ai_build_reserve,"paid_target_order":p.queue.has(planned_unit),"queue":p.queue.duplicate()})
	cast_spells(sim,side,enemies,allies,threatened)


# Respond to a currently observed ranged engagement with an unlocked weapon
# that can reach that opponent. These queries do not pay or consume RNG.
static func contact_ranged_offer(sim,side: int,allies: Array,enemies: Array) -> String:
	var p: Dictionary=sim.players[side]
	var own: Array=allies.filter(func(u):return u.side==side and u.hp>0 and not sim.db.balance.units[u.id].get("economy",false))
	var visible: Array=enemies.filter(func(u):return u.side!=side and u.hp>0 and sim.visible_to(side,u) and not sim.db.balance.units[u.id].get("economy",false))
	if spawn_camped(sim,side,visible):return ""
	var targets: Array=[]
	for enemy in visible:
		var weapon: Dictionary=sim.db.balance.units[enemy.id]
		if float(weapon.range)<=1.5 or not str(weapon.attack).begins_with("projectile"):continue
		var fighting: bool=own.any(func(u):
			var def: Dictionary=sim.db.balance.units[u.id]
			if not is_frontline(def) or sim.combat_distance(enemy,u,weapon)>float(weapon.range)+.3:return false
			for status in ["bind","stun","root","cold"]:
				if not u.statuses.has(status) or int(u.statuses[status].get("source",-1))!=int(enemy.side):continue
				if status in ["bind","stun"] or sim.combat_distance(u,enemy,def)>float(def.range)+.3:return true
			return false)
		if not fighting:continue
		var covered: bool=own.any(func(u):return str(sim.db.balance.units[u.id].attack).begins_with("projectile") and float(sim.db.balance.units[u.id].range)>=float(weapon.range))
		if not covered:targets.append(enemy)
	var best: String="";var best_cost: float=INF
	for enemy in targets:
		var range_needed: float=float(sim.db.balance.units[enemy.id].range)
		if p.queue.any(func(id):return str(sim.db.balance.units[id].attack).begins_with("projectile") and float(sim.db.balance.units[id].range)>=range_needed):continue
		for id in p.roster:
			if not p.unlocked.has(id):continue
			var weapon: Dictionary=sim.db.balance.units[id]
			if not str(weapon.attack).begins_with("projectile") or float(weapon.range)<range_needed or not weapon.get("manual_recruit",true):continue
			if float(weapon.gold)<best_cost:best=id;best_cost=float(weapon.gold)
	return best

static func unbuilt_facility_reserve(sim,side: int) -> float:
	for building in sim.buildings:
		if building.side==side and building.hp>0 and building.id.ends_with(".mana"):return 0
	for slot in range(sim.side_sites(side).size()):
		var site: Dictionary=sim.slot_anchor(side,slot)
		if not site.get("types",["tower","mana"]).has("mana") or not sim.visibility.point_visible(side,site):continue
		var occupied: bool=false
		for building in sim.buildings:
			if building.side==side and building.hp>0 and building.slot==slot:occupied=true;break
		if not occupied:return float(sim.db.balance.buildings["building."+sim.players[side].faction+".mana"].gold)+25
	return 0

static func authored_research_offer(sim,side: int,phase: Dictionary,allies: Array,enemies: Array) -> Dictionary:
	var p: Dictionary=sim.players[side]
	var candidates: Array=[]
	for node in sim.db.technology.nodes:
		if node.faction!=p.faction or p.studied.has(node.id):continue
		if str(node.grant).begins_with("unit.") and not p.roster.has(node.grant):continue
		if not phase.get("research_path",[]).has(node.id):continue
		if node.requires.all(func(id):return p.studied.has(id)):candidates.append(node)
	return choose_research(sim,side,candidates,phase,allies,enemies) if not candidates.is_empty() else {}

# Archived deployment experiments own their plan; the normal paid pipeline
# must not overwrite a deliberately selected alternative planner.
static func legacy_deployment_active(sim,side: int) -> bool:
	for policy in ["experimental_ai_sequential_deployment","experimental_ai_funded_deployment","experimental_ai_deployment_commitment","experimental_ai_research_deployment","experimental_ai_demand_deployment","experimental_ai_visible_counter_deployment","experimental_ai_research_screen_budget"]:
		if sim.config.get(policy,false) and int(sim.config.get(policy+"_side",side))==side:return true
	return false

static func first_grant_offer(sim,side: int,phase: Dictionary,allies: Array,enemies: Array) -> Dictionary:
	var p: Dictionary=sim.players[side]
	var candidates: Array=[]
	for node in sim.db.technology.nodes:
		if node.faction!=p.faction or p.studied.has(node.id) or not sim.db.balance.units.has(node.grant):continue
		if not p.roster.has(node.grant) or p.unlocked.has(node.grant):continue
		if node.requires.all(func(id):return p.studied.has(id)):candidates.append(node)
	return choose_paid_research(sim,side,candidates,phase,allies,enemies) if not candidates.is_empty() else {}

static func paid_grant_target(sim,side: int) -> String:
	var p: Dictionary=sim.players[side]
	var id: String=str(p.get("ai_grant_goal",""))
	if id=="":return ""
	if not p.roster.has(id) or not sim.db.balance.units.has(id) or p.queue.has(id):
		p["ai_grant_goal"]="";return ""
	return id

static func paid_grant_formation(sim,side: int,id: String,allies: Array,threatened: bool,front_broken: bool) -> bool:
	allies=allies.filter(func(u):return u.side==side and u.hp>0 and not sim.db.balance.units[u.id].get("economy",false))
	var def: Dictionary=sim.db.balance.units[id]
	if threatened or front_broken:
		# An affordable unlocked frontline can itself replace a missing screen;
		# this does not save for an unaffordable order during immediate danger.
		return is_frontline(def) and sim.players[side].unlocked.has(id) and float(sim.players[side].gold)>=float(def.gold)
	if is_frontline(def):return true
	# Offensive ranged roles need a screen; ally-dependent abilities also
	# need a second living fighter. No paper-worker or queued body counts.
	var ally_dependent: bool=def.has("heal_amount") or def.has("repair_building") or def.has("auto_clone_seconds") or (def.has("summons") and def.has("corpse_range"))
	if ally_dependent and allies.size()<2:return false
	return allies.any(func(u):return is_frontline(sim.db.balance.units[u.id]))

# An opt-in paid start window. Selection remains independent of current cash.
# Existing group and cash are observations, not a future survival guarantee.
static func requires_deployment_group(sim,side: int,def: Dictionary) -> bool:
	if is_frontline(def):return false
	if not sim.config.get("experimental_ai_role_deployment",false) or int(sim.config.get("experimental_ai_role_deployment_side",side))!=side or not sim.config.get("experimental_ai_sequential_deployment",false) or int(sim.config.get("experimental_ai_sequential_deployment_side",side))!=side:return true
	# Targeting enemy support is an offensive ability, not ally dependency.
	return def.has("heal_amount") or def.has("repair_building") or def.has("auto_clone_seconds") or (def.has("summons") and def.has("corpse_range"))

static func sequential_purchase_ready(sim,side: int,node: Dictionary) -> bool:
	if not sim.config.get("experimental_ai_sequential_funded_start",false):return true
	if not sim.config.get("experimental_ai_sequential_deployment",false) or int(sim.config.get("experimental_ai_sequential_deployment_side",side))!=side:return true
	var grant: String=str(node.grant)
	if not sim.db.balance.units.has(grant):return true
	var def: Dictionary=sim.db.balance.units[grant]
	if sim.players[side].gold<float(node.gold)+float(def.gold):return false
	if not requires_deployment_group(sim,side,def):return true
	var group: Dictionary=RecruitmentReadiness.deployment_group(sim,side)
	return bool(group.supported) and not group.members.is_empty()

static func research_deployment_target(sim,side: int,allies: Array,phase: Dictionary) -> String:
	var p: Dictionary=sim.players[side]
	var front: bool=allies.any(func(u):return is_frontline(sim.db.balance.units[u.id]))
	if not front:return ""
	for node in sim.db.technology.nodes:
		if node.faction!=p.faction or not p.studied.has(node.id) or not str(node.grant).begins_with("unit.") or node.requires.is_empty():continue
		var id: String=node.grant
		if not p.roster.has(id) or not p.unlocked.has(id) or p.queue.has(id):continue
		if allies.any(func(u):return u.id==id):continue
		if not phase.get("prefer_units",[]).is_empty() and not phase.prefer_units.has(id):continue
		var def: Dictionary=sim.db.balance.units[id]
		if def.get("economy",false):continue
		if def.has("heal_amount") and allies.size()<3:continue
		if def.has("heal_amount") and sim.config.get("experimental_ai_support_arrival",false) and not support_arrival_viable(sim,side,id,allies):continue
		return id
	return ""

# Redeem a completed offensive counter only while its actual visible need exists.
# No saved target after vision loss, no phantom queue formation or free unlocks.
static func visible_counter_deployment_target(sim,side: int,allies: Array,enemies: Array) -> String:
	var p: Dictionary=sim.players[side]
	var own: Array=allies.filter(func(u):return u.side==side and u.hp>0 and not sim.db.balance.units[u.id].get("economy",false))
	if own.size()<2 or not own.any(func(u):return is_frontline(sim.db.balance.units[u.id])):return ""
	var targets: Array=[]
	for enemy in enemies:
		if enemy.side==side or enemy.hp<=0 or not sim.visible_to(side,enemy):continue
		if not sim.db.balance.units[enemy.id].get("economy",false):targets.append(enemy)
	if targets.is_empty():return ""
	for node in sim.db.technology.nodes:
		var id: String=str(node.grant)
		if node.faction!=p.faction or node.requires.is_empty() or not p.studied.has(node.id) or not p.roster.has(id) or not p.unlocked.has(id):continue
		if not sim.db.balance.units.has(id):continue
		var def: Dictionary=sim.db.balance.units[id]
		if not def.get("support_priority",false):continue
		if not targets.any(func(u):return visible_counter_match(def,sim.db.balance.units[u.id])):continue
		if p.queue.has(id) or allies.any(func(u):return u.side==side and u.hp>0 and u.id==id):continue
		return id
	return ""

static func visible_counter_match(def: Dictionary,target: Dictionary) -> bool:
	if target.get("role","") in ["medic","engineer","scribe","necromancer","summoner","illusionist","oracle"]:return true
	# An out-ranging shooter is a different need from the support-damage bonus.
	return str(def.get("attack",""))=="projectile" and str(target.get("attack",""))=="projectile" and float(target.range)>1.5 and float(def.range)>=float(target.range)+1.0

static func research_demand_deployment_target(sim,side: int,allies: Array,enemies: Array) -> String:
	var p: Dictionary=sim.players[side]
	var own: Array=allies.filter(func(u):return u.side==side and u.hp>0 and not sim.db.balance.units[u.id].get("economy",false))
	if own.size()<2 or not own.any(func(u):return is_frontline(sim.db.balance.units[u.id])):return ""
	for node in sim.db.technology.nodes:
		var id: String=str(node.grant)
		if node.faction!=p.faction or node.requires.is_empty() or not p.studied.has(node.id) or not p.roster.has(id) or not p.unlocked.has(id):continue
		if not sim.db.balance.units.has(id) or p.queue.has(id) or own.any(func(u):return u.id==id):continue
		if research_demand_score(sim,side,node,own,enemies)>0 or research_context_score(sim,side,node,own,enemies)>0:return id
	return ""

# Bounded intent from genuinely observed combat, not tracking an unseen actor.
static func resolve_demand_deployment(sim,side: int,allies: Array,enemies: Array,unsafe: bool) -> String:
	var p: Dictionary=sim.players[side]
	var own: Array=allies.filter(func(u):return u.side==side and u.hp>0 and not sim.db.balance.units[u.id].get("economy",false))
	if unsafe or own.size()<2 or not own.any(func(u):return is_frontline(sim.db.balance.units[u.id])):
		p["ai_demand_plan"]="";p["ai_demand_plan_until"]=0.0;return ""
	var fresh: String=research_demand_deployment_target(sim,side,own,enemies)
	if fresh!="":p["ai_demand_plan"]=fresh;p["ai_demand_plan_until"]=sim.time+12.0
	var id: String=str(p.get("ai_demand_plan",""))
	if id!="" and sim.time<=float(p.get("ai_demand_plan_until",0)) and p.roster.has(id) and p.unlocked.has(id) and not p.queue.has(id) and not own.any(func(u):return u.id==id):return id
	p["ai_demand_plan"]="";p["ai_demand_plan_until"]=0.0
	return ""

# Preserve one currently unlocked screen in real cash, not future income.
# This pilot changes the purchase window, without cancelling savings at low HP.
static func screen_budget_ready(sim,side: int,node: Dictionary) -> bool:
	if not sim.config.get("experimental_ai_research_screen_budget",false) or int(sim.config.get("experimental_ai_research_screen_budget_side",side))!=side:return true
	var p: Dictionary=sim.players[side]
	var reserve: float=INF
	for id in p.roster:
		if not p.unlocked.has(id):continue
		var def: Dictionary=sim.db.balance.units[id]
		if is_frontline(def):reserve=minf(reserve,float(def.gold))
	# Fund the first recruit or emergency screen, whichever is more expensive.
	# Existing paid frontline bodies are not charged again as a second order.
	if sim.config.get("experimental_ai_deployment_commitment",false) and int(sim.config.get("experimental_ai_deployment_commitment_side",side))==side and sim.db.balance.units.has(node.grant):
		reserve=maxf(reserve,float(sim.db.balance.units[node.grant].gold))
	return reserve!=INF and p.gold>=float(node.gold)+reserve

# Pay research now with one quarter of its first-unit cost retained in cash.
# Later income must actually arrive; no gold is created or forecast as spendable.
static func staged_research_affordable(sim,side: int,node: Dictionary) -> bool:
	if not sim.db.balance.units.has(node.grant):return funded_research_affordable(sim,side,node)
	return sim.players[side].gold>=float(node.gold)+float(sim.db.balance.units[node.grant].gold)*.25

# Fund the unlock and first real deployment together; never promise future income.
static func funded_research_affordable(sim,side: int,node: Dictionary) -> bool:
	var reserve: float=0
	if sim.db.balance.units.has(node.grant):reserve=float(sim.db.balance.units[node.grant].gold)
	else:
		for id in sim.players[side].roster:
			if not sim.players[side].unlocked.has(id) or not is_frontline(sim.db.balance.units[id]):continue
			var cost: float=float(sim.db.balance.units[id].gold)
			reserve=cost if reserve==0 else minf(reserve,cost)
	return sim.players[side].gold>=float(node.gold)+reserve

# Pilot screening at research purchase time, before gold is irreversibly spent.
static func research_arrival_ready(sim,side: int,node: Dictionary,allies: Array) -> bool:
	if not sim.config.get("experimental_ai_research_arrival",false):return true
	var id: String=str(node.grant)
	if not sim.db.balance.units.has(id) or not sim.db.balance.units[id].has("heal_amount"):return true
	return support_arrival_viable(sim,side,id,allies,float(node.seconds))

# Conservative known-threat forecast, not a promise of survival or free healing.
static func support_arrival_viable(sim,side: int,id: String,allies: Array,extra_wait: float=0.0) -> bool:
	var distance: float=RecruitmentReadiness.front_distance(sim,side)
	if distance<0:return false
	var def: Dictionary=sim.db.balance.units[id]
	var p: Dictionary=sim.players[side]
	var wait: float=maxf(0,extra_wait)+float(def.get("production_seconds",2))
	if not p.queue.is_empty():wait+=RecruitmentReadiness.queued_seconds(sim,side,p.queue.size()-1)
	var arrival: float=wait+maxf(0,distance-float(def.get("heal_radius",0)))/maxf(.001,float(def.speed))
	var known: Array=[]
	for enemy in sim.units:
		if enemy.side!=side and enemy.hp>0 and not sim.db.balance.units[enemy.id].get("economy",false) and sim.visible_to(side,enemy):known.append(enemy)
	for front in allies:
		var front_def: Dictionary=sim.db.balance.units[front.id]
		if front.hp<=0 or not is_frontline(front_def):continue
		var projected_damage: float=0
		for enemy in known:
			var threat: Dictionary=sim.db.balance.units[enemy.id]
			var separation: float=sim.melee_distance(front,enemy)
			if separation==INF:continue
			var contact: float=maxf(0,separation-float(threat.range))/maxf(.001,float(threat.speed)+float(front_def.speed))
			projected_damage+=maxf(0,arrival-contact)*float(threat.damage)/maxf(.1,float(threat.attack_interval))
		if projected_damage<float(front.hp)*.8:return true
	return false

static func is_frontline(def: Dictionary) -> bool:
	return str(def.get("attack","")).begins_with("melee")

static func frontline_near_contact(sim,ally: Dictionary,enemies: Array) -> bool:
	if enemies.is_empty():return true
	for enemy in enemies:
		if sim.melee_distance(ally,enemy)<=8:return true
	return false

static func backline_without_screen(sim,allies: Array,enemies: Array) -> bool:
	for back in allies:
		var def: Dictionary=sim.db.balance.units[back.id]
		if is_frontline(def):continue
		for enemy in enemies:
			if not sim.visible_to(int(back.side),enemy) or sim.melee_distance(back,enemy)>float(def.range)+3:continue
			var protected: bool=false
			for front in allies:
				if not is_frontline(sim.db.balance.units[front.id]) or front.hp<=0:continue
				# The screen must be close to this backliner and lie toward this
				# threat along the road, not merely attend a different engagement.
				var to_back: float=sim.melee_distance(front,back)
				var to_enemy: float=sim.melee_distance(front,enemy)
				if to_back<=6 and to_back+to_enemy<=sim.melee_distance(back,enemy)+.15:protected=true;break
			if not protected:return true
	return false

static func immediate_economic_threat(sim,side: int,enemies: Array,production: float) -> bool:
	# Current sightings only. Do not save for a screen while the economy is
	# already within one production interval of contact.
	var targets: Array=[sim.bases[side]]
	for worker in sim.units:
		if worker.side==side and worker.hp>0 and sim.db.balance.units[worker.id].get("economy",false):targets.append(worker)
	for enemy in enemies:
		var def: Dictionary=sim.db.balance.units[enemy.id]
		for target in targets:
			var path: Dictionary=sim.map.route_to(enemy,sim.physical_anchor(target))
			if not path.is_empty() and float(path.distance)<=float(def.range)+float(def.speed)*production:return true
	return false

static func watchpost_slot(sim,side: int) -> int:
	var id: String="building."+sim.players[side].faction+".tower"
	if not sim.players[side].unlocked.has(id):return -1
	for building in sim.buildings:
		if building.side==side and building.hp>0 and building.id.ends_with(".tower"):return -1
	var forks: Array=sim.map.fork_nodes(side)
	for slot in range(sim.side_sites(side).size()):
		var site: Dictionary=sim.slot_anchor(side,slot)
		if not site.get("types",["tower","mana"]).has("tower"):continue
		var occupied: bool=false
		for building in sim.buildings:
			if building.side==side and building.hp>0 and building.slot==slot:occupied=true;break
		if occupied:continue
		for fork in forks:
			var point: Array=sim.map.nodes[fork.node].position
			if Vector2(site.x,site.y).distance_to(Vector2(point[0],point[1]))<=float(sim.db.balance.buildings[id].range):return slot
	return -1

static func uncovered_approach(sim,side: int,enemies: Array,allies: Array) -> bool:
	# Only current sightings are used. A distant attacking army cannot screen
	# its own base after the enemy has passed it on a different branch.
	for enemy in enemies:
		var enemy_def: Dictionary=sim.db.balance.units[enemy.id]
		var path: Dictionary=sim.map.route_to(enemy,sim.bases[side])
		if path.is_empty():continue
		var remaining: float=maxf(0,float(path.distance)-float(enemy_def.range))
		if remaining/maxf(.1,float(enemy_def.speed))>12:continue
		var screened: bool=false
		for ally in allies:
			var def: Dictionary=sim.db.balance.units[ally.id]
			if ally.hp<=0:continue
			var home: Dictionary=sim.map.route_to(ally,sim.bases[side])
			if home.is_empty():continue
			# Firing briefly at a passing enemy from behind is not an interception.
			# The enemy must meet a homeward defender or already be held in a duel.
			if float(home.distance)<=float(path.distance) or (enemy.target==ally.uid and enemy.windup>0 and sim.combat_distance(ally,enemy,def)<=float(def.range)):
				screened=true;break
		if not screened:return true
	return false

static func campaign_phase(sim,side: int) -> Dictionary:
	# Authored intent only: no opponent resources, hidden actors or free spawns.
	if side!=1:return {}
	var phases: Array=sim.config.get("ai_phases",[])
	var chosen: Dictionary={}
	for phase in phases:
		if sim.time>=float(phase.get("at",0)):chosen=phase
	if not chosen.is_empty():
		var p: Dictionary=sim.players[side]
		if p.get("ai_phase","")!=chosen.id:
			p["ai_phase"]=chosen.id
			p.ai_research="";p.ai_research_at=sim.time;p.ai_route_at=sim.time
	return chosen

static func research_priority(node: Dictionary,phase: Dictionary) -> int:
	if phase.get("prefer_units",[]).has(node.grant):return 3
	if phase.get("research_path",[]).has(node.get("id","")):return 3
	return 2 if str(node.grant).begins_with("unit.") else 1

# Compare the real unlock-plus-recruit investment, not an alphabetical grant.
# Authored campaign priorities retain their eight-point separation. Tactical
# terms use only own bodies, own facilities and currently visible adversaries.
static func choose_paid_research(sim,side: int,candidates: Array,phase: Dictionary,allies: Array,enemies: Array) -> Dictionary:
	var best: Dictionary={};var best_score: float=-INF
	var own: Array=allies.filter(func(u):return u.side==side and u.hp>0)
	var visible: Array=enemies.filter(func(u):return u.side!=side and u.hp>0 and sim.visible_to(side,u))
	var screen_committed: bool=own.any(func(u):return is_frontline(sim.db.balance.units[u.id])) or sim.players[side].queue.any(func(id):return is_frontline(sim.db.balance.units[id]))
	for node in candidates:
		var adjustment: float=research_context_score(sim,side,node,own,visible)+research_demand_score(sim,side,node,own,visible)
		if sim.db.balance.units.has(node.grant):
			var def: Dictionary=sim.db.balance.units[node.grant]
			var investment: float=float(node.gold)+float(def.gold)
			adjustment-=investment/120.0
			if is_frontline(def):adjustment+=.15
			if def.has("heal_amount") and screen_committed:adjustment+=.7
			if def.has("repair_building") and not sim.buildings.any(func(b):return b.side==side and b.hp>0 and b.hp<b.max_hp):adjustment-=2.0
			if def.has("corpse_range") and not sim.corpses.any(func(c):return sim.visibility.point_visible(side,c)):adjustment-=.6
			if def.has("radius") and visible.size()>=3:adjustment+=.6
		var score: float=float(research_priority(node,phase))*8.0+clampf(adjustment,-3.0,4.0)
		if score>best_score:best=node;best_score=score
	return best

# Deterministic, visible-context pilot; never spends resources or consumes RNG.
# Keep authored campaign intent above the bounded tactical adjustment.
static func choose_research(sim,side: int,candidates: Array,phase: Dictionary,allies: Array,enemies: Array) -> Dictionary:
	var pilot: bool=sim.config.get("experimental_ai_context_research",false) and int(sim.config.get("experimental_ai_context_research_side",side))==side
	var demand_pilot: bool=sim.config.get("experimental_ai_demand_research",false) and int(sim.config.get("experimental_ai_demand_research_side",side))==side
	var best: Dictionary={};var best_score: float=-INF
	for node in candidates:
		var score: float=float(research_priority(node,phase))*8.0
		if pilot or demand_pilot:
			var tactical: float=research_context_score(sim,side,node,allies,enemies)
			if demand_pilot:tactical+=research_demand_score(sim,side,node,allies,enemies)
			score+=clampf(tactical,-3.0,4.0)
		if score>best_score:best=node;best_score=score
	return best

# Context without a use is not a counter: bounded priority, never a hard gate.
static func research_demand_score(sim,side: int,node: Dictionary,allies: Array,enemies: Array) -> float:
	if not sim.db.balance.units.has(node.grant):return 0.0
	var def: Dictionary=sim.db.balance.units[node.grant]
	var visible: Array=enemies.filter(func(u):return u.side!=side and u.hp>0 and sim.visible_to(side,u) and not sim.db.balance.units[u.id].get("economy",false))
	var own: Array=allies.filter(func(u):return u.side==side and u.hp>0 and not sim.db.balance.units[u.id].get("economy",false))
	var adjustment: float=0.0
	if def.has("heal_amount") and not own.any(func(u):return float(u.hp)<float(u.max_hp)*.99):adjustment-=.75
	if visible.is_empty():return adjustment
	if def.get("support_priority",false) and not visible.any(func(u):return visible_counter_match(def,sim.db.balance.units[u.id])):adjustment-=1.25
	if is_frontline(def):
		var melee_count: int=0
		for enemy in visible:
			if is_frontline(sim.db.balance.units[enemy.id]):melee_count+=1
		adjustment+=minf(1.8,float(melee_count)*.6)
	# Phase scores are 8 points apart; combined tactical terms cannot cross them.
	return clampf(adjustment,-1.25,1.8)

static func research_context_score(sim,side: int,node: Dictionary,allies: Array,enemies: Array) -> float:
	if not sim.db.balance.units.has(node.grant):return 0.0
	var def: Dictionary=sim.db.balance.units[node.grant]
	var score: float=0.0;var wounded: float=0.0;var duplicates: int=0
	for ally in allies:
		if ally.side!=side or ally.hp<=0 or sim.db.balance.units[ally.id].get("economy",false):continue
		if ally.id==node.grant:duplicates+=1
		wounded+=clampf(1.0-float(ally.hp)/float(ally.max_hp),0.0,1.0)
	for id in sim.players[side].queue:
		if id==node.grant:duplicates+=1
	if def.has("heal_amount"):score+=minf(3.0,wounded*1.5)
	for enemy in enemies:
		# Recheck the boundary so this helper cannot accidentally accept hidden intel.
		if enemy.side==side or enemy.hp<=0 or not sim.visible_to(side,enemy):continue
		var target: Dictionary=sim.db.balance.units[enemy.id]
		if target.get("economy",false):continue
		if def.get("support_priority",false) and target.get("role","") in ["medic","engineer","scribe","necromancer","summoner","illusionist","oracle"]:
			score+=.8
		if def.has("anti_fast_multiplier") and float(target.speed)>=1.2:score+=.5
	# No hard formation/funding gate: those pilots previously suppressed research.
	return clampf(score-float(duplicates)*.75,-3.0,4.0)

static func preferred_research_path(sim,phase: Dictionary) -> Array:
	var pending: Array=[];var path: Array=[]
	for node in sim.db.technology.nodes:
		if phase.get("prefer_units",[]).has(node.grant):pending.append(node.id)
	while not pending.is_empty():
		var id: String=str(pending.pop_back())
		if path.has(id):continue
		path.append(id)
		for prerequisite in sim.db.tech(id).requires:pending.append(prerequisite)
	return path

static func choose_routes(sim,side: int,enemies: Array,allies: Array,style: String):
	for fork in sim.map.fork_nodes(side):
		var node_id: String = fork.node
		var exits: Array = sim.map.outgoing[node_id] if side==0 else sim.map.incoming[node_id]
		var best: String = str(sim.map.choices[side][node_id]);var best_score: float = INF
		for edge_id in exits:
			var e: Dictionary = sim.map.edges[edge_id]
			var score: float = float(e.length)*(.9 if style=="rush" else .25)
			var strength: float = 0;var defense: float = 0
			var fire_risk: float=0
			for enemy in enemies:
				if enemy.edge==edge_id:strength+=enemy.hp
			for ally in allies:
				if ally.edge==edge_id:defense+=ally.hp
			for b in sim.buildings:
				if b.side!=side and b.hp>0 and sim.visible_to(side,b) and b.state=="active" and b.disabled<=0:fire_risk+=tower_crossing_cost(sim,side,b.id,Vector2(b.x,b.y),edge_id,float(b.hp))
			fire_risk+=remembered_structure_pressure(sim,side,edge_id)
			score+=fire_risk*(.5 if style=="rush" else 1)
			# Pressure an exposed route; contest enemies already threatening an owned outer mine.
			if style=="counter":score+=(strength-defense)*.012
			else:score+=strength*.006
			for mine in sim.map.definition.mines:
				if mine.edge==edge_id and int(mine.owner)==side and mine_under_visible_pressure(sim,side,mine,enemies):score-=3
			if side==0 and sim.config.get("win","")=="escort":
				var carrier: Dictionary = sim.actor(sim.escort_uid)
				if not carrier.is_empty() and carrier.edge==edge_id:score-=50
			if side==0 and sim.config.get("win","")=="protect":
				var facility: Dictionary = sim.actor(sim.protected_uid)
				if not facility.is_empty() and facility.edge==edge_id:score-=10
			if edge_id==sim.map.choices[side][node_id]:score-=.25
			if score<best_score:best=edge_id;best_score=score
		if best!=sim.map.choices[side][node_id]:sim.request(side,"route",{"node":node_id,"edge":best})

static func mine_under_visible_pressure(sim,side: int,mine: Dictionary,enemies: Array) -> bool:
	for enemy in enemies:
		if enemy.hp<=0 or enemy.side==side or not sim.visible_to(side,enemy):continue
		var path: Dictionary=sim.map.route_to(sim.physical_anchor(enemy),mine)
		if not path.is_empty() and float(path.distance)<=6:return true
	return false

static func structure_covers_road(sim,id: String,position: Vector2,edge_id: String) -> bool:
	if not sim.db.balance.buildings.has(id) or not sim.map.edges.has(edge_id):return false
	var def: Dictionary=sim.db.balance.buildings[id]
	if float(def.get("damage",0))<=0:return false
	var points: Array=sim.map.edges[edge_id].points
	for i in range(1,points.size()):
		var nearest: Vector2=Geometry2D.get_closest_point_to_segment(position,points[i-1],points[i])
		if position.distance_to(nearest)<=float(def.range):return true
	return false

static func structure_fire_length(sim,id: String,position: Vector2,edge_id: String) -> float:
	if not sim.db.balance.buildings.has(id) or not sim.map.edges.has(edge_id):return 0
	var def: Dictionary=sim.db.balance.buildings[id]
	if float(def.get("damage",0))<=0:return 0
	var radius: float=float(def.range);var total: float=0
	var points: Array=sim.map.edges[edge_id].points
	for i in range(1,points.size()):
		var delta: Vector2=points[i]-points[i-1];var length: float=delta.length()
		if length<=.000001:continue
		var axis: Vector2=delta/length;var offset: Vector2=position-points[i-1]
		var center: float=offset.dot(axis)
		var squared: float=radius*radius-maxf(0,offset.length_squared()-center*center)
		if squared<=0:continue
		var half: float=sqrt(squared)
		total+=maxf(0,minf(length,center+half)-maxf(0,center-half))
	return total

static func structure_exposure_weight(sim,id: String,position: Vector2,edge_id: String) -> float:
	var radius: float=float(sim.db.balance.buildings.get(id,{}).get("range",0))
	return structure_fire_length(sim,id,position,edge_id)/radius if radius>0 else 0

static func remembered_structure_pressure(sim,side: int,edge_id: String) -> float:
	var pressure: float=0
	for uid in sim.visibility.last_seen[side]:
		if sim.visibility.visible_uids[side].has(uid):continue
		var memory: Dictionary=sim.visibility.last_seen[side][uid]
		var age: float=maxf(0,sim.time-float(memory.seen_at))
		if age>=30 or not sim.db.balance.buildings.has(memory.id):continue
		var def: Dictionary=sim.db.balance.buildings[memory.id]
		if not structure_covers_road(sim,memory.id,Vector2(memory.x,memory.y),edge_id):continue
		# Historical position plus public definition, never hidden live HP/state.
		pressure+=tower_crossing_cost(sim,side,memory.id,Vector2(memory.x,memory.y),edge_id)*.5*(1-age/30)
	return pressure

static func tower_crossing_cost(sim,side: int,id: String,position: Vector2,edge_id: String,observed_hp: float=-1) -> float:
	var screen: Dictionary={}
	for unit_id in sim.players[side].roster:
		if not sim.players[side].unlocked.has(unit_id):continue
		var candidate: Dictionary=sim.db.balance.units[unit_id]
		if is_frontline(candidate) and (screen.is_empty() or float(candidate.gold)<float(screen.gold)):screen=candidate
	if screen.is_empty():
		for unit_id in sim.players[side].roster:
			if sim.players[side].unlocked.has(unit_id):screen=sim.db.balance.units[unit_id];break
	if screen.is_empty():return 0
	var tower: Dictionary=sim.db.balance.buildings.get(id,{})
	var exposure: float=structure_fire_length(sim,id,position,edge_id)
	if exposure<=0:return 0
	var seconds: float=exposure/maxf(.1,float(screen.speed))
	if is_frontline(screen):
		var hp: float=float(tower.get("hp",0)) if observed_hp<0 else maxf(0,observed_hp)
		var strike: float=maxf(.1,float(screen.damage)*float(screen.get("building_multiplier",1)))
		# Conservative solo siege estimate: approach plus repeated windup/cooldown.
		seconds+=ceil(hp/strike)*(float(screen.attack_interval)+float(screen.windup))
	var estimated: float=seconds*float(tower.get("damage",0))/maxf(.1,float(tower.get("attack_interval",1)))
	estimated*=float(screen.get("physical_damage_multiplier",1))
	return estimated/maxf(1,float(screen.hp))*4

static func choose_mine(sim,side: int,enemies: Array,style: String):
	var selected: String = "";var best_score: float = INF
	for mine in sim.map.definition.mines:
		if int(mine.owner)!=side or int(mine.resource)==0:continue
		var estimate: Dictionary = sim.mine_income(side,mine)
		var score: float = -float(estimate.marginal_rate)*20.0
		if style=="rush":score+=float(estimate.cycle)*.1
		for enemy in enemies:
			if dist(enemy,mine)<6:score+=18
		if score<best_score:selected=mine.id;best_score=score
	if selected!="" and p_mine(sim,side)!=selected:sim.request(side,"mine_priority",{"mine":selected})

static func p_mine(sim,side: int) -> String:
	return str(sim.players[side].get("preferred_mine",""))

static func cast_spells(sim,side: int,enemies: Array,allies: Array,threatened: bool):
	if enemies.is_empty() and allies.is_empty():return
	var p: Dictionary = sim.players[side]
	var weakest: Dictionary = {};var valuable: Dictionary = {};var cluster: Dictionary = {}
	var cluster_count: int = 0
	for ally in allies:
		if ally.clone or sim.db.balance.units[ally.id].get("summoned",false):continue
		if weakest.is_empty() or float(ally.hp)/float(ally.max_hp)<float(weakest.hp)/float(weakest.max_hp):weakest=ally
	for enemy in enemies:
		if valuable.is_empty() or float(sim.db.balance.units[enemy.id].gold)>float(sim.db.balance.units[valuable.id].gold):valuable=enemy
		var count: int = 0
		for known in enemies:
			if dist(enemy,known)<=2.0:count+=1
		if count>cluster_count:cluster=enemy;cluster_count=count
	# Any visible lethal windup outranks the most expensive enemy.
	for enemy in enemies:
		if dangerous_windup(sim,side,enemy):valuable=enemy;break
	# Price is not a measure of urgency: a cheap visible raider can erase income.
	if not dangerous_windup(sim,side,valuable):
		for enemy in enemies:
			if economic_attack(sim,side,enemy):valuable=enemy;break
	if side==0 and sim.config.get("win","")=="intercept":
		var giant: Dictionary = sim.actor(sim.intercept_uid)
		if not giant.is_empty() and sim.visible_to(side,giant):valuable=giant
	var spell_order: Array=sim.db.spell_ids(p.faction).duplicate()
	var budget: Dictionary=spell_budget(sim,side,enemies,allies)
	var field_aims: Dictionary={}
	if not sim.config.get("experimental_legacy_area_aim",false):
		for id in spell_order:
			var definition: Dictionary=sim.db.balance.spells[id]
			if not definition.has("zone") or id.get_slice(".",2) in ["repair","fury","sacrifice","protect","clone","lightning","bind","convert","root","guardian"]:continue
			field_aims[id]=field_location(sim,side,id,enemies,allies,cluster)
	spell_order.sort_custom(func(a,b):return formation_spell_priority(sim,a,valuable,weakest,maxi(cluster_count,int(field_aims.get(a,{}).get("covered",0))))>formation_spell_priority(sim,b,valuable,weakest,maxi(cluster_count,int(field_aims.get(b,{}).get("covered",0)))))
	for id in spell_order:
		if not p.unlocked.has(id):continue
		var tail: String = id.get_slice(".",2);var target: Dictionary = {};var useful: bool = false
		var d: Dictionary=sim.db.balance.spells[id]
		match tail:
			"repair":target=weakest;useful=not target.is_empty() and target.max_hp-target.hp>=55
			"sacrifice":target=sacrifice_candidate(sim,side,allies,enemies,d);useful=not target.is_empty()
			"protect":target=protection_candidate(sim,allies,enemies,d);useful=not target.is_empty()
			"fury","clone":target=formation_candidate(sim,allies,enemies,tail);useful=not target.is_empty()
			"lightning","bind","convert","root":
				target=valuable
				if tail in ["bind","root"]:
					target={}
					var best: float=-INF
					for enemy in enemies:
						if enemy.statuses.has("bind") or enemy.statuses.has("stun") or (tail=="root" and enemy.statuses.has("root")):continue
						var score: float=float(sim.db.balance.units[enemy.id].gold)+(1000 if dangerous_windup(sim,side,enemy) else 500 if economic_attack(sim,side,enemy) else 300 if enemy.windup>0 else 0)
						if score>best:target=enemy;best=score
				# Honor a dangerous windup when this ability actually stops it.
				# Root only blocks movement; lightning must defeat the attacker.
				var stops_attack: bool=not target.is_empty() and dangerous_windup(sim,side,target) and (tail in ["bind","convert"] or (tail=="lightning" and sim.damage_after_defense(target,float(d.damage),side,false)>=float(target.hp)))
				useful=not target.is_empty() and (stops_attack or threatened or enemies.size()>1 or sim.db.balance.units[target.id].gold>=95 or economic_attack(sim,side,target))
			"guardian":useful=not cluster.is_empty() and (threatened or enemies.size()>2)
			_:useful=int(field_aims[id].get("covered",0))>=2 if field_aims.has(id) else cluster_count>=2
		if not useful:continue
		if not budget.is_empty() and id!=budget.id and float(d.mana)>0 and float(p.mana)-float(d.mana)<float(budget.mana) and not urgent_spell(sim,side,tail,target,enemies):continue
		var location: Dictionary = cluster if target.is_empty() else target
		if target.is_empty() and field_aims.has(id):location=field_aims[id]
		if location.is_empty():continue
		var uid: int = int(target.get("uid",0))
		if sim.spell_error(side,id,location.x,uid,location.y)=="":
			sim.request(side,"cast",{"id":id,"x":location.x,"y":location.y,"target":uid});break

# Count actual field coverage, then protect wounded screens on tied coverage.
# Midpoints are candidates only; the same visibility/terrain/cost rules as a
# human cast still validate them. No hidden enemy can enter this calculation.
static func field_location(sim,side: int,id: String,enemies: Array,allies: Array,fallback: Dictionary) -> Dictionary:
	var d: Dictionary=sim.db.balance.spells[id]
	if not sim.players[side].unlocked.has(id) or sim.players[side].mana<float(d.mana) or float(sim.players[side].cooldowns.get(id,0))>0:return {}
	var radius: float=float(d.get("zone",{}).get("radius",d.get("radius",0)))
	if radius<=0:return fallback
	var known: Array=[];var points: Array=[];var weights: Array=[]
	for enemy in enemies:
		if enemy.hp<=0 or enemy.side==side or not sim.visible_to(side,enemy):continue
		known.append(enemy);points.append(sim.physical_point(enemy))
		var urgency: float=0
		for ally in (allies if sim.config.get("experimental_ai_area_threat_weight",false) else []):
			if ally.side!=side or ally.hp<=0 or not is_frontline(sim.db.balance.units[ally.id]):continue
			var separation: float=sim.melee_distance(ally,enemy)
			if separation<=3:urgency=maxf(urgency,(1-float(ally.hp)/float(ally.max_hp))*(1-separation/3))
		weights.append(1+urgency)
	var candidates: Array=[]
	if known.is_empty():return {}
	if not fallback.is_empty() and known.has(fallback):candidates.append(sim.physical_point(fallback))
	candidates.append_array(points)
	for i in range(points.size()):
		for j in range(i+1,points.size()):
			if points[i].distance_squared_to(points[j])<=4*radius*radius:candidates.append((points[i]+points[j])*.5)
	var chosen: Dictionary={};var best_count: int=-1;var best_weight: float=-INF
	var checked: Dictionary={}
	for candidate in candidates:
		var anchor: Dictionary=sim.map.project(candidate)
		if float(anchor.distance)>2:continue
		var center=Vector2(anchor.x,anchor.y)
		if checked.has(center):continue
		checked[center]=true
		if sim.spell_error(side,id,center.x,0,center.y)!="":continue
		var count: int=0;var weight: float=0
		for i in range(points.size()):
			if center.distance_squared_to(points[i])<=radius*radius+.000001:count+=1;weight+=float(weights[i])
		if count>best_count or (sim.config.get("experimental_ai_area_threat_weight",false) and count==best_count and weight>best_weight+.000001):
			chosen={"x":center.x,"y":center.y,"covered":count};best_count=count;best_weight=weight
		if best_count==points.size():break
	return chosen

static func spell_budget(sim,side: int,enemies: Array,allies: Array) -> Dictionary:
	# Reserve an available formation tool only for a visible approaching wave.
	# The cheapest relevant tool avoids saving indefinitely for every late spell.
	if enemies.size()<2:return {}
	var p: Dictionary=sim.players[side];var chosen: Dictionary={}
	for id in sim.db.spell_ids(p.faction):
		if not p.unlocked.has(id) or float(p.cooldowns.get(id,0))>1.0:continue
		var d: Dictionary=sim.db.balance.spells[id];var relevant: bool=false
		if d.has("zone"):
			var field: Dictionary=d.zone
			if float(field.get("damage",0))>0 or str(field.get("status",""))!="":
				for center in enemies:
					var nearby: int=0
					for enemy in enemies:
						if dist(center,enemy)<=float(field.radius)+2.0:nearby+=1
					if nearby>=2:relevant=true;break
		elif id.ends_with(".clone"):
			relevant=not formation_candidate(sim,allies,enemies,"clone").is_empty()
		if relevant and (chosen.is_empty() or float(d.mana)<float(chosen.mana)):chosen={"id":id,"mana":float(d.mana)}
	return chosen

static func urgent_spell(sim,side: int,tail: String,target: Dictionary,enemies: Array) -> bool:
	if tail=="sacrifice":return true
	if target.is_empty():return false
	if tail in ["repair","protect"]:
		if target.hp<target.max_hp*.25 and engaged(sim,target,enemies,0):return true
		for enemy in enemies:
			if enemy.target==target.uid and enemy.windup>0:
				var amount: float=float(sim.db.balance.units[enemy.id].damage)
				if amount>=34 or amount>=float(target.hp):return true
	if tail in ["bind","root","lightning","convert"]:
		if economic_attack(sim,side,target):return true
		var def: Dictionary=sim.db.balance.units[target.id]
		var victim: Dictionary=sim.actor(int(target.get("target",0)))
		if target.windup>0 and not victim.is_empty() and victim.side==side and (float(def.damage)>=34 or float(def.damage)>=float(victim.hp)):return true
		if sim.combat_distance(target,sim.bases[side],def)<=float(def.range)+.5:return true
	return false

static func spawn_camped(sim,side: int,enemies: Array) -> bool:
	if side==1 and not sim.config.get("enemy_entries",[]).is_empty():return false
	var x: float=float(sim.bases[side].x)+(.65 if side==0 else -.65)
	var origin: Dictionary=sim.map.project(Vector2(x,sim.map.ground_y_at(x)))
	for enemy in enemies:
		if enemy.hp<=0 or enemy.side==side or not sim.visible_to(side,enemy):continue
		var def: Dictionary=sim.db.balance.units[enemy.id]
		if is_frontline(def) and sim.map.melee_distance(origin,sim.physical_anchor(enemy))<=float(def.range)+.25:return true
	return false

static func economic_attack(sim,side: int,enemy: Dictionary) -> bool:
	if enemy.is_empty() or enemy.hp<=0 or int(enemy.side)==side or not sim.visible_to(side,enemy):return false
	var victim: Dictionary=sim.actor(int(enemy.get("target",0)))
	if victim.is_empty() or victim.hp<=0 or victim.side!=side or victim.get("building",false):return false
	if not sim.db.balance.units[victim.id].get("economy",false):return false
	var weapon: Dictionary=sim.db.balance.units[enemy.id]
	return enemy.windup>0 or sim.combat_distance(enemy,victim,weapon)<=float(weapon.range)+.3

static func dangerous_windup(sim,side: int,enemy: Dictionary) -> bool:
	if enemy.is_empty() or enemy.hp<=0 or enemy.windup<=0 or not sim.visible_to(side,enemy):return false
	var victim: Dictionary=sim.actor(int(enemy.get("target",0)))
	if victim.is_empty() or victim.hp<=0 or victim.side!=side:return false
	var damage: float=float(sim.db.balance.units[enemy.id].damage)
	return damage>=34 or damage>=float(victim.hp)

static func engaged(sim,ally: Dictionary,enemies: Array,extra: float=1.0) -> bool:
	var def: Dictionary=sim.db.balance.units[ally.id]
	for enemy in enemies:
		var other: Dictionary=sim.db.balance.units[enemy.id]
		if sim.combat_distance(ally,enemy,def)<=maxf(float(def.range),float(other.range))+extra:return true
	return false

static func formation_candidate(sim,allies: Array,enemies: Array,tail: String) -> Dictionary:
	var chosen: Dictionary={};var best: float=-INF
	for ally in allies:
		var def: Dictionary=sim.db.balance.units[ally.id]
		if ally.hp<=0 or ally.clone or def.get("summoned",false) or ally.get("objective_unit",false):continue
		if tail=="clone" and (def.get("giant",false) or ally.hp<ally.max_hp*.6):continue
		if tail=="fury" and ally.statuses.has("fury"):continue
		# Spend temporary combat buffs at the fight, not while walking in distant fog.
		if not engaged(sim,ally,enemies):continue
		var score: float=float(def.damage)*int(def.get("burst_count",1))/maxf(.1,float(def.attack_interval))*float(ally.hp)/float(ally.max_hp)
		if tail=="fury":
			var group: int=0
			for member in allies:
				if dist(member,ally)<=2.4 and engaged(sim,member,enemies):group+=1
			score+=group*15
		if score>best:best=score;chosen=ally
	return chosen

static func protection_candidate(sim,allies: Array,enemies: Array,d: Dictionary) -> Dictionary:
	var chosen: Dictionary={};var best: float=-INF
	for ally in allies:
		if ally.hp<=0 or ally.statuses.has("protect") or not engaged(sim,ally,enemies,0):continue
		var incoming: float=0
		for enemy in enemies:
			if enemy.target==ally.uid and enemy.windup>0:incoming+=float(sim.db.balance.units[enemy.id].damage)
		var utility: bool=(d.get("cleanse",false) and (ally.statuses.has("bind") or ally.statuses.has("stun") or ally.statuses.has("burn"))) or (d.get("reset_reload",false) and float(ally.get("reload_left",0))>0)
		if incoming<=0 and ally.hp>=ally.max_hp*.6 and not utility:continue
		var score: float=incoming+float(sim.db.balance.units[ally.id].gold)*(1-float(ally.hp)/float(ally.max_hp))+(60 if utility else 0)
		if score>best:best=score;chosen=ally
	return chosen

static func sacrifice_candidate(sim,side: int,allies: Array,enemies: Array,d: Dictionary) -> Dictionary:
	var p: Dictionary=sim.players[side];var chosen: Dictionary={};var best: float=-INF
	if p.mana>=65:return chosen
	var fronts: int=0
	for ally in allies:
		if is_frontline(sim.db.balance.units[ally.id]):fronts+=1
	for ally in allies:
		var def: Dictionary=sim.db.balance.units[ally.id]
		if ally.clone or def.get("summoned",false) or ally.get("objective_unit",false) or ally.statuses.has("protect") or ally.hp>=ally.max_hp*.22:continue
		# Last-stand fighters and the last screen still have an important combat job.
		if def.has("enrage_threshold") or (is_frontline(def) and fronts<=1):continue
		var incoming: float=0
		for enemy in enemies:
			var other: Dictionary=sim.db.balance.units[enemy.id]
			if enemy.target==ally.uid and enemy.windup>0:incoming+=float(other.damage)
		if incoming<float(ally.hp) or not engaged(sim,ally,enemies,0):continue
		var recovered: float=minf(100-p.mana,floorf(ally.hp*.18))
		if recovered<5:continue
		var synergy: float=0
		for member in allies:
			if member.uid==ally.uid or dist(member,ally)>float(d.get("heal_radius",d.get("after_radius",0))):continue
			synergy+=minf(float(d.get("heal_splash",0)),float(member.max_hp)-float(member.hp))
			if d.get("after_status","")=="strength" and engaged(sim,member,enemies):synergy+=10
		if recovered+synergy>best:best=recovered+synergy;chosen=ally
	return chosen

static func formation_spell_priority(sim,id: String,enemy: Dictionary,ally: Dictionary,cluster_count: int) -> float:
	var priority: float=spell_priority(sim,id,enemy,ally)
	var d: Dictionary=sim.db.balance.spells[id]
	# A formation-wide field is worth more than a routine single-target bind.
	# An actual windup interrupt retains priority over damage setup.
	if cluster_count>=2 and d.has("zone") and (str(d.zone.get("status",""))!="" or float(d.zone.get("damage",0))>0):priority=maxf(priority,105)
	return priority

static func spell_priority(sim,id: String,enemy: Dictionary,ally: Dictionary) -> float:
	var tail: String=id.get_slice(".",2)
	var d: Dictionary=sim.db.balance.spells[id]
	var attacking: bool=not enemy.is_empty() and float(enemy.get("windup",0))>0
	if attacking:
		var weapon: Dictionary=sim.db.balance.units[enemy.id]
		var victim: Dictionary=sim.actor(int(enemy.get("target",0)))
		attacking=float(weapon.damage)>=34 or (not victim.is_empty() and float(weapon.damage)>=float(victim.hp))
	var interrupting: bool=tail=="bind" or d.get("interrupt",false) or float(d.get("initial_stun",0))>0 or d.get("after_status","")=="stun"
	if attacking and interrupting:return 120
	if not enemy.is_empty() and economic_attack(sim,1-int(enemy.side),enemy):
		if tail=="lightning" and float(d.get("damage",0))>=float(enemy.hp):return 115
		if enemy.windup>0 and interrupting:return 110
	if tail=="repair":return 100 if not ally.is_empty() and ally.hp<ally.max_hp*.25 else 30
	if tail=="protect":return 95 if attacking else 35
	if tail=="fury":return 85 if attacking else 45
	if tail=="convert":return 80
	if tail in ["lightning","bind","root"]:return 70
	if tail in ["stamp","burst","fire","poison","cold"]:return 60
	if tail=="sacrifice":return 20
	return 40
