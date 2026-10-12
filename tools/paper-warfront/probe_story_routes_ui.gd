extends SceneTree
const App=preload("res://scripts/main.gd")
var checks: Array=[]
var shots: Array=[]
var folder: String
var app
func _initialize():call_deferred("run")
func verify(value: bool,note: String):
	checks.append({"passed":value,"name":note})
	if not value:print("STORY_UI_FAIL ",note)
func settle(frames: int=4):
	for i in range(frames):await process_frame
func card(id: String):
	for button in app.ui.find_children("*","Button",true,false):
		if button.get_meta("campaign_id","")==id:return button
	return null
func named(parent,caption: String):
	for button in parent.find_children("*","Button",true,false):
		if button.is_visible_in_tree() and button.text==caption:return button
	return null
func click(button):
	verify(button!=null,"pointer target exists")
	if button==null:return
	var parent=button.get_parent()
	while parent!=null:
		if parent is ScrollContainer:
			parent.ensure_control_visible(button);await settle()
		parent=parent.get_parent()
	var position: Vector2=button.get_global_rect().get_center()
	verify(app.get_viewport().get_visible_rect().has_point(position),"pointer target scrolled into visible viewport")
	for down in [true,false]:
		var event: InputEvent
		if app.mobile_ui:
			var touch=InputEventScreenTouch.new();touch.index=0;touch.position=position;touch.pressed=down;event=touch
		else:
			var mouse=InputEventMouseButton.new();mouse.button_index=MOUSE_BUTTON_LEFT;mouse.position=position;mouse.pressed=down;event=mouse
		app.get_viewport().push_input(event,true);await process_frame
	await settle()
func shot(name_value: String):
	await settle();await app.qa_snapshot(folder,name_value)
	shots.append({"path":name_value+".png","sha256":FileAccess.get_sha256(folder+"/"+name_value+".png")})
func result_fixture(index: int):
	app.mode="campaign";app.start_battle(app.db.campaign[index]);app.set_process(false)
	app.sim.ai_enabled=[false,false];app.paused=true
	app.sim.winner=0;app.sim.result_reason="剧情UI结果转换夹具，并非真实通关"
	app.show_result();await settle()
