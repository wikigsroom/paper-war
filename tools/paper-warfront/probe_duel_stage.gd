extends SceneTree
const App=preload("res://scripts/main.gd")
const Duel=preload("res://scripts/local_duel.gd")
const Simulation=preload("res://scripts/battle_sim.gd")
func _initialize():call_deferred("run")
func run():
	var app=App.new();root.add_child(app);await process_frame;app.set_process(false)
	var records: Array=[];var good: bool=true
	var settings: Dictionary={"map":"map.08.20","faction":"shuang","enemy":"mo","seed":137}
	# Local two-player is explicitly guarded below 800x600 by the real entry.
	for area in [Vector2(568,304),Vector2(640,254)]:
		app.ui.size=area;app.start_local_duel(settings)
		var blocked: bool=not is_instance_valid(app.local_duel)
		records.append({"area":str(area),"local_entry_blocks_unsupported_size":blocked,"passed":blocked});good=good and blocked
	var scenarios: Array=[{"area":Vector2(1600,900),"side":-1},{"area":Vector2(800,600),"side":-1}]
	for area in [Vector2(568,304),Vector2(640,254)]:
		for side in [0,1]:scenarios.append({"area":area,"side":side})
	for scenario in scenarios:
		var area: Vector2=scenario.area
		var duel=Duel.new();duel.size=area;duel.theme=app.theme;root.add_child(duel)
		if scenario.side<0:duel.initialize(app.db,settings)
		else:
			var sim=Simulation.new(app.db);sim.start(settings)
			duel.initialize_network(app.db,sim,scenario.side,func(_kind,_args):return {})
		duel.set_process(false)
		await process_frame
		for panel in duel.panels:
			if panel.is_empty():continue
			var view=panel.view
			var head: float=view.floor_y()+duel.sim.map.bounds.position.y*view.PY-view.unit_height("unit.mo.giant")-22
			var passed: bool=head>=view.playfield_rect().position.y
			records.append({"area":str(area),"network_side":scenario.side,"top_clearance_ui_units":(head-view.playfield_rect().position.y)*view.scale.y,"view_scale":view.scale.y,"giant_height_ui_units":view.unit_height("unit.mo.giant")*view.scale.y,"passed":passed})
			good=good and passed
		duel.queue_free();await process_frame
	var inputs: Dictionary={}
	for name_value in ["main","local_duel","battle_view","theatre_fog","mobile_ui"]:
		var path: String="res://scripts/"+name_value+".gdc"
		if FileAccess.file_exists(path):inputs[path]=FileAccess.get_sha256(path)
	var report: Dictionary={"passed":good,"version":ProjectSettings.get_setting("application/config/version"),"records":records,"inputs":inputs,"observer_sha256":FileAccess.get_sha256(get_script().resource_path),"scope":"Native compiled Control/SubViewport geometry; supported two-player sizes and mobile LAN panels on the maximum-height map. Real local entry rejects unsupported small screens. No Android hardware or human multiplayer proof."}
	var args=OS.get_cmdline_user_args()
	if args.has("--output"):
		var output: String=args[args.find("--output")+1]
		var destination=FileAccess.open(output,FileAccess.WRITE)
		if destination==null:
			push_error("Duel stage output must be a writable JSON file: "+output)
			quit(1);return
		destination.store_string(JSON.stringify(report,"  "))
	print("DUEL_STAGE ",JSON.stringify(report))
	quit(0 if good else 1)
