extends RefCounted
# Native ScreenTouch / ScreenDrag injection, density / safe-area geometry and
# controlled UI fixtures. This does not claim Android device performance.
static var last_positions: Dictionary={}

static func check(checks: Array,name_value: String,passed: bool,details: Dictionary={}):
	checks.append({"name":name_value,"passed":passed,"details":details})
	if not passed:print("MOBILE_FAIL ",name_value," ",JSON.stringify(details))

static func settle(app,frames: int=3):
	for i in range(frames):await app.get_tree().process_frame

static func send(app,event: InputEvent):
	app.get_viewport().push_input(event,true)
	await app.get_tree().process_frame

static func finger(app,position: Vector2,pressed: bool,index: int=0,canceled: bool=false):
	var e=InputEventScreenTouch.new();e.index=index;e.position=position;e.pressed=pressed;e.canceled=canceled
	last_positions[index]=position
	await send(app,e)

static func drag(app,position: Vector2,index: int=0):
	var e=InputEventScreenDrag.new();e.index=index;e.position=position
	e.relative=position-last_positions.get(index,position);e.screen_relative=e.relative;last_positions[index]=position
	await send(app,e)

static func tap(app,position: Vector2,index: int=0):
	await finger(app,position,true,index);await finger(app,position,false,index);await settle(app)

static func named(parent: Node,caption: String):
	if parent==null:return null
	for child in parent.find_children("*","Button",true,false):
		if child.is_visible_in_tree() and child.text.begins_with(caption):return child
	return null

static func press(app,button):
	if button==null:return
	await tap(app,button.get_global_rect().get_center())

static func scroll_to_end(app):
	var root: Node=app.overlay if app.overlay else app.ui
	for sc in root.find_children("MobileScroll","ScrollContainer",true,false):sc.scroll_vertical=100000
	await settle(app)

static func clipped_rect(control: Control) -> Rect2:
	var rect: Rect2=control.get_global_rect();var parent: Node=control.get_parent()
	while parent!=null:
		if parent is Control and parent.clip_contents:rect=rect.intersection(parent.get_global_rect())
		parent=parent.get_parent()
	return rect

static func audit(app,checks: Array,name_value: String):
	var root: Node=app.overlay if app.overlay else app.ui
	var bounds: Rect2=app.mobile.metrics.safe if app.screen=="battle" and app.overlay==null else app.mobile.metrics.content
	var controls: Array=[]
	for control in root.find_children("*","Control",true,false):
		if not control.is_visible_in_tree() or not (control is BaseButton or control is HSlider):continue
		var rect: Rect2=control.get_global_rect()
		check(checks,name_value+" touch "+str(control.name),rect.size.x>=47.9 and rect.size.y>=47.9,{"rect":[rect.position.x,rect.position.y,rect.size.x,rect.size.y]})
		var visible: Rect2=clipped_rect(control)
		if not visible.has_area():continue
		check(checks,name_value+" safe "+str(control.name),bounds.grow(.2).encloses(visible),{"visible":[visible.position.x,visible.position.y,visible.size.x,visible.size.y]})
		controls.append(visible)
	var overlap=false
	for i in range(controls.size()):
		for j in range(i+1,controls.size()):
			if controls[i].grow(-.5).intersects(controls[j].grow(-.5)):overlap=true
	check(checks,name_value+" disjoint targets",not overlap)

