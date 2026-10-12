extends RefCounted
# Ability contracts belong to combat definitions, not art IDs or arbitrary name checks.

static func nearby(sim, u: Dictionary, side: int, radius: float) -> Array:
	var p: Vector2=sim.physical_point(u)
	return sim.area_units(p.x,radius,side,p.y)

static func tick(sim,u: Dictionary,def: Dictionary,dt: float):
	u.ability_clock-=dt
	if def.get("regeneration",0)>0 and u.hurt<=0 and not u.statuses.has("poison") and not u.statuses.has("burn"):
		var restored: float = minf(float(u.max_hp)-float(u.hp),float(def.regeneration)*dt)
		u.hp+=restored
		if restored>0 and not u.clone and not def.get("summoned",false) and sim.db.factions[sim.players[u.side].faction].mana=="growth":
			var p: Dictionary = sim.players[u.side]
			if sim.time-float(p.get("growth_at",-1))>=1:p["growth_at"]=sim.time;p["growth_used"]=0.0
			var reward: float = minf(maxf(0,1.5-float(p.get("growth_used",0))),restored*.1)
			sim.gain_mana(u.side,reward);p["growth_used"]=float(p.get("growth_used",0))+reward
	if u.statuses.has("silence") or u.ability_clock>0: return
	u.ability_clock=.5
	if def.has("erase_projectiles_radius") and u.summon_cd<=0:
		var erased: int=0
		for p in sim.projectiles.duplicate():
			if p.side==u.side:continue
			if Vector2(p.x,p.y).distance_to(sim.physical_point(u))<=float(def.erase_projectiles_radius):
				sim.projectiles.erase(p);erased+=1
		if erased>0:
			u.summon_cd=float(def.erase_interval);u["visual_special"]=.6
			sim.event("unit_special",{"uid":u.uid,"target_uid":u.uid,"side":u.side,"x":u.x,"y":u.y,"fx":"erase"})
	for key in ["aura_speed","aura_damage"]:
		if def.has(key):
			for ally in nearby(sim,u,u.side,float(def.get("aura_radius",3))):
				if sim.db.balance.units[ally.id].get("economy",false): continue
				sim.set_status(ally,"haste" if key=="aura_speed" else "strength",.7,float(def[key]),u.side)
	if def.has("heal_amount"):
		u.summon_cd=maxf(-100,u.summon_cd)
		if u.summon_cd<=0:
			var selected: Dictionary = {}; var priority: float = 0
			for ally in nearby(sim,u,u.side,float(def.heal_radius)):
				if ally.uid==u.uid or ally.hp<=0 or sim.db.balance.units[ally.id].get("economy",false): continue
				var urgency: float=1-float(ally.hp)/float(ally.max_hp)
				# A cleanser must remove damage-over-time before it prevents the
				# living-paper recovery loop, including a newly afflicted full body.
				if def.get("cleanse_on_heal",false) and (ally.statuses.has("poison") or ally.statuses.has("burn")):urgency+=1
				if urgency>priority:selected=ally;priority=urgency
			if not selected.is_empty():
				var restored: float = minf(float(def.heal_amount),float(selected.max_hp)-float(selected.hp))
				selected.hp+=restored;sim.stats[u.side].healed+=int(restored)
				if def.get("cleanse_on_heal",false):
					selected.statuses.erase("poison");selected.statuses.erase("burn")
				u["visual_special"]=.6
				sim.event("unit_special",{"uid":u.uid,"target_uid":selected.uid,"side":u.side,"x":u.x,"y":u.y,"fx":"heal"})
				if restored>0:sim.event("heal",{"uid":selected.uid,"source_uid":u.uid,"side":u.side,"x":selected.x,"y":selected.y,"amount":restored})
				u.summon_cd=float(def.heal_interval)
	if def.has("repair_building") and u.summon_cd<=0:
		for b in sim.buildings:
			if b.side!=u.side or b.hp<=0 or b.hp>=b.max_hp or Vector2(b.x,b.y).distance_to(Vector2(u.x,u.y))>float(def.repair_radius): continue
			var restored: float = minf(float(def.repair_building),float(b.max_hp)-float(b.hp))
			b.hp+=restored;sim.stats[u.side].healed+=int(restored)
			sim.event("heal",{"uid":b.uid,"source_uid":u.uid,"side":u.side,"x":b.x,"y":b.y,"amount":restored})
			u["visual_special"]=.6;sim.event("unit_special",{"uid":u.uid,"target_uid":b.uid,"side":u.side,"x":u.x,"y":u.y,"fx":"repair"})
			u.summon_cd=float(def.repair_interval);break
	if u.clone or def.get("summoned",false):return
	if not def.has("auto_guardian_seconds") and not def.has("auto_clone_seconds"):return
	if sim.population(u.side)>=60:return
	if def.has("auto_guardian_seconds") and u.summon_cd<=0:
		var count: int = 0
		for other in sim.units:
			if other.hp>0 and other.owner==u.uid: count+=1
		if count<2:
			var guard = sim.spawn("unit.deng.guardian",u.side,u.x,false,u.uid)
			sim.map.apply_anchor(guard,sim.map.anchor(u.edge,float(u.s)))
			guard.ttl=float(def.auto_guardian_seconds);sim.stats[u.side].summons+=1
			u["visual_special"]=.6;sim.event("unit_special",{"uid":u.uid,"target_uid":guard.uid,"side":u.side,"x":u.x,"y":u.y,"fx":"summon"})
			u.summon_cd=float(def.ability_interval)
	if def.has("auto_clone_seconds") and u.summon_cd<=0:
		for ally in nearby(sim,u,u.side,3.0):
			var other: Dictionary = sim.db.balance.units[ally.id]
			if ally.uid==u.uid or ally.clone or other.get("economy",false) or other.get("giant",false) or other.get("summoned",false): continue
			var count: int = 0
			for copy in sim.units:
				if copy.hp>0 and copy.owner==u.uid: count+=1
			if count>=1: break
			var copy = sim.spawn(ally.id,u.side,ally.x,true,u.uid)
			sim.map.apply_anchor(copy,sim.map.anchor(ally.edge,float(ally.s)))
			copy.hp=ally.hp;copy.max_hp=ally.max_hp;copy.ttl=float(def.auto_clone_seconds)
			sim.stats[u.side].summons+=1;u.summon_cd=float(def.ability_interval)
			u["visual_special"]=.6;sim.event("unit_special",{"uid":u.uid,"target_uid":copy.uid,"side":u.side,"x":u.x,"y":u.y,"fx":"clone"});break

