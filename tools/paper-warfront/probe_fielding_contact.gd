extends SceneTree
# Paid normal AI trace. Observations never mutate units, resources or decisions.
const Data=preload("res://scripts/data_store.gd")
const Simulation=preload("res://scripts/battle_sim.gd")
func _initialize():call_deferred("run")
func values(unit: Dictionary) -> Dictionary:
	var out: Dictionary={}
	for key in ["uid","id","side","x","y","edge","s","hp","max_hp","anim","target","windup","cooldown","cargo","mine","job","job_time","statuses","clone","owner"]:
		if unit.has(key):out[key]=unit[key]
	return out.duplicate(true)
func run():
	var args=OS.get_cmdline_user_args()
	var folder: String=args[args.find("--output")+1]
	DirAccess.make_dir_recursive_absolute(folder)
	var db=Data.new();var sim=Simulation.new(db)
	var west: String=args[args.find("--west")+1] if args.has("--west") else "yin"
	var east: String=args[args.find("--east")+1] if args.has("--east") else "mu"
	var warmup: float=float(args[args.find("--warmup")+1]) if args.has("--warmup") else 4.0
	var stock: int=int(args[args.find("--stock")+1]) if args.has("--stock") else 300
	var map_id: String=args[args.find("--map")+1] if args.has("--map") else "map.01.04"
	var duration: int=int(args[args.find("--duration")+1]) if args.has("--duration") else 240
	var seed_value: int=int(args[args.find("--seed")+1]) if args.has("--seed") else 137
	sim.start({"map":map_id,"faction":west,"enemy":east,"starting_gold":stock,"enemy_starting_gold":stock,
		"seed":seed_value,"ai_warmup":warmup,"difficulty":1,"ai_style":"counter","full_tech":false,"win":"destroy_base",
		"observe_ai_recruitment":true})
	if args.has("--counter-side"):sim.config["contact_counter_side"]=int(args[args.find("--counter-side")+1])
	sim.ai_enabled=[true,true]
	var first: Array=[{},{}];var actors: Dictionary={};var events: Array=[];var samples: Array=[]
	for unit in sim.units:actors[unit.uid]=unit.id
	sim.drain_events()
	for step in range(duration*60):
		sim.tick(1.0/60)
		for event in sim.drain_events():
			var side: int=int(event.get("side",-1))
			if event.kind=="research_start" and side in [0,1]:
				var node: Dictionary=db.tech(event.id)
				if first[side].is_empty() and str(node.grant).begins_with("unit."):
					first[side]={"grant":node.grant,"tech":node.id,"research_started":event.time}
			if event.kind=="spawn":actors[event.uid]=event.id
			if side in [0,1] and not first[side].is_empty():
				var item: Dictionary=first[side]
				if event.kind=="research_done" and event.id==item.grant:item["completed"]=event.time
				if event.kind=="recruit" and event.id==item.grant and not item.has("ordered"):item["ordered"]=event.time
				if event.kind=="spawn" and event.id==item.grant and event.get("origin","")=="production" and not item.has("uid"):
					item["uid"]=event.uid;item["born"]=event.time
				if event.kind=="death" and event.get("uid",0)==item.get("uid",-1):item["death"]=event.time
			if event.kind in ["recruit","research_start","research_done","build","building_completed","route_changed","mine_priority","gold","spawn","death","attack","hit","heal","cast"]:
				var logged: Dictionary=event.duplicate(true)
				logged["actor_id"]=actors.get(int(event.get("uid",0)),"")
				logged["source_id"]=actors.get(int(event.get("source_uid",0)),"")
				events.append(logged)
		if step%30==29:
			var sides: Array=[]
			for side in [0,1]:
				var p: Dictionary=sim.players[side];var own: Array=[];var visible: Array=[]
				for unit in sim.units:
					if unit.hp<=0:continue
					if unit.side==side:own.append(values(unit))
					elif sim.visible_to(side,unit):visible.append(values(unit))
				sides.append({"own":own,"visible":visible,"gold":p.gold,"mana":p.mana,"research":p.research.duplicate(true),
					"goal":p.get("ai_grant_goal",""),"queue":p.queue.duplicate(),"workers":sim.population(side,true,true),
					"delivered":sim.stats[side].gold_delivered,"base_hp":sim.bases[side].hp,"routes":sim.map.choices[side].duplicate(true)})
			samples.append({"time":sim.time,"sides":sides})
		if sim.winner!=-2:break
	for side in [0,1]:
		var item: Dictionary=first[side]
		item["direct_hits"]=events.filter(func(e):return e.kind=="hit" and e.get("source_uid",0)==item.get("uid",-1) and e.get("attacker_side",-1)==side and float(e.get("amount",0))>0)
	var inputs: Dictionary={}
	for directory in ["scripts","data"]:
		for file in DirAccess.get_files_at("res://"+directory):
			if file.ends_with(".gd") or file.ends_with(".json"):
				inputs[directory+"/"+file]=FileAccess.get_sha256("res://"+directory+"/"+file)
	var report: Dictionary={"config":sim.config.duplicate(true),"first":first,"events":events,"samples":samples,
		"time":sim.time,"winner":sim.winner,"inputs":inputs,"observer_sha256":FileAccess.get_sha256(get_script().resource_path),
		"scope":"Frozen native Windows CPU, normal300-gold/4s enemy-warmup defaults unless explicitly overridden in config. Both AI sides; no actor/resource/HP/technology gifts or hidden-information inputs to AI. Trace is not GPU, human play, original-game equivalence or hardware acceptance."}
	FileAccess.open(folder+"/report.json",FileAccess.WRITE).store_string(JSON.stringify(report,"  "))
	print("FIELDING_CONTACT ",JSON.stringify({"time":sim.time,"winner":sim.winner,"first_units":first.map(func(item):return {"grant":item.get("grant",""),"uid":item.get("uid",0),"born":item.get("born",-1),"death":item.get("death",-1),"hits":item.direct_hits.size()})}))
	quit(0)