static func battlefield_coverage(app,checks: Array,name_value: String) -> Dictionary:
	# Measure rendered/control rectangles, including corner controls over the stage.
	# A paper background behind an opaque HUD does not count as visible gameplay.
	var stage: Rect2=app.mobile.playfield if app.mobile_ui else Rect2(app.view.to_global(app.view.playfield_rect().position),app.view.playfield_rect().size*app.view.scale)
	var screen: Rect2=app.get_viewport().get_visible_rect()
	var covered: Array=[];var xs: Array=[stage.position.x,stage.end.x];var ys: Array=[stage.position.y,stage.end.y]
	for key in ["HudTopRail","HudBottomRail","HudPause","HudMiniMap"]:
		for control in app.ui.find_children(key+"*","Control",true,false):
			if not control.is_visible_in_tree():continue
			var rect: Rect2=control.get_global_rect().intersection(stage)
			if not rect.has_area():continue
			covered.append(rect);xs.append(rect.position.x);xs.append(rect.end.x);ys.append(rect.position.y);ys.append(rect.end.y)
	xs.sort();ys.sort()
	var blocked: float=0
	for x in range(xs.size()-1):
		for y in range(ys.size()-1):
			var cell: Rect2=Rect2(xs[x],ys[y],xs[x+1]-xs[x],ys[y+1]-ys[y])
			if covered.any(func(r):return r.has_point(cell.get_center())):blocked+=cell.get_area()
	var ratio: float=(stage.get_area()-blocked)/screen.get_area()
	var result: Dictionary={"visible_ratio":ratio,"stage":str(stage),"screen":str(screen),"covered_stage_area":blocked}
	check(checks,name_value+" at least 70 percent unobscured battlefield",ratio>=.70,result)
	return result

static func fixture(app,faction: String="yin",map_id: String="map.01.04"):
	app.db.deployments[faction]=app.db.factions[faction].core_roster.duplicate()
	app.mode="skirmish";app.start_battle({"title":"移动触屏验收","faction":faction,"enemy":"mo","map":map_id,"full_tech":true,"starting_gold":900,"enemy_starting_gold":300})
	app.sim.ai_enabled=[false,false];app.accumulator=-100000;app.view.follow_front=false;app.toast_left=0

static func camera(app,x: float):
	var half: float=minf(app.view.width/app.view.PX*.5,app.sim.map.length*.5)
	app.view.camera_x=clampf(x,half,app.sim.map.length-half);app.view.target_camera=app.view.camera_x;app.view.follow_front=false

