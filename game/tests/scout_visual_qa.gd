extends SceneTree
const App=preload("res://scripts/main.gd")
func run():
	var args=OS.get_cmdline_user_args();var folder: String=args[args.find("--output")+1]
	DirAccess.make_dir_recursive_absolute(folder)
	var app=App.new();root.add_child(app)
	await process_frame
	app.mode="skirmish";app.start_battle({"title":"侦察与旧情报验收","faction":"yin","enemy":"mo","map":"map.01.01","starting_gold":1000,"enemy_starting_gold":1000,"full_tech":true})
	app.sim.ai_enabled=[false,false];app.sim.units.clear();app.sim.time=10
	var slot: int=app.sim.side_sites(1).size()-1
	var site: Dictionary=app.sim.slot_anchor(1,slot)
	app.sim.request(1,"build",{"id":"building.mo.mana","slot":slot})
	var building: Dictionary=app.sim.buildings[0];building.state="active";building.construction=0
	var scout=app.sim.spawn("unit.yin.axe",0,site.x-2)
	var giant=app.sim.spawn("unit.mo.giant",1,site.x-1)
	app.sim.visibility.refresh();app.view.follow_front=false;app.view.camera_x=site.x-4;app.view.target_camera=site.x-4
	await app.qa_snapshot(folder,"01-revealed")
	var key=InputEventKey.new();key.keycode=KEY_7;key.physical_keycode=KEY_7;key.pressed=true
	app.get_viewport().push_input(key,true);await process_frame
	var seventh_key: bool=app.sim.players[0].queue==["unit.yin.worker"]
	app.paused=true;app.accumulator=-100000;app.sim.map.apply_anchor(scout,app.sim.map.at_node(app.sim.map.definition.bases[0].node,0))
	app.sim.visibility.refresh();app.update_hud();await app.qa_snapshot(folder,"02-hidden-history")
	var retained: bool=app.sim.visibility.last_seen[0].has(building.uid) and not app.sim.visible_to(0,building)
	building.hp=0;app.sim.visibility.refresh()
	var hidden_retained: bool=app.sim.visibility.last_seen[0].has(building.uid)
	app.sim.map.apply_anchor(scout,site);app.sim.visibility.refresh();app.update_hud()
	await app.qa_snapshot(folder,"03-revisited-clear")
	var cleared: bool=not app.sim.visibility.last_seen[0].has(building.uid)
	var report={"scope":"Native Windows GPU snapshots of controlled reveal, lost vision and hidden destruction followed by revisit, plus real key-7 input; not Android hardware.","passed":retained and hidden_retained and cleared and seventh_key and app.capture_errors.is_empty(),"key_7_recruits_worker":seventh_key,"remembered_hidden":retained,"hidden_destruction_retained":hidden_retained,"revisit_clears":cleared,"inputs":{"view":FileAccess.get_sha256("res://scripts/battle_view.gd"),"visibility":FileAccess.get_sha256("res://scripts/battle_visibility.gd"),"main":FileAccess.get_sha256("res://scripts/main.gd")}}
	var file=FileAccess.open(folder+"/report.json",FileAccess.WRITE);file.store_string(JSON.stringify(report,"  "));file.close()
	print("SCOUT_VISUAL_QA ",JSON.stringify(report));quit(0 if report.passed else 1)
func _initialize():call_deferred("run")
