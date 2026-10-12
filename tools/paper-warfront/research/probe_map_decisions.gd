extends SceneTree
# Research measurements of the current native simulation; no game data mutations.
const Store = preload("res://scripts/data_store.gd")
const Simulation = preload("res://scripts/battle_sim.gd")
var db

func _init():
	db=Store.new()
	var economics: Array=[]
	for id in ["map.01.01","map.01.09","map.01.20"]:
		for side in [0,1]:
			for priority in ["near","outer","auto"]:
				economics.append(economy(id,side,priority,1))
		for count in [3,4,6]:
			economics.append(economy(id,0,"auto",count))
			economics.append(economy(id,0,"near",count))
	var routes: Array=[]
	for id in ["map.01.04","map.01.09","map.01.13","map.01.16","map.01.19"]:
		for edge in ["ground.2","bridge"]:routes.append(walk_route(id,edge))
	var contact: Array=[]
	for id in ["map.01.01","map.01.10","map.01.20"]:contact.append(first_contact(id))
	var output: Dictionary={"date":"2026-10-08","engine":Engine.get_version_info().string,
		"scope":"Current working tree only; original game not run; deterministic native fixtures, not human playtest",
		"conditions":{"dt":1.0/60.0,"seed":137,"ai_enabled":false,"faction_each":"yin",
			"economy_seconds":120,"worker_spawn":"base.x + 0.1 world units; no recruit cost or production delay",
			"route_unit":"unit.yin.axe, solitary, no enemies before merge",
			"contact":"one axe each at time 0, no workers or production delay"},
		"economics":economics,"routes":routes,"first_contact":contact}
	var args: PackedStringArray=OS.get_cmdline_user_args()
	if args.is_empty():quit(2);return
	var file=FileAccess.open(args[0],FileAccess.WRITE)
	if file==null:quit(2);return
	file.store_string(JSON.stringify(output,"\t"));file.close()
	print("MAP_DECISION_RESEARCH ",JSON.stringify({"economic_fixtures":economics.size(),"route_fixtures":routes.size(),"contact_fixtures":contact.size(),"output":args[0]}))
	quit()

func fresh(id: String):
	var sim=Simulation.new(db)
	sim.start({"map":id,"seed":137,"faction":"yin","enemy":"yin","starting_gold":0,"enemy_starting_gold":0,"difficulty":1})
	sim.ai_enabled=[false,false]
	sim.units.clear();sim.drain_events()
	return sim

func economy(id: String,side: int,priority: String,count: int) -> Dictionary:
	var sim=fresh(id)
	if priority!="auto":sim.request(side,"mine_priority",{"mine":"mine.%d.%d"%[side,0 if priority=="near" else 1]})
	for i in range(count):sim.spawn("unit.yin.worker",side,sim.bases[side].x+.1*(1 if side==0 else -1))
	sim.drain_events()
	var delivered: Dictionary={};var first: float=-1.0;var buckets: Array=[0,0,0,0]
	var max_waiting: int=0
	for tick in range(60*120):
		sim.tick(1.0/60.0)
		for e in sim.drain_events():
			if e.kind=="gold" and int(e.side)==side:
				if first<0:first=sim.time
				delivered[e.mine]=int(delivered.get(e.mine,0))+int(e.amount)
				buckets[mini(3,int((sim.time-.00001)/30.0))]+=int(e.amount)
		if tick%60==0:
			var waiting: int=0
			for u in sim.units:
				if u.anim=="idle" and u.job=="mine":waiting+=1
			max_waiting=maxi(max_waiting,waiting)
	var final_workers: Array=[]
	for u in sim.units:
		var destination: Dictionary=sim.bases[side]
		if u.job=="mine":
			for m in sim.map.definition.mines:
				if m.id==u.mine:destination=m;break
		final_workers.append({"uid":u.uid,"job":u.job,"mine":u.mine,"edge":u.edge,
			"s":u.s,"x":u.x,"y":u.y,"cargo":u.cargo,"route_plan":sim.map.route_to(u,destination)})
	return {"map":id,"side":side,"worker_count":count,"priority":priority,
		"first_delivery_seconds":first,"gold_delivered":sim.stats[side].gold_delivered,
		"gold_per_30_second_interval":buckets,"by_mine":delivered,"max_idle_mining_sampled":max_waiting,
		"final_worker_states":final_workers}

func walk_route(id: String,edge: String) -> Dictionary:
	var sim=fresh(id)
	sim.request(0,"route",{"node":"fork","edge":edge})
	var u: Dictionary=sim.spawn("unit.yin.axe",0,sim.bases[0].x+.1)
	var fork_at: float=-1.0;var merge_at: float=-1.0
	for tick in range(60*90):
		sim.tick(1.0/60.0);sim.drain_events()
		if fork_at<0 and (u.edge=="ground.2" or u.edge=="bridge"):fork_at=sim.time
		if u.edge=="ground.3":merge_at=sim.time;break
	return {"map":id,"chosen_edge":edge,"fork_seconds":fork_at,"merge_seconds":merge_at,
		"crossed_nodes":u.crossed_nodes}

func first_contact(id: String) -> Dictionary:
	var sim=fresh(id)
	for side in [0,1]:sim.spawn("unit.yin.axe",side,sim.bases[side].x+.1*(1 if side==0 else -1))
	var result: Dictionary={"map":id,"first_hit_seconds":-1.0}
	for tick in range(60*90):
		sim.tick(1.0/60.0)
		for e in sim.drain_events():
			if e.kind=="hit":
				result.first_hit_seconds=sim.time
				result["positions"]=sim.units.map(func(u):return {"side":u.side,"x":u.x,"y":u.y,"edge":u.edge})
				return result
	return result
