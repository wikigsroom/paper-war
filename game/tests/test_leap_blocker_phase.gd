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
var checks: int=0
var failures: Array=[]
func _initialize():call_deferred("run")
func fixture(s,map_id: String,side: int,order: Array):
	s.start({"map":map_id,"faction":"mo","enemy":"yin","full_tech":true})
	s.units.clear();s.ai_enabled=[false,false]
	var choices: Array=s.map.edges.keys().filter(func(id):return float(s.map.edges[id].length)>=4)
	var edge: String=choices[0]
	var direction: float=1.0 if side==0 else -1.0
	var origin: float=2.0 if side==0 else float(s.map.edges[edge].length)-2.0
	var actors: Array=[]
	for spec in [["unit.mo.blade",side,0.0],["unit.yin.axe",side,-.5],["unit.yin.axe",side,1.0],["unit.yin.axe",1-side,2.0]]:
		var u=s.spawn(spec[0],spec[1],2)
		s.map.apply_anchor(u,s.map.anchor(edge,origin+float(spec[2])*direction))
		u.hp=10000;u.max_hp=u.hp;u.special_cd=0
		if spec[2]>=1.0:u["speed_override"]=0.0
		actors.append(u)
	s.units=order.map(func(i):return actors[i])
	s.visibility.refresh();s.drain_events()
func canonical(s) -> Dictionary:
	return {"units":s.units.duplicate(true),"events":s.drain_events(),"projectiles":s.projectiles.duplicate(true),"vision":s.visibility.current.duplicate(true),"explored":s.visibility.explored.duplicate(true)}
func run():
	var db=Data.new()
	for definition in db.maps.values():
		for side in [0,1]:
			for order in [[0,1,2,3],[1,0,2,3],[2,1,3,0]]:
				var actual=Simulation.new(db);var expected=LinearSimulation.new(db)
				fixture(actual,definition.id,side,order);fixture(expected,definition.id,side,order)
				actual.tick(1.0/60.0);expected.tick(1.0/60.0)
				checks+=1
				if canonical(actual)!=canonical(expected) and failures.size()<20:failures.append({"map":definition.id,"side":side,"order":order})
	print("LEAP_BLOCKER_PHASE: ",checks," checks; failures=",failures)
	var args=OS.get_cmdline_user_args()
	if args.has("--output"):FileAccess.open(args[args.find("--output")+1],FileAccess.WRITE).store_string(JSON.stringify({"checks":checks,"failures":failures,"simulation_sha256":FileAccess.get_sha256("res://scripts/battle_sim.gd"),"observer_sha256":FileAccess.get_sha256(get_script().resource_path),"scope":"All200 maps, both directions and3 traversal orders. Actual60Hz leap against friendly front, actor/events/projectiles/fog compared with independent prior linear blocking. Not paid AI/FPS evidence."},"  "))
	quit(0 if failures.is_empty() else 1)
