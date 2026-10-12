extends SceneTree
# Controlled native scenarios verify consequences of space, time and commands.
const Store=preload("res://scripts/data_store.gd")
const Simulation=preload("res://scripts/battle_sim.gd")
var checks: Array=[]
var measurements: Dictionary={}

func verify(kind: String,passed: bool,data: Dictionary={}):
	checks.append({"kind":kind,"passed":passed,"data":data})
	if not passed:print("FAIL ",kind," ",JSON.stringify(data))

func clean(db,config: Dictionary):
	var sim=Simulation.new(db);sim.start(config);sim.ai_enabled=[false,false]
	sim.units=sim.units.filter(func(u):return not db.balance.units[u.id].get("economy",false))
	sim.drain_events();return sim

func arrival(db,id: String,side: int) -> Dictionary:
	var sim=clean(db,{"map":"map.01.11","faction":"yin","enemy":"yin"})
	var u=sim.spawn(id,side,sim.bases[side].x+(0.65 if side==0 else -.65))
	var goal: float=21 if side==0 else 37
	for tick in range(60*150):
		sim.tick(1.0/60.0);sim.drain_events()
		if (u.x-goal)*(1 if side==0 else -1)>=0:break
	return {"id":id,"side":side,"time":sim.time,"x":u.x,"mana":sim.players[side].mana}

func fork_run(db,route: String,defender_edge: String="") -> Dictionary:
	var sim=clean(db,{"map":"map.01.04","faction":"yin","enemy":"mo","starting_gold":45,"enemy_starting_gold":300})
	if defender_edge!="":
		var enemy=sim.spawn("unit.mo.giant",1,22);enemy["speed_override"]=0.0
		var edge: Dictionary=sim.map.edges[defender_edge]
		sim.map.apply_anchor(enemy,sim.map.anchor(defender_edge,float(edge.length)*.5))
		# The same initial defender costs the same amount in both fixtures.
		sim.players[1].gold-=float(db.balance.units[enemy.id].gold)
	sim.request(0,"route",{"node":"fork","edge":route})
	verify("fork fixture recruits through paid production",sim.request(0,"recruit",{"id":"unit.yin.axe"}).ok)
	var uid: int=0;var last_hp: float=0;var reached: bool=false
	for tick in range(60*100):
		sim.tick(1.0/60.0)
		for e in sim.drain_events():
			if e.kind=="spawn" and e.side==0 and e.id=="unit.yin.axe":uid=e.uid
		var unit: Dictionary=sim.actor(uid)
		if uid>0 and unit.is_empty():last_hp=0;break
		if not unit.is_empty():
			last_hp=unit.hp
			if float(unit.x)>=30:reached=true;break
	return {"route":route,"defender":defender_edge,"reached_merge":reached,"time":sim.time,"hp":last_hp}

func crossing_hits(db,near: bool,outside: bool=false,scouted: bool=true) -> int:
	var sim=clean(db,{"map":"map.01.04","faction":"yin","enemy":"yin"})
	var x: float=17 if near else 22
	var attacker=sim.spawn("unit.yin.spear",0,x-6 if outside else x);attacker["speed_override"]=0.0
	var target=sim.spawn("unit.yin.axe",1,x);target["speed_override"]=0.0;target.hp=5000;target.max_hp=5000
	var s: float=Vector2(14,0).distance_to(Vector2(17,-2))
	if not near:s+=Vector2(17,-2).distance_to(Vector2(22,-4))
	sim.map.apply_anchor(target,sim.map.anchor("bridge",s))
	# This fixture isolates physical range after legal road scouting. The
	# ground attacker alone cannot see a different branch through terrain.
	if scouted:
		var scout=sim.spawn("unit.yin.worker",0,x)
		sim.map.apply_anchor(scout,sim.map.anchor("bridge",s+2.0))
		sim.set_status(scout,"bind",10,0)
	sim.visibility.refresh()
	verify("bridge target visibility matches scouting",sim.visible_to(0,target)==scouted)
	var hits: int=0
	for tick in range(60*3):
		sim.tick(1.0/60.0)
		for e in sim.drain_events():
			if e.kind=="hit" and e.uid==target.uid:hits+=1
	return hits