static func attack_amount(sim,u: Dictionary,target: Dictionary,def: Dictionary) -> float:
	var amount: float = float(def.damage)*(1+float(u.statuses.get("strength",{}).get("potency",0)))
	if def.has("charge_distance") and float(u.get("charge_walk",0))>=float(def.charge_distance):amount*=float(def.charge_multiplier)
	if def.has("treasury_damage_per_100"):amount*=1+minf(float(def.treasury_bonus_cap),float(sim.players[u.side].gold)/100*float(def.treasury_damage_per_100))
	if def.has("controlled_multiplier") and not target.get("building",false) and (target.statuses.has("cold") or target.statuses.has("root") or target.statuses.has("stun") or target.statuses.has("bind")):amount*=float(def.controlled_multiplier)
	if def.has("enrage_threshold") and float(u.hp)/float(u.max_hp)<=float(def.enrage_threshold): amount*=float(def.enrage_multiplier)
	if def.has("execute_threshold") and float(target.hp)/float(target.max_hp)<=float(def.execute_threshold): amount*=float(def.execute_multiplier)
	if def.has("workshop_bonus"):
		for b in sim.buildings:
			if b.side==u.side and b.state=="active" and b.disabled<=0 and sim.melee_distance(u,b)<=4:
				amount*=1+float(def.workshop_bonus);break
	if target.get("building",false):
		if target.get("state","")=="constructing":amount*=float(def.get("construction_multiplier",1))
	else:
		var other: Dictionary = sim.db.balance.units[target.id]
		if other.get("economy",false): amount*=float(def.get("worker_multiplier",1))
		if float(other.speed)>=1.2: amount*=float(def.get("anti_fast_multiplier",1))
		if other.get("role","") in ["medic","engineer","scribe","necromancer","summoner","illusionist","oracle"]:amount*=float(def.get("support_multiplier",1))
		if def.get("role","")=="duelist" and nearby(sim,u,1-u.side,1.8).size()==1:amount*=float(def.get("duel_multiplier",1))
	return amount