static func run(app,folder: String):
	DirAccess.make_dir_recursive_absolute(folder)
	var checks: Array=[];var original=app.profile.duplicate(true);var deployments=app.db.deployments.duplicate(true)
	await settle(app,5)
	var size: Vector2i=app.get_window().size
	# A portrait launch must reject gameplay then recover without losing the page.
	if app.mobile_blocked:
		check(checks,"portrait guard intercepts input",not app.ui.visible and app.rotation_layer!=null)
		await app.qa_snapshot(folder,"00-portrait-guard")
		app.get_window().size=Vector2i(maxi(size.x,size.y),mini(size.x,size.y));await settle(app,8);app.refresh_mobile_layout();await settle(app)
	check(checks,"landscape startup is operable",not app.mobile_blocked and app.ui.visible,{"physical":str(app.get_window().size),"content":str(app.mobile.metrics.content)})
	if app.mobile_blocked:
		push_error("Native QA window cannot fit the required landscape density; cannot continue touch actions.")
		app.get_tree().quit(1);return
	var tested_metrics: Dictionary=app.mobile.metrics.duplicate(true)
	check(checks,"landscape logical pixels match density",app.get_viewport().get_visible_rect().size.is_equal_approx(app.mobile.metrics.viewport),{"viewport":str(app.get_viewport().get_visible_rect().size),"measured":str(app.mobile.metrics.viewport)})
	check(checks,"no touch to mouse emulation",not Input.emulate_mouse_from_touch)
	check(checks,"Android back default exit disabled",not app.get_tree().quit_on_go_back)
	audit(app,checks,"menu");await app.qa_snapshot(folder,"01-menu")
	var menu_buttons: Array=app.ui.find_children("*","Button",true,false).filter(func(b):return b.is_visible_in_tree())
	var menu_order: Array=["继续战役","新战役","成就挑战","兵书","设置"]
	check(checks,"main menu exactly five rows",menu_buttons.size()==5)
	for i in range(mini(5,menu_buttons.size())):
		var r: Rect2=menu_buttons[i].get_global_rect()
		check(checks,"main menu row "+str(i)+" order and fully visible",menu_buttons[i].text==menu_order[i] and app.mobile.metrics.content.grow(.2).encloses(r) and clipped_rect(menu_buttons[i]).size.is_equal_approx(r.size))
		if i>0:
			var previous: Rect2=menu_buttons[i-1].get_global_rect()
			check(checks,"main menu single column "+str(i),absf(r.position.x-previous.position.x)<.2 and r.position.y>=previous.end.y)
	await press(app,named(app.ui,"新战役"));check(checks,"native touch enters new battle",app.screen=="new-battle");audit(app,checks,"new battle")
	check(checks,"new battle has both choices",named(app.ui,"故事战役")!=null and named(app.ui,"遭遇战")!=null)
	app.mobile.back();await settle(app);check(checks,"new battle back returns main menu",app.screen=="menu")
	await press(app,named(app.ui,"新战役"))
	await press(app,named(app.ui,"故事战役"));check(checks,"native touch enters campaign",app.screen=="campaign");audit(app,checks,"campaign")
	await scroll_to_end(app);audit(app,checks,"campaign tail");await app.qa_snapshot(folder,"02-campaign-tail")
	for sc in app.ui.find_children("MobileScroll","ScrollContainer",true,false):sc.scroll_vertical=0
	await settle(app)
	await press(app,named(app.ui,"第 01 章"));check(checks,"chapter chooser",app.modal=="choice")
	await scroll_to_end(app);await press(app,named(app.overlay,"第 10 章"));check(checks,"last chapter selected by touch",app.campaign_chapter==9)
	app.mobile.back();await settle(app)
	app.theatre_menu();await settle(app);audit(app,checks,"six maps");await app.qa_snapshot(folder,"03-six-maps")
	app.show_brief(app.db.campaign[3],"campaign");await settle(app);audit(app,checks,"brief");await scroll_to_end(app);audit(app,checks,"brief tail");await app.qa_snapshot(folder,"04-brief")
	await press(app,named(app.overlay,"调整部署"));check(checks,"brief deployment chain",app.modal=="loadout");audit(app,checks,"loadout")
	app.mobile.back();await settle(app);check(checks,"back preserves brief",app.modal=="brief")
	app.close_overlay();app.skirmish_menu();await settle(app);audit(app,checks,"skirmish")
	await press(app,named(app.ui,"纸面山河"));check(checks,"map chooser",app.modal=="choice")
	var choice_scroll=app.overlay.find_child("MobileScroll",true,false);var scroll_start: Vector2=choice_scroll.get_global_rect().get_center()+Vector2(0,32)
	await finger(app,scroll_start,true)
	for offset in [24,48,72,96,120]:await drag(app,scroll_start-Vector2(0,offset))
	await finger(app,scroll_start-Vector2(0,120),false);await settle(app)
	check(checks,"native list swipe scrolls without choosing",app.modal=="choice" and choice_scroll.scroll_vertical>20,{"scroll":choice_scroll.scroll_vertical,"modal":app.modal})
	await scroll_to_end(app);audit(app,checks,"map chooser tail")
	var map_count: int=app.db.maps.size();var last=named(app.overlay,app.db.maps.values()[-1].name)
	await press(app,last);check(checks,"200-map selector accepts last entry",app.mobile.skirmish_values.map==map_count-1)
	app.challenge_menu();await settle(app);audit(app,checks,"challenges");await scroll_to_end(app);audit(app,checks,"challenges tail")
	app.archive_menu("bai",app.db.all_unit_ids("bai")[-1],5);await settle(app);audit(app,checks,"archive");await scroll_to_end(app);audit(app,checks,"archive tail");await app.qa_snapshot(folder,"05-library")
	app.settings_menu(false);await settle(app);audit(app,checks,"settings")
	var slider=app.overlay.find_child("MobileVolume_music",true,false);var rect: Rect2=slider.get_global_rect()
	await finger(app,rect.position+Vector2(rect.size.x*.15,rect.size.y*.5),true)
	await drag(app,rect.position+Vector2(rect.size.x*.75,rect.size.y*.5));await finger(app,rect.position+Vector2(rect.size.x*.75,rect.size.y*.5),false)
	check(checks,"native touch adjusts volume",app.profile.settings.music>.6 and app.profile.settings.music<.9,{"value":app.profile.settings.music})
	var battery=named(app.overlay,"省电模式")
	var settings_scroll=app.overlay.find_child("MobileScroll",true,false)
	settings_scroll.ensure_control_visible(battery);await settle(app)
	await press(app,battery);check(checks,"battery mode applies 30fps and effects budget",Engine.max_fps==30 and app.view.particle_budget==100)
	app.mobile.back();await settle(app);check(checks,"settings back saves and returns",app.screen=="menu")
	app.profile.settings.battery_saver=false;app.apply_mobile_quality()
	# Ten factions, all 50 spells use native touch, with isolated controlled actors.
	for faction in app.db.FACTIONS:
		fixture(app,faction,"map.%02d.01"%[app.db.FACTIONS.find(faction)+1]);await settle(app);audit(app,checks,"HUD "+faction)
		var id: String=app.sim.players[0].roster[0];var gold: float=app.sim.players[0].gold
		await press(app,app.unit_cards[id]);check(checks,"exactly one paid touch recruit "+faction,app.sim.players[0].queue==[id] and is_equal_approx(gold-app.sim.players[0].gold,float(app.db.balance.units[id].gold)))
		app.open_queue();await settle(app);audit(app,checks,"queue "+faction)
		await press(app,named(app.overlay,"1 · "));check(checks,"touch refund "+faction,app.sim.players[0].queue.is_empty() and is_equal_approx(gold,app.sim.players[0].gold))
		app.close_overlay();await settle(app);audit(app,checks,"simultaneous spells "+faction)
		battlefield_coverage(app,checks,"HUD "+faction)
		check(checks,"full recruit catalog and all five spells coexist "+faction,app.unit_cards.size()==7 and app.spell_cards.size()==5 and app.unit_cards.values().all(func(c):return c.is_visible_in_tree()) and app.spell_cards.values().all(func(c):return clipped_rect(c).size.is_equal_approx(c.size)))
		# The new strip is a real horizontal native touch scroll, never a recruit drag.
		var sc: ScrollContainer=app.mobile.recruit_scroll
		var drag_point: Vector2=sc.get_global_rect().get_center()
		var old_scroll: int=sc.scroll_horizontal;var queue_before: Array=app.sim.players[0].queue.duplicate()
		await finger(app,drag_point,true);await drag(app,drag_point-Vector2(96,0));await finger(app,drag_point-Vector2(96,0),false)
		check(checks,"native recruit swipe never buys "+faction,app.sim.players[0].queue==queue_before and sc.touch_finger==-1)
		check(checks,"native recruit swipe reveals later cards "+faction,sc.get_h_scroll_bar().max_value<=sc.size.x+1 or sc.scroll_horizontal>old_scroll)
		sc.velocity=0;sc.set_process(false)
		for unit_id in app.unit_cards:
			var recruit_card=app.unit_cards[unit_id];sc.ensure_control_visible(recruit_card);await settle(app)
			check(checks,"entire recruit touch target accessible "+unit_id,clipped_rect(recruit_card).size.is_equal_approx(recruit_card.size))
			var cash: float=app.sim.players[0].gold
			await press(app,recruit_card)
			check(checks,"scroll catalog recruits once with real price "+unit_id,app.sim.players[0].queue==[unit_id] and is_equal_approx(cash-app.sim.players[0].gold,float(app.db.balance.units[unit_id].gold)))
			if not app.sim.players[0].queue.is_empty():app.execute("cancel_queue",{"index":0,"id":unit_id,"queue_revision":app.sim.players[0].queue_revision})
		sc.scroll_horizontal=0;await settle(app)
		for spell in app.db.spell_ids(faction):
			app.sim.units.clear();app.sim.events.clear();app.sim.players[0].mana=100;app.sim.players[0].cooldowns[spell]=0
			var ally=app.sim.spawn(id,0,24);ally.hp=ally.max_hp*.5
			var enemy=app.sim.spawn("unit.mo.giant",1,26)
			var target: Dictionary=ally if spell.get_slice(".",2) in ["repair","fury","sacrifice","protect","clone"] else enemy
			if spell.ends_with(".sacrifice"):app.sim.players[0].mana=60
			app.sim.visibility.refresh();camera(app,target.x);await settle(app)
			var casts: int=app.sim.stats[0].casts
			await press(app,app.spell_cards[spell]);check(checks,"touch selects "+spell,app.view.selected_spell==spell)
			await tap(app,app.view.to_global(app.view.unit_position(target)-Vector2(0,35)))
			check(checks,"touch casts once "+spell,app.sim.stats[0].casts==casts+1 and app.view.selected_spell=="")
		if faction in ["yin","shuang","bai"]:await app.qa_snapshot(folder,"06-HUD-"+faction)
	# Gesture latching, independent fingers, HUD capture and cancellation.
	fixture(app);await settle(app);camera(app,20);app.sim.units.clear();app.sim.players[0].mana=100
	app.hud_section="spells";app.build_hud();await settle(app);await press(app,app.spell_cards["spell.yin.cold"])
	var p: Vector2=app.mobile.playfield.get_center();var casts: int=app.sim.stats[0].casts
	await finger(app,p,true);await drag(app,p+Vector2(50,0));await drag(app,p);await finger(app,p,false)
	check(checks,"drag then return never casts",app.sim.stats[0].casts==casts and app.view.selected_spell=="spell.yin.cold")
	await finger(app,p,true);await finger(app,p,false,0,true)
	check(checks,"canceled touch never casts",app.sim.stats[0].casts==casts and app.touch_input.finger==-1)
	app.cancel_selection();app.hud_section="units";app.build_hud();await settle(app)
	var recruit: String=app.sim.players[0].roster[0]
	await finger(app,app.unit_cards[recruit].get_global_rect().get_center(),true)
	await app.get_tree().create_timer(.7).timeout
	check(checks,"long press opens full unit information without paying",app.modal=="info" and app.sim.players[0].queue.is_empty())
	app.close_overlay();await settle(app)
	await finger(app,app.unit_cards[recruit].get_global_rect().get_center(),true,0)
	app.set_mobile_background(true);app.set_mobile_background(false);await settle(app);app.mobile.back();await settle(app)
	check(checks,"background cancels a held HUD button",app.sim.players[0].queue.is_empty() and app.mobile_touch_points.is_empty())
	app.accumulator=-100000
	await finger(app,p,true,0);await drag(app,p+Vector2(-48,0),0)
	await press_with_finger(app,app.unit_cards[recruit],1)
	check(checks,"second finger recruits during captured pan",app.sim.players[0].queue==[recruit] and app.touch_input.finger==0)
	var length: int=app.sim.players[0].queue.size()
	await drag(app,app.unit_cards[recruit].get_global_rect().get_center(),0);await finger(app,app.unit_cards[recruit].get_global_rect().get_center(),false,0)
	check(checks,"field drag release over HUD does not recruit",app.sim.players[0].queue.size()==length and app.touch_input.finger==-1)
	var map: Rect2=app.view.minimap_rect();var map_point: Vector2=app.view.to_global(map.position+Vector2(map.size.x*.9,map.size.y*.5))
	var half: float=minf(app.view.width/app.view.PX*.5,app.sim.map.length*.5)
	var expected: float=clampf(app.sim.map.length*.9,half,app.sim.map.length-half)
	await tap(app,map_point);check(checks,"touch minimap navigates to legal camera extent",is_equal_approx(app.view.target_camera,expected),{"expected":expected,"actual":app.view.target_camera,"view_width":app.view.width/app.view.PX})
	app.open_tech();await settle(app);audit(app,checks,"research")
	var before: int=app.sim.stats[0].casts;await tap(app,p);check(checks,"modal blocks battlefield",app.sim.stats[0].casts==before and app.touch_input.finger==-1)
	app.close_overlay();await settle(app)
	# Actual geometry input: mine priority, route switch, placement and area target.
	fixture(app);await settle(app)
	var mine: Dictionary=app.sim.map.definition.mines.filter(func(m):return int(m.owner)==0)[0]
	camera(app,mine.x);await settle(app);await tap(app,app.view.to_global(app.view.point_to_screen(mine.x,mine.y)+Vector2(0,-22)))
	check(checks,"native touch mine preference",app.sim.players[0].get("preferred_mine","")==mine.id,{"mine":mine,"selection":app.view.selected_building,"toast":app.toast_text})
	var fork: Dictionary=app.sim.map.fork_nodes(0)[0];var old: String=app.sim.map.choices[0][fork.node]
	check(checks,"hidden road sign has no invisible touch target",app.sim.location_visible(0,float(fork.position[0]),float(fork.position[1])) or not app.view.route_sign_rect(0,fork).has_area())
	var route_scout=app.sim.spawn(app.sim.players[0].roster[0],0,float(fork.position[0]))
	app.sim.map.apply_anchor(route_scout,app.sim.map.project(Vector2(float(fork.position[0]),float(fork.position[1]))));app.sim.visibility.refresh()
	var stage_half_world: float=app.mobile.playfield.size.x/app.view.scale.x/app.view.PX*.5
	camera(app,float(fork.position[0])+stage_half_world*.86);await settle(app)
	var edge_marker: Rect2=app.view.route_sign_rect(0,fork)
	check(checks,"edge road marker is fully visible",edge_marker.has_area() and app.view.mobile_playfield.encloses(edge_marker))
	await tap(app,app.view.to_global(edge_marker.get_center()))
	check(checks,"native touch switches road",app.sim.map.choices[0][fork.node]!=old)
	await app.qa_snapshot(folder,"09-road-edge")
	var site: Dictionary=app.sim.slot_anchor(0,0)
	var scout=app.sim.spawn("unit.yin.axe",0,site.x);app.sim.map.apply_anchor(scout,site);app.sim.visibility.refresh()
	camera(app,site.x);await settle(app)
	app.choose_building("building.yin.tower");await settle(app);await tap(app,app.view.to_global(app.view.point_to_screen(site.x,site.y)))
	check(checks,"native touch placement pays once",app.sim.buildings.size()==1 and app.sim.buildings[0].state=="constructing",{"buildings":app.sim.buildings.size(),"selection":app.view.selected_building,"modal":app.modal,"point":str(app.view.to_global(app.view.point_to_screen(site.x,site.y))),"stage":str(app.mobile.playfield),"site":site,"toast":app.toast_text})
	app.sim.units.clear();app.sim.events.clear();var worker=app.sim.spawn("unit.mo.worker",1,23)
	worker.body_anchor=app.sim.map.anchor(worker.edge,maxf(0,worker.s-2.7))
	var observer=app.sim.spawn("unit.yin.axe",0,float(worker.body_anchor.x)-2)
	app.sim.map.apply_anchor(observer,app.sim.map.anchor(worker.edge,maxf(0,float(worker.body_anchor.s)-2)))
	app.sim.visibility.refresh()
	camera(app,app.sim.physical_point(worker).x);app.hud_section="spells";app.build_hud();await settle(app);app.sim.players[0].mana=100
	await press(app,app.spell_cards["spell.yin.cold"]);await tap(app,app.view.to_global(app.view.unit_position(worker)-Vector2(0,35)))
	check(checks,"area spell hits actual worker body",worker.statuses.has("cold"),{"selection":app.view.selected_spell,"modal":app.modal,"body":worker.body_anchor,"toast":app.toast_text,"statuses":worker.statuses})
	# Back stack and background / orientation state, including open settings.
	app.sim.players[0].mana=100;app.select_spell("spell.yin.stamp");app._notification(app.NOTIFICATION_WM_GO_BACK_REQUEST)
	check(checks,"system back cancels selection first",app.view.selected_spell=="" and app.modal=="")
	app._notification(app.NOTIFICATION_WM_GO_BACK_REQUEST);check(checks,"system back pauses",app.paused and app.modal=="pause")
	app.settings_menu(true);await settle(app);await scroll_to_end(app);audit(app,checks,"battle settings");await app.qa_snapshot(folder,"07-settings")
	app._notification(app.NOTIFICATION_WM_GO_BACK_REQUEST);check(checks,"settings back returns to pause",app.paused and app.modal=="pause")
	app.mobile.back();var time: float=app.sim.time
	app._notification(app.NOTIFICATION_APPLICATION_PAUSED);await settle(app,4)
	check(checks,"background freezes battle and resets input",app.app_suspended and app.paused and app.sim.time==time and app.touch_input.finger==-1 and app.audio.background)
	app._notification(app.NOTIFICATION_APPLICATION_RESUMED);await settle(app)
	check(checks,"foreground requires explicit resume",not app.app_suspended and app.paused and app.modal=="pause" and not app.audio.background)
	app.mobile.back();app.accumulator=-100000
	app.mobile.back();app.sim.winner=1;app.sim.result_reason="受控失败夹具";app.show_result();await settle(app);audit(app,checks,"defeat");await scroll_to_end(app);audit(app,checks,"defeat tail");await app.qa_snapshot(folder,"08-defeat")
	await press(app,named(app.overlay,"调整部署再战"));check(checks,"defeat opens loadout",app.modal=="loadout")
	app.main_menu();app.show_epilogue();await settle(app);await scroll_to_end(app);audit(app,checks,"epilogue tail")
	app.close_overlay();app.credits_menu();await settle(app);await scroll_to_end(app);audit(app,checks,"licenses tail")
	app.main_menu();app.mobile.back();await settle(app);check(checks,"main back asks before exit",app.modal=="exit");audit(app,checks,"exit")
	# Real campaign geometry must remain reachable through the smaller playfield.
	for map_id in app.db.maps:
		fixture(app,app.db.maps[map_id].region,map_id);await settle(app,1)
		for anchor in app.sim.map.definition.mines+app.sim.map.definition.build_sites:
			camera(app,float(anchor.x))
			var point: Vector2=app.view.to_global(app.view.point_to_screen(anchor.x,anchor.y))
			check(checks,"map anchor visible "+map_id+" "+anchor.id,app.mobile.playfield.has_point(point),{"point":str(point),"stage":str(app.mobile.playfield)})
		for fork_node in app.sim.map.fork_nodes(0):
			camera(app,float(fork_node.position[0]))
			check(checks,"unscouted road has no touch target "+map_id+" "+fork_node.node,app.sim.location_visible(0,float(fork_node.position[0]),float(fork_node.position[1])) or not app.view.route_sign_rect(0,fork_node).has_area())
			var road_observer=app.sim.spawn(app.sim.players[0].roster[0],0,float(fork_node.position[0]))
			app.sim.map.apply_anchor(road_observer,app.sim.map.project(Vector2(float(fork_node.position[0]),float(fork_node.position[1]))));app.sim.visibility.refresh()
			var touch: Rect2=app.view.route_sign_rect(0,fork_node)
			var centre: Vector2=app.view.to_global(touch.get_center())
			check(checks,"route reachable "+map_id+" "+fork_node.node,app.mobile.playfield.has_point(centre) and touch.size.x*app.view.scale.x>=48 and touch.size.y*app.view.scale.y>=47.9)
			for direction in [-.88,.88]:
				camera(app,float(fork_node.position[0])+direction*app.mobile.playfield.size.x/app.view.scale.x/app.view.PX*.5)
				var foot: Vector2=app.view.point_to_screen(float(fork_node.position[0]),float(fork_node.position[1]))
				var edge_touch: Rect2=app.view.route_sign_rect(0,fork_node)
				var near: bool=app.view.mobile_playfield.grow(44/app.view.scale.x).has_point(foot)
				check(checks,"road edge label "+map_id+" "+fork_node.node+" "+str(direction),edge_touch.has_area() and app.view.mobile_playfield.encloses(edge_touch) if near else not edge_touch.has_area(),{"touch":str(edge_touch),"stage":str(app.view.mobile_playfield),"foot":str(foot)})
			camera(app,float(fork_node.position[0])+app.view.width/app.view.PX*2)
			var distant: Vector2=app.view.point_to_screen(float(fork_node.position[0]),float(fork_node.position[1]))
			if not app.view.mobile_playfield.grow(44/app.view.scale.x).has_point(distant):
				check(checks,"distant road sign has no touch target "+map_id+" "+fork_node.node,not app.view.route_sign_rect(0,fork_node).has_area())
	check(checks,"mobile texture cache bounded",app.db.textures.size()<=128,{"entries":app.db.textures.size()})
	# Perform desktop window rotation last: Windows caps some resized client
	# heights to the monitor. Menu, HUD and all 200 maps use the requested size.
	await press(app,app.unit_cards[app.sim.players[0].roster[0]])
	var native_size: Vector2i=app.get_window().size;var queue: Array=app.sim.players[0].queue.duplicate()
	check(checks,"rotation fixture has a paid production queue",not queue.is_empty())
	app.get_window().size=Vector2i(native_size.y,native_size.x);await settle(app,8);app.refresh_mobile_layout();await settle(app)
	check(checks,"portrait resize pauses and guards",app.mobile_blocked and app.paused and not app.ui.visible)
	app.get_window().size=native_size;await settle(app,8);app.refresh_mobile_layout();await settle(app)
	check(checks,"landscape recovery preserves live battle",not app.mobile_blocked and app.ui.visible and app.paused and app.sim.players[0].queue==queue)
	app.profile=original;app.db.deployments=deployments;app.save_profile()
	var failed: Array=checks.filter(func(c):return not c.passed)
	var report: Dictionary={"version":ProjectSettings.get_setting("application/config/version","unknown"),"scope":"Native Windows Godot GPU with injected Android density/safe insets and actual ScreenTouch/ScreenDrag, controlled actors and results. Not Android hardware, human usability or device FPS proof.","engine":Engine.get_version_info(),"metrics":{},"recovery_metrics":{},"checks":checks,"failures":failed,"capture_errors":app.capture_errors,"inputs":{},"passed":failed.is_empty() and app.capture_errors.is_empty()}
	report["battlefield_coverage"]=checks.filter(func(c):return c.name.contains("70 percent"))
	for key in ["density","pixels","viewport","safe","content"]:
		report.metrics[key]=str(tested_metrics[key]);report.recovery_metrics[key]=str(app.mobile.metrics[key])
	for path in ["res://scripts/main.gd","res://scripts/mobile_layout.gd","res://scripts/mobile_input.gd","res://scripts/mobile_ui.gd","res://scripts/mobile_slider.gd","res://scripts/mobile_scroll.gd","res://scripts/battle_view.gd","res://scripts/theatre_fog.gd","res://scripts/battle_visibility.gd","res://scripts/action_card.gd","res://scripts/ui_theme.gd","res://scripts/audio_controller.gd","res://scripts/data_store.gd","res://tests/mobile_ui_qa.gd","res://scripts/battle_sim.gd"]:report.inputs[path]=FileAccess.get_sha256(path)
	for path in ["res://assets/fonts/NotoSansSC.ttf","res://assets/fonts/NotoSerifSC.ttf"]:report.inputs[path]=FileAccess.get_sha256(path)
	var file=FileAccess.open(folder+"/report.json",FileAccess.WRITE);file.store_string(JSON.stringify(report,"\t"));file.close()
	print("MOBILE_QA ",JSON.stringify({"checks":checks.size(),"failures":failed.size(),"passed":report.passed}))
	app.get_tree().quit(0 if report.passed else 1)

static func press_with_finger(app,button,index: int):
	await tap(app,button.get_global_rect().get_center(),index)
