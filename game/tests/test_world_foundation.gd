extends SceneTree
const Store = preload("res://scripts/data_store.gd")
const Simulation = preload("res://scripts/battle_sim.gd")
const MapRuntime = preload("res://scripts/map_runtime.gd")
var failures: Array = []
var checks: int = 0
var data

func verify(condition: bool, message: String):
	checks+=1
	if not condition: failures.append(message);print("FAIL ",message)

func run_seconds(sim, seconds: float):
	for i in range(int(seconds*60)):
		sim.tick(1.0/60.0)
		sim.drain_events()

func _init():
	data=Store.new()
	verify(data.maps.size()>=200,"At least 200 map definitions")
	verify(data.FACTIONS.size()>=10,"At least 10 factions")
	var geometry: Dictionary = {}
	for id in data.maps:
		var definition: Dictionary = data.maps[id]
		var graph = MapRuntime.new(definition)
		var path: Dictionary = graph.shortest_nodes("west","east")
		verify(not path.is_empty(),id+" military/depot connectivity")
		geometry[definition.geometry_sha256]=true
		for mine in definition.mines:
			verify(graph.edges.has(mine.edge) and int(mine.capacity)>0,id+" mine anchor/capacity "+mine.id)
			verify(not graph.route_to(graph.at_node(definition.bases[int(mine.owner)].node,int(mine.owner)),mine).is_empty(),id+" worker return route "+mine.id)
		for site in definition.build_sites: verify(graph.edges.has(site.edge),id+" construction site "+site.id)
		var sim=Simulation.new(data)
		sim.start({"map":id,"faction":"yin","enemy":"mo","full_tech":true,"win":"destroy_base"})
		sim.ai_enabled=[false,false]
		run_seconds(sim,30)
		verify(sim.stats[0].gold_delivered>0 and sim.stats[1].gold_delivered>0,id+" actual early deposits on both sides")
		verify(definition.get("design_card",{}).get("plans",[]).size()>=2,id+" explicit spatial alternatives")
	verify(geometry.size()>=20,"Distinct authored layouts; shared layouts across faction mechanics are permitted")
	for faction in data.FACTIONS:
		verify(data.all_unit_ids(faction).size()==6,faction+" six curated combat recruits")
		var roles: Dictionary = {}
		var sim=Simulation.new(data)
		sim.start({"map":"map.01.04","faction":faction,"enemy":"yin","full_tech":true})
		sim.ai_enabled=[false,false]
		var original_uids: Array=[]
		for id in data.all_unit_ids(faction):
			var definition: Dictionary = data.balance.units[id]
			verify(definition.get("manual_recruit",true) and not definition.get("economy",false),id+" counted combat unit")
			roles[definition.role]=true
			var unit=sim.spawn(id,0,float(sim.bases[0].x)+1)
			original_uids.append(unit.uid)
			verify(sim.map.edges.has(unit.edge),id+" anchored spawn")
		verify(roles.size()>=5,faction+" distinct curated combat roles")
		run_seconds(sim,3)
		verify(original_uids.all(func(uid):return not sim.actor(uid).is_empty() and sim.actor(uid).hp>0),faction+" original six recruits survive movement smoke; summons allowed")
	var routed=Simulation.new(data)
	routed.start({"map":"map.01.04","faction":"yin","enemy":"mo","full_tech":true})
	routed.ai_enabled=[false,false]
	var fork: Dictionary = routed.map.fork_nodes(0)[0]
	var incoming: String = routed.map.incoming[fork.node][0]
	var soldier=routed.spawn("unit.yin.axe",0,2.5)
	routed.map.apply_anchor(soldier,routed.map.anchor(incoming,routed.map.edges[incoming].length-.2))
	verify(routed.request(0,"route",{"node":fork.node,"edge":fork.options[1]}).ok,"Legal route switch uses command API")
	routed.map.advance(soldier,.4,0)
	verify(soldier.edge==fork.options[1],"Later arriving soldier chooses new outlet")
	routed.request(0,"route",{"node":fork.node,"edge":fork.options[0]})
	verify(soldier.edge==fork.options[1],"Committed soldier stays on existing edge")
	var upper=routed.spawn("unit.yin.axe",0,20)
	var lower=routed.spawn("unit.mo.blade",1,20)
	var first: String = fork.options[0];var second: String = fork.options[1]
	routed.map.apply_anchor(upper,routed.map.anchor(first,routed.map.edges[first].length*.5))
	routed.map.apply_anchor(lower,routed.map.anchor(second,routed.map.edges[second].length*.5))
	verify(routed.combat_distance(upper,lower,data.balance.units[upper.id])>float(data.balance.units[upper.id].range),"Separated branches cannot melee at same X")
	var old_hp: float = lower.hp
	routed.area_damage(upper.x,.5,30,0,false,upper.y)
	verify(lower.hp==old_hp,"Area spell respects vertical separation")
	var construction=Simulation.new(data)
	construction.start({"map":"map.03.03","faction":"deng","enemy":"yin","full_tech":true,"starting_gold":500})
	construction.ai_enabled=[false,false]
	var rate: float = construction.mana_rate(0)
	var rear_slot: int=construction.side_sites(0).find(construction.side_sites(0).filter(func(site):return site.id=="site.0.home-mana")[0])
	verify(construction.request(0,"build",{"id":"building.deng.mana","slot":rear_slot}).ok,"Construction command pays normally")
	verify(construction.buildings[0].state=="constructing" and construction.mana_rate(0)==rate,"Unfinished mana facility has no contribution")
	run_seconds(construction,4.2)
	verify(construction.buildings[0].state=="active" and construction.mana_rate(0)>rate,"Completed facility contributes")
	verify(data.campaign.size()>=200,"200 linked story missions")
	for i in range(data.campaign.size()):
		var level: Dictionary = data.campaign[i]
		verify(int(level.index)==i and data.maps.has(level.map),"Mission index/map "+str(i))
		verify(not level.story_before.is_empty() and not level.story_after.is_empty(),"Mission dialogue "+str(i))
		if i>0:verify(level.predecessor==data.campaign[i-1].id,"Linear story predecessor "+str(i))
		if i<data.campaign.size()-1:verify(level.next_level==data.campaign[i+1].id,"Linear story continuation "+str(i))
	var report: Dictionary = {"stage":"world-foundation-only","checks":checks,"failures":failures,"passed":failures.is_empty(),"maps":data.maps.size(),"factions":data.FACTIONS.size(),"campaign":data.campaign.size(),"not_covered":["complete human UI","all unit ability outcomes","all campaign victories","new art review","Windows export","Android export/device"]}
	report["geometry_records"]=geometry.size();report["engine"]=Engine.get_version_info();report["inputs"]={}
	for path in ["res://data/maps.json","res://data/campaign.json","res://data/balance-prototype.json","res://scripts/map_runtime.gd","res://scripts/battle_sim.gd","res://tests/test_world_foundation.gd"]:report.inputs[path]=FileAccess.get_sha256(path)
	var args=OS.get_cmdline_user_args();var destination: String=args[args.find("--output")+1] if args.has("--output") else "res://tests/world-foundation-report.json"
	var file=FileAccess.open(destination,FileAccess.WRITE)
	file.store_string(JSON.stringify(report,"\t"));file.close()
	print("WORLD_FOUNDATION ",JSON.stringify(report))
	quit(0 if failures.is_empty() else 1)
