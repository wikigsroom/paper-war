extends SceneTree
# Controlled real attacks use the shipped simulation and renderer. These actors
# are QA fixtures, independent of the ordinary paid AI replay.
func _initialize():call_deferred("run")
func run():
	var args=OS.get_cmdline_user_args();var folder: String=args[args.find("--output")+1]
	DirAccess.make_dir_recursive_absolute(folder)
	var app=load("res://main.tscn").instantiate();root.add_child(app);await process_frame;app.set_process(false)
	var rows: Array=[];var captures: Array=[]
	for uid in ["unit.yin.axe","unit.yin.hammer","unit.yin.spear","unit.yin.cannon","unit.ji.javelin","unit.ji.artillery","unit.yuan.archer","unit.yuan.lancer","unit.shuang.javelin","unit.shuang.mortar","unit.jin.archer","unit.bai.repeater","unit.bai.colossus","unit.mu.warden"]:
		app.start_battle({"title":app.db.name_of(uid),"faction":uid.get_slice(".",1),"enemy":"mo","map":"map.01.01","full_tech":true})
		app.sim.ai_enabled=[false,false];app.sim.units.clear();app.sim.events.clear();app.view.follow_front=false
		var actor: Dictionary=app.sim.spawn(uid,0,22);var def: Dictionary=app.db.balance.units[uid]
		var foe: Dictionary=app.sim.spawn("unit.mo.giant",1,22+minf(4,float(def.range)*.8));foe.hp=100000;foe.max_hp=100000
		app.sim.set_status(foe,"stun",20);actor.target=foe.uid;app.view.camera_x=24;app.view.target_camera=24
		var states: Dictionary={};var styles: Dictionary={};var hits: int=0
		for tick in range(210):
			app.sim.tick(1.0/60)
			for event in app.sim.drain_events():
				app.view.on_event(event);app.audio.battle_event(event,app.view.camera_x)
				if event.kind=="hit":hits+=1
			app.view.update(1.0/60,false)
			if actor.anim=="windup" and actor.anim_t>float(def.windup)*.5 and not states.has("windup"):
				states.windup=true;var path: String=uid+"-windup";await app.qa_snapshot(folder,path);captures.append(path+".png")
			if actor.anim=="attack" and not states.has("release"):
				states.release=true;var path: String=uid+"-release";await app.qa_snapshot(folder,path);captures.append(path+".png")
			for missile in app.sim.projectiles:
				styles[missile.style]=true
				var progress: float=1-float(missile.left)/float(missile.total)
				if progress>.38 and progress<.75 and not states.has("flight"):
					states.flight=true;var path: String=uid+"-flight";await app.qa_snapshot(folder,path);captures.append(path+".png")
			if tick%12==0:await process_frame
		rows.append({"id":uid,"poses":states.keys(),"projectile_styles":styles.keys(),"hits":hits,"passed":states.has("windup") and states.has("release") and hits>0 and (not str(def.attack).begins_with("projectile") or states.has("flight"))})
	var report={"passed":rows.all(func(r):return r.passed) and app.capture_errors.is_empty(),"duels":rows,"captures":captures,"capture_errors":app.capture_errors,"scope":"Controlled native GPU fixture with real windup, projectiles and damage. Not ordinary economy, performance or Android hardware evidence.","inputs":{}}
	for path in ["res://scripts/battle_view.gd","res://scripts/unit_frame_player.gd","res://scripts/battle_sim.gd","res://data/assets.json","res://data/unit-frames.json","res://data/balance-prototype.json","res://data/unit-actions.json","res://tests/record_weapon_duels.gd"]:report.inputs[path]=FileAccess.get_sha256(path)
	var file=FileAccess.open(folder+"/report.json",FileAccess.WRITE);file.store_string(JSON.stringify(report,"\t"));file.close()
	print("WEAPON_DUELS ",JSON.stringify(report.duels));quit(0 if report.passed else 1)
