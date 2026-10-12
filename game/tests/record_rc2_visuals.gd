extends SceneTree
# Native rendering of actual worker state transitions; not a performance benchmark.
var app
var folder: String
var evidence: Array=[]
func _initialize():call_deferred("run")
func save_image(name: String):
	app.update_hud();app.view.queue_redraw()
	await process_frame;await RenderingServer.frame_post_draw
	get_root().get_texture().get_image().save_png(folder+"/"+name+".png")
func run():
	var args=OS.get_cmdline_user_args();folder=args[args.find("--output")+1]
	DirAccess.make_dir_recursive_absolute(folder)
	DirAccess.make_dir_recursive_absolute(folder+"/frames")
	app=load("res://main.tscn").instantiate();root.add_child(app)
	await process_frame;app.set_process(false)
	app.main_menu();await save_image("menu")
	app.campaign_menu(0);await save_image("campaign")
	app.show_brief(app.db.campaign[3],"campaign");await save_image("brief")
	for f in (["yin"] if args.has("--quick") else app.db.FACTIONS):
		app.mode="skirmish"
		var map_id: String="map.%02d.07"%(app.db.FACTIONS.find(f)+1)
		app.start_battle({"title":app.db.FACTION_NAMES[f]+" · 矿路与军阵","map":map_id,"faction":f,"enemy":"mo","starting_gold":230,"enemy_starting_gold":210,"full_tech":false})
		app.sim.ai_enabled=[false,false];app.toast_left=0;app.view.camera_x=9.5;app.view.target_camera=9.5
		var mine: Dictionary=app.sim.map.definition.mines.filter(func(m):return m.owner==0 and m.capacity==1)[0]
		app.sim.request(0,"mine_priority",{"mine":mine.id})
		var captured: Dictionary={};var strikes: int=0
		for step in range(60*13):
			app.sim.tick(1.0/60.0);app.view.update(1.0/60.0)
			for e in app.sim.drain_events():app.view.on_event(e);app.audio.battle_event(e,app.view.camera_x);strikes+=1 if e.kind=="mine_strike" and e.side==0 else 0
			var workers: Array=app.sim.units.filter(func(u):return u.side==0 and u.id.ends_with(".worker"))
			for u in workers:
				if u.anim=="mine":
					var phase: float=fmod(float(u.job_time),.95)/.95
					for marker in [.30,.56,.79]:
						var key: String="mine-"+str(int(marker*100))
						if not captured.has(key) and absf(phase-marker)<.018:
							await save_image(f+"-"+key);captured[key]=true
							evidence.append({"pose":f+"-"+key,"workers":workers.map(func(w):return {"uid":w.uid,"anim":w.anim,"s":w.s,"slot":w.get("work_slot",-1),"position":[app.view.unit_position(w).x,app.view.unit_position(w).y],"facing":w.facing})})
				elif u.anim=="unload" and not captured.has("unload"):
					await save_image(f+"-unload");captured["unload"]=true
			if not args.has("--quick") and f=="yin" and step%4==0:
				await save_image("frames/mining-%04d"%(step/4))
			if step%120==0:await process_frame
		evidence.append({"faction":f,"map":map_id,"captured":captured.keys(),"strikes":strikes,"gold_deposited":app.sim.stats[0].gold_delivered})
		print("NATIVE_MINING ",f," ",captured.keys())
	# Ground signatures use unchanged campaign map data, with legal paid recruits.
	for index in [0,6,10,3,11,5]:
		var config: Dictionary=app.db.campaign[index]
		app.start_battle(config);app.sim.ai_enabled=[false,false];app.toast_left=0
		var positions: Array=[10.5] if index==0 or index==6 else [app.sim.map.length*.5]
		app.view.camera_x=positions[0];app.view.target_camera=positions[0]
		for id in app.sim.players[0].roster.slice(0,2):app.sim.request(0,"recruit",{"id":id})
		for i in range(240):
			app.sim.tick(1.0/60.0);app.view.update(1.0/60.0)
			for e in app.sim.drain_events():app.view.on_event(e)
		await save_image("map-"+config.map)
	var file=FileAccess.open(folder+"/report.json",FileAccess.WRITE)
	file.store_string(JSON.stringify({"version":"3.0.0-rc2","native_renderer":RenderingServer.get_video_adapter_name(),"workers":evidence,"view_sha256":FileAccess.get_sha256("res://scripts/battle_view.gd"),"ground_sha256":FileAccess.get_sha256("res://scripts/theatre_ground.gd"),"simulation_sha256":FileAccess.get_sha256("res://scripts/battle_sim.gd")},"  "));file.close()
	quit()
