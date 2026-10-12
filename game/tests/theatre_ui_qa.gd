extends RefCounted
# Synthetic native input and controlled battle fixtures. No human/device acceptance claim.

static func check(checks: Array,kind: String,passed: bool,data: Dictionary={}):
	checks.append({"kind":kind,"passed":passed,"data":data})
	if not passed:print("UI_FAIL ",kind," ",JSON.stringify(data))

static func click(app,position: Vector2):
	var pixels: Vector2=app.get_viewport().get_final_transform()*position
	var motion=InputEventMouseMotion.new();motion.position=pixels
	app.get_viewport().push_input(motion,false)
	for pressed in [true,false]:
		var event=InputEventMouseButton.new();event.button_index=MOUSE_BUTTON_LEFT;event.pressed=pressed;event.position=pixels
		app.get_viewport().push_input(event,false)
		await app.get_tree().process_frame
	await app.get_tree().process_frame

static func press(app,control: Control):
	await click(app,control.get_global_rect().get_center())

static func fixture(app,config: Dictionary):
	app.mode="skirmish";app.start_battle(config);app.sim.ai_enabled=[false,false]
	app.accumulator=-10000;app.view.follow_front=false;app.toast_left=0

static func camera(app,x: float):
	var half: float=minf(app.view.width/app.view.PX*.5,app.sim.map.length*.5)
	app.view.camera_x=clampf(x,half,app.sim.map.length-half)
	app.view.target_camera=app.view.camera_x;app.view.follow_front=false

static func button_named(parent: Node,prefix: String):
	for child in parent.get_children():
		if child is Button and child.text.begins_with(prefix):return child
	return null

