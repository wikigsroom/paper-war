extends SceneTree
# Continuous native worker journeys, including both depot ends and every mine.
const Store = preload("res://scripts/data_store.gd")
const Simulation = preload("res://scripts/battle_sim.gd")
const Geometry = preload("res://scripts/map_runtime.gd")
var checks: int = 0
var failures: Array = []

func verify(condition: bool,message: String):
	checks+=1
	if not condition:failures.append(message);print("FAIL ",message)

func _init():
	var db=Store.new()
	var args=OS.get_cmdline_user_args()
	var all_maps: bool = args.has("--all-maps")
	var results: Array = []
	var selected: Array = db.maps.keys() if all_maps else ["map.01.01","map.01.07","map.01.11","map.01.04","map.01.09","map.01.20"]
	for map_id in selected:
		for mine in db.maps[map_id].mines:
			var side: int = int(mine.owner)
			if side not in [0,1] or int(mine.resource)>=0:continue
			var sim=Simulation.new(db)
			sim.start({"map":map_id,"faction":"yin","enemy":"yin","starting_gold":0,"enemy_starting_gold":0,"seed":137})
			sim.ai_enabled=[false,false];sim.units.clear();sim.drain_events()
			sim.request(side,"mine_priority",{"mine":mine.id})
			var worker: Dictionary = sim.spawn("unit.yin.worker",side,sim.bases[side].x+.1*(1 if side==0 else -1))
			worker.mine=mine.id
			var cycle: float=sim.mine_income(side,mine,worker.uid).cycle
			var expected_trips: int=maxi(1,int(floor(300.0/cycle)))
			var trips: int = 0;var late_trips: int = 0;var final_cycle_trips: int=0;var gold: int = 0
			for tick in range(60*300):
				sim.tick(1.0/60.0)
				for event in sim.drain_events():
					if event.kind=="gold" and event.mine==mine.id:
						trips+=1;gold+=int(event.amount)
						if sim.time>270:late_trips+=1
						if sim.time>300-cycle-2:final_cycle_trips+=1
			verify(trips>=expected_trips-1,"Continuous trips match actual round-trip length: "+map_id+" "+mine.id)
			verify(final_cycle_trips>0,"Transport still deposits in final complete cycle: "+map_id+" "+mine.id)
			results.append({"map":map_id,"mine":mine.id,"side":side,"trips":trips,"expected_trips":expected_trips,"cycle":cycle,"gold":gold,"last_30_seconds_trips":late_trips,"final_cycle_trips":final_cycle_trips})
		if selected.find(map_id)%20==0:print("TRANSPORT_PROGRESS ",selected.find(map_id)+1,"/",selected.size())
	# A steep main road plus a raised branch: decoration sampling must stay on
	# the main road at the requested X, rather than project to another point.
	var sample=Geometry.new({"length":10,"nodes":[{"id":"west","position":[0,0]},{"id":"east","position":[10,4]}],"edges":[{"id":"main","from":"west","to":"east","points":[[0,0],[10,4]]},{"id":"bridge","from":"west","to":"east","points":[[0,0],[5,-2],[10,4]]}],"presentation":{"ground_edges":["main"]}})
	verify(is_equal_approx(sample.ground_y_at(5),2),"Sample main floor at X, independent of raised branch")
	var report: Dictionary = {"scope":"Native continuous transport, 300s per infinite mine, both directions, no AI; not human gameplay or visual acceptance","checks":checks,"failures":failures,"passed":failures.is_empty(),"maps":selected.size(),"results":results}
	report["engine"]=Engine.get_version_info()
	report["inputs"]={}
	for path in ["res://data/maps.json","res://data/balance-prototype.json","res://scripts/map_runtime.gd","res://scripts/battle_sim.gd"]:report.inputs[path]=FileAccess.get_sha256(path)
	var destination: String = "res://tests/map-transport-report.json"
	if args.has("--output"):destination=args[args.find("--output")+1]
	var file=FileAccess.open(destination,FileAccess.WRITE);file.store_string(JSON.stringify(report,"\t"));file.close()
	print("MAP_TRANSPORT ",JSON.stringify({"maps":selected.size(),"mines":results.size(),"checks":checks,"failures":failures.size()}))
	quit(0 if failures.is_empty() else 1)
