extends SceneTree
const Data=preload("res://scripts/data_store.gd")
const Review=preload("res://tests/frame_motion_view.gd")
func _initialize():call_deferred("run")
func run():
	var args=OS.get_cmdline_user_args();var out: String=args[args.find("--output")+1]
	DirAccess.make_dir_recursive_absolute(out+"/frames")
	root.size=Vector2i(1320,810);root.content_scale_size=Vector2i.ZERO
	var db=Data.new();var view=Review.new();view.db=db;root.add_child(view)
	view.review_ids=["unit.yin.spear","unit.mo.giant","unit.deng.shadow","unit.ji.javelin","unit.ji.artillery","unit.yuan.archer","unit.mu.colossus","unit.mu.warden","unit.mu.worker","unit.shuang.javelin","unit.jin.archer","unit.bai.colossus"]
	var failures: Array=[]
	for uid in view.review_ids:
		if not db.unit_frames.has(uid):failures.append("missing "+uid)
	for index in range(120):
		view.play_time=float(index)/15;view.queue_redraw()
		await process_frame;await RenderingServer.frame_post_draw
		if root.get_texture().get_image().save_png(out+"/frames/frame-%04d.png"%index)!=OK:failures.append("capture "+str(index))
	var report={"passed":failures.is_empty(),"failures":failures,"units":view.review_ids,"frames":120,"playback_fps":15,"inputs":{},"scope":"Native Windows Godot GPU, actual whole-frame selector and draw call. Offline 15fps controlled pose review; not an actual battle or realtime Android performance."}
	for path in ["res://scripts/battle_view.gd","res://scripts/unit_frame_player.gd","res://data/unit-frames.json","res://data/unit-actions.json","res://data/assets.json","res://data/balance-prototype.json","res://tests/frame_motion_view.gd","res://tests/record_frame_motion.gd"]:report.inputs[path]=FileAccess.get_sha256(path)
	FileAccess.open(out+"/report.json",FileAccess.WRITE).store_string(JSON.stringify(report,"\t"));quit(0 if failures.is_empty() else 1)