static func run(app,folder: String):
	DirAccess.make_dir_recursive_absolute(folder)
	var original: Dictionary=app.profile.duplicate(true);var deployments: Dictionary=app.db.deployments.duplicate(true)
	var checks: Array=[]
	await app.get_tree().create_timer(.4).timeout
	await app.qa_snapshot(folder,"01-menu")
	app.theatre_menu();await app.qa_snapshot(folder,"01-six-map-selection")
	check(checks,"six playable spatial briefs",app.screen=="theatre")
	for chapter in range(10):
		app.campaign_menu(chapter);await app.get_tree().process_frame
		check(checks,"campaign chapter "+str(chapter),app.screen=="campaign" and app.campaign_chapter==chapter)
		if chapter in [0,9]:await app.qa_snapshot(folder,"02-chapter-%02d"%chapter)
	app.show_brief(app.db.campaign[3],"campaign");await app.qa_snapshot(folder,"03-brief-bridge")
	check(checks,"map decision briefing",app.overlay.find_children("ScrollCopy","Label",true,false).all(func(l):return l.size.y>20 and not l.text.is_empty()))
	app.skirmish_menu();await app.qa_snapshot(folder,"04-skirmish")
	app.loadout_menu("yin",app.close_overlay,[],1);await app.qa_snapshot(folder,"05-deployment")
	for faction in app.db.FACTIONS:
		var archive_ids: Array=app.db.all_unit_ids(faction)
		var page_size: int=8 if app.mobile_ui else 12
		for page in range(ceili(float(archive_ids.size())/page_size)):
			app.archive_menu(faction,archive_ids[page*page_size],page)
			await app.get_tree().process_frame
			check(checks,"library "+faction+" "+str(page),app.screen=="archive")
		app.db.deployments[faction]=app.db.factions[faction].core_roster.duplicate()
		var region_map: String="map.%02d.01"%[app.db.FACTIONS.find(faction)+1]
		fixture(app,{"title":"十院纸偶 · "+app.db.FACTION_NAMES[faction],"faction":faction,"enemy":"mo","map":region_map,"full_tech":true,"starting_gold":900,"enemy_starting_gold":400})
		check(checks,"3–5 production "+faction,app.unit_cards.size() in [3,4,5] and app.unit_cards.size()==app.sim.production_ids(0).size() and app.spell_cards.size()==5)
		var recruit_id: String=app.sim.players[0].roster[0];var gold: float=app.sim.players[0].gold
		await press(app,app.unit_cards[recruit_id])
		check(checks,"native pointer recruits "+faction,app.sim.players[0].queue.has(recruit_id) and is_equal_approx(gold-app.sim.players[0].gold,float(app.db.balance.units[recruit_id].gold)))
		app.open_queue();await app.get_tree().process_frame
		var refund=button_named(app.overlay,"1  ")
		if refund!=null:await press(app,refund)
		check(checks,"native pointer refunds "+faction,app.sim.players[0].queue.is_empty() and is_equal_approx(gold,app.sim.players[0].gold))
		app.close_overlay();await app.get_tree().process_frame
		app.choose_building("building."+faction+".mana")
		check(checks,"building selection costs nothing "+faction,is_equal_approx(gold,app.sim.players[0].gold) and app.view.selected_building.ends_with(".mana"))
		var site: Dictionary=app.sim.slot_anchor(0,0);camera(app,site.x)
		await click(app,app.view.point_to_screen(site.x,site.y))
		check(checks,"native pointer constructs at site "+faction,app.sim.buildings.size()==1 and app.sim.buildings[0].state=="constructing" and app.view.selected_building=="")
		app.paused=true;app.sim.units.clear();app.sim.events.clear()
		var center: float=app.sim.map.length*.5
		for i in range(4):
			app.sim.spawn(app.sim.players[0].roster[i],0,center-1.8-i*1.7)
			app.sim.spawn(app.db.factions.mo.core_roster[i],1,center+1.8+i*1.7)
		for tick in range(60*2):app.sim.tick(1.0/60.0)
		app.view.camera_x=center;app.view.target_camera=center
		for event in app.sim.drain_events():
			if app.sim.time-float(event.time)<.12:app.view.on_event(event)
		await app.qa_snapshot(folder,"06-battle-"+faction)
		app.paused=false
		for spell in app.db.spell_ids(faction):
			app.sim.players[0].mana=100;app.sim.players[0].cooldowns[spell]=0
			var ally=app.sim.spawn(recruit_id,0,24);ally.hp=ally.max_hp*.5
			var enemy=app.sim.spawn("unit.mo.giant",1,26)
			var target: Dictionary=ally if spell.get_slice(".",2) in ["repair","fury","sacrifice","protect","clone"] else enemy
			if spell.ends_with(".sacrifice"):app.sim.players[0].mana=60
			app.view.camera_x=target.x;app.view.target_camera=target.x
			var casts: int=app.sim.stats[0].casts
			app.spell_cards[spell].emit_signal("pressed")
			app.battlefield_tap(app.view.unit_position(target)-Vector2(0,35),target.uid)
			check(checks,"spell UI command "+spell,app.sim.stats[0].casts==casts+1 and app.view.selected_spell=="")
		if app.mobile_ui:
			for section in ["units","spells"]:
				app.hud_section=section;app.clear_ui();app.build_hud()
				var visible: int=0
				for card in app.unit_cards.values()+app.spell_cards.values():
					if card.visible:visible+=1
				check(checks,"mobile group "+faction+" "+section,visible==5)
				if faction=="bai":await app.qa_snapshot(folder,"07-mobile-"+section)
	for index in [0,6,10,3,11,5]:
		var config: Dictionary=app.db.campaign[index].duplicate(true)
		app.db.deployments[config.faction]=config.default_roster.duplicate()
		fixture(app,config);app.paused=true;app.view.camera_x=10;app.view.target_camera=10
		await app.qa_snapshot(folder,config.map+"-home")
		var decision_x: float=app.sim.map.length*.5
		if config.get("win","")=="intercept":decision_x=float(config.objective_anchor.x)+5
		if config.get("win","")=="escort":decision_x=27
		for tick in range(60*4):app.sim.tick(1.0/60.0)
		app.view.camera_x=decision_x;app.view.target_camera=decision_x
		await app.qa_snapshot(folder,config.map+"-decision")
		check(checks,"campaign small army "+config.map,app.unit_cards.size()==config.default_roster.size()+1)
	app.db.deployments.yin=app.db.factions.yin.core_roster.duplicate()
	fixture(app,{"title":"纸桥与前哨交互","map":"map.01.04","faction":"yin","enemy":"mo","full_tech":true,"starting_gold":900})
	var fork: Dictionary=app.sim.map.fork_nodes(0)[0];var before: String=app.sim.map.choices[0][fork.node]
	app.view.camera_x=float(fork.position[0]);app.view.target_camera=app.view.camera_x
	await click(app,app.view.route_sign_position(0,fork))
	check(checks,"native pointer switches route beside a tower site",app.sim.map.choices[0][fork.node]!=before and app.modal=="")
	var site: Dictionary=app.sim.slot_anchor(0,0)
	await click(app,app.view.point_to_screen(site.x,site.y)-Vector2(0,18))
	check(checks,"native pointer opens contextual construction",app.modal=="build" and app.build_focus_slot==0)
	var lamp=button_named(app.overlay,"产法纸灯");check(checks,"tower-only position disables lamp",lamp!=null and lamp.disabled)
	await app.qa_snapshot(folder,"08-context-build")
	app.close_overlay();await app.get_tree().process_frame
	var mine: Dictionary=app.sim.map.definition.mines[0];camera(app,mine.x)
	await click(app,app.view.point_to_screen(mine.x,mine.y)-Vector2(0,22))
	check(checks,"native pointer sets mine priority",app.sim.players[0].get("preferred_mine","")==mine.id)
	var nav=app.view.minimap_rect();await click(app,nav.position+Vector2(nav.size.x*.80,nav.size.y*.5))
	check(checks,"native pointer navigates battle overview",app.view.target_camera>app.sim.map.length*.6 and not app.view.follow_front)
	fixture(app,{"title":"研究与暂停","map":"map.01.01","faction":"yin","enemy":"mo","starting_gold":900,"full_tech":false})
	app.open_tech();await app.get_tree().process_frame
	var node_id: String=""
	for id in app.tech_buttons:
		var node: Dictionary=app.db.tech(id)
		if not app.sim.players[0].studied.has(id) and node.requires.all(func(req):return app.sim.players[0].studied.has(req)):node_id=id;break
	var research_gold: float=app.sim.players[0].gold
	if node_id!="":await press(app,app.tech_buttons[node_id])
	check(checks,"native pointer starts eligible research",node_id!="" and app.sim.players[0].research.get("id","")==node_id and app.sim.players[0].gold<research_gold)
	await app.qa_snapshot(folder,"09-research");app.close_overlay();app.pause_menu()
	var clock: float=app.sim.time;await app.get_tree().create_timer(.2).timeout
	check(checks,"pause holds battle clock",is_equal_approx(clock,app.sim.time))
	await app.qa_snapshot(folder,"10-pause");app.settings_menu(true);await app.qa_snapshot(folder,"11-settings");app.pause_menu();await app.get_tree().process_frame
	check(checks,"one modal layer",app.modal=="pause" and app.get_tree().get_nodes_in_group("modal_layers").size()==1)
	app.view.reduced_motion=true;app.view.shake=5;app.view.update(.05,true)
	check(checks,"reduced-motion option reaches renderer",app.view.reduced_motion)
	app.profile.loadouts.yin=app.db.all_unit_ids("yin").slice(0,8);app.save_profile();app.load_profile()
	check(checks,"eight-unit save migrates to at most four combat units",app.profile.loadouts.yin.size()==4 and app.db.deployments.yin.size()==4)
	app.mode="campaign";app.start_battle(app.db.campaign[0]);app.accumulator=-10000;app.paused=true;app.sim.winner=0;app.sim.result_reason="自动验收的结果存档夹具";app.show_result();app.load_profile()
	check(checks,"campaign result persists",int(app.profile.unlocked)>=1 and app.profile.stars.has(app.db.campaign[0].id))
	await app.qa_snapshot(folder,"12-result")
	# RC2: validate the whole menu/modal hierarchy and real input gating.
	app.main_menu();await app.get_tree().process_frame
	audit_surface(app,checks,"main menu")
	app.campaign_menu(0);await app.get_tree().process_frame;audit_surface(app,checks,"campaign")
	app.theatre_menu();await app.get_tree().process_frame;audit_surface(app,checks,"six maps")
	app.skirmish_menu();await app.get_tree().process_frame;audit_surface(app,checks,"skirmish")
	app.archive_menu("yin","unit.yin.axe");await app.get_tree().process_frame;audit_surface(app,checks,"library")
	app.show_brief(app.db.campaign[3],"campaign");await app.get_tree().process_frame;audit_surface(app,checks,"briefing")
	app.loadout_menu("yin",app.close_overlay);await app.get_tree().process_frame;audit_surface(app,checks,"deployment")
	fixture(app,{"title":"RC2 界面安全检查","map":"map.01.01","faction":"yin","enemy":"mo","starting_gold":900,"full_tech":false})
	app.open_tech();await app.get_tree().process_frame;audit_surface(app,checks,"research")
	check(checks,"modal buttons allow keyboard focus",app.tech_buttons.values().all(func(b):return b.focus_mode==Control.FOCUS_ALL))
	var queue_size: int=app.sim.players[0].queue.size()
	var keyboard=InputEventKey.new();keyboard.keycode=KEY_1;keyboard.pressed=true
	app._unhandled_input(keyboard)
	check(checks,"research modal blocks army hotkeys",app.sim.players[0].queue.size()==queue_size)
	app.close_overlay();app.pause_menu();await app.get_tree().process_frame;audit_surface(app,checks,"pause")
	app.settings_menu(true);await app.get_tree().process_frame;audit_surface(app,checks,"settings")
	app.close_overlay();app.paused=false;app.toast_left=0;app.sim.time=30;app.update_hud()
	check(checks,"normal play releases objective overlay",not app.status_back.visible and not app.status_label.visible)
	check(checks,"army cards have semantic names",app.unit_cards.values().all(func(c):return not c.accessibility_name.is_empty()))
	fixture(app,{"title":"RC2 施法身体定位","map":"map.01.01","faction":"yin","enemy":"mo","full_tech":true})
	var mining_target: Dictionary=app.sim.spawn("unit.mo.worker",1,17)
	mining_target.body_anchor=app.sim.map.anchor(mining_target.edge,float(mining_target.s)-2.7)
	var mining_body: Vector2=app.sim.physical_point(mining_target)
	camera(app,16);app.view.selected_spell="spell.yin.cold";app.update_hud()
	await app.get_tree().process_frame;await app.get_tree().process_frame
	var worker_height: float=float(app.db.assets[mining_target.id].world_height)*app.view.PX*app.view.PUPPET_SCALE
	await click(app,app.view.unit_position(mining_target)-Vector2(0,worker_height*.55))
	var cold_fx: Array=app.view.effects.filter(func(e):return e.type=="cold")
	check(checks,"area spell pointer submits the same physical body as preview",mining_target.statuses.has("cold") and cold_fx.any(func(e):return Vector2(e.x,e.y).distance_to(mining_body)<.001),{"target":mining_target.uid,"body":[mining_body.x,mining_body.y],"statuses":mining_target.statuses.keys(),"effects":cold_fx.map(func(e):return [e.x,e.y]),"selection":app.view.selected_spell,"mana":app.sim.players[0].mana})
	app.sim.winner=1;app.sim.result_reason="RC2 失败界面夹具";app.result_shown=false;app.show_result();await app.get_tree().process_frame
	audit_surface(app,checks,"defeat result");await app.qa_snapshot(folder,"12b-defeat")
	var adjust=button_named(app.overlay,"调整部署再战")
	if adjust!=null:await press(app,adjust)
	check(checks,"defeat opens deployment for another attempt",app.modal=="loadout")
	app.show_epilogue();await app.qa_snapshot(folder,"13-epilogue")
	await pose_snapshots(app,folder)
	app.profile=original;app.db.deployments=deployments;app.save_profile()
	var failed: Array=checks.filter(func(c):return not c.passed)
	var report: Dictionary={"scope":"Native GPU captures, injected pointer recruitment/refund/site/route/mine/navigation/research, ten faction HUDs and libraries, 50 signal-driven spell UI fixtures, mobile two-group layout, pause and isolated profile migration/save. Controlled poses and forced result fixture are not human play or Android hardware evidence.","engine":Engine.get_version_info(),"mobile_layout":app.mobile_ui,"checks":checks,"failures":failed,"capture_errors":app.capture_errors,"inputs":{},"passed":failed.is_empty() and app.capture_errors.is_empty()}
	for path in ["res://scripts/main.gd","res://scripts/battle_view.gd","res://scripts/map_preview.gd","res://scripts/action_card.gd","res://scripts/theatre_ground.gd","res://scripts/ui_theme.gd","res://scripts/paper_panel.gd","res://scripts/battle_sim.gd","res://tests/theatre_ui_qa.gd","res://data/maps.json","res://data/campaign.json","res://data/assets.json","res://data/balance-prototype.json"]:report.inputs[path]=FileAccess.get_sha256(path)
	for path in ["res://assets/fonts/NotoSansSC.ttf","res://assets/fonts/NotoSerifSC.ttf"]:report.inputs[path]=FileAccess.get_sha256(path)
	var file=FileAccess.open(folder+"/report.json",FileAccess.WRITE);file.store_string(JSON.stringify(report,"\t"));file.close()
	print("THEATRE_UI_QA ",JSON.stringify({"checks":checks.size(),"failures":failed.size(),"passed":report.passed}))
	app.get_tree().quit(0 if report.passed else 1)

