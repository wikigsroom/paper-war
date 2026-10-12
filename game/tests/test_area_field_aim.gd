extends SceneTree
const Data=preload("res://scripts/data_store.gd")
const Simulation=preload("res://scripts/battle_sim.gd")
const AI=preload("res://scripts/tactical_ai.gd")
var checks: int=0
var failures: Array=[]
var timings: Array=[]
func check(ok: bool,note: String):
	checks+=1
	if not ok:failures.append(note)
func _initialize():call_deferred("run")
func run():
	for side in [0,1]:
		var s=Simulation.new(Data.new())
		s.start({"map":"map.01.01","faction":"mu","enemy":"mu"});s.ai_enabled=[false,false]
		var sign: float=1 if side==0 else -1
		var front=s.spawn("unit.mu.guard",side,s.bases[side].x+15*sign);front.speed_override=0;front.hp=150
		var a=s.spawn("unit.mu.guard",1-side,front.x+2*sign);a.speed_override=0
		var b=s.spawn("unit.mu.guard",1-side,front.x+5.4*sign);b.speed_override=0
		s.visibility.refresh()
		check(s.visible_to(side,a) and s.visible_to(side,b),"Both targets are actually visible")
		var radius: float=2.1
		check(s.physical_point(a).distance_to(s.physical_point(b))>radius,"An enemy-centered field misses the other body")
		var before: String=JSON.stringify(s.players[side])+JSON.stringify(s.units)
		var point: Dictionary=AI.field_location(s,side,"spell.mu.poison",[a,b],[front],a)
		var center=Vector2(point.x,point.y)
		check(center.distance_to(s.physical_point(a))<=radius and center.distance_to(s.physical_point(b))<=radius,"Legal intermediate field covers both spaced enemies")
		check(JSON.stringify(s.players[side])+JSON.stringify(s.units)==before,"Aim query has no simulation or economic side effects")
		var hidden=s.spawn("unit.mu.guard",1-side,s.bases[1-side].x);s.visibility.refresh()
		check(not s.visible_to(side,hidden),"Hidden fixture remains beyond actual vision")
		check(AI.field_location(s,side,"spell.mu.poison",[a,b,hidden],[front],a)==point,"Injected hidden body cannot affect targeting")
		hidden.hp=1
		check(AI.field_location(s,side,"spell.mu.poison",[a,b,hidden],[front],a)==point,"Hidden health cannot affect targeting")
		check(AI.field_location(s,side,"spell.mu.poison",[hidden],[front],hidden).is_empty(),"Hidden fallback cannot create a targeting location")
		AI.cast_spells(s,side,[a,b],[front],false)
		check(s.players[side].mana==0 and s.stats[side].spell_counts.get("spell.mu.poison",0)==1 and s.spell_areas.size()==1,"Actual AI recognizes intermediate two-body coverage and pays full 40 mana")
		for i in range(31):s.tick(1.0/60.0)
		check(a.statuses.has("poison") and b.statuses.has("poison") and a.hp<a.max_hp and b.hp<b.max_hp,"Actual persistent field damages both targets")
		check(AI.field_location(s,side,"spell.mu.poison",[a,b],[front],a).is_empty(),"Unavailable mana or cooldown prevents speculative targeting")
		s.start({"map":"map.01.01","faction":"mu","enemy":"mu"});s.ai_enabled=[false,false]
		front=s.spawn("unit.mu.guard",side,s.bases[side].x+15*sign)
		var crowd: Array=[]
		for i in range(50):crowd.append(s.spawn("unit.mu.guard",1-side,front.x+(1+i*.05)*sign))
		s.visibility.refresh()
		var started: int=Time.get_ticks_usec()
		point=AI.field_location(s,side,"spell.mu.poison",crowd,[front],crowd[0])
		timings.append(float(Time.get_ticks_usec()-started)/1000)
		var covered: int=0
		for u in crowd:
			if Vector2(point.x,point.y).distance_to(s.physical_point(u))<=radius:covered+=1
		check(covered==50,"Dense fifty-body field retains full coverage")
		s.start({"map":"map.01.04","faction":"mu","enemy":"mu"});s.ai_enabled=[false,false]
		a=s.spawn("unit.mu.guard",1-side,18);s.map.apply_anchor(a,s.map.anchor("ground.2",4))
		b=s.spawn("unit.mu.guard",1-side,18);s.map.apply_anchor(b,s.map.project(Vector2(18,-2.4)))
		var ground_scout=s.spawn("unit.mu.guard",side,18);s.map.apply_anchor(ground_scout,s.map.anchor("ground.2",4))
		var bridge_scout=s.spawn("unit.mu.guard",side,18);s.map.apply_anchor(bridge_scout,s.map.project(Vector2(18,-2.4)))
		s.visibility.refresh()
		point=AI.field_location(s,side,"spell.mu.poison",[a,b],[ground_scout,bridge_scout],a)
		check(not point.is_empty() and float(s.map.project(Vector2(point.x,point.y)).distance)<.001,"Two-road aim evaluates projected paper location, not midair midpoint")
		var accepted: bool=s.request(side,"cast",{"id":"spell.mu.poison","x":point.x,"y":point.y,"target":0}).ok
		var field: Dictionary=s.spell_areas[0]
		check(accepted and Vector2(field.x,field.y).distance_to(Vector2(point.x,point.y))<.001 and s.area_units(field.x,radius,1-side,field.y).size()==1,"Actual anchored field agrees with projected coverage across bridge and ground")
	print("AREA_FIELD_AIM: ",checks," checks; failures=",failures," dense_query_ms=",timings)
	quit(0 if failures.is_empty() else 1)
