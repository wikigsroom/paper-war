extends RefCounted
# Opt-in macro policy. Savings are a claim on existing treasury, never income
# created by the planner. Production, research and buildings use UI commands.
const SAVINGS_SHARE: float=.35

static func frontline(def: Dictionary) -> bool:
	return str(def.get("attack","")).begins_with("melee")

static func frontline_offer(sim,side: int) -> Dictionary:
	var best: Dictionary={}
	for id in sim.players[side].roster:
		var def: Dictionary=sim.db.balance.units[id]
		if not sim.players[side].unlocked.has(id) or not frontline(def):continue
		if best.is_empty() or float(def.gold)<float(best.gold):
			best={"id":id,"gold":float(def.gold),"seconds":float(def.get("production_seconds",2))}
	return best

static func needs_front_reserve(army: Dictionary) -> bool:
	# One costly contact body may first receive three affordable shooters.
	# Beyond that, continued cheap purchases would starve its replacement fee.
	return int(army.front)==0 or int(army.back)>=maxi(1,int(army.front)*3)

static func counts(sim,side: int) -> Dictionary:
	var result: Dictionary={"front":0,"back":0,"ids":{},"living_front":0,"living":0}
	for u in sim.units:
		if u.side!=side or u.hp<=0 or sim.db.balance.units[u.id].get("economy",false):continue
		result.living+=1
		if frontline(sim.db.balance.units[u.id]):result.living_front+=1
		result.ids[u.id]=int(result.ids.get(u.id,0))+1
	for id in sim.players[side].queue:
		if not sim.db.balance.units[id].get("economy",false):result.ids[id]=int(result.ids.get(id,0))+1
	for id in result.ids:
		if frontline(sim.db.balance.units[id]):result.front+=int(result.ids[id])
		else:result.back+=int(result.ids[id])
	return result

static func value(sim,side: int,id: String,allies: Array,enemies: Array) -> float:
	var def: Dictionary=sim.db.balance.units[id]
	var rate: float=float(def.damage)*float(def.get("burst_count",1))/maxf(.1,float(def.attack_interval))
	var score: float=rate/maxf(1,float(def.gold))*15+float(def.hp)/maxf(1,float(def.gold))*.1
	if float(def.range)>1.5:score+=minf(.6,(float(def.range)-3)*.15)
	if def.has("radius"):score+=1.1 if enemies.size()>=2 or allies.size()>=3 else .4
	if def.has("heal_amount"):
		var wounded: int=0
		for u in allies:
			if u.hp<float(u.max_hp)*.85:wounded+=1
		score+=float(def.heal_amount)/maxf(.1,float(def.heal_interval))/maxf(1,float(def.gold))*15
		score+=minf(1.6,wounded*.8) if allies.size()>=3 else -2.0
	if def.has("repair_building"):
		var damaged: bool=sim.buildings.any(func(b):return b.side==side and b.hp>0 and b.hp<b.max_hp)
		score+=1.2 if damaged else -2.0
	if def.has("corpse_range"):
		var corpses: bool=sim.corpses.any(func(c):return sim.visibility.point_visible(side,c))
		score+=2.0 if corpses and allies.size()>=3 else -1.2
	if def.has("worker_guard_radius"):score-=.7
	if def.has("workshop_bonus"):
		score+=.5 if sim.buildings.any(func(b):return b.side==side and b.hp>0) else -.7
	if def.has("lifesteal"):score+=.5
	if def.has("root_seconds") or def.has("stun_seconds") or def.has("on_hit_status"):score+=.45
	if def.has("anti_fast_multiplier") and enemies.any(func(u):return float(sim.db.balance.units[u.id].speed)>=1.2):score+=.7
	if def.has("support_priority") and enemies.any(func(u):return sim.db.balance.units[u.id].get("role","") in ["medic","engineer","scribe","necromancer","summoner","illusionist","oracle"]):score+=1.0
	return score