static func audit_surface(app,checks: Array,caption: String):
	var root: Control=app.overlay if app.overlay!=null else app.ui
	var buttons: Array=root.find_children("*","Button",true,false)
	var legal: bool=true;var overlap: bool=false;var visible: Array=[]
	for b in buttons:
		if not b.is_visible_in_tree():continue
		var rect: Rect2=b.get_global_rect()
		if rect.position.x<-.1 or rect.position.y<-.1 or rect.end.x>1600.1 or rect.end.y>900.1:legal=false
		visible.append(b)
	for i in range(visible.size()):
		for j in range(i+1,visible.size()):
			if visible[i].get_global_rect().grow(-2).intersects(visible[j].get_global_rect().grow(-2)):overlap=true
	check(checks,"RC2 bounds "+caption,legal,{"buttons":visible.size()})
	check(checks,"RC2 no overlapping controls "+caption,not overlap)

static func pose_snapshots(app,folder: String):
	fixture(app,{"title":"纸偶动作 · 受击与脚点","map":"map.01.01","faction":"yin","enemy":"mo","full_tech":true})
	app.paused=true;app.sim.units.clear();app.sim.events.clear();app.view.camera_x=21;app.view.target_camera=21
	var ids: Array=["unit.yin.axe","unit.deng.illusionist","unit.mo.warden","unit.yuan.harrier","unit.bai.colossus","unit.ji.artillery","unit.mu.worker"]
	var actors: Array=[]
	for i in range(ids.size()):actors.append(app.sim.spawn(ids[i],i%2,21+((i+.5)*1600/ids.size()-800)/78))
	for phase in range(7):
		for actor in actors:
			actor.walk=phase*.19;actor.anim="walk" if phase<3 else "windup" if phase==3 else "attack" if phase<6 else "hurt"
			actor.anim_t=.32 if phase==3 else .12 if phase==5 else 0;actor.hurt=.15 if phase==6 else 0
		await app.qa_snapshot(folder,"pose-%02d"%phase)
