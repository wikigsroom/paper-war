extends SceneTree
const Data=preload("res://scripts/data_store.gd")
const Sim=preload("res://scripts/battle_sim.gd")
var checks: int=0
var failures: Array=[]
func _initialize():call_deferred("run")
func verify(value: bool,note: String):
	checks+=1
	if not value and failures.size()<20:failures.append(note)
func run():
	var db=Data.new();var evidence: Dictionary={};var before_copy: Dictionary={};var after_copy: Dictionary={}
	for level in db.campaign:
		var beat: Dictionary=db.campaign_narrative[level.id]
		var bound: Dictionary=beat.objective_binding
		var sim=Sim.new(db);sim.start(level);sim.ai_enabled=[false,false]
		verify(beat.map==sim.map.definition.id and beat.objective==level.win,"story identifies actual loaded battle "+level.id)
		verify(not evidence.has(beat.evidence_name),"distinct map evidence "+level.id);evidence[beat.evidence_name]=true
		var before: String=JSON.stringify(level.story_before);var after: String=JSON.stringify(level.story_after)
		verify(not before_copy.has(before) and not after_copy.has(after),"distinct authored conflict and result "+level.id)
		before_copy[before]=true;after_copy[after]=true
		verify(before!=after and not after.contains("这一页已经留下可见的证据"),"result develops its conflict "+level.id)
		var opening_paid: Array=[0.0,0.0]
		for opening in level.get("opening_forces",[]):
			var side: int=int(opening.get("side",1))
			var cost: float=float(db.balance.units[opening.id].gold)
			var initial: float=float(level.starting_gold if side==0 else level.enemy_starting_gold)
			if initial-opening_paid[side]>=cost:opening_paid[side]+=cost
		verify(is_equal_approx(float(sim.players[0].gold)+opening_paid[0],float(level.starting_gold)) and is_equal_approx(float(sim.players[1].gold)+opening_paid[1],float(level.enemy_starting_gold)),"narrative grants no resources; existing opening troops remain paid "+level.id)
		match level.win:
			"protect":
				var actor: Dictionary=sim.actor(sim.protected_uid)
				verify(not actor.is_empty() and actor.id==bound.id and actor.get("prebuilt",false) and actor.state=="active","prebuilt named objective tower exists "+level.id)
				verify(actor.edge==bound.anchor.edge and is_equal_approx(float(actor.s),float(bound.anchor.s)),"protection references actual site, not generic end anchor "+level.id)
				verify(bound.duration==level.duration,"protection deadline preserved "+level.id)
			"escort","intercept":
				var actor: Dictionary=sim.actor(sim.escort_uid if level.win=="escort" else sim.intercept_uid)
				verify(not actor.is_empty() and actor.id==bound.id and bound.name==db.balance.units[actor.id].name,"correct actual objective body "+level.id)
				verify(is_equal_approx(float(actor.hp),float(bound.hp)) and is_equal_approx(float(actor.speed_override),float(bound.speed)),"objective life and movement preserved "+level.id)
				verify(bound.anchor==level.objective_anchor and sim.map.edges.has(bound.anchor.edge),"goal or failure marker references real edge "+level.id)
				verify(actor.objective_unit and not actor.clone and bound.must_be_original_actor,"unique original actor required "+level.id)
			"deliver_gold":
				verify(bound.amount==level.goal_gold and int(sim.stats[0].gold_delivered)==0 and not bound.initial_gold_counts,"only actual delivery counts "+level.id)
			"survive":verify(bound.duration==level.duration and sim.bases[0].hp>0,"actual base survival deadline "+level.id)
			"destroy_base":verify(bound.id==sim.bases[1].id and bound.side==1,"actual enemy base remains objective "+level.id)
		verify(sim.winner==-2,"story alone cannot clear loaded battle "+level.id)
	# Route-aware objective distances are part of the authored map contract. The
	# bridge and ground lanes on map.01.04 intentionally have different lengths;
	# the HUD must follow the selected fork instead of using world X distance.
	var route_level: Dictionary={}
	for level in db.campaign:
		if str(level.get("map",""))=="map.01.04":route_level=level;break
	var route_sim=Sim.new(db);route_sim.start(route_level);route_sim.ai_enabled=[false,false]
	var route_actor: Dictionary=route_sim.spawn("unit.yin.axe",0,float(route_sim.bases[0].x)+1.0)
	var route_goal: Dictionary=route_sim.map.anchor("ground.4",2.0)
	route_sim.map.apply_anchor(route_actor,route_sim.map.anchor("ground.1",0.0))
	verify(not route_level.is_empty() and route_sim.map.set_route(0,"fork","ground.2"),"route objective fixture selects ground lane")
	var ground_distance: float=route_sim.map.selected_route_distance(route_actor,route_goal,0)
	verify(is_finite(ground_distance) and ground_distance>0,"ground lane objective distance is finite")
	verify(route_sim.map.set_route(0,"fork","bridge"),"route objective fixture selects bridge lane")
	var bridge_distance: float=route_sim.map.selected_route_distance(route_actor,route_goal,0)
	verify(is_finite(bridge_distance) and bridge_distance>ground_distance+0.1,"bridge lane reports its longer authored distance")
	route_sim.config["win"]="escort";route_sim.config["objective_anchor"]=route_goal;route_sim.escort_uid=int(route_actor.uid)
	verify(route_sim.objective_text().contains("距交接") and route_sim.objective_text().contains("步"),"objective HUD uses route distance wording")
	route_sim.map.apply_anchor(route_actor,route_goal)
	verify(route_sim.map.objective_reached(route_actor,route_goal,0),"objective reaches on the authored edge")
	print("STORY_OBJECTIVES: ",checks," checks; failures=",failures)
	var args=OS.get_cmdline_user_args()
	if args.has("--output"):FileAccess.open(args[args.find("--output")+1],FileAccess.WRITE).store_string(JSON.stringify({"checks":checks,"failures":failures,"maps":200,"scope":"All200 actual Sim.start objective actors, actual protection site, original escort/intercept body, deadline, unchanged initial resources and no automatic result. Initial-state fixtures, not200 played victories."},"  "))
	quit(0 if failures.is_empty() else 1)
