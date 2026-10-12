extends SceneTree
const Data=preload("res://scripts/data_store.gd")
const Simulation=preload("res://scripts/battle_sim.gd")
const AI=preload("res://scripts/tactical_ai.gd")
var checks: int=0
var failures: Array=[]
func verify(ok: bool,note: String):
	checks+=1
	if not ok:failures.append(note)
func _initialize():call_deferred("run")
func run():
	var db=Data.new();var s=Simulation.new(db);s.start({"faction":"mu","enemy":"mo","map":"map.01.04"});s.time=20
	var p: String="ground.2"
	verify(AI.remembered_structure_pressure(s,0,p)==0,"unseen structures add no risk")
	s.visibility.last_seen[0][999]={"id":"building.mo.tower","x":22.0,"y":0.0,"seen_at":20.0}
	var fresh: float=AI.remembered_structure_pressure(s,0,p)
	verify(fresh>0,"observed tower contributes historical risk without a live actor")
	s.time=35
	verify(is_equal_approx(AI.remembered_structure_pressure(s,0,p),fresh*.5),"memory confidence decays")
	s.time=50
	verify(AI.remembered_structure_pressure(s,0,p)==0,"old memory no longer forces route avoidance")
	s.time=20;s.visibility.visible_uids[0][999]=true
	verify(AI.remembered_structure_pressure(s,0,p)==0,"visible tower is not counted twice")
	verify(AI.structure_covers_road(s,"building.mo.tower",Vector2(30,0),"bridge"),"merge tower threatens the bridge endpoint")
	verify(AI.structure_covers_road(s,"building.mo.tower",Vector2(14,0),"ground.2"),"fork tower threatens road start")
	verify(not AI.structure_covers_road(s,"building.mo.tower",Vector2(22,9),"bridge"),"horizontal alignment does not reveal cross-height fire coverage")
	verify(not AI.structure_covers_road(s,"building.mo.mana",Vector2(22,0),"ground.2"),"nonattacking facility does not contribute fire risk")
	verify(is_equal_approx(AI.structure_fire_length(s,"building.mo.tower",Vector2(22,0),"ground.2"),8.6),"interior flat road has exact diameter exposure")
	verify(is_equal_approx(AI.structure_fire_length(s,"building.mo.tower",Vector2(30,0),"ground.2"),4.3),"endpoint road has exact radius exposure")
	verify(AI.structure_fire_length(s,"building.mo.tower",Vector2(22,9),"bridge")==0,"out-of-range road has zero exposure")
	verify(is_equal_approx(AI.structure_exposure_weight(s,"building.mo.tower",Vector2(22,0),"ground.2"),2),"longer exposure carries larger route risk")
	var mine: Dictionary=s.map.anchor("ground.2",8);mine["owner"]=0
	verify(not AI.mine_under_visible_pressure(s,0,mine,[]),"historical tower does not masquerade as a mine raider")
	var enemy=s.spawn("unit.mo.blade",1,22)
	s.visibility.visible_uids[0][enemy.uid]=true
	verify(AI.mine_under_visible_pressure(s,0,mine,[enemy]),"currently visible nearby raider raises mine priority")
	s.visibility.visible_uids[0].erase(enemy.uid)
	verify(not AI.mine_under_visible_pressure(s,0,mine,[enemy]),"hidden raider cannot trigger mine priority")
	var cost: float=AI.tower_crossing_cost(s,0,"building.mo.tower",Vector2(22,0),"ground.2")
	var original_speed: float=db.balance.units["unit.mu.guard"].speed
	db.balance.units["unit.mu.guard"].speed=original_speed*.5
	var slower: float=AI.tower_crossing_cost(s,0,"building.mo.tower",Vector2(22,0),"ground.2")
	verify(cost>0 and slower>cost and slower<cost*2,"slower approach adds exposure while siege duration remains independent of speed")
	db.balance.units["unit.mu.guard"].speed=original_speed
	verify(AI.tower_crossing_cost(s,0,"building.mo.tower",Vector2(22,9),"bridge")==0,"no exposure means no crossing damage cost")
	verify(AI.tower_crossing_cost(s,0,"building.mo.tower",Vector2(22,0),"ground.2",14)<cost,"visible wounded tower requires less siege investment")
	print("AI_STRUCTURE_MEMORY: ",checks," checks; failures=",failures);quit(0 if failures.is_empty() else 1)
