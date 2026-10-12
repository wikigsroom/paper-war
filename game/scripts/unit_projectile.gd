extends RefCounted
# Equipment only; character poses are complete drawn frames.
static func projectile(def: Dictionary,id: String="") -> String:
	if def.has("projectile_style"):return str(def.projectile_style)
	if def.get("building",false) or id.begins_with("building."):return "bolt"
	match str(def.get("role","")):
		"archer":return "arrow"
		"sniper","repeater":return "bolt"
		"javelin":return "spear"
		"artillery":return "cannon"
		"mortar":return "mortar"
		"poisoner":return "needle"
		"burner":return "fire"
		"chain":return "chain"
		"drummer":return "sound"
		"engineer":return "gear"
		"medic":return "leaf"
		"necromancer":return "soul"
		"oracle":return "orb"
		"scribe":return "ink"
		"summoner":return "paper"
		"illusionist":return "fan"
		"caravan":return "seal"
	return "bolt"
