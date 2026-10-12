extends SceneTree
const App=preload("res://scripts/main.gd")
var checks: Array=[]
func verify(ok: bool,note: String):
	checks.append({"name":note,"passed":ok})
func click(viewport: SubViewport,control: Control):
	var point: Vector2=control.get_global_rect().get_center()
	await click_point(viewport,point)
func click_point(viewport: SubViewport,point: Vector2):
	var container: Control=viewport.get_parent()
	var window_viewport: Viewport=container.get_viewport()
	point=window_viewport.get_final_transform()*(container.get_global_transform()*point)
	var motion=InputEventMouseMotion.new();motion.position=point;window_viewport.push_input(motion,false)
	await process_frame
	for pressed in [true,false]:
		var event=InputEventMouseButton.new();event.button_index=MOUSE_BUTTON_LEFT;event.pressed=pressed;event.position=point
		window_viewport.push_input(event,false);await process_frame
func touch_card(viewport: SubViewport,control: Control,index: int,pressed: bool):
	var container: Control=viewport.get_parent();var window_viewport: Viewport=container.get_viewport()
	var point: Vector2=window_viewport.get_final_transform()*(container.get_global_transform()*control.get_global_rect().get_center())
	var event=InputEventScreenTouch.new();event.index=index;event.position=point;event.pressed=pressed
	window_viewport.push_input(event,false);await process_frame
