extends RefCounted
# Transport projection, not a client simulation. Never serialize the authority.
const PUBLIC_ACTOR_FIELDS=["uid","id","side","hp","max_hp","age","cooldown","windup","hurt","anim","anim_t","walk","facing","building","base","state","construction","construction_total","disabled","clone","ttl","cargo","job_time","work_duration"]
static func fields(source: Dictionary,keys: Array) -> Dictionary:
	var result: Dictionary={}
	for key in keys:
		if source.has(key):result[key]=source[key]
	return result
static func visible_events(sim,side: int,events: Array) -> Array:
	var result: Array=[]
	for event in events:
		if event.get("kind","") in ["scouted","economy_alarm"] and int(event.get("observer",-1))!=side:continue
		if not sim.event_visible(side,event):continue
		if not event.has("x") and int(event.get("side",-1))!=side and event.kind not in ["start","result"]:continue
		var item=fields(event,["kind","side","x","y","id","amount","heavy","ranged","fx","radius","facing","winner","observer","mana_reward"])
		for key in ["uid","target_uid"]:
			if not event.has(key):continue
			var actor: Dictionary=sim.actor(int(event[key]))
			if not actor.is_empty() and sim.visible_to(side,actor):item[key]=event[key]
		if item.has("target_uid"):
			var target: Dictionary=sim.actor(int(item.target_uid))
			var point: Vector2=sim.physical_point(target)
			item["target_x"]=point.x;item["target_y"]=point.y
		# Death actors are already removed, but a visible death needs a visual UID.
		if event.kind in ["death","hit","attack"] and not item.has("uid"):item["uid"]=0
		if event.kind=="dash":item["from"]=item.get("x",0);item["from_y"]=item.get("y",0)
		result.append(item)
	return result
static func snapshot(sim,side: int) -> Dictionary:
	if side not in [0,1]:return {}
	var actors: Array=[]
	var permitted: Dictionary={}
	for a in sim.units+sim.buildings+sim.bases:
		if a.hp<=0 or not sim.visible_to(side,a):continue
		permitted[a.uid]=true
	for a in sim.units+sim.buildings+sim.bases:
		if not permitted.has(a.uid):continue
		var item: Dictionary={}
		if int(a.side)==side:
			item=a.duplicate(true)
			# Even an owned actor must not expose its hidden target identifier.
			if item.has("target") and not permitted.has(item.target):item.target=0
		else:
			for key in PUBLIC_ACTOR_FIELDS:
				if a.has(key):item[key]=a[key]
			var anchor: Dictionary=sim.physical_anchor(a)
			for key in ["x","y","edge","s"]:item[key]=anchor[key]
			item["statuses"]={}
			for status in a.get("statuses",{}):item.statuses[status]={}
		actors.append(item)
	var missiles: Array=[]
	for p in sim.projectiles:
		if not sim.location_visible(side,float(p.x),float(p.y)):continue
		# Send observed position, never private destination, damage or ability data.
		var item=fields(p,["uid","side","x","y","style","reflected","render_dx","render_dy"])
		item["source"]=int(p.get("source",0)) if permitted.has(p.get("source",0)) else 0
		item["target"]=int(p.get("target",0)) if permitted.has(p.get("target",0)) else 0
		missiles.append(item)
	var zones: Array=[]
	for z in sim.spell_areas:
		if float(z.left)<=0 or sim.time<float(z.get("start_at",0)) or not sim.location_visible(side,float(z.x),float(z.y)):continue
		zones.append(fields(z,["id","side","x","y","edge","s","radius","left","status","heal","vision","speed"]))
	var bodies: Array=[]
	for c in sim.corpses:
		if sim.location_visible(side,float(c.x),float(c.y)):bodies.append(fields(c,["uid","x","y","edge","s","left"]))
	return {"protocol":1,"side":side,"tick":sim.tick_count,"time":sim.time,"winner":sim.winner,"player":sim.players[side].duplicate(true),"opponent":{"faction":sim.players[1-side].faction},"actors":actors,"projectiles":missiles,"spell_areas":zones,"corpses":bodies,"vision":sim.visibility.current[side].duplicate(true),"explored":sim.visibility.explored[side].duplicate(true),"last_seen":sim.visibility.last_seen[side].duplicate(true)}
