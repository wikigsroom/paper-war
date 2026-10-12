extends "res://scripts/battle_sim.gd"
# Test-only policy isolation. Never loaded by production scenes.
func ai_turn(side: int):
	var p: Dictionary=players[side]
	var id: String="spell.bai.clone"
	var held: bool=config.get("experimental_white_hold_clone",false) and p.faction=="bai" and p.unlocked.has(id)
	var original: Array=p.unlocked.duplicate()
	if held:p.unlocked.erase(id)
	super.ai_turn(side)
	if held:
		# Preserve any unlocks acquired by commands during the turn.
		for added in p.unlocked:
			if not original.has(added):original.append(added)
		p.unlocked=original
