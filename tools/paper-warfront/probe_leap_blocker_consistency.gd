extends SceneTree
const Data=preload("res://scripts/data_store.gd")
const Simulation=preload("res://scripts/battle_sim.gd")
class LinearSimulation extends Simulation:
	func _init(data):super(data)
	func marching_step(u: Dictionary,def: Dictionary,enemy: Dictionary,step: float,forward: float) -> float:
		for ally in units if step>0 else []:
			if ally.uid==u.uid or ally.side!=u.side or ally.hp<=0 or ally.edge!=u.edge or db.balance.units[ally.id].get("economy",false):continue
			var other: Dictionary=db.balance.units[ally.id]
			if float(def.range)<=1.5 and (float(other.range)>1.5 or other.get("role","") in ["medic","engineer","necromancer","summoner","oracle","scribe"]):continue
			if not enemy.is_empty() and float(def.range)>1.5 and float(other.range)>float(def.range)+.05:continue
			var ahead: float=(float(ally.s)-float(u.s))*forward
			if ahead>0:
				var gap: float=.72 if def.get("role","")=="colossus" else .54
				step=minf(step,maxf(0,ahead-gap))
				if step==0:break
		return step
func _initialize():call_deferred("run")
func fixture(s,side: int):
	s.start({"map":"map.01.01","faction":"mo","enemy":"yin","full_tech":true})
	s.units.clear();s.ai_enabled=[false,false]
	var edge: String=s.map.edges.keys()[0]
	var direction: float=1.0 if side==0 else -1.0
	var origin: float=2.0 if side==0 else float(s.map.edges[edge].length)-2.0
	for spec in [["unit.mo.blade",side,0.0],["unit.yin.axe",side,-.5],["unit.yin.axe",side,1.0],["unit.yin.axe",1-side,2.0]]:
		var u=s.spawn(spec[0],spec[1],2)
		s.map.apply_anchor(u,s.map.anchor(edge,origin+float(spec[2])*direction))
		u.hp=10000;u.max_hp=u.hp;u.special_cd=0
		if spec[2]>=1.0:u["speed_override"]=0.0
	s.visibility.refresh();s.drain_events()
func state(s) -> Dictionary:
	return {"units":s.units.duplicate(true),"events":s.drain_events(),"projectiles":s.projectiles.duplicate(true)}
func run():
	var db=Data.new();var cases: Array=[];var failures: Array=[]
	for side in [0,1]:
		var actual=Simulation.new(db);var expected=LinearSimulation.new(db)
		fixture(actual,side);fixture(expected,side)
		actual.tick(1.0/60.0);expected.tick(1.0/60.0)
		var actual_state: Dictionary=state(actual);var expected_state: Dictionary=state(expected)
		var equal: bool=actual_state==expected_state
		var row: Dictionary={"side":side,"equal":equal,"actual_rear_s":actual.units[1].s,"expected_rear_s":expected.units[1].s,"actual_leap_s":actual.units[0].s,"expected_leap_s":expected.units[0].s,"actual":actual_state,"expected":expected_state}
		cases.append(row)
		if not equal:failures.append({"side":side,"actual_rear_s":row.actual_rear_s,"expected_rear_s":row.expected_rear_s})
	print("LEAP_BLOCKER_CONSISTENCY: ",cases.size()," checks; failures=",failures)
	var args=OS.get_cmdline_user_args()
	if args.has("--output"):
		FileAccess.open(args[args.find("--output")+1],FileAccess.WRITE).store_string(JSON.stringify({"checks":cases.size(),"failures":failures,"cases":cases,"simulation_sha256":FileAccess.get_sha256("res://scripts/battle_sim.gd"),"observer_sha256":FileAccess.get_sha256(get_script().resource_path),"scope":"One real 60 Hz tick, both directions; actual closing leap limited by allied melee screen, compared with independent prior linear blocking. Includes actor and event state; not FPS or paid AI evidence."},"  "))
	quit(0 if failures.is_empty() else 1)
