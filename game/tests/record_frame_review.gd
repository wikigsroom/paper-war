extends SceneTree
const Data=preload("res://scripts/data_store.gd")
const Review=preload("res://tests/frame_review_view.gd")
var failures: Array=[]
func _initialize():call_deferred("run")
func run():
	var args=OS.get_cmdline_user_args();var out: String="user://frame-rebuild"
	if args.has("--out"):out=args[args.find("--out")+1]
	DirAccess.make_dir_recursive_absolute(out)
	root.size=Vector2i(1320,1080);root.content_scale_size=Vector2i.ZERO
	var db=Data.new();var view=Review.new();view.db=db;root.add_child(view)
	var captures: Array=[]
	for uid in db.unit_frames:
		if not db.balance.units.has(uid):continue
		view.unit_id=uid;view.queue_redraw()
		await process_frame;await RenderingServer.frame_post_draw
		var name: String=uid.replace(".","-")+".png"
		var result: int=root.get_texture().get_image().save_png(out+"/"+name)
		if result!=OK:failures.append(name)
		captures.append(name)
	var inputs={}
	for path in ["res://scripts/battle_view.gd","res://scripts/unit_frame_player.gd","res://data/unit-frames.json","res://data/balance-prototype.json","res://data/assets.json","res://tests/frame_review_view.gd","res://tests/record_frame_review.gd"]:inputs[path]=FileAccess.get_sha256(path)
	var report={"passed":failures.is_empty(),"units":captures.size(),"frames_per_unit":36,"captures":captures,"failures":failures,"inputs":inputs,"scope":"Native Windows Godot GPU. Actual draw_frame_unit and actual frame selector; controlled poses. Separate combat and AI reports verify gameplay. No Android hardware performance claim."}
	FileAccess.open(out+"/report.json",FileAccess.WRITE).store_string(JSON.stringify(report,"\t"))
	print("FRAME_REVIEW ",captures.size()," unit sheets failures ",failures.size());quit(0 if failures.is_empty() else 1)
