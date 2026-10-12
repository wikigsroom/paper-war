extends "res://scripts/battle_sim.gd"
const AI=preload("res://scripts/tactical_ai.gd")
var plan_attempted: Array=[false,false]
var plan_paid: Array=[false,false]
var plan_trace: Array=[]
func ai_turn(side: int):
	var p: Dictionary=players[side]
	if config.get("experimental_white_map_plan",false) and not plan_attempted[side]:
		plan_attempted[side]=true
		var path: Dictionary=map.shortest_nodes(str(map.definition.bases[0].node),str(map.definition.bases[1].node))
		var road: float=float(path.get("distance",INF))
		# Public road length and own initial budget only; no hidden enemy lookup.
		if p.faction=="bai" and is_finite(road) and road>=50 and p.gold>=235 and p.research.is_empty() and not p.studied.has("tech.bai.unit.scribe"):
			var result: Dictionary=request(side,"research",{"id":"tech.bai.unit.scribe"})
			plan_paid[side]=result.ok
			plan_trace.append({"side":side,"time":time,"road":road,"research":result,"gold_after":p.gold})
	var original: Array=p.unlocked.duplicate()
	var held: bool=false
	if plan_paid[side] and p.unlocked.has("spell.bai.clone") and p.unlocked.has("spell.bai.fire") and float(p.cooldowns.get("spell.bai.fire",0))<=1 and p.mana<105:
		var enemies: Array=[]
		for enemy in visibility.enemies[side]:
			if not enemy.get("building",false) and enemy.hp>0 and not db.balance.units[enemy.id].get("economy",false):enemies.append(enemy)
		for center in enemies:
			var count: int=0
			for enemy in enemies:
				if AI.dist(center,enemy)<=float(db.balance.spells["spell.bai.fire"].zone.radius)+2:count+=1
			if count>=2:held=true;break
	if held:p.unlocked.erase("spell.bai.clone")
	super.ai_turn(side)
	if held:
		for added in p.unlocked:
			if not original.has(added):original.append(added)
		p.unlocked=original