func run():
	var args=OS.get_cmdline_user_args();var folder: String=args[args.find("--output")+1]
	DirAccess.make_dir_recursive_absolute(folder)
	var app=App.new();root.add_child(app);await process_frame
	app.start_local_duel({"title":"双人验收","faction":"yin","enemy":"mo","map":"map.01.04","starting_gold":800,"enemy_starting_gold":800,"full_tech":false})
	await process_frame
	var duel=app.local_duel;duel.set_process(false)
	verify(duel.sim.ai_enabled==[false,false],"both seats are human")
	for side in range(2):
		var panel: Dictionary=duel.panels[side];var player: Dictionary=duel.sim.players[side]
		verify(panel.view.player_side==side and panel.view.sim==duel.sim,"shared simulation with independent perspective "+str(side))
		verify(panel.cards.size()==7 and panel.spells.size()==5,"complete faction controls "+str(side))
		for card in panel.cards.values()+panel.spells.values():verify(card.size.x>=48 and card.size.y>=48,"touch size "+str(side)+card.title)
		var id: String=duel.sim.production_ids(side)[0];var gold: float=player.gold
		await click(panel.viewport,panel.cards[id])
		verify(player.queue==[id] and player.gold==gold-float(app.db.balance.units[id].gold),"native paid recruit for seat "+str(side))
		duel.open_sheet(side,"queue");await process_frame
		var buttons=panel.overlay.find_children("*","Button",true,false)
		if buttons.size()<2:
			print("DUEL_INPUT_DIAGNOSTIC ",side," queue=",player.queue," gold=",player.gold," message=",panel.message," rect=",panel.cards[id].get_global_rect())
			await app.qa_snapshot(folder,"failed-input");quit(1);return
		await click(panel.viewport,buttons[1])
		verify(player.queue.is_empty() and player.gold==gold,"native queue refund for seat "+str(side))
		duel.close_sheet(side)
		duel.open_sheet(side,"research");await process_frame
		var study_buttons=panel.overlay.find_children("*","Button",true,false).filter(func(b):return b.text!="返回战场" and not b.disabled)
		await click(panel.viewport,study_buttons[0])
		verify(not player.research.is_empty() and player.gold<gold,"native technology investment for seat "+str(side))
		duel.open_sheet(side,"build");await process_frame
		var mana_id: String="building."+player.faction+".mana"
		var build_buttons=panel.overlay.find_children("*","Button",true,false).filter(func(b):return not b.disabled and b.text.contains(app.db.name_of(mana_id)))
		var before_build: float=player.gold
		await click(panel.viewport,build_buttons[-1])
		verify(duel.sim.stats[side].buildings==1 and player.gold==before_build-float(app.db.balance.buildings[mana_id].gold),"native paid facility construction for seat "+str(side))
	var unit0: String=duel.sim.production_ids(0)[0];var unit1: String=duel.sim.production_ids(1)[0]
	await touch_card(duel.panels[0].viewport,duel.panels[0].cards[unit0],0,true)
	await touch_card(duel.panels[1].viewport,duel.panels[1].cards[unit1],1,true)
	await touch_card(duel.panels[0].viewport,duel.panels[0].cards[unit0],0,false)
	await touch_card(duel.panels[1].viewport,duel.panels[1].cards[unit1],1,false)
	verify(duel.sim.players[0].queue==[unit0] and duel.sim.players[1].queue==[unit1],"two simultaneous fingers independently recruit for both seats")
	await touch_card(duel.panels[0].viewport,duel.panels[0].cards[unit0],2,true)
	await create_timer(.7).timeout
	verify(is_instance_valid(duel.panels[0].overlay) and duel.sim.players[0].queue==[unit0],"long press opens information without recruitment")
	await touch_card(duel.panels[0].viewport,duel.panels[0].cards[unit0],2,false)
	duel.close_sheet(0)
	duel.sim.units.clear()
	var ally=duel.sim.spawn("unit.yin.axe",0,20);ally.hp=60
	var enemy=duel.sim.spawn("unit.mo.blade",1,21);enemy.hp=60;duel.sim.visibility.refresh()
	for panel in duel.panels:
		panel.view.camera_x=20;panel.view.target_camera=20
	duel._process(0)
	await process_frame
	var p0: Dictionary=duel.panels[0];var p1: Dictionary=duel.panels[1]
	await click(p0.viewport,p0.spells["spell.yin.repair"])
	await click_point(p0.viewport,(p0.view.unit_position(ally)-Vector2(0,35))*p0.view.scale)
	verify(ally.hp==145 and duel.sim.stats[0].casts==1,"seat0 heals own target through shared command")
	await click(p1.viewport,p1.spells["spell.mo.bind"])
	await click_point(p1.viewport,(p1.view.unit_position(ally)-Vector2(0,35))*p1.view.scale)
	verify(ally.statuses.has("bind") and duel.sim.stats[1].casts==1,"seat1 targets its visible opponent")
	duel.sim.map.apply_anchor(ally,duel.sim.map.at_node(duel.sim.map.definition.bases[0].node,0));duel.sim.visibility.refresh()
	verify(not duel.sim.visible_to(1,ally) and p1.view.target_at(p1.view.unit_position(ally)-Vector2(0,35))==0,"seat1 cannot target hidden western enemy")
	duel._process(0);await app.qa_snapshot(folder,"01-dual-HUD")
	var start_time: float=duel.sim.time
	for i in range(120):duel._process(1.0/60.0)
	verify(absf(duel.sim.time-start_time-2)<.0001,"two views advance one shared 60Hz simulation, not twice")
	verify(duel.sim.players[0].queue.is_empty() and duel.sim.players[1].queue.is_empty(),"both human production timers complete normally")
	duel.halted=true;var time: float=duel.sim.time;var gold: float=duel.sim.players[0].gold
	duel._process(.5);verify(duel.sim.time==time and not duel.issue(0,"recruit",{"id":"unit.yin.axe"}).ok and duel.sim.players[0].gold==gold,"shared pause blocks simulation and commands")
	duel.set_paused(false);app._notification(app.NOTIFICATION_APPLICATION_PAUSED)
	verify(duel.halted,"background pauses both human seats")
	app._notification(app.NOTIFICATION_APPLICATION_RESUMED)
	verify(duel.halted,"foreground does not resume without explicit action")
	duel.size=Vector2(800,600);duel.build();await process_frame;await process_frame
	for panel in duel.panels:
		verify(panel.cards.values().all(func(c):return c.size.x>=48 and c.size.y>=48),"minimum split size retains valid touch cards")
	verify(duel.sim.time==time and duel.sim.players[0].gold==gold,"layout rebuild preserves shared match state")
	duel._process(0);await app.qa_snapshot(folder,"02-minimum-split")
	var failures: Array=checks.filter(func(c):return not c.passed)
	var report={"scope":"Actual native Windows GPU, two SubViewport human seats, mouse recruit/refund/research/build/cast, simultaneous ScreenTouch, long press, shared timers, background and layout rebuild; not LAN, Android hardware or human usability.","passed":failures.is_empty() and app.capture_errors.is_empty(),"checks":checks,"failures":failures,"inputs":{"duel":FileAccess.get_sha256("res://scripts/local_duel.gd"),"view":FileAccess.get_sha256("res://scripts/battle_view.gd"),"main":FileAccess.get_sha256("res://scripts/main.gd"),"simulation":FileAccess.get_sha256("res://scripts/battle_sim.gd")}}
	var file=FileAccess.open(folder+"/report.json",FileAccess.WRITE);file.store_string(JSON.stringify(report,"  "));file.close()
	print("LOCAL_DUEL_QA ",JSON.stringify({"passed":report.passed,"checks":checks.size(),"failures":failures}));quit(0 if report.passed else 1)
func _initialize():call_deferred("run")
