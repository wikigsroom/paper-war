extends SceneTree
const Data=preload("res://scripts/data_store.gd")
const Simulation=preload("res://scripts/battle_sim.gd")
var checks: int=0
var failures: Array=[]
var observations: Array=[]
func _initialize():call_deferred("run")
func check(ok: bool,note: String):
	checks+=1
	if not ok:failures.append(note)
func run():
	var db=Data.new()
	for f in db.FACTIONS:
		var sim=Simulation.new(db)
		sim.start({"map":"map.01.07","faction":f,"enemy":"mo","starting_gold":230,"enemy_starting_gold":210,"full_tech":false})
		sim.ai_enabled=[false,false]
		var mine: Dictionary=sim.map.definition.mines.filter(func(m):return m.owner==0 and m.capacity==1)[0]
		check(sim.request(0,"mine_priority",{"mine":mine.id}).ok,f+" public near-mine priority")
		var seen: Dictionary={};var strikes: int=0;var queue_strikes: int=0;var loaded: int=0
		var body_on_road: bool=true;var queue_body_separated: bool=false
		for i in range(60*36):
			sim.tick(1.0/60.0)
			for u in sim.units:
				if u.side==0 and u.id.ends_with(".worker"):
					seen[u.anim]=true
					var body: Dictionary=sim.physical_anchor(u)
					body_on_road=body_on_road and sim.physical_point(u).distance_to(sim.map.point(body.edge,float(body.s)))<.001
					if u.anim=="queue" and sim.physical_point(u).distance_to(Vector2(u.x,u.y))>.5:queue_body_separated=true
					if u.anim=="queue" and float(u.job_time)>0:check(false,f+" waiting miner accumulated service time")
			for e in sim.drain_events():
				if e.get("side",1)!=0:continue
				if e.kind=="mine_strike":
					strikes+=1
					var u: Dictionary=sim.actor(int(e.uid))
					if u.is_empty() or u.anim=="queue":queue_strikes+=1
				if e.kind=="cargo_loaded":
					loaded+=1;var carrier: Dictionary=sim.actor(int(e.uid))
					check(not carrier.is_empty() and float(carrier.get("visual_load",0))>0,f+" real completion shows loading pose")
		check(seen.has("walk") and seen.has("mine") and seen.has("queue") and seen.has("unload"),f+" walk / mine / queue / unload all reached")
		check(strikes>0 and loaded>0 and queue_strikes==0,f+" actual strikes and load, no queued mining")
		check(sim.stats[0].gold_delivered>0,f+" work yields real deposited gold")
		check(body_on_road and queue_body_separated,f+" FIFO bodies have real separate stations on authored road")
		var id: String="unit."+f+".worker"
		check(db.unit_frames.has(id) and db.unit_frames[id].clips.mine.size()==6 and ResourceLoader.exists(db.unit_frames[id].atlas),f+" six actual mining drawings bound to shipped atlas")
		observations.append({"faction":f,"states":seen.keys(),"strikes":strikes,"loaded":loaded,"gold_deposited":sim.stats[0].gold_delivered,"queue_strikes":queue_strikes,"body_on_road":body_on_road,"queue_body_separated":queue_body_separated})
	var args=OS.get_cmdline_user_args();var out="user://worker-actions.json"
	if args.has("--output"):out=args[args.find("--output")+1]
	DirAccess.make_dir_recursive_absolute(out.get_base_dir());var file=FileAccess.open(out,FileAccess.WRITE)
	file.store_string(JSON.stringify({"checks":checks,"failed":failures.size(),"failures":failures,"factions":observations,"simulation_sha256":FileAccess.get_sha256("res://scripts/battle_sim.gd"),"assets_sha256":FileAccess.get_sha256("res://data/assets.json"),"test_sha256":FileAccess.get_sha256("res://tests/test_worker_actions.gd")},"  "));file.close()
	print("WORKERS ",checks," checks / ",failures.size()," failures");quit(0 if failures.is_empty() else 1)
