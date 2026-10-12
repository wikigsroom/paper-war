extends SceneTree
const App=preload("res://scripts/main.gd")
const Touch=preload("res://tests/mobile_ui_qa.gd")
var checks: Array=[]
func verify(ok: bool,note: String):checks.append({"passed":ok,"name":note})
func _initialize():call_deferred("run")
func run():
	var args=OS.get_cmdline_user_args()
	var folder: String=args[args.find("--output")+1]
	DirAccess.make_dir_recursive_absolute(folder)
	var app=App.new();root.add_child(app)
	await process_frame
	app.mode="skirmish"
	app.start_battle({"title":"补兵时间验收","faction":"yin","enemy":"mo","map":"map.01.04","full_tech":true,"starting_gold":10000})
	app.sim.ai_enabled=[false,false];app.accumulator=-100000
	await Touch.settle(app,5)
	Touch.battlefield_coverage(app,checks,"actual runtime HUD")
	if app.mobile_ui:
		Touch.audit(app,checks,"compact action strip")
		await Touch.press(app,app.mobile.orders_button);await Touch.settle(app)
		verify(app.modal=="orders","Native compact military button opens full orders")
		Touch.audit(app,checks,"orders sheet")
		var study_action=Touch.named(app.overlay,"研究科技")
		await reveal(app,study_action)
		await Touch.press(app,study_action);await Touch.settle(app)
		verify(app.modal=="tech","Research remains reachable through compact military sheet")
		app.close_overlay()
	else:
		app.orders_button.pressed.emit();await Touch.settle(app)
		verify(app.modal=="orders","Desktop compact military button opens full orders")
		Touch.named(app.overlay,"研究科技").pressed.emit();await Touch.settle(app)
		verify(app.modal=="tech","Desktop research remains reachable through military panel")
		app.close_overlay()
	app.toast_left=0;app.sim.time=12;app.update_hud();await Touch.settle(app)
	await app.qa_snapshot(folder,"00-battle-hud")
	var soldier=app.sim.spawn("unit.yin.guard",0,float(app.sim.bases[0].x)+.65)
	app.sim.map.advance(soldier,15,0);app.update_hud()
	verify(app.unit_cards["unit.yin.guard"].tooltip_text.contains("研究＋出仓＋行军"),"Desktop card combined response text installed")
	verify(app.unit_cards["unit.yin.guard"].tooltip_text.contains("首次投入还需 70") and app.unit_cards["unit.yin.guard"].tooltip_text.contains("足额金币"),"First investment cost and timing assumptions installed")
	for id in app.sim.players[0].roster:
		verify(app.sim.recruit(0,id)=="","Real paid full queue order")
	app.sim.players[0].production=.5
	app.open_queue();await Touch.settle(app,5)
	var buttons: Array=[]
	for b in app.overlay.find_children("*","Button",true,false):
		if not b.text.contains("出仓"):continue
		buttons.append(b)
		var font: Font=b.get_theme_font("font")
		var font_size: int=b.get_theme_font_size("font_size")
		var style: StyleBox=b.get_theme_stylebox("normal")
		var available: float=b.size.x-style.get_content_margin(SIDE_LEFT)-style.get_content_margin(SIDE_RIGHT)
		for line in b.text.split("\n"):
			verify(font.get_string_size(line,HORIZONTAL_ALIGNMENT_LEFT,-1,font_size).x<=available+.1,"Queue line fits button width")
	verify(buttons.size()==6,"All six orders display exit estimates")
	if app.mobile_ui:Touch.audit(app,checks,"recruitment queue")
	await app.qa_snapshot(folder,"01-queue")
	var expected: Array=app.sim.players[0].queue.duplicate();expected.remove_at(2)
	if app.mobile_ui:
		var parent: Node=buttons[2].get_parent()
		while parent!=null:
			if parent is ScrollContainer:parent.ensure_control_visible(buttons[2]);break
			parent=parent.get_parent()
		await Touch.settle(app)
		verify(Touch.clipped_rect(buttons[2]).size.is_equal_approx(buttons[2].size),"Scroll reveals entire intended cancellation target")
		await Touch.press(app,buttons[2])
	else:buttons[2].pressed.emit();await Touch.settle(app)
	verify(app.sim.players[0].queue==expected,"Cancel chooses intended middle order")
	app.close_overlay()
	if app.mobile_ui:
		app.mobile.card_info("unit.yin.guard",false);await Touch.settle(app,5)
		await Touch.scroll_to_end(app)
		var travel_visible: bool=false
		for label in app.overlay.find_children("*","Label",true,false):
			if label.text.contains("研究＋出仓＋行军"):
				await reveal(app,label)
				travel_visible=await readable_by_scroll(app,label)
		verify(travel_visible,"Complete travel estimate is reachable by scrolling")
		Touch.audit(app,checks,"unit travel info")
		await app.qa_snapshot(folder,"02-unit-info")
	app.close_overlay()
	while not app.sim.players[0].queue.is_empty():app.sim.cancel_queue(0,0)
	for i in range(3):app.sim.recruit(0,"unit.yin.guard")
	app.open_queue();await Touch.settle(app,5)
	var stale_buttons: Array=[]
	for b in app.overlay.find_children("*","Button",true,false):
		if b.text.contains("出仓"):stale_buttons.append(b)
	var elapsed: float=0
	while app.sim.players[0].queue.size()==3 and elapsed<6:
		app.sim.tick(1.0/60.0);elapsed+=1.0/60.0
	verify(app.sim.players[0].queue.size()==2,"Production advances while queue panel remains open")
	var gold_before: float=app.sim.players[0].gold
	stale_buttons[1].pressed.emit();await Touch.settle(app,5)
	verify(app.sim.players[0].queue.size()==2 and app.sim.players[0].gold==gold_before,"Stale identical-order button cannot cancel or refund another order")
	var fresh_buttons: Array=[]
	for b in app.overlay.find_children("*","Button",true,false):
		if b.text.contains("出仓"):fresh_buttons.append(b)
	verify(fresh_buttons.size()==2,"Rejected operation refreshes actual queue")
	fresh_buttons[1].pressed.emit();await Touch.settle(app,5)
	verify(app.sim.players[0].queue.size()==1 and is_equal_approx(app.sim.players[0].gold,gold_before+float(app.db.balance.units["unit.yin.guard"].gold)),"Refreshed button cancels and refunds exact order")
	app.close_overlay()
	if app.mobile_ui:
		var fork: Dictionary=app.sim.map.fork_nodes(0)[0]
		var old: String=app.sim.map.choices[0][fork.node]
		var half_world: float=app.mobile.playfield.size.x/app.view.scale.x/app.view.PX*.5
		Touch.camera(app,float(fork.position[0])+half_world*.86);await Touch.settle(app,5)
		var marker: Rect2=app.view.route_sign_rect(0,fork)
		verify(marker.has_area() and app.view.mobile_playfield.encloses(marker),"Edge route marker is entirely inside actual compiled playfield")
		await Touch.tap(app,app.view.to_global(marker.get_center()))
		verify(app.sim.map.choices[0][fork.node]!=old,"Actual touch on clamped compiled marker changes route")
		await app.qa_snapshot(folder,"03-road-edge")
	await check_shared_controls(app,folder)
	var passed: bool=app.capture_errors.is_empty()
	for item in checks:passed=passed and item.passed
	var report={"passed":passed,"checks":checks,"scope":"Native Windows GPU UI and injected phone touch; no Android hardware proof"}
	report["inputs"]={}
	for path in ["res://scripts/main.gd","res://scripts/mobile_ui.gd","res://scripts/recruitment_readiness.gd","res://scripts/battle_view.gd","res://scripts/action_card.gd","res://scripts/mobile_scroll.gd","res://scripts/local_duel.gd","res://scripts/duel_scroll.gd","res://tests/recruitment_ui_qa.gd"]:
		report.inputs[path]=FileAccess.get_sha256(path)
	var file=FileAccess.open(folder+"/report.json",FileAccess.WRITE);file.store_string(JSON.stringify(report,"  "));file.close()
	print("RECRUITMENT_UI_QA ",JSON.stringify(report));quit(0 if passed else 1)

