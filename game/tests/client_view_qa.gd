extends SceneTree
const Data=preload("res://scripts/data_store.gd")
const Simulation=preload("res://scripts/battle_sim.gd")
const ClientBattle=preload("res://scripts/client_battle.gd")
const MatchProjection=preload("res://scripts/match_projection.gd")
const View=preload("res://scripts/battle_view.gd")
const Duel=preload("res://scripts/local_duel.gd")
var submitted: Array=[]
func _initialize():call_deferred("run")
func run():
	var db=Data.new();var authority=Simulation.new(db)
	var options={"map":"map.01.01","faction":"yin","enemy":"mo","full_tech":true}
	authority.start(options);authority.ai_enabled=[false,false]
	var near: float=float(authority.bases[1].x)-3
	authority.spawn("unit.yin.axe",0,near)
	authority.spawn("unit.mo.giant",1,near-2)
	authority.visibility.refresh()
	authority.projectiles=[{"uid":900,"side":0,"x":near,"y":authority.bases[1].y,"style":"arrow","target":0,"source":0,"reflected":false}]
	var mirror=ClientBattle.new(db);mirror.start(options)
	if not mirror.apply_snapshot(MatchProjection.snapshot(authority,1)):quit(1);return
	var view=View.new();view.db=db;view.sim=mirror;view.player_side=1;view.menu=false;view.camera_x=near;view.target_camera=near
	root.add_child(view)
	var events: Array=[]
	# The synthetic observed-position missile above is a render-only fixture.
	authority.projectiles.clear()
	for i in range(180):
		authority.tick(1.0/60.0)
		events.append_array(MatchProjection.visible_events(authority,1,authority.drain_events()))
	mirror.apply_snapshot(MatchProjection.snapshot(authority,1))
	for event in events:view.on_event(event)
	await process_frame;await process_frame
	await RenderingServer.frame_post_draw
	var folder: String=ProjectSettings.globalize_path("res://../output/qa/godot/core-alignment-rc7/client-view")
	DirAccess.make_dir_recursive_absolute(folder)
	var err: Error=root.get_texture().get_image().save_png(folder+"/east-player.png")
	view.queue_free()
	var controls=Duel.new();controls.size=root.get_visible_rect().size;root.add_child(controls)
	controls.initialize_network(db,mirror,1,func(kind,args):submitted.append({"kind":kind,"args":args}))
	controls.panels[1].cards["unit.mo.blade"].pressed.emit()
	await process_frame;await RenderingServer.frame_post_draw
	var ui_err: Error=root.get_texture().get_image().save_png(folder+"/east-player-controls.png")
	var passed: bool=err==OK and ui_err==OK and controls.panels[0].is_empty() and submitted.size()==1 and submitted[0].kind=="recruit"
	controls.size=Vector2(552,304);controls.build();await process_frame
	var compact: Dictionary=controls.panels[1]
	for c in compact.cards.values()+compact.spells.values():passed=passed and c.size.x>=48 and c.size.y>=48
	passed=passed and compact.stage.size.y>=100
	controls.open_sheet(1,"research");await process_frame
	passed=passed and compact.overlay.size.y>=200
	await RenderingServer.frame_post_draw
	root.get_texture().get_image().save_png(folder+"/compact-research.png")
	print("CLIENT_VIEW_CAPTURE ",passed," actors=",mirror.units.size()," submitted=",submitted);quit(0 if passed else 1)
