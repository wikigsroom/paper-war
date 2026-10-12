extends RefCounted
# Data-authored faction spell extensions use the same ownership and path APIs as combat.
static func zone(sim,side: int,id: String,x: float,y: float,data: Dictionary,definition: Dictionary):
	var field: Dictionary=data.duplicate(true)
	field.merge(sim.map.project(Vector2(x,y)),true)
	field.merge({"id":id,"side":side,"left":float(data.duration),"pulse":0.0,"start_at":sim.time+float(definition.get("delay",0)),"secondary":definition.get("zone_secondary",""),"knockback":float(definition.get("zone_knockback",0))},true)
	sim.spell_areas.append(field)
	if float(field.get("vision",0))>0 and sim.visibility!=null:sim.visibility.mark_dirty()

static func override_cast(sim,side: int,id: String,x: float,y: float,target: Dictionary,definition: Dictionary) -> bool:
	if definition.has("zone"):
		zone(sim,side,id,x,y,definition.zone,definition)
		if definition.has("initial_stun"):
			for victim in sim.area_units(x,float(definition.zone.radius),1-side,y):
				sim.set_status(victim,"stun",float(definition.initial_stun),0,side);sim.interrupt(victim,side)
		return true
	if definition.get("fury_mode","")=="guard":
		for ally in sim.area_units(x,2.4,side,y):
			if not sim.db.balance.units[ally.id].get("economy",false):sim.set_status(ally,"protect",.8,0,side)
		return true
	return false

static func reset_reload(u: Dictionary):
	u["reload_left"]=0.0;u["reload_pending"]=false
	u.cooldown=minf(float(u.cooldown),.08)

static func after_cast(sim,side: int,id: String,x: float,y: float,target: Dictionary,d: Dictionary):
	var tail: String=id.get_slice(".",2)
	var friendly: bool=tail in ["repair","fury","sacrifice","protect","clone","convert","guardian"]
	var affected: Array=sim.area_units(x,float(d.after_radius),side if friendly else 1-side,y) if d.has("after_radius") else ([] if target.is_empty() else [target])
	if d.has("after_status"):
		for u in affected:
			if u.hp<=0 or sim.db.balance.units[u.id].get("economy",false):continue
			sim.set_status(u,str(d.after_status),float(d.get("after_duration",2)),float(d.get("after_potency",0)),side)
	if not target.is_empty() and target.hp>0:
		if d.get("cleanse",false):
			for key in ["cold","bind","root","stun","silence","poison","burn","exposed"]:target.statuses.erase(key)
		if d.get("reset_reload",false):reset_reload(target)
		if d.get("interrupt",false):sim.interrupt(target,side)
		if d.has("conversion_heal"):heal(sim,target,float(d.conversion_heal),side)
	if d.has("chain_damage"):
		var count: int=0
		for victim in sim.area_units(x,float(d.chain_radius),1-side,y):
			if victim.uid==target.uid or not sim.visible_to(side,victim):continue
			sim.damage(victim,float(d.chain_damage),side,false);count+=1
			if count>=2:break
	if d.get("reset_group_reload",false):
		for ally in sim.area_units(x,2.4,side,y):reset_reload(ally)
	if d.has("heal_splash"):
		for ally in sim.area_units(x,float(d.heal_radius),side,y):
			if not target.is_empty() and ally.uid==target.uid:continue
			heal(sim,ally,float(d.heal_splash),side)
	if d.has("knockback"):
		var victims: Array=sim.area_units(x,float(d.get("after_radius",.5)),1-side,y) if target.is_empty() else [target]
		for victim in victims:
			if sim.hostile_target(victim,side):
				sim.map.advance(victim,float(d.knockback),side);sim.interrupt(victim,side)
				if sim.visibility!=null:sim.visibility.mark_dirty()
	if d.has("corpse_burst"):
		var count: int=0
		for corpse in sim.corpses.duplicate():
			if Vector2(corpse.x,corpse.y).distance_to(Vector2(x,y))<=float(d.radius):
				sim.corpses.erase(corpse);count+=1
		if count>0:sim.area_damage(x,float(d.radius),minf(72,count*float(d.corpse_burst)),side,false,y)
	if d.has("after_zone"):zone(sim,side,id,x,y,d.after_zone,{})

static func heal(sim,u: Dictionary,amount: float,side: int):
	if u.hp<=0 or u.side!=side:return
	var restored: float=minf(u.max_hp-u.hp,amount)
	if restored<=0:return
	u.hp+=restored;sim.stats[side].healed+=restored
	sim.event("heal",{"x":u.x,"y":u.y,"uid":u.uid,"amount":restored,"side":side})

static func tick_zones(sim,dt: float):
	for field in sim.spell_areas.duplicate():
		if sim.time<float(field.get("start_at",0)):continue
		field.left-=dt;field.pulse-=dt
		if field.left<=0:
			sim.spell_areas.erase(field)
			if float(field.get("vision",0))>0 and sim.visibility!=null:sim.visibility.mark_dirty()
			continue
		if float(field.get("speed",0))>0:
			sim.map.advance(field,float(field.speed)*dt,int(field.side))
			if float(field.get("vision",0))>0 and sim.visibility!=null:sim.visibility.mark_dirty()
		if field.pulse>0:continue
		field.pulse+=field.period
		for victim in sim.area_units(field.x,field.radius,1-int(field.side),field.y):
			if str(field.status)!="":sim.set_status(victim,field.status,1.0,field.potency,int(field.side))
			if str(field.get("secondary",""))!="":sim.set_status(victim,field.secondary,.65,0,int(field.side))
			if float(field.get("knockback",0))>0:
				sim.map.advance(victim,float(field.knockback),int(field.side))
				if sim.visibility!=null:sim.visibility.mark_dirty()
		if float(field.get("damage",0))>0:sim.area_damage(field.x,field.radius,float(field.damage),int(field.side),false,field.y)
		if float(field.get("heal",0))>0:
			for ally in sim.area_units(field.x,field.radius,int(field.side),field.y):heal(sim,ally,float(field.heal),int(field.side))
