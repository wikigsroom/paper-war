extends SceneTree
# External input observer. App and widgets resolve from source or the actual
# exported pack; helpers contain no game UI implementation.
const App=preload("res://scripts/main.gd")
var checks: Array=[]
var shots: Array=[]
var folder: String
var touch_helper

func _initialize():call_deferred("run")

func verify(ok: bool,name_value: String,details: Dictionary={}):
	checks.append({"passed":ok,"name":name_value,"details":details})
	if not ok:print("NAV_FAIL ",name_value," ",JSON.stringify(details))

func settle(frames: int=4):
	for i in range(frames):await process_frame

func key(app,code: Key,shift: bool=false):
	for down in [true,false]:
		var event=InputEventKey.new();event.keycode=code;event.physical_keycode=code;event.pressed=down;event.shift_pressed=shift
		app.get_viewport().push_input(event,true);await process_frame
	await settle(2)

func modal_has_focus(app) -> bool:
	var focused=app.get_viewport().gui_get_focus_owner()
	return is_instance_valid(focused) and is_instance_valid(app.overlay) and app.overlay.is_ancestor_of(focused)

func shot(app,name_value: String):
	await settle();await app.qa_snapshot(folder,name_value);shots.append(name_value+".png")

func menu_scroll(app):
	for child in app.ui.find_children("*","ScrollContainer",true,false):
		if child.is_visible_in_tree() and not child.horizontal:return child
	return null

func shared_has_focus(panel: Dictionary) -> bool:
	var focused=panel.viewport.gui_get_focus_owner()
	return is_instance_valid(focused) and is_instance_valid(panel.overlay) and panel.overlay.is_ancestor_of(focused)

func check_shared(app):
	app.main_menu()
	var settings={"title":"共享焦点验证","faction":"yin","enemy":"mo","map":"map.01.04","starting_gold":300,"enemy_starting_gold":300,"full_tech":false,"win":"destroy_base"}
	var controller
	if not app.mobile_ui:
		app.start_local_duel(settings);controller=app.local_duel
	else:
		app.start_battle(settings);app.sim.ai_enabled=[false,false];app.accumulator=-100000
		controller=app.LocalDuel.new();controller.size=app.ui.size;controller.theme=app.theme;app.ui.add_child(controller)
		controller.initialize_network(app.db,app.sim,0,func(_kind,_args):return {"ok":false,"error":"只读焦点观察"})
	await settle(6)
	var panel: Dictionary=controller.panels[0]
	panel.orders.grab_focus();controller.open_sheet(0,"orders");await settle()
	verify(shared_has_focus(panel),"Shared controller sheet owns its viewport focus")
	for reverse in [false,true]:
		for i in range(8):
			await key(panel.root,KEY_TAB,reverse)
			verify(shared_has_focus(panel),"Shared sheet focus cycle %s %d"%["reverse" if reverse else "forward",i])
	controller.open_sheet(0,"research");await settle()
	verify(shared_has_focus(panel),"Shared replacement research sheet owns focus")
	controller.close_sheet(0);await settle()
	verify(panel.orders.has_focus(),"Shared sheet restores the original military order focus")
	if app.mobile_ui:
		controller.open_sheet(0,"research");await settle()
		var scroll=panel.overlay.find_children("*","ScrollContainer",true,false)[0]
		await swipe_list(panel.root,scroll)
		controller.set_paused(true)
		var old: int=scroll.scroll_vertical;await settle(10)
		verify(scroll.scroll_vertical==old and is_zero_approx(scroll.velocity),"Paused shared research sheet stops its momentum",{"before":old,"after":scroll.scroll_vertical,"velocity":scroll.velocity})
		controller.set_paused(false)
	await shot(app,"05-shared-controller")
	if app.mobile_ui:controller.queue_free();await settle()

func swipe_list(app,scroll):
	scroll.scroll_vertical=0;scroll.velocity=0;scroll.set_process(false);await settle()
	var point: Vector2=scroll.get_global_rect().get_center()+Vector2(0,35)
	await touch_helper.finger(app,point,true)
	for offset in [18,36,54,72]:await touch_helper.drag(app,point-Vector2(0,offset))
	await touch_helper.finger(app,point-Vector2(0,72),false)
	verify(scroll.touch_finger==-1 and absf(scroll.velocity)>8,"Real released swipe enters momentum",{"velocity":scroll.velocity,"offset":scroll.scroll_vertical})