func run():
	var args=OS.get_cmdline_user_args();folder=args[args.find("--output")+1]
	DirAccess.make_dir_recursive_absolute(folder)
	app=App.new();root.add_child(app);await settle(6);app.set_process(false)
	verify(app.profile.campaign_completed.is_empty(),"isolated new save begins without evidence")
	app.campaign_menu(0);await settle()
	verify(not card("campaign.yin.01").disabled and card("campaign.yin.02").disabled and card("campaign.yin.03").disabled,"only opening map begins playable")
	await result_fixture(0);await shot("01-result-choice")
	await click(named(app.overlay,"选择下一页"))
	verify(app.screen=="campaign" and app.overlay==null,"actual result input opens chapter selection")
	verify(not card("campaign.yin.02").disabled and not card("campaign.yin.03").disabled and card("campaign.yin.04").disabled,"actual saved result offers both branches, not their convergence")
	await shot("02-two-story-routes")
	await click(card("campaign.yin.02"))
	verify(app.modal=="brief" and app.options.id=="campaign.yin.02","native pointer chooses economic story branch")
	await shot("03-map-story-brief")
	await result_fixture(1)
	app.load_profile();app.campaign_menu(0);await settle()
	verify(not card("campaign.yin.04").disabled and not card("campaign.yin.03").disabled,"saved economic route opens convergence and leaves defense available")
	verify(not app.profile.campaign_completed.has("campaign.yin.03") and not app.profile.story_flags.has("evidence.yin.03"),"unplayed defense has no invented clear or story flag")
	verify(app.campaign_progress.recommended(app.profile).id=="campaign.yin.04","continue recommends real convergence")
	verify(int(app.profile.schema)==3 and int(app.profile.stars["campaign.yin.01"])>=1,"schema3 save reload retains real clear")
	await shot("04-branch-convergence")
	app.campaign_menu(1);await settle()
	verify(card("campaign.mo.01").disabled,"chapter2 remains locked until chapter1 ending")
	var progress: Dictionary=app.profile.duplicate(true)
	app.mode="skirmish";app.start_battle(app.db.campaign[0]);app.set_process(false);app.sim.winner=0;app.show_result();await settle()
	verify(app.profile==progress,"skirmish result cannot create chapter evidence")
	# Check actual wrapped copy geometry for all200 authored briefs. Story text
	# can scroll, but the fixed victory/tactical summary must fit completely.
	for index in range(200):
		var level: Dictionary=app.db.campaign[index]
		app.show_brief(level,"campaign");await settle(2)
		var summary: String=app.mission_brief(level,app.db.maps[level.map])
		var label
		for node in app.overlay.find_children("*","Label",true,false):
			if node.text==summary:label=node;break
		var fits: bool=false
		if label!=null:
			var required: float=label.get_line_count()*label.get_theme_font("font").get_height(label.get_theme_font_size("font_size"))
			fits=required<=label.size.y+.2
		verify(fits,"complete visible mission summary "+level.id)
	app.close_overlay()
	# Actual mouse/ScreenTouch actions on an AND gate and a three-way
	# investigation. Prior victories are explicit progression fixtures, not a
	# claim that a human or battle AI has played these chapters.
	for number in [1,2,4,5,7,8,10,11,13,14,16,17,18,20]:
		app.campaign_progress.record_victory(app.profile,app.db.campaign[number-1].id,2)
	await result_fixture(20)
	app.campaign_menu(1);await settle()
	verify(not card("campaign.mo.02").disabled and not card("campaign.mo.03").disabled,"two compulsory investigations open together")
	await click(card("campaign.mo.02"));verify(app.options.id=="campaign.mo.02","native pointer selects wage evidence")
	await result_fixture(21);app.load_profile();app.campaign_menu(1);await settle()
	verify(card("campaign.mo.04").disabled and not card("campaign.mo.03").disabled,"one actual evidence leaves conjunction locked")
	verify(app.campaign_progress.recommended(app.profile).id=="campaign.mo.03","continue offers missing investigation")
	verify(not app.profile.story_flags.has("evidence.mo.03"),"missing compulsory clue is not invented")
	await shot("05-and-one-clue-pending")
	await click(card("campaign.mo.03"));verify(app.options.id=="campaign.mo.03","native pointer selects missing burial evidence")
	await result_fixture(22);app.load_profile();app.campaign_menu(1);await settle()
	verify(not card("campaign.mo.04").disabled,"two actual evidence clears unlock hearing after save reload")
	verify(app.campaign_progress.requirement_hint("campaign.mo.04")=="需完成02和03折","UI explains conjunction")
	await shot("06-and-both-clues-complete")
	for index in range(23,60):app.campaign_progress.record_victory(app.profile,app.db.campaign[index].id,2)
	await result_fixture(60);app.campaign_menu(3);await settle()
	verify(not card("campaign.ji.02").disabled and not card("campaign.ji.03").disabled and not card("campaign.ji.04").disabled,"factory offers all three investigations")
	await click(card("campaign.ji.04"));verify(app.options.id=="campaign.ji.04","native pointer can investigate bridge first")
	await result_fixture(63);app.campaign_menu(3);await settle()
	verify(card("campaign.ji.05").disabled and app.campaign_progress.next_choices(app.profile,"campaign.ji.04").size()==2,"three-way hearing remains locked and offers two missing pages")
	await shot("07-factory-bridge-first")
	for index in [61,62]:
		await click(card(app.db.campaign[index].id))
		await result_fixture(index);app.campaign_menu(3);await settle()
	app.load_profile();app.campaign_menu(3);await settle()
	verify(not card("campaign.ji.05").disabled and app.campaign_progress.recommended(app.profile).id=="campaign.ji.05","all three actual factory results converge after reload")
	await shot("08-factory-three-clues-complete")
	var inputs: Dictionary={}
	for name_value in ["main","mobile_ui","campaign_progress","battle_sim"]:
		# Godot preserves the logical .gd resource path after remapping. Hash
		# the actual file bytes, as the established packaged observers do.
		var path: String="res://scripts/"+name_value+(".gd" if FileAccess.file_exists("res://scripts/"+name_value+".gd") else ".gdc")
		assert(FileAccess.file_exists(path))
		inputs[path]=FileAccess.get_sha256(path)
	var result: Dictionary={"passed":checks.all(func(row):return row.passed),"checks":checks.size(),"results":checks,"inputs":inputs,"captures":shots,"observer_sha256":FileAccess.get_sha256(get_script().resource_path),"mobile_layout_on_windows":app.mobile_ui,"authored_briefs_checked":200,"scope":"Actual App/Control and isolated save, native mouse or ScreenTouch selection after fixture scroll-to-visible; all200 fixed brief summaries. Forced victories check alternatives, two/three-part conjunctions and reload, not played campaign wins, Android hardware, touch-scroll gestures or human narrative review."}
	FileAccess.open(folder+"/report.json",FileAccess.WRITE).store_string(JSON.stringify(result,"  "))
	print("STORY_ROUTES_UI ",JSON.stringify({"passed":result.passed,"checks":result.checks}))
	app.queue_free();await settle(2);quit(0 if result.passed else 1)
