extends SceneTree
const App=preload("res://scripts/main.gd")
const Touch=preload("res://tests/mobile_ui_qa.gd")
const UI=preload("res://scripts/ui_theme.gd")
var checks: Array=[]
var shots: Array=[]
var folder: String
func verify(ok: bool,note: String):checks.append({"passed":ok,"name":note})
func _initialize():call_deferred("run")
func shot(app,name_value: String):
	await Touch.settle(app,5);await app.qa_snapshot(folder,name_value);shots.append(name_value+".png")
func tap_control(app,button):
	if app.mobile_ui:await Touch.press(app,button)
	else:
		var point: Vector2=button.get_global_transform_with_canvas()*(button.size*.5)
		for down in [true,false]:
			var event=InputEventMouseButton.new();event.button_index=MOUSE_BUTTON_LEFT;event.pressed=down;event.position=point
			await Touch.send(app,event)
		await Touch.settle(app)
func run():
	var args=OS.get_cmdline_user_args();folder=args[args.find("--output")+1];DirAccess.make_dir_recursive_absolute(folder)
	var app=App.new();root.add_child(app);await Touch.settle(app,5)
	var assets: Dictionary=JSON.parse_string(FileAccess.get_file_as_string("res://data/paper-ui.json"))
	verify(assets.model=="gpt-image-2.5" and assets.assets.size()==38,"Approved image route and all 38 UI assets")
	for entry in assets.assets:
		var texture=load(entry.path) as Texture2D
		verify(texture!=null and texture.get_width()==entry.size[0] and texture.get_height()==entry.size[1],"Runtime decoded UI texture "+entry.id)
	await shot(app,"00-main-menu")
	var first=Touch.named(app.ui,"继续战役");first.grab_focus();await shot(app,"01-keyboard-focus")
	verify(first.has_focus(),"Keyboard focus remains visible on primary action")
	var first_point: Vector2=first.get_global_rect().get_center() if app.mobile_ui else first.get_global_transform_with_canvas()*(first.size*.5)
	if app.mobile_ui:await Touch.finger(app,first_point,true)
	else:
		var event=InputEventMouseButton.new();event.position=first_point;event.button_index=MOUSE_BUTTON_LEFT;event.pressed=true;await Touch.send(app,event)
	verify(first.is_pressed(),"Primary paper action has an actual held input state")
	await shot(app,"01a-primary-pressed")
	if app.mobile_ui:await Touch.finger(app,first_point,false)
	else:
		var event=InputEventMouseButton.new();event.position=first_point;event.button_index=MOUSE_BUTTON_LEFT;event.pressed=false;await Touch.send(app,event)
	app.main_menu()
	app.new_battle_menu();await shot(app,"02-new-battle")
	var disabled=Touch.named(app.ui,"故事战役");disabled.disabled=true;await tap_control(app,disabled)
	verify(app.screen=="new-battle","Disabled paper action rejects native activation")
	await shot(app,"02a-disabled");disabled.disabled=false
	app.campaign_menu();await shot(app,"03-campaign")
	app.skirmish_menu();await shot(app,"04-skirmish")
	var options=app.ui.find_children("*","OptionButton",true,false)
	verify(Touch.named(app.ui,"我方")!=null if app.mobile_ui else not options.is_empty(),"Styled native selectors remain reachable")
	if not options.is_empty():
		options[0].show_popup();await shot(app,"05-dropdown");options[0].get_popup().hide()
	elif app.mobile_ui:
		await Touch.press(app,Touch.named(app.ui,"我方"));await shot(app,"05-dropdown");app.close_overlay()
	app.archive_menu("yin","unit.yin.guard");await shot(app,"06-archive")
	app.settings_menu(false);await shot(app,"07-settings")
	var settings_root=app.overlay if app.overlay else app.ui
	var toggles=settings_root.find_children("*","CheckButton",true,false)
	if not toggles.is_empty():
		var before: bool=toggles[0].button_pressed
		await tap_control(app,toggles[0]);verify(toggles[0].button_pressed!=before,"Generated switch skin preserves native toggle behavior")
	var sliders=settings_root.find_children("*","HSlider",true,false)
	if not sliders.is_empty():
		var slider=sliders[0];slider.grab_focus();slider.value=.63
		verify(is_equal_approx(slider.value,.63),"Generated slider thumb preserves Range value")
	await shot(app,"08-settings-active")
	app.main_menu();app.show_brief(app.db.campaign[0],"campaign");await shot(app,"09-mission-brief")
	app.mode="skirmish";app.start_battle({"title":"纸艺界面验收","faction":"yin","enemy":"mo","map":"map.01.04","full_tech":false,"starting_gold":300})
	app.sim.ai_enabled=[false,false];app.accumulator=-100000;app.toast_left=0;app.update_hud()
	await shot(app,"10-battle-hud");Touch.battlefield_coverage(app,checks,"paper UI battle")
	var spell_id: String=app.db.spell_ids("yin")[0]
	await tap_control(app,app.spell_cards[spell_id]);verify(app.view.selected_spell==spell_id,"Paper spell card visibly enters targeting state")
	await shot(app,"10a-selected-spell");app.cancel_selection()
	var id: String=""
	for candidate in app.unit_cards:
		if app.sim.players[0].unlocked.has(candidate) and not candidate.ends_with(".worker"):id=candidate;break
	var c=app.unit_cards[id];var cash: float=app.sim.players[0].gold
	await tap_control(app,c);verify(app.sim.players[0].queue==[id] and cash-app.sim.players[0].gold==app.db.balance.units[id].gold,"Paper card tap submits exactly one paid recruitment")
	if not checks[-1].passed:print("PAPER_RECRUIT_DIAGNOSTIC ",app.sim.players[0].queue," ",cash," ",app.sim.players[0].gold," disabled=",c.disabled," rect=",c.get_global_rect())
	app.open_orders();await shot(app,"11-orders")
	app.close_overlay();app.open_tech();await shot(app,"12-technology")
	verify(not app.tech_buttons.is_empty(),"Research controls remain accessible with paper theme")
	app.close_overlay();app.open_queue();await shot(app,"13-production")
	app.close_overlay();app.open_build();await shot(app,"14-build")
	app.close_overlay();app.pause_menu();await shot(app,"15-pause")
	app.close_overlay();app.paused=false;app.sim.winner=0;app.show_result();await shot(app,"16-victory")
	app.close_overlay();app.result_shown=false;app.sim.winner=1;app.show_result();await shot(app,"17-defeat")
	var passed: bool=checks.all(func(c):return c.passed)
	var inputs: Dictionary={}
	for path in ["res://scripts/main.gd","res://scripts/mobile_ui.gd","res://scripts/ui_theme.gd","res://scripts/paper_panel.gd","res://scripts/action_card.gd","res://scripts/mobile_slider.gd","res://scripts/local_duel.gd","res://data/paper-ui.json"]:
		var actual: String=path if FileAccess.file_exists(path) else path+"c"
		inputs[actual]=FileAccess.get_sha256(actual)
	var f=FileAccess.open(folder+"/report.json",FileAccess.WRITE);f.store_string(JSON.stringify({"passed":passed,"version":ProjectSettings.get_setting("application/config/version"),"checks":checks,"shots":shots,"inputs":inputs,"scope":"Native Windows Godot rendered UI, controlled touch and paid orders. Not Android hardware."},"\t"));f.close()
	print("PAPER_UI ",checks.size()," checks; passed=",passed);app.queue_free();await process_frame;quit(0 if passed else 1)