static func on_hit(sim,source: Dictionary,target: Dictionary,def: Dictionary,actual_damage: float,context: Dictionary={}):
	if actual_damage<=0 or source.is_empty() or target.is_empty() or source.side==target.side or source.get("building",false):return
	# An already lethal impact cannot revive its attacker through a queued hit.
	var can_heal: bool=source.hp>0 and not source.get("death_processed",false) and not source.get("death_queued",false)
	if can_heal and float(def.get("lifesteal",0))>0:
		source.hp=minf(source.max_hp,source.hp+actual_damage*float(def.lifesteal))
	if can_heal and def.has("lifesteal_on_burning") and not target.get("building",false) and target.statuses.has("burn"):
		source.hp=minf(source.max_hp,source.hp+actual_damage*float(def.lifesteal_on_burning))
	if target.hp<=0:
		if context.get("kill_credit",true) and not target.get("building",false) and not target.clone and not sim.db.balance.units[target.id].get("summoned",false) and not sim.db.balance.units[target.id].get("economy",false):
			sim.players[source.side].gold+=int(def.get("bounty_gold",0))
			sim.gain_mana(source.side,float(def.get("kill_mana",0)))
		return
	if context.get("silenced",source.statuses.has("silence")):return
	if target.get("building",false):
		if def.has("disable_facility_seconds") and not target.get("base",false):
			target.disabled=maxf(float(target.disabled),float(def.disable_facility_seconds))
			if sim.visibility!=null:sim.visibility.mark_dirty()
			sim.event("facility_disabled",{"uid":target.uid,"side":source.side,"x":target.x,"seconds":def.disable_facility_seconds})
		return
	var controlled: bool = false
	if def.has("armor_break_seconds"):sim.set_status(target,"exposed",float(def.armor_break_seconds),float(def.armor_break_amount),source.side,int(source.uid))
	if def.has("third_hit_stun") and int(context.get("attack_serial",source.get("attack_serial",0)))%3==0:
		sim.set_status(target,"stun",float(def.third_hit_stun),0,source.side,int(source.uid));sim.interrupt(target,source.side);controlled=true
	for pair in [["root_after_hits","root_seconds_on_combo","root"],["freeze_after_hits","freeze_seconds","stun"]]:
		if not def.has(pair[0]):continue
		var key: String=pair[0]+":"+str(source.uid)
		var stacks: Dictionary=target.get("combo_stacks",{})
		stacks[key]=int(stacks.get(key,0))+1;target["combo_stacks"]=stacks
		if int(stacks[key])>=int(def[pair[0]]):
			stacks[key]=0;sim.set_status(target,pair[2],float(def[pair[1]]),0,source.side,int(source.uid));controlled=true
			if pair[2]=="stun":sim.interrupt(target,source.side)
	if def.has("pull_distance") and target.edge==source.edge and not target.statuses.has("protect"):
		var delta: float=clampf(float(source.s)-float(target.s),-float(def.pull_distance),float(def.pull_distance))
		sim.map.apply_anchor(target,sim.map.anchor(target.edge,float(target.s)+delta))
		if sim.visibility!=null:sim.visibility.mark_dirty()
	if def.has("on_hit_slow"):sim.set_status(target,"cold",float(def.on_hit_slow),0,int(source.side),int(source.uid));controlled=true
	if def.has("root_seconds"):sim.set_status(target,"root",float(def.root_seconds),0,int(source.side),int(source.uid));controlled=true
	if def.has("stun_seconds"):sim.set_status(target,"stun",float(def.stun_seconds),0,int(source.side),int(source.uid));sim.interrupt(target,source.side);controlled=true
	if def.has("silence_seconds"):sim.set_status(target,"silence",float(def.silence_seconds),0,int(source.side),int(source.uid))
	if def.has("burn_damage_per_second"):sim.set_status(target,"burn",3,float(def.burn_damage_per_second),source.side,int(source.uid))
	if controlled and source.control_clock<=0 and def.has("control_mana"):
		sim.gain_mana(source.side,float(def.control_mana));source.control_clock=1
	if def.has("chain_targets"):
		var candidates: Array = nearby(sim,target,1-int(source.side),float(def.chain_radius))
		var count: int = 0
		for enemy in candidates:
			if enemy.uid==target.uid or enemy.hp<=0:continue
			var point: Vector2=sim.physical_point(enemy);var origin: Vector2=sim.physical_point(target)
			sim.damage(enemy,actual_damage*.6,source.side,false,int(source.uid))
			sim.event("chain",{"uid":enemy.uid,"side":source.side,"x":point.x,"y":point.y,"from":origin.x,"from_y":origin.y})
			count+=1
			if count>=int(def.chain_targets)-1:break

static func node_reached(sim,u: Dictionary,def: Dictionary,node_id: String):
	if u.clone or def.get("summoned",false):return
	if def.has("junction_haste_seconds"):
		sim.set_status(u,"haste",float(def.junction_haste_seconds),.35,u.side)
	if sim.db.factions[sim.players[u.side].faction].mana=="junction":sim.gain_mana(u.side,2)

