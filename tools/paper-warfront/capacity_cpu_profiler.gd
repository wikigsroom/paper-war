extends "res://scripts/battle_sim.gd"
var timings: Dictionary={}
func _init(data):super(data)
func record(label: String,before: int):
	if not timings.has(label):timings[label]={"calls":0,"us":0}
	timings[label].calls+=1;timings[label].us+=Time.get_ticks_usec()-before
func nearest_enemy(u: Dictionary) -> Dictionary:
	var before=Time.get_ticks_usec();var result=super.nearest_enemy(u);record("target_search",before);return result
func area_units(x: float,radius: float,side: int,y: float=NAN) -> Array:
	var before=Time.get_ticks_usec();var result=super.area_units(x,radius,side,y);record("area_search",before);return result
func actor(uid: int) -> Dictionary:
	var before=Time.get_ticks_usec();var result=super.actor(uid);record("actor_lookup",before);return result
func tick_unit(u: Dictionary,dt: float):
	var before=Time.get_ticks_usec();super.tick_unit(u,dt);record("unit_phase_including_queries_and_damage",before)
func tick_worker(u: Dictionary,dt: float):
	var before=Time.get_ticks_usec();super.tick_worker(u,dt);record("workers",before)
func update_ranged_formations():
	var before=Time.get_ticks_usec();super.update_ranged_formations();record("ranged_formation",before)
func marching_step(u: Dictionary,def: Dictionary,enemy: Dictionary,step: float,forward: float) -> float:
	var before=Time.get_ticks_usec();var result=super.marching_step(u,def,enemy,step,forward);record("marching_query",before);return result
func damage_after_defense(target: Dictionary,amount: float,side: int,physical: bool) -> float:
	var before=Time.get_ticks_usec();var result=super.damage_after_defense(target,amount,side,physical);record("defense_including_area_queries",before);return result
func resolve_combat_hits():
	var before=Time.get_ticks_usec();super.resolve_combat_hits();record("hit_resolution",before)