func missions(db):
	var intercept: Dictionary=db.campaign[11].duplicate(true)
	var sim=clean(db,intercept);var target=sim.actor(sim.intercept_uid)
	sim.damage(target,99999,0,false);sim.tick(1.0/60.0)
	verify("intercept target dies before line: victory",sim.winner==0)
	sim=clean(db,intercept);target=sim.actor(sim.intercept_uid)
	var line: Dictionary=intercept.objective_anchor
	sim.map.apply_anchor(target,sim.map.anchor(line.edge,float(line.s)+.001))
	sim.projectiles.append({"uid":10000,"side":0,"source":0,"target":target.uid,"start_x":target.x,"start_y":target.y,"end_x":target.x,"end_y":target.y,"x":target.x,"y":target.y,"left":.001,"total":.001,"damage":99999,"radius":0.0,"building_multiplier":1.0,"poison":0.0,"reflected":false,"reflectable":false,"ability":{},"style":"spear"})
	sim.tick(1.0/60.0)
	verify("live crossing remains failure after later same-tick impact",sim.winner==1 and sim.intercept_crossed)
	var escort: Dictionary=db.campaign[5].duplicate(true)
	sim=clean(db,escort);target=sim.actor(sim.escort_uid)
	sim.map.apply_anchor(target,escort.objective_anchor);sim.damage(target,99999,1,false);sim.tick(1.0/60.0)
	verify("escort must arrive alive",sim.winner==1)
	sim=clean(db,escort);target=sim.actor(sim.escort_uid)
	sim.map.apply_anchor(target,escort.objective_anchor);sim.tick(1.0/60.0)
	verify("live named escort reaches goal",sim.winner==0)
	for index in [9,15]:
		var seam: Dictionary=db.campaign[index].duplicate(true)
		sim=clean(db,seam)
		for tick in range(60*150):
			sim.tick(1.0/60.0);sim.drain_events()
			if sim.winner!=-2:break
		verify("escort endpoint seam settles after crossing: "+seam.map,sim.winner==0,{"time":sim.time})
	escort.enemy_starting_gold=1000;escort.full_tech=true
	sim=clean(db,escort)
	for tick in range(60*21):sim.tick(1.0/60.0);sim.drain_events()
	var id: String=sim.players[1].roster[0];var gold: float=sim.players[1].gold
	verify("entry unit pays ordinary recruitment price",sim.request(1,"recruit",{"id":id}).ok and is_equal_approx(gold-sim.players[1].gold,float(db.balance.units[id].gold)))
	var entry: float=-1
	for tick in range(60*5):
		sim.tick(1.0/60.0)
		for e in sim.drain_events():
			if e.kind=="spawn" and e.side==1 and e.id==id:entry=e.x
	verify("paid enemy production uses the declared first entrance",is_equal_approx(entry,33),{"spawn_x":entry})
	# A mission's visible goal remains its win condition after an enemy base falls.
	for index in [2,7,11]:
		var mission: Dictionary=db.campaign[index].duplicate(true)
		sim=clean(db,mission);sim.bases[1].hp=0;sim.tick(1.0/60.0)
		verify("base destruction cannot skip "+mission.win,sim.winner==-2)
		verify("destroyed base cannot recruit",not sim.request(1,"recruit",{"id":sim.players[1].roster[0]}).ok)

