extends SceneTree
const Gallery=preload("res://tests/action_gallery.gd")
const Data=preload("res://scripts/data_store.gd")
const Sim=preload("res://scripts/battle_sim.gd")
var folder: String
var gallery
var db
func _initialize():call_deferred("run")
func capture(path: String):
	gallery.queue_redraw();await process_frame;await RenderingServer.frame_post_draw
	var picture=root.get_texture().get_image();var err: int=picture.save_png(folder+"/"+path)
	if err!=OK:push_error("Gallery capture failed "+path);quit(1)
func set_phase(state: String,t: float):
	for u in gallery.sim.units:
		var profile: Dictionary=db.unit_actions[u.id]
		u.anim=state;u.anim_t=t*float(profile.windup if state=="windup" else profile.recovery);u.walk=t*2.1;u.age=t+1;u.hurt=.13*(1-t) if state=="hurt" else 0
		u.job_time=t*.95;u.work_duration=2.4;u.facing=-1 if state=="left" else 1;u["visual_load"]=0;u["visual_special"]=0
		if state=="left":u.anim="windup";u.anim_t=float(profile.windup)*.72
		if state=="special":u.anim="idle";u["visual_special"]=(1-t)*.45
		if state=="death":u.anim_t=t*.44
		if db.balance.units[u.id].get("economy",false):
			u.anim="mine" if state in ["attack","windup"] else "load" if state=="special" else "walk" if state=="left" else state
			if state=="attack":u.job_time=.57*.95
			if state=="special":u["visual_load"]=(1-t)*.25
			u.cargo=12 if state in ["walk","special","unload"] else 0
func populate(ids: Array,page: int):
	gallery.sim.units.clear();gallery.positions.clear();gallery.captions.clear()
	for index in range(ids.size()):
		var uid: String=ids[index];var u: Dictionary=gallery.sim.spawn(uid,0,20+index*.01)
		gallery.positions[u.uid]=Vector2(202+(index%4)*398,283+(index/4)*287)
		gallery.captions[u.uid]=db.name_of(uid)
func run():
	var args=OS.get_cmdline_user_args();folder=args[args.find("--output")+1];var preview: bool=args.has("--preview")
	DirAccess.make_dir_recursive_absolute(folder+"/frames");db=Data.new()
	gallery=Gallery.new();gallery.db=db;gallery.sim=Sim.new(db);gallery.sim.start({"faction":"yin","enemy":"mo","map":"map.01.01"});gallery.sim.units.clear();root.add_child(gallery)
	await process_frame
	var all_ids: Array=db.balance.units.keys();var fixtures: Array=[];var captured: Array=[]
	var phases=["idle","walk","windup","attack","hurt","left","special","death"]
	if preview:all_ids=["unit.yin.axe","unit.yin.spear","unit.yin.hammer","unit.yin.cannon","unit.yuan.archer","unit.jin.archer","unit.yin.duelist","unit.mo.giant","unit.mo.priest","unit.yin.pike","unit.bai.repeater","unit.yin.worker"]
	for offset in range(0,all_ids.size(),12):
		var ids: Array=all_ids.slice(offset,mini(offset+12,all_ids.size()));populate(ids,offset/12)
		for state in phases:
			set_phase(state,.60 if state=="windup" else .15 if state=="attack" else .5)
			gallery.page_title="PAPER WARFRONT / Runtime rig review / %02d / %s"%[offset/12,state]
			var path: String="page-%02d-%s.png"%[offset/12,state];await capture(path);captured.append(path)
		fixtures.append({"page":offset/12,"ids":ids,"phases":phases})
		if offset%48==0:print("GALLERY_PAGE ",offset/12)
	# One representative of every actual combat role plus all ten miner silhouettes.
	var role_ids: Dictionary={}
	for f in db.FACTIONS:
		for id in db.factions[f].core_roster:role_ids[db.balance.units[id].role]=id
	for uid in all_ids:
		var role: String=str(db.balance.units[uid].get("role",""))
		if not role.is_empty() and not role_ids.has(role):role_ids[role]=uid
	var demo: Array=role_ids.values()
	for f in db.FACTIONS:demo.append("unit."+f+".worker")
	var frames: int=0
	if not preview:
		for offset in range(0,demo.size(),12):
			populate(demo.slice(offset,mini(offset+12,demo.size())),offset/12)
			for frame in range(90):
				var stage: int=frame/15;var t: float=float(frame%15)/14
				var state: String=["walk","windup","attack","special","hurt","death"][stage]
				set_phase(state,t);gallery.page_title="40 role families + 10 miners / slow pose inspection / %d / %s"%[offset/12+1,state]
				await capture("frames/frame-%04d.png"%frames);frames+=1
	populate(db.FACTIONS.map(func(f):return "unit."+f+".worker"),99)
	for state in ["queue","unload","bound"]:
		set_phase(state,.5);gallery.page_title="Ten miners / "+state
		var path: String="workers-"+state+".png";await capture(path);captured.append(path)
	var report={"units":all_ids.size(),"fixtures":fixtures,"screenshots":captured,"frames":frames,"demo_ids":demo,"scope":"Native Windows Godot/GPU, shipped draw_unit and articulated rig functions. Controlled pose gallery, 15fps slow offline inspection video. Actual damage/timing separately tested; not gameplay or Android hardware evidence.","inputs":{}}
	for p in ["res://scripts/unit_motion.gd","res://scripts/worker_motion.gd","res://scripts/battle_view.gd","res://data/assets.json","res://data/unit-actions.json","res://data/action-rig-provenance.json","res://tests/record_unit_actions.gd"]:report.inputs[p]=FileAccess.get_sha256(p)
	var file=FileAccess.open(folder+"/gallery-report.json",FileAccess.WRITE);file.store_string(JSON.stringify(report,"\t"));file.close()
	print("NATIVE_ACTION_GALLERY ",JSON.stringify({"units":report.units,"frames":frames,"captures":captured.size()}));quit(0)
