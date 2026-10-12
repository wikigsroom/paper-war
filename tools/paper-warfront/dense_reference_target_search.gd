extends "res://scripts/battle_sim.gd"
func _init(data):super(data)
func nearest_enemy(u: Dictionary) -> Dictionary:
	var best={}; var distance=10000.0
	var def = db.balance.buildings[u.id] if u.get("building",false) else db.balance.units[u.id]
	var anchor: Dictionary=physical_anchor(u)
	var origin: Vector2=Vector2(anchor.x,anchor.y)
	var melee: bool=str(def.get("attack","projectile")).begins_with("melee")
	for e in visibility.enemies[int(u.side)]:
		if e.side==u.side or e.hp<=0:continue
		var destination: Dictionary=physical_anchor(e)
		var d: float=map.melee_distance(anchor,destination) if melee else origin.distance_to(Vector2(destination.x,destination.y))
		var score: float = d
		if def.get("support_priority",false) and not u.get("building",false) and not e.get("building",false) and d<=float(def.range):
			if db.balance.units[e.id].get("role","") in ["medic","engineer","scribe","necromancer","summoner","illusionist","oracle"]:score*=.35
		if score<distance:best=e;distance=score
	return best