func smoke(db):
	var rows: Array=[]
	for index in [0,6,10,3,11,5]:
		var config: Dictionary=db.campaign[index].duplicate(true)
		var sim=Simulation.new(db);sim.start(config);sim.ai_enabled=[true,true]
		var first_hit: float=-1;var first_deposit: Array=[-1.0,-1.0]
		for tick in range(60*180):
			sim.tick(1.0/60.0)
			for e in sim.drain_events():
				if e.kind=="hit" and int(e.get("attacker_side",e.side))!=int(e.side) and first_hit<0:first_hit=sim.time
				if e.kind=="gold" and first_deposit[e.side]<0:first_deposit[e.side]=sim.time
			if sim.winner!=-2:break
		var row: Dictionary={"map":config.map,"time":sim.time,"winner":sim.winner,"first_hit":first_hit,"first_deposit":first_deposit,"player":sim.stats[0],"enemy":sim.stats[1],"production_counts":[sim.production_ids(0).size(),sim.production_ids(1).size()]}
		rows.append(row)
		verify("authored-map first combat within 30 seconds: "+config.map,first_hit>0 and first_hit<=30,row)
		verify("normal missions retain six combat choices plus worker: "+config.map,row.production_counts==[7,7],{"counts":row.production_counts})
	measurements["authored_smoke"]=rows

func _init():
	var db=Store.new()
	var walking: Array=[]
	for side in [0,1]:
		var fast: Dictionary=arrival(db,"unit.yin.axe",side);var heavy: Dictionary=arrival(db,"unit.yin.cannon",side)
		walking.append({"fast":fast,"heavy":heavy})
		verify("long-map reinforcement delay: side "+str(side),heavy.time>fast.time+3,{"fast":fast,"heavy":heavy})
	measurements["long_map"]=walking
	var routes: Array=[]
	for defender in ["","ground.2","bridge"]:
		var direct: Dictionary=fork_run(db,"ground.2",defender);var bridge: Dictionary=fork_run(db,"bridge",defender)
		routes.append({"defender":defender,"direct":direct,"bridge":bridge})
		if defender=="":verify("paper bridge takes extra reinforcement time",direct.reached_merge and bridge.reached_merge and bridge.time>direct.time+.5)
		elif defender=="ground.2":verify("bridge avoids the main melee position",bridge.reached_merge and bridge.hp>direct.hp,{"direct":direct,"bridge":bridge})
		else:verify("ground route avoids an upper melee position",direct.reached_merge and direct.hp>bridge.hp,{"direct":direct,"bridge":bridge})
	measurements["route_pressure_matrix"]=routes
	var near: int=crossing_hits(db,true);var high: int=crossing_hits(db,false);var outside: int=crossing_hits(db,false,true)
	verify("cross-route ranged hit at the bridge approach",near>0,{"hits":near})
	verify("bridge height gives no immunity inside the actual 4.2 range",high>0,{"hits":high})
	verify("bridge target beyond actual 2D range cannot be hit",outside==0,{"hits":outside})
	var hidden: int=crossing_hits(db,false,false,false)
	verify("unscouted bridge target cannot be shot across roads",hidden==0,{"hits":hidden})
	missions(db);smoke(db)
	var report: Dictionary={"scope":"Native controlled route-pressure alternatives, real paid production, reinforcement timing, two-dimensional ranged hits, explicit mission event order and six automated opening smokes. Not original-HD measurements, human balance acceptance or Android hardware QA.","engine":Engine.get_version_info(),"inputs":{},"checks":checks,"measurements":measurements,"failures":checks.filter(func(c):return not c.passed)}
	for path in ["res://data/maps.json","res://data/campaign.json","res://data/balance-prototype.json","res://scripts/map_runtime.gd","res://scripts/battle_sim.gd","res://scripts/tactical_ai.gd"]:report.inputs[path]=FileAccess.get_sha256(path)
	report["passed"]=report.failures.is_empty()
	var args=OS.get_cmdline_user_args();var destination: String=args[0] if not args.is_empty() else "res://tests/theatre-decisions-report.json"
	var file=FileAccess.open(destination,FileAccess.WRITE);file.store_string(JSON.stringify(report,"\t"));file.close()
	print("THEATRE_DECISIONS ",JSON.stringify({"checks":checks.size(),"failures":report.failures.size(),"passed":report.passed}))
	quit(0 if report.passed else 1)