static func cargo_bonus(sim,worker: Dictionary) -> int:
	var best: int = 0
	for ally in nearby(sim,worker,worker.side,3.3):
		var def: Dictionary = sim.db.balance.units[ally.id]
		if sim.melee_distance(worker,ally)<=float(def.get("aura_radius",0)):
			best=maxi(best,int(def.get("delivery_aura",0)))
	return best

static func on_death(sim,u: Dictionary,def: Dictionary):
	if def.has("heal_death_burst") and not u.clone:
		for ally in nearby(sim,u,u.side,float(def.heal_death_radius)):
			if ally.uid==u.uid or ally.hp<=0:continue
			var amount: float=minf(float(def.heal_death_burst),float(ally.max_hp)-float(ally.hp))
			ally.hp+=amount;sim.stats[u.side].healed+=int(amount)
			if amount>0:sim.event("heal",{"uid":ally.uid,"source_uid":u.uid,"side":u.side,"x":ally.x,"y":ally.y,"amount":amount})
	if def.has("death_burst_damage") and not u.clone:
		sim.area_damage(u.x,float(def.death_burst_radius),float(def.death_burst_damage),u.side,false,u.y,int(u.uid))
		sim.event("impact",{"x":u.x,"y":u.y,"side":u.side,"fx":"bone_burst" if u.id=="unit.mo.giant" else "fire","radius":def.death_burst_radius})

static func before_attack(sim,u: Dictionary,target: Dictionary,def: Dictionary):
	if not sim.hostile_target(target,int(u.side),int(u.uid)) or u.statuses.has("silence"):return
	if def.get("dispel_on_attack",false) and not target.get("building",false):
		for status in ["protect","strength","fury","haste"]:target.statuses.erase(status)

static func after_attack(u: Dictionary,def: Dictionary):
	u["charge_walk"]=0.0
	if def.has("reload_every") and int(u.get("attack_serial",0))%int(def.reload_every)==0:u["reload_pending"]=true
	if def.has("skirmish_retreat"):u["retreat_left"]=float(def.retreat_seconds)

static func defense(sim,u: Dictionary,def: Dictionary,amount: float,physical: bool) -> float:
	if physical and u.statuses.has("exposed"):amount*=1+float(u.statuses.exposed.potency)
	if not physical:
		if def.has("spell_absorb_interval") and float(u.get("absorb_at",-1))<=float(sim.time) and not u.statuses.has("silence"):
			u["absorb_at"]=float(sim.time)+float(def.spell_absorb_interval);u["visual_special"]=.6
			sim.event("blocked",{"uid":u.uid,"x":u.x,"side":u.side});return 0
		var ward: float=0
		for ally in nearby(sim,u,u.side,3.5):
			var other: Dictionary=sim.db.balance.units[ally.id]
			if other.has("ward_aura") and not ally.statuses.has("silence") and sim.melee_distance(u,ally)<=float(other.aura_radius):ward=maxf(ward,float(other.ward_aura))
		amount*=1-ward
	return amount

static func on_damaged(sim,u: Dictionary,def: Dictionary,source_uid: int,physical: bool):
	if not physical or not def.has("retaliation_damage") or u.hp<=0 or u.statuses.has("silence") or float(u.get("retaliate_at",-1))>float(sim.time):return
	var source: Dictionary=sim.actor(source_uid)
	if source.is_empty() or source.get("building",false) or source.side==u.side or sim.melee_distance(u,source)>1.6:return
	var attacker: Dictionary=sim.db.balance.units[source.id]
	if not str(attacker.attack).begins_with("melee"):return
	u["retaliate_at"]=float(sim.time)+float(def.retaliation_interval)
	sim.damage(source,float(def.retaliation_damage),int(u.side),true,int(u.uid))

static func poison_hit(sim,target: Dictionary,p: Dictionary):
	if float(p.poison)<=0 or target.get("building",false) or target.hp<=0:return
	var potency: float=float(p.poison)
	if p.ability.has("poison_stack_limit") and target.statuses.has("poison"):
		var old: Dictionary=target.statuses.poison
		if old.source==p.side and int(old.get("source_uid",0))==int(p.source):potency=minf(potency*float(p.ability.poison_stack_limit),float(old.potency)+potency)
	sim.set_status(target,"poison",3.0,potency,int(p.side),int(p.source))