func sub_touch(panel: Dictionary,position: Vector2,pressed: bool):
	var event=InputEventScreenTouch.new();event.position=position;event.index=0;event.pressed=pressed
	panel.viewport.push_input(event,true);await process_frame

func reveal(app,control: Control):
	if control==null:return
	var parent: Node=control.get_parent()
	while parent!=null:
		if parent is ScrollContainer:
			parent.ensure_control_visible(control);await Touch.settle(app);return
		parent=parent.get_parent()

func readable_by_scroll(app,control: Control) -> bool:
	if Touch.clipped_rect(control).size.is_equal_approx(control.size):return true
	var sc: Node=control.get_parent()
	while sc!=null and not sc is ScrollContainer:sc=sc.get_parent()
	if sc==null:return false
	# A paragraph can exceed a small viewport. Verify the union of actual
	# visible spans covers all of it, without gaps or horizontal clipping.
	var bar=sc.get_v_scroll_bar();var maximum: int=ceili(bar.max_value-bar.page)
	var covered_to: float=0
	var stops: Array=[];var position: int=0;var step: int=maxi(16,int(sc.size.y*.65))
	while position<maximum:stops.append(position);position+=step
	stops.append(maximum)
	for stop in stops:
		sc.scroll_vertical=stop;await Touch.settle(app,2)
		var visible: Rect2=Touch.clipped_rect(control)
		if not visible.has_area():continue
		if absf(visible.size.x-control.size.x)>.2:return false
		var start: float=visible.position.y-control.get_global_rect().position.y
		if start>covered_to+.2:return false
		covered_to=maxf(covered_to,start+visible.size.y)
		if covered_to>=control.size.y-.2:return true
	return false

