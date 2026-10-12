extends SceneTree
# Fixed native-render poses to compare geometry and atlas selection caches.
# Deliberately frozen fixtures: these captures are not real-time play evidence.
const App=preload("res://scripts/main.gd")
var app
var folder: String
var shots: Array=[]
func _initialize():call_deferred("run")
func render(name_value: String):
	app.update_hud();app.view.queue_redraw()
	await process_frame;await process_frame;await RenderingServer.frame_post_draw
	var path: String=folder+"/"+name_value+".png"
	var img: Image=root.get_texture().get_image()
	if img.save_png(path)!=OK:quit(2);return
	shots.append({"path":path,"sha256":FileAccess.get_sha256(path),"size":str(img.get_size()),"camera_x":app.view.camera_x,"simulation_seconds":app.sim.time})
func run():
	var args=OS.get_cmdline_user_args();folder=args[args.find("--output")+1]
	DirAccess.make_dir_recursive_absolute(folder)
	app=App.new();root.add_child(app);await process_frame
	app.set_process(false);app.audio.silent=true;app.audio.set_background(true);app.mode="skirmish"
	for map_id in ["map.01.01","map.01.04","map.01.11"]:
		app.start_battle({"title":"纸层与动作缓存对照","map":map_id,"faction":"yin","enemy":"mu","full_tech":true,"seed":137})
		app.sim.ai_enabled=[false,false];app.sim.units.clear();app.sim.events.clear()
		var edge_ids: Array=app.sim.map.edges.keys()
		for side in [0,1]:
			var ids: Array=app.sim.players[side].roster
			for i in range(ids.size()):
				var u=app.sim.spawn(ids[i],side,app.sim.map.length*.5-3+float(i)*.65+float(side)*1.2)
				var edge: String=edge_ids[i%edge_ids.size()]
				app.sim.map.apply_anchor(u,app.sim.map.anchor(edge,app.sim.map.edges[edge].length*(.35+float(i%4)*.12)))
				u.age=2.4;u.walk=.35;u.anim_t=.17;u.anim=["idle","walk","windup","attack","reload","mine","bound"][i%7]
				if u.anim=="reload":u["reload_left"]=.6;u["reload_duration"]=1.0
				if app.db.balance.units[u.id].get("economy",false):
					u.anim="mine";u.job_time=.4;u["work_duration"]=1.0;u.cargo=5
				if i%3==0:u.statuses["protect"]={"left":2,"source":side};u.statuses["cold"]={"left":2,"source":1-side}
		app.sim.visibility.refresh()
		app.view.visual_time=2.4;app.view.follow_front=false;app.view.shake=0
		for camera_index in [0,1]:
			app.view.camera_x=app.sim.map.length*.5+float(camera_index)*3.173
			app.view.target_camera=app.view.camera_x
			await render(map_id+"-"+str(camera_index))
	var inputs: Dictionary={}
	for file in ["scripts/battle_view","scripts/theatre_ground","scripts/unit_frame_player","scripts/battle_sim","scripts/battle_visibility"]:
		var path: String="res://"+file+(".gd" if FileAccess.file_exists("res://"+file+".gd") else ".gdc")
		inputs[path]=FileAccess.get_sha256(path)
	FileAccess.open(folder+"/report.json",FileAccess.WRITE).store_string(JSON.stringify({"scope":"Fixed native GPU paper terrain/shadow/status/whole-body pose cache fixtures across short, branched and long maps at two subpixel camera positions. No gameplay timing or Android hardware claim.","inputs":inputs,"observer_sha256":FileAccess.get_sha256(get_script().resource_path),"captures":shots},"  "))
	print("RENDER_CACHE_EQUIVALENCE captures=",shots.size());quit()
