extends SceneTree
const Data=preload("res://scripts/data_store.gd")
const Frames=preload("res://scripts/unit_frame_player.gd")
var checks: Array=[]
var failures: Array=[]
func _initialize():call_deferred("run")
func check(ok: bool,note: String):
	checks.append({"name":note,"passed":ok})
	if not ok:failures.append(note)
func run():
	var db=Data.new();check(db.unit_frames.size()==db.balance.units.size(),"every active actor has a complete frame sheet")
	for uid in db.balance.units:
		if not db.unit_frames.has(uid):check(false,uid+" missing actual frames");continue
		var p: Dictionary=db.unit_frames[uid].duplicate(true);p["windup"]=float(db.balance.units[uid].get("windup",.3))
		check(p.frame_count==36 and p.columns==6 and p.rows==6,uid+" complete 36 frame production layout")
		check(ResourceLoader.exists(p.atlas) and ResourceLoader.exists(p.portrait),uid+" native imported sprite and portrait")
		check(p.normalization.one_scale_for_all_36_frames and p.normalization.fixed_anchor,uid+" shared scale and ground anchor")
		check(p.source.begins_with("output/imagegen/paper-warfront/frame-rebuild/v2/") and db.balance.units[uid].identity_version==2,uid+" new identity source is active")
		var u={"uid":0,"age":0.0,"walk":0.0,"anim":"windup","anim_t":float(p.windup)*.99,"hurt":0.0,"visual_special":0.0,"visual_load":0.0,"job_time":0.0,"work_duration":2.8}
		if not db.balance.units[uid].get("economy",false):
			check(Frames.selection(u,p).frame==14,uid+" preparation reaches final anticipation frame")
			u.anim="attack";u.anim_t=0;check(Frames.selection(u,p).frame==15,uid+" actual release begins distinct impact frame")
		u.anim="death";u.anim_t=.70;u.visual_special=.5;check(Frames.selection(u,p).frame==29,uid+" death finishes lying frame even with stale special effect")
		u.anim="idle";u.visual_special=0;u.hurt=.30;check(Frames.selection(u,p).state=="hurt",uid+" actual incoming damage selects whole drawn hurt pose")
		u.hurt=0;u.anim="queue";u.job_time=2;check(Frames.selection(u,p).state=="queue",uid+" queued pose never mines")
		if db.balance.units[uid].get("economy",false):
			u.anim="mine";u.job_time=.95*.45;check(Frames.selection(u,p).frame==14,uid+" mining preparation raises the tool before impact")
			u.anim="mine";u.job_time=.95*.57;check(Frames.selection(u,p).frame==15,uid+" actual service strike matches pick impact frame")
			u.job_time=.95*1.57;check(Frames.selection(u,p).frame==15,uid+" repeated service cycles keep stroke aligned")
			u.anim="unload";u.job_time=.55;u.work_duration=1;check(Frames.selection(u,p).state=="unload",uid+" actual unload uses separate drawings")
		for frame in range(36):
			var r: Rect2=Frames.region(p,frame);check(r.position.x>=0 and r.position.y>=0 and r.end.x<=1152 and r.end.y<=1152,uid+" frame "+str(frame)+" remains in atlas")
	# Browsing and successive matches must not retain all 72 uncompressed atlases.
	for uid in db.unit_frames:db.texture(db.unit_frames[uid].atlas)
	var atlases: Array=db.textures.keys().filter(func(path):return str(path).ends_with("-atlas.png"))
	check(atlases.size()<=18,"native unit atlas cache stays within mobile memory budget")
	var portrait: String=db.unit_frames.values()[0].portrait;db.texture(portrait);db.release_unit_atlases()
	check(db.textures.keys().all(func(path):return not str(path).ends_with("-atlas.png")) and db.textures.has(portrait),"returning to menu releases full sheets while retaining small UI icons")
	var inputs={}
	for path in ["res://scripts/unit_frame_player.gd","res://scripts/data_store.gd","res://scripts/battle_view.gd","res://data/unit-frames.json","res://data/unit-actions.json","res://data/balance-prototype.json","res://tests/test_frame_contracts.gd"]:inputs[path]=FileAccess.get_sha256(path)
	var args=OS.get_cmdline_user_args();var out: String=args[args.find("--report")+1] if args.has("--report") else "user://frames.json"
	FileAccess.open(out,FileAccess.WRITE).store_string(JSON.stringify({"passed":failures.is_empty(),"checks":checks,"failures":failures,"units":db.unit_frames.size(),"inputs":inputs,"scope":"Fixed anchor/scale, complete actual frame bindings, preparation/release and actual mining strike alignment. Native image/animation inspection is a separate required gate."},"\t"))
	print("FRAME_CONTRACTS ",checks.size()," checks failures ",failures);quit(0 if failures.is_empty() else 1)