static func study(sim,side: int,allies: Array,enemies: Array,phase: Dictionary) -> Dictionary:
	var p: Dictionary=sim.players[side]
	var best: Dictionary={};var best_score: float=-INF
	for node in sim.db.technology.nodes:
		if node.faction!=p.faction or p.studied.has(node.id) or not node.requires.all(func(id):return p.studied.has(id)):continue
		var score: float=0
		if sim.db.balance.units.has(node.grant):
			if not p.roster.has(node.grant):continue
			var def: Dictionary=sim.db.balance.units[node.grant]
			var investment: float=float(node.gold)+float(def.gold)
			# Do not bank the opening economy for a huge first siege investment.
			if investment>260 and not p.get("ai_budget_deployed",false):continue
			score=10+value(sim,side,node.grant,allies,enemies)-investment/240.0
		else:
			score=6.0
			if str(node.grant).begins_with("upgrade.") and p.mana<40:score+=2.0
		if phase.get("prefer_units",[]).has(node.grant) or phase.get("research_path",[]).has(node.id):score+=20
		if score>best_score:best=node;best_score=score
	return best

static func fighter(sim,side: int,army: Dictionary,budget: float,allies: Array,enemies: Array,phase: Dictionary,urgent: bool) -> String:
	var p: Dictionary=sim.players[side]
	# Fund early ranged output before making a costly second contact body a
	# hard savings gate. Once that screen has three shooters, safe turns wait
	# for its next front; urgent defence and ranged-only rosters retain fallbacks.
	var want_front: bool=int(army.front)==0 or (int(army.back)>0 and int(army.front)<maxi(2,(int(army.front)+int(army.back)+1)/3))
	var hold_for_front: bool=needs_front_reserve(army) and not urgent and not frontline_offer(sim,side).is_empty()
	var best: String="";var best_score: float=-INF
	for id in p.roster:
		var def: Dictionary=sim.db.balance.units[id]
		if not p.unlocked.has(id) or float(def.gold)>budget:continue
		if hold_for_front and not frontline(def):continue
		var same: int=int(army.ids.get(id,0))
		if (def.has("heal_amount") or def.has("corpse_range") or def.has("repair_building") or def.has("auto_clone_seconds")) and same>=1:continue
		var score: float=value(sim,side,id,allies,enemies)-same*.35
		if frontline(def)==want_front:score+=6.0
		if urgent and frontline(def):score+=2.0
		if phase.get("prefer_units",[]).has(id):score+=3.0
		if score>best_score:best=id;best_score=score
	return best

static func facility_slot(sim,side: int,tail: String) -> int:
	for slot in range(sim.side_sites(side).size()):
		var site: Dictionary=sim.slot_anchor(side,slot)
		if not site.get("types",["tower","mana"]).has(tail) or not sim.visibility.point_visible(side,site):continue
		if not sim.buildings.any(func(b):return b.side==side and b.hp>0 and b.slot==slot):return slot
	return -1

