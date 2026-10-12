extends "res://scripts/battle_sim.gd"
var timings: Dictionary={}
func _init(data):super(data)
func record(label: String,start: int):
	if not timings.has(label):timings[label]={"calls":0,"us":0}
	timings[label].calls+=1;timings[label].us+=Time.get_ticks_usec()-start
func nearest_enemy(u: Dictionary) -> Dictionary:
	var t=Time.get_ticks_usec();var result=super.nearest_enemy(u);record("target_search",t);return result
func area_units(x: float,radius: float,side: int,y: float=NAN) -> Array:
	var t=Time.get_ticks_usec();var result=super.area_units(x,radius,side,y);record("area_search",t);return result
func tick_unit(u: Dictionary,dt: float):
	var t=Time.get_ticks_usec();super.tick_unit(u,dt);record("unit_phase_including_searches",t)
func tick_worker(u: Dictionary,dt: float):
	var t=Time.get_ticks_usec();super.tick_worker(u,dt);record("workers",t)
func update_ranged_formations():
	var t=Time.get_ticks_usec();super.update_ranged_formations();record("ranged_formation",t)
func movement_anchor(u: Dictionary) -> Dictionary:
	var t=Time.get_ticks_usec();var result=super.movement_anchor(u);record("movement_snapshot",t);return result
func resolve_combat_hits():
	var t=Time.get_ticks_usec();super.resolve_combat_hits();record("hit_resolution",t)