func sub_tap(panel: Dictionary,control: Control):
	await sub_touch(panel,control.get_global_rect().get_center(),true)
	await sub_touch(panel,control.get_global_rect().get_center(),false)
	await process_frame

func check_shared_controls(app,folder: String):
	# LAN UI fixtures use a command sender with actual simulation requests.
	# They do not establish a human match, TCP delivery or Android hardware.
	app.set_process(false);app.set_process_input(false);app.set_process_unhandled_input(false);app.clear_ui();app.view.hide()
	for mode_value in (["network-west","network-east"] if app.mobile_ui else ["split","network-west","network-east"]):
		var duel=app.LocalDuel.new();duel.size=app.ui.size;duel.theme=app.theme;app.ui.add_child(duel)
		var side: int=1 if mode_value=="network-east" else 0
		if mode_value=="split":duel.initialize(app.db,app.options)
		else:duel.initialize_network(app.db,app.sim,side,func(kind,args):app.sim.request(side,kind,args))
		duel.set_process(false);duel.sim.ai_enabled=[false,false];duel._process(0)
		await Touch.settle(app,5)
		var visible: float=0
		for p in duel.panels:
			if p.is_empty():continue
			var stage: Rect2=Rect2(p.view.to_global(p.view.playfield_rect().position),p.view.playfield_rect().size*p.view.scale)
			var navigator: Rect2=Rect2(p.view.to_global(p.view.minimap_rect().position),p.view.minimap_rect().size*p.view.scale)
			visible+=stage.get_area()-stage.intersection(navigator).get_area()
			for rail in p.rails:visible-=stage.intersection(rail.get_global_rect()).get_area()
			var exit_button=Touch.named(duel,"返回")
			if duel.external_driver and exit_button!=null:
				var absolute_stage: Rect2=Rect2(stage.position+p.container.get_global_rect().position,stage.size)
				visible-=absolute_stage.intersection(exit_button.get_global_rect()).get_area()
			verify(p.cards.size()==7 and p.spells.size()==5,"Shared HUD retains full roster and five spells "+mode_value)
		var ratio: float=visible/app.get_viewport().get_visible_rect().get_area()
		checks.append({"passed":ratio>=.70,"name":"shared "+mode_value+" at least 70 percent unobscured battlefield","details":{"visible_ratio":ratio}})
		var panel: Dictionary=duel.panels[side]
		var id: String=duel.sim.production_ids(side)[0]
		while not duel.sim.players[side].queue.is_empty():duel.sim.cancel_queue(side,0)
		var cash: float=duel.sim.players[side].gold
		panel.recruit_scroll.ensure_control_visible(panel.cards[id]);await Touch.settle(app)
		await sub_tap(panel,panel.cards[id])
		verify(duel.sim.players[side].queue==[id] and is_equal_approx(cash-duel.sim.players[side].gold,float(app.db.balance.units[id].gold)),"Shared native button issues one real paid order "+mode_value)
		duel._process(0);await sub_tap(panel,panel.orders);await Touch.settle(app,5)
		verify(is_instance_valid(panel.overlay),"Shared native military menu opens "+mode_value)
		var queue_action=Touch.named(panel.overlay,"招募队列")
		if queue_action==null:
			print("SHARED_MENU_DIAGNOSTIC ",mode_value," ",panel.overlay.get_children())
			await app.qa_snapshot(folder,"04-orders-debug-"+mode_value)
		else:
			var menu_scroll=queue_action.get_parent().get_parent();menu_scroll.ensure_control_visible(queue_action);await Touch.settle(app)
			await sub_tap(panel,queue_action);await Touch.settle(app)
		panel=duel.panels[side]
		var cancel
		for b in panel.overlay.find_children("*","Button",true,false):
			if b.is_visible_in_tree() and (b.text.contains("退还") or b.text.contains("退款")):cancel=b;break
		if cancel==null:
			var descriptions: Array=[]
			for b in panel.overlay.find_children("*","Button",true,false):descriptions.append({"text":b.text,"rect":str(b.get_global_rect()),"visible":b.is_visible_in_tree()})
			print("SHARED_QUEUE_DIAGNOSTIC ",JSON.stringify({"buttons":descriptions,"kind":panel.get("sheet_kind",""),"queue":duel.sim.players[side].queue}))
			await app.qa_snapshot(folder,"04-orders-after-"+mode_value)
		verify(cancel!=null,"Shared queue remains reachable from military menu "+mode_value)
		if cancel!=null:await sub_tap(panel,cancel)
		verify(duel.sim.players[side].queue.is_empty() and is_equal_approx(cash,duel.sim.players[side].gold),"Shared exact order refunded through native queue "+mode_value)
		duel.close_sheet(side);await Touch.settle(app)
		var point: Vector2=panel.recruit_scroll.get_global_rect().get_center()
		await sub_touch(panel,point,true)
		var drag=InputEventScreenDrag.new();drag.index=0;drag.position=point-Vector2(96,0);drag.relative=Vector2(-96,0);drag.screen_relative=drag.relative;panel.viewport.push_input(drag,true);await process_frame
		await sub_touch(panel,drag.position,false)
		verify(duel.sim.players[side].queue.is_empty() and panel.recruit_scroll.touch_finger==-1,"Shared recruit swipe never buys "+mode_value)
		panel.recruit_scroll.velocity=0;panel.recruit_scroll.set_process(false);panel.recruit_scroll.scroll_horizontal=0
		var spell: String=app.db.spell_ids(duel.sim.players[side].faction)[0]
		await sub_tap(panel,panel.spells[spell]);duel._process(0)
		verify(panel.view.selected_spell==spell and panel.orders.text=="取消","Shared manual spell and quick cancel coexist "+mode_value)
		await sub_tap(panel,panel.orders);verify(panel.view.selected_spell=="","Shared quick cancel clears selected spell "+mode_value)
		await app.qa_snapshot(folder,"04-"+mode_value)
		duel.hide();duel.queue_free();await Touch.settle(app)