static func turn(sim,side: int,phase: Dictionary,style: String,allies: Array,enemies: Array,threatened: bool,front_broken: bool,immediate_danger: bool=false,outlet_camped: bool=false):
	var p: Dictionary=sim.players[side]
	var army: Dictionary=counts(sim,side)
	var planned: int=int(army.front)+int(army.back)
	var worker: String="unit."+str(p.faction)+".worker"
	var workers: int=sim.population(side,true,true)
	var desired_workers: int=clampi(int(phase.get("workers",3 if style=="rush" else 5)),2,6)
	desired_workers=mini(desired_workers,int(sim.config.get("worker_limit",sim.db.balance.simulation.max_workers_per_side)))
	var desired_army: int=mini(int(sim.config.get("ai_army_limit",60)) if side==1 else 60,5 if style=="rush" else 8 if style=="economy" else 6)
	var opening_army: int=mini(4,desired_army)
	# Pay for the initial four-body wave first. After its first investment has
	# been seeded, one casualty need not repeatedly consume all study savings.
	var minimum_army: int=mini(3,opening_army) if p.get("ai_budget_seeded",false) else opening_army
	var worker_cost: float=float(sim.db.balance.units[worker].gold)
	var urgent: bool=threatened or front_broken
	var delivered: float=float(sim.stats[side].gold_delivered)
	var income: float=maxf(0,delivered-float(p.get("ai_budget_delivered",delivered)))
	p["ai_budget_delivered"]=delivered
	var bank: float=minf(float(p.get("ai_budget_bank",0)),float(p.gold))
	var target: String=str(p.get("ai_budget_study",""))
	var pending: String=str(p.get("ai_budget_unit",""))
	if pending!="" and (p.queue.has(pending) or allies.any(func(u):return u.id==pending)):
		pending="";p["ai_budget_deployed"]=true;bank=0
	# A changed contact condition is not a cash transaction. Keep the study and
	# unused reserve; emergency commands below can spend only real treasury.
	var front_offer: Dictionary=frontline_offer(sim,side)
	var min_front_cost: float=float(front_offer.get("gold",0))
	var front_reserve: float=min_front_cost if not urgent and needs_front_reserve(army) and not front_offer.is_empty() else 0.0
	# A depleted mining crew may use reserved cash; this does not forgive fees.
	# Costly armies may expand after three safe fighters. Junction armies
	# first complete four: their forward wave also drives crossing bonuses,
	# and inserting miners can displace the opening's second shooter.
	# Research still requires the full opening and its paid mining crew.
	var growth_fighters: int=opening_army if sim.db.factions[p.faction].mana=="junction" else mini(3,opening_army)
	var expansion_ready: bool=planned>=2 if workers<3 else planned>=growth_fighters
	if p.queue.size()<2 and workers<desired_workers and (workers<2 or (expansion_ready and not urgent)) and p.gold>=worker_cost and not (urgent and int(army.front)==0 and not front_offer.is_empty() and p.gold>=min_front_cost):
		if workers<3 or p.gold-worker_cost>=maxf(bank,front_reserve):
			if sim.request(side,"recruit",{"id":worker}).ok:workers+=1;bank=minf(bank,float(p.gold))
	var resource_build: bool=sim.db.factions[p.faction].mana in ["facility","construction"]
	var mana_id: String="building."+str(p.faction)+".mana"
	var mana_needed: bool=resource_build and p.unlocked.has(mana_id) and not sim.buildings.any(func(b):return b.side==side and b.hp>0 and b.id==mana_id)
	var build_reserve: float=0
	if mana_needed and workers>=mini(3,desired_workers) and planned>=opening_army and not urgent and pending=="":
		var slot: int=facility_slot(sim,side,"mana")
		if slot>=0:
			build_reserve=float(sim.db.balance.buildings[mana_id].gold)
			if p.gold>=build_reserve+min_front_cost and sim.request(side,"build",{"id":mana_id,"slot":slot}).ok:
				mana_needed=false;build_reserve=0;bank=minf(bank,float(p.gold))
	var foundation: bool=workers>=desired_workers and planned>=minimum_army and (int(army.living_front)>0 or front_offer.is_empty()) and not urgent and not mana_needed and front_reserve==0
	if target!="" and p.studied.has(target):target="";bank=0
	if foundation and pending=="" and p.research.is_empty() and target=="":
		var node: Dictionary=study(sim,side,allies,enemies,phase)
		target=str(node.get("id",""))
	if target!="" and pending=="" and p.research.is_empty():
		var node: Dictionary=sim.db.tech(target)
		var unit_cost: float=float(sim.db.balance.units[node.grant].gold) if sim.db.balance.units.has(node.grant) else 0.0
		var total: float=float(node.gold)+unit_cost
		if not p.get("ai_budget_seeded",false):
			p["ai_budget_seeded"]=true;bank=minf(total,float(p.gold))
		else:bank=minf(total,minf(float(p.gold),bank+income*SAVINGS_SHARE))
		# Once the paid crew and target formation are complete, otherwise idle
		# cash may finish the investment. Keep one replacement contact body in
		# free treasury rather than waiting solely for another income fraction.
		if foundation and planned>=desired_army:
			bank=maxf(bank,minf(total,maxf(0,float(p.gold)-min_front_cost)))
		# A defended formation pays only the command due now. Requiring the
		# later recruit fee as well keeps a casualty-heavy treasury permanently
		# below the combined gate. Mining can continue through the real study
		# timer; the first recruit still has to fund its own normal-price order.
		if foundation and bank>=float(node.gold) and p.gold>=float(node.gold):
			if sim.request(side,"research",{"id":target}).ok:
				bank=minf(unit_cost,maxf(0,bank-float(node.gold)))
				pending=str(node.grant) if unit_cost>0 else "";target=""
	# During study, save existing cash toward the first unit; its price has not
	# been paid or guaranteed. In an emergency, a missing contact body may use
	# that cash, and the resulting shortfall must be earned again.
	if pending!="":
		var def: Dictionary=sim.db.balance.units[pending]
		if p.unlocked.has(pending) and p.gold>=float(def.gold) and (frontline(def) or (int(army.front)>0 and planned>=mini(3,opening_army))) and p.queue.size()<2:
			if sim.request(side,"recruit",{"id":pending}).ok:
				pending="";bank=0;p["ai_budget_deployed"]=true;planned+=1
		else:bank=minf(float(def.gold),float(p.gold))
	army=counts(sim,side);planned=int(army.front)+int(army.back)
	# The study requires this minimum formation. If casualties remove it,
	# reserving its entire replacement budget would make both the study and
	# the replacement wait on each other. Restore paid bodies from actual
	# treasury, retaining the target and the unspent part of its reserve.
	var rebuilding: bool=planned<minimum_army or (not urgent and needs_front_reserve(army) and not front_offer.is_empty())
	if p.queue.size()<2 and (planned<desired_army or urgent):
		var available: float=maxf(0,float(p.gold)-bank-build_reserve)
		var id: String=""
		if int(army.front)==0 and not front_offer.is_empty():
			# Do not keep buying a cheap archer every time it becomes affordable
			# while a missing expensive contact body can never reach its fee.
			if p.gold>=min_front_cost:id=str(front_offer.id)
			elif urgent and immediate_danger and not outlet_camped:id=fighter(sim,side,army,float(p.gold),allies,enemies,phase,true)
		else:id=fighter(sim,side,army,float(p.gold) if urgent or rebuilding else available,allies,enemies,phase,urgent)
		if id!="" and sim.request(side,"recruit",{"id":id}).ok:bank=minf(bank,float(p.gold))
	# Nonurgent watchposts use genuine surplus after the crew, army and study.
	if planned>=desired_army and not urgent and pending=="" and workers>=desired_workers:
		var tower_id: String="building."+str(p.faction)+".tower"
		var tower_cost: float=float(sim.db.balance.buildings[tower_id].gold)
		if p.unlocked.has(tower_id) and p.gold-bank>=tower_cost+min_front_cost:
			var slot: int=facility_slot(sim,side,"tower")
			if slot>=0:sim.request(side,"build",{"id":tower_id,"slot":slot})
	p["ai_budget_bank"]=minf(bank,float(p.gold));p["ai_budget_study"]=target;p["ai_budget_unit"]=pending
	if sim.config.get("observe_ai_budget",false):
		if not sim.config.has("ai_budget_trace"):sim.config["ai_budget_trace"]=[]
		sim.config.ai_budget_trace.append({"time":sim.time,"side":side,"gold":p.gold,"bank":p.ai_budget_bank,"study":target,"pending":pending,"workers":workers,"planned":planned,"opening_army":opening_army,"minimum_army":minimum_army,"rebuilding":rebuilding,"urgent":urgent,"delivered":delivered})
