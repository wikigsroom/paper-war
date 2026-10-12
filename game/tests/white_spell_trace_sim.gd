extends "res://scripts/battle_sim.gd"
const AI=preload("res://scripts/tactical_ai.gd")
var spell_trace: Array=[]
var blocked_trace: Array=[]
func cast(side: int,id: String,x: float,target_uid: int,y: float=NAN) -> String:
	var target: Dictionary=actor(target_uid)
	var row: Dictionary={"time":time,"side":side,"id":id,"mana":players[side].mana,"target":target_uid,"target_hp":target.get("hp",0),"target_id":target.get("id",""),"attackers":[],"projectiles":[],"nearby_visible":[],"fire_unlocked":players[side].unlocked.has("spell.bai.fire"),"fire_cooldown":players[side].cooldowns.get("spell.bai.fire",0)}
	if players[side].faction=="bai":
		for enemy in units:
			if enemy.hp<=0 or enemy.side==side or not visible_to(side,enemy):continue
			row.nearby_visible.append({"uid":enemy.uid,"id":enemy.id,"x":enemy.x,"y":enemy.y,"hp":enemy.hp,"target":enemy.target,"windup":enemy.windup,"damage":db.balance.units[enemy.id].damage})
			if not target.is_empty() and enemy.target==target_uid:row.attackers.append({"uid":enemy.uid,"windup":enemy.windup,"damage":db.balance.units[enemy.id].damage})
		for shot in projectiles:
			if shot.target==target_uid:row.projectiles.append(shot.duplicate(true))
	var result: String=super.cast(side,id,x,target_uid,y)
	if result=="" and players[side].faction=="bai":spell_trace.append(row)
	return result
func damage_after_defense(target: Dictionary,amount: float,side: int,physical: bool) -> float:
	if not target.get("building",false) and target.get("statuses",{}).has("protect") and players[target.side].faction=="bai":
		blocked_trace.append({"time":time,"target":target.uid,"target_id":target.id,"raw_amount":amount,"hp":target.hp,"physical":physical})
	return super.damage_after_defense(target,amount,side,physical)
