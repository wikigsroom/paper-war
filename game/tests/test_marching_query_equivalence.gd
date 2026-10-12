extends SceneTree
const Data=preload("res://scripts/data_store.gd")
const Simulation=preload("res://scripts/battle_sim.gd")
var checks: int=0
var failures: Array=[]
func _initialize():call_deferred("run")
func reference(s,u: Dictionary,def: Dictionary,enemy: Dictionary,step: float,forward: float) -> float:
	for ally in s.units if step>0 else []:
		if ally.uid==u.uid or ally.side!=u.side or ally.hp<=0 or ally.edge!=u.edge or s.db.balance.units[ally.id].get("economy",false):continue
		var other: Dictionary=s.db.balance.units[ally.id]
		if float(def.range)<=1.5 and (float(other.range)>1.5 or other.get("role","") in ["medic","engineer","necromancer","summoner","oracle","scribe"]):continue
		if not enemy.is_empty() and float(def.range)>1.5 and float(other.range)>float(def.range)+.05:continue
		var ahead: float=(float(ally.s)-float(u.s))*forward
		if ahead>0:
			var gap: float=.72 if def.get("role","")=="colossus" else .54
			step=minf(step,maxf(0,ahead-gap))
			if step==0:break
	return step
func compare(s,u: Dictionary,enemy: Dictionary,step: float,note: String):
	var def: Dictionary=s.db.balance.units[u.id]
	var forward: float=1 if int(u.side)==0 else -1
	var expected: float=reference(s,u,def,enemy,step,forward)
	var actual: float=s.marching_step(u,def,enemy,step,forward)
	checks+=1
	if actual!=expected:failures.append({"case":note,"actual":actual,"expected":expected})
func run():
	var db=Data.new()
	for definition in db.maps.values():
		for side in [0,1]:
			var s=Simulation.new(db)
			s.start({"map":definition.id,"faction":"yin","enemy":"mo","full_tech":true})
			s.units.clear();s.ai_enabled=[false,false]
			var ids: Array=db.all_unit_ids("yin" if side==0 else "mo")
			var actors: Array=[]
			var edge_ids: Array=s.map.edges.keys()
			for i in range(30):
				var u=s.spawn(ids[i%ids.size()],side,3)
				var edge: String=edge_ids[i%edge_ids.size()]
				s.map.apply_anchor(u,s.map.anchor(edge,float(s.map.edges[edge].length)*(.2+float(i%4)*.15)))
				if i%8==0:u.hp=0
				actors.append(u)
			s.prepare_movement_sides();s.movement_sides_active=true
			for i in range(actors.size()):
				compare(s,actors[i],{} if i%2==0 else s.bases[1-side],.05 if i%3==0 else 2,definition.id+"/"+str(side)+"/"+str(i))
			# References remain live after the index is built. A dead front stops
			# blocking; conversion is regrouped just as the real cast does.
			actors[3].hp=0;actors[7].side=1-side
			s.prepare_movement_sides()
			compare(s,actors[5],s.bases[1-side],3,"death/ownership "+definition.id)
			var born=s.spawn(ids[1],side,3)
			s.map.apply_anchor(born,s.map.anchor(actors[5].edge,float(actors[5].s)+(.55 if side==0 else -.55)))
			compare(s,actors[5],{},2,"phase-born anchor "+definition.id)
			born.s=INF;s.blocker_roads_dirty=true
			compare(s,actors[5],{},2,"invalid arc linear fallback "+definition.id)
			s.movement_sides_active=false
			compare(s,actors[5],{},2,"outside phase linear API "+definition.id)
	print("MARCHING_QUERY_EQUIVALENCE: ",checks," checks; failures=",failures)
	var args=OS.get_cmdline_user_args()
	if args.has("--output"):
		var path: String=args[args.find("--output")+1]
		FileAccess.open(path,FileAccess.WRITE).store_string(JSON.stringify({"checks":checks,"failures":failures,"source_sha256":FileAccess.get_sha256("res://scripts/battle_sim.gd"),"scope":"Independent prior linear blocker scan on all authored maps, both directions, workers/mixed ranges, duplicate positions, dead/converted and phase-born actors, invalid arcs and outside-phase API."},"  "))
	quit(0 if failures.is_empty() else 1)