func run():
	var args=OS.get_cmdline_user_args();folder=args[args.find("--output")+1]
	DirAccess.make_dir_recursive_absolute(folder)
	touch_helper=load(args[args.find("--touch-helper")+1])
	var app=App.new();root.add_child(app);await settle(8)
	var opener=touch_helper.named(app.ui,"继续战役");opener.grab_focus()
	app.show_brief(app.db.campaign[0],"campaign");await settle(6)
	verify(modal_has_focus(app),"Opening modal moves keyboard focus inside the paper sheet")
	await shot(app,"01-modal-opening")
	for direction in [false,true]:
		for i in range(12):
			await key(app,KEY_TAB,direction)
			var focused=app.get_viewport().gui_get_focus_owner()
			verify(modal_has_focus(app),"Modal keyboard cycle %s %d"%["reverse" if direction else "forward",i],{"focused":str(focused),"modal":app.modal})
	await shot(app,"02-modal-keyboard-cycle")
	app.close_overlay();await settle()
	verify(opener.has_focus(),"Closing sheet returns focus to the original menu action")
	app.show_brief(app.db.campaign[0],"campaign");await settle()
	app.loadout_menu("yin",app.close_overlay);await settle()
	verify(modal_has_focus(app),"Replacement deployment sheet owns keyboard focus")
	app.close_overlay();await settle()
	verify(opener.has_focus(),"Replacing a sheet retains its original return focus")
	await shot(app,"03-return-focus")
	if app.mobile_ui:
		app.campaign_menu();await settle()
		var scroll=menu_scroll(app)
		await swipe_list(app,scroll)
		app.mobile.choices("故事章节",["朱印疆","墨骸院"],0,func(_i):pass,app.campaign_menu)
		var old: int=scroll.scroll_vertical;await settle(10)
		verify(scroll.scroll_vertical==old and is_zero_approx(scroll.velocity),"Underlay momentum stops while the chooser is open",{"before":old,"after":scroll.scroll_vertical,"velocity":scroll.velocity})
		await shot(app,"04-scroll-behind-modal")
		app.close_overlay();await settle()
		await swipe_list(app,scroll)
		app.set_mobile_background(true);old=scroll.scroll_vertical;await settle(10)
		verify(scroll.scroll_vertical==old and is_zero_approx(scroll.velocity),"Released menu momentum stops when the app is suspended",{"before":old,"after":scroll.scroll_vertical,"velocity":scroll.velocity})
		app.set_mobile_background(false);await settle()
		app.campaign_menu();await settle();scroll=menu_scroll(app)
		await swipe_list(app,scroll);scroll.hide();old=scroll.scroll_vertical;await settle(10)
		verify(scroll.scroll_vertical==old and is_zero_approx(scroll.velocity),"Hidden list stops momentum",{"before":old,"after":scroll.scroll_vertical,"velocity":scroll.velocity})
	await check_shared(app)
	var inputs: Dictionary={}
	for path in ["res://scripts/main.gd","res://scripts/mobile_ui.gd","res://scripts/mobile_scroll.gd","res://scripts/mobile_slider.gd","res://scripts/ui_theme.gd","res://scripts/local_duel.gd","res://scripts/duel_scroll.gd","res://scripts/ui_focus_scope.gd"]:
		var actual: String=path if FileAccess.file_exists(path) else path+"c"
		if FileAccess.file_exists(actual):inputs[actual]=FileAccess.get_sha256(actual)
	var passed: bool=checks.all(func(c):return c.passed)
	var f=FileAccess.open(folder+"/report.json",FileAccess.WRITE)
	f.store_string(JSON.stringify({"passed":passed,"version":ProjectSettings.get_setting("application/config/version"),"checks":checks,"shots":shots,"inputs":inputs,"scope":"Native Windows keyboard and injected ScreenTouch. No Android hardware claim."},"\t"));f.close()
	print("MODAL_NAVIGATION ",checks.size()," checks; passed=",passed)
	app.queue_free();await process_frame;quit(0 if passed else 1)
