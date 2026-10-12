extends Node

const Data = preload("res://scripts/data_store.gd")
const Simulation = preload("res://scripts/battle_sim.gd")
const LocalDuel = preload("res://scripts/local_duel.gd")
const LanSession = preload("res://scripts/lan_session.gd")
var local_duel
var lan_session
const View = preload("res://scripts/battle_view.gd")
const Sound = preload("res://scripts/audio_controller.gd")
const Card = preload("res://scripts/action_card.gd")
const HudRail = preload("res://scripts/theatre_hud.gd")
const MiniMap = preload("res://scripts/theatre_minimap.gd")
const CampaignRouteGraph = preload("res://scripts/campaign_route_graph.gd")
const UITheme=preload("res://scripts/ui_theme.gd")
const FocusScope=preload("res://scripts/ui_focus_scope.gd")
const BattleSheets=preload("res://scripts/ui_battle_sheets.gd")
const CommandRules=preload("res://scripts/battle_command_rules.gd")
const PaperPanel=preload("res://scripts/paper_panel.gd")
const MobileLayout=preload("res://scripts/mobile_layout.gd")
const MobileUI=preload("res://scripts/mobile_ui.gd")
const MobileInput=preload("res://scripts/mobile_input.gd")
const RecruitmentReadiness=preload("res://scripts/recruitment_readiness.gd")
const CampaignProgress=preload("res://scripts/campaign_progress.gd")
var campaign_progress
var campaign_chapter: int = 0
var tech_page: int = 0
var hud_section: String = "units"
var db
var sim
var view
var audio
var canvas: CanvasLayer
var ui: Control
var overlay: Control
var modal_focus=FocusScope.new()
var theme: Theme
var body_font: Font
var title_font: Font
var screen: String = "menu"
var modal: String = ""
var paused: bool = false
var mode: String = "campaign"
var options: Dictionary = {}
var profile: Dictionary = {"schema":3,"campaign_completed":{},"campaign_last_completed":"","loadouts":{},"story_flags":{},"unlocked":0,"stars":{},"challenge_stars":{},"settings":{"music":.45,"sfx":.7,"reduced_motion":false,"follow_front":false,"battery_saver":false}}
var unit_cards: Dictionary = {}
var spell_cards: Dictionary = {}
var resource_label: Label
var clock_label: Label
var mana_label: Label
var base_label: Label
var army_label: Label
var queue_box: HBoxContainer
var hint_label: Label
var hint_back: Panel
var status_label: Label
var status_back: Panel
var tech_buttons: Dictionary = {}
var battle_sheet
var queue_signature: String = ""
var orders_button: Button
var accumulator: float = 0
var hud_clock: float = 0
var toast_text: String = ""
var toast_left: float = 0
var dragging: bool = false
var drag_start: Vector2
var drag_camera: float = 0
var drag_minimap: bool = false
var pending_target: int = -1
var build_focus_slot: int = -1
var footstep_clock: float = 0
var result_shown: bool = false
var inspect_id: String = ""
var automation: bool = false
var capture_name: String = ""
var mobile_ui: bool = false
var capture_errors: Array = []
var profile_path: String = "user://profile.json"
var mobile
var touch_input
var mobile_blocked: bool=false
var app_suspended: bool=false
var rotation_layer: Control
var mobile_layout_clock: float=0
var mobile_layout_signature: String=""
var mobile_layout_busy: bool=false
var mobile_touch_points: Dictionary={}

func _ready():
	db=Data.new()
	campaign_progress=CampaignProgress.new(db)
	mobile_ui=OS.has_feature("android") or OS.get_cmdline_user_args().has("--mobile-ui")
	var user_args=OS.get_cmdline_user_args()
	if user_args.has("--profile-path"):
		profile_path=user_args[user_args.find("--profile-path")+1]
	load_profile()
	var font_variation=FontVariation.new()
	font_variation.base_font=load("res://assets/fonts/NotoSansSC.ttf")
	font_variation.variation_opentype={"wght":500.0}
	body_font=font_variation
	title_font=body_font
	if ResourceLoader.exists("res://assets/fonts/NotoSerifSC.ttf"): title_font=load("res://assets/fonts/NotoSerifSC.ttf")
	create_theme()
	view=View.new(); view.db=db; view.mobile_ui=mobile_ui; view.menu_characters=not mobile_ui; add_child(view)
	audio=Sound.new(); add_child(audio); audio.settings=profile.settings
	view.reduced_motion=profile.settings.reduced_motion
	canvas=CanvasLayer.new(); add_child(canvas)
	ui=Control.new(); ui.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT); ui.mouse_filter=Control.MOUSE_FILTER_IGNORE; ui.theme=theme; canvas.add_child(ui)
	if mobile_ui:
		Input.emulate_mouse_from_touch=false
		get_tree().quit_on_go_back=false
		get_window().min_size=Vector2i(320,240)
		mobile=MobileUI.new(self);touch_input=MobileInput.new(self)
		get_window().size_changed.connect(func():call_deferred("refresh_mobile_layout"))
		refresh_mobile_layout(false);apply_mobile_quality()
	main_menu()
	audio.set_music("yin")
	# Deterministic screenshot/demo hooks use the shipped simulation, without changing rules.
	var args=OS.get_cmdline_user_args()
	if args.has("--demo"):
		mode="skirmish"
		start_battle({"title":"纸桥岔口 · 地图重做版","faction":"yin","enemy":"mo","map":"map.01.04","difficulty":1,"starting_gold":420,"enemy_starting_gold":420,"full_tech":true,"ai_style":"counter"})
		sim.ai_enabled=[true,true]; automation=true
	if args.has("--capture"):
		var index=args.find("--capture")
		if index+1<args.size(): capture_name=args[index+1]
		capture_delayed()
	if args.has("--qa"):
		var index=args.find("--qa")
		if index+1<args.size(): run_ui_qa(args[index+1])
	if args.has("--qa-world"):
		var index=args.find("--qa-world")
		if index+1<args.size() and ResourceLoader.exists("res://tests/world_ui_qa.gd"):load("res://tests/world_ui_qa.gd").run(self,args[index+1])
	if args.has("--qa-theatre"):
		var index=args.find("--qa-theatre")
		if index+1<args.size() and ResourceLoader.exists("res://tests/theatre_ui_qa.gd"):load("res://tests/theatre_ui_qa.gd").run(self,args[index+1])
	if args.has("--qa-mobile"):
		var index=args.find("--qa-mobile")
		if index+1<args.size() and ResourceLoader.exists("res://tests/mobile_ui_qa.gd"):load("res://tests/mobile_ui_qa.gd").run(self,args[index+1])

func load_profile():
	var path=profile_path
	var campaign_saved: Dictionary=profile.duplicate(true)
	if profile_path=="user://profile.json" and not FileAccess.file_exists(path) and OS.get_name()=="Windows":
		path=OS.get_environment("APPDATA").path_join("Godot/app_userdata/纸上兵戈 · Paper Warfront/profile.json")
	if FileAccess.file_exists(path):
		var saved=JSON.parse_string(FileAccess.get_file_as_string(path))
		if typeof(saved)==TYPE_DICTIONARY:
			campaign_saved=saved
			if int(saved.get("schema",1))<2:
				profile["legacy_campaign"]={"unlocked":saved.get("unlocked",0),"stars":saved.get("stars",{})}
			else:
				profile.unlocked=clampi(int(saved.get("unlocked",0)),0,db.campaign.size()-1)
				profile.stars=saved.get("stars",{})
				profile.loadouts=saved.get("loadouts",{})
				profile.story_flags=saved.get("story_flags",{})
				if saved.has("legacy_campaign"):profile["legacy_campaign"]=saved.legacy_campaign
			profile.challenge_stars=saved.get("challenge_stars",{})
			profile["challenge_scores"]=saved.get("challenge_scores",{})
			for key in profile.settings:
				if typeof(saved.get("settings",{}))==TYPE_DICTIONARY and saved.settings.has(key):profile.settings[key]=saved.settings[key]
	profile.settings.music=clampf(float(profile.settings.music),0,1)
	profile.settings.sfx=clampf(float(profile.settings.sfx),0,1)
	profile.settings.reduced_motion=bool(profile.settings.reduced_motion)
	profile.settings.follow_front=bool(profile.settings.follow_front)
	profile.settings.battery_saver=bool(profile.settings.battery_saver)
	for f in db.FACTIONS:
		var roster: Array = []
		for id in profile.loadouts.get(f,db.factions[f].default_roster):
			if db.all_unit_ids(f).has(id) and not roster.has(id) and roster.size()<4:roster.append(id)
		db.deployments[f]=db.normalize_roster(f,roster)
		profile.loadouts[f]=db.deployments[f].duplicate()
	campaign_progress.migrate(profile,campaign_saved)
	if FileAccess.file_exists(path):save_profile()

func save_profile():
	var file=FileAccess.open(profile_path+".tmp",FileAccess.WRITE)
	if file==null: return
	file.store_string(JSON.stringify(profile,"\t")); file.close()
	DirAccess.rename_absolute(ProjectSettings.globalize_path(profile_path+".tmp"),ProjectSettings.globalize_path(profile_path))

func box(color: Color, border: Color, radius: int = 4) -> StyleBoxFlat:
	return UITheme.paper_box(color,border,radius)

func create_theme():
	theme=UITheme.make_mobile(body_font) if mobile_ui else UITheme.make(body_font)

func clear_ui():
	dragging=false;drag_minimap=false
	modal_focus.release(false)
	if view:view.direct_pan=false
	if touch_input:cancel_mobile_touches()
	for child in ui.get_children():
		if child is CanvasItem:child.hide()
		child.queue_free()
	if overlay and is_instance_valid(overlay): overlay.queue_free()
	overlay=null; modal="";battle_sheet=null
	unit_cards.clear(); spell_cards.clear(); tech_buttons.clear()

func panel(parent: Node, rect: Rect2) -> Panel:
	var p=PaperPanel.new();p.position=rect.position;p.size=rect.size;parent.add_child(p);return p

func label(parent: Node, text: String, rect: Rect2, size_value: int = 22, color: Color = Color("343332"), display: bool = false) -> Label:
	var l=Label.new(); l.text=text; l.position=rect.position; l.size=rect.size
	l.clip_text=true
	l.add_theme_font_size_override("font_size",size_value); l.add_theme_color_override("font_color",color)
	if display: l.add_theme_font_override("font",title_font)
	l.mouse_filter=Control.MOUSE_FILTER_IGNORE; parent.add_child(l); return l

func paragraph(parent: Node, text: String, rect: Rect2, size_value: int = 22) -> Label:
	var l=label(parent,text,rect,size_value); l.autowrap_mode=TextServer.AUTOWRAP_WORD_SMART;l.size=rect.size;return l

func scroll_text(parent: Node, text: String, rect: Rect2, font_size: int = 22):
	var scroll=ScrollContainer.new();scroll.position=rect.position;scroll.size=rect.size;scroll.horizontal_scroll_mode=ScrollContainer.SCROLL_MODE_DISABLED;parent.add_child(scroll)
	var l=Label.new();l.name="ScrollCopy";l.text=text;l.custom_minimum_size=Vector2(rect.size.x-22,0);l.size_flags_horizontal=Control.SIZE_EXPAND_FILL;l.autowrap_mode=TextServer.AUTOWRAP_WORD_SMART
	l.add_theme_font_size_override("font_size",font_size);scroll.add_child(l)
	return l

func button(parent: Node, text: String, rect: Rect2, action: Callable) -> Button:
	var b=Button.new(); b.text=text; b.position=rect.position; b.size=rect.size
	b.clip_text=true;b.text_overrun_behavior=TextServer.OVERRUN_TRIM_ELLIPSIS
	b.tooltip_text=text.replace("\n"," · ")
	b.accessibility_name=text.replace("\n"," · ")
	if mobile_ui:b.add_theme_font_size_override("font_size",18)
	if screen=="battle" and parent==ui:b.focus_mode=Control.FOCUS_NONE
	if not (screen=="battle" and parent==ui):UITheme.decorate(b,text)
	if text.begins_with("继续战役") or text in ["展开战场","继续对战","保存部署","下一折","保存并返回"]:UITheme.primary(b)
	b.pressed.connect(func():audio.play("ui-click"); action.call())
	parent.add_child(b); return b

func image_rect(parent: Node, texture: Texture2D, rect: Rect2) -> TextureRect:
	var t=TextureRect.new(); t.expand_mode=TextureRect.EXPAND_IGNORE_SIZE; t.stretch_mode=TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	t.texture=texture; t.position=rect.position; t.size=rect.size
	t.mouse_filter=Control.MOUSE_FILTER_IGNORE; parent.add_child(t); return t

func menu_header(title: String, subtitle: String):
	var heading=panel(ui,Rect2(64,40,1472,132));heading.mouse_filter=Control.MOUSE_FILTER_IGNORE
	label(ui,title,Rect2(88,50,1260,65),46,UITheme.INK,true)
	label(ui,subtitle,Rect2(90,119,1290,38),21,UITheme.MUTED)
	button(ui,"返回",Rect2(1380,65,130,58),main_menu)

func main_menu():
	if is_instance_valid(local_duel):local_duel.queue_free()
	local_duel=null;view.visible=true
	db.release_unit_atlases()
	if mobile_ui:mobile.main_menu();return
	clear_ui();screen="menu";paused=false;result_shown=false;sim=null
	view.sim=null;view.menu=true;view.selected_spell="";view.selected_building="";view.direct_pan=false
	view.camera_x=28;view.target_camera=28
	label(ui,"纸上",Rect2(100,115,640,150),112,Color("343332"),true)
	label(ui,"兵戈",Rect2(254,230,590,160),126,Color("b74532"),true)
	label(ui,"P A P E R  W A R F R O N T",Rect2(112,395,670,38),22,UITheme.MUTED)
	label(ui,"一纸山河 · 十院对弈",Rect2(114,435,660,40),28,UITheme.INK,true)
	var p=panel(ui,Rect2(920,112,574,680))
	label(p,"展开你的下一折",Rect2(32,24,510,55),34,UITheme.INK,true)
	var actions=[
		["继续战役",func():show_brief(campaign_progress.recommended(profile),"campaign")],
		["新战役",new_battle_menu],["成就挑战",challenge_menu],
		["兵书",func():archive_menu("yin","unit.yin.axe")],["设置",func():settings_menu(false)]]
	for i in range(actions.size()):
		var b=button(p,actions[i][0],Rect2(32,104+i*94,510,76),actions[i][1])
		b.add_theme_font_size_override("font_size",28)
		if i==0:b.add_theme_font_override("font",title_font)
	label(p,"当前军令 · 第 %03d 折"%(int(profile.unlocked)+1),Rect2(34,581,510,30),18,UITheme.MUTED)
	label(p,db.campaign[int(profile.unlocked)].title,Rect2(34,616,510,39),25,UITheme.INK,true)
	label(ui,"离线单人游戏 · "+ProjectSettings.get_setting("application/config/version"),Rect2(88,837,790,32),18,UITheme.MUTED)

func new_battle_menu():
	if mobile_ui:mobile.new_battle_menu();return
	clear_ui();screen="new-battle";view.menu=true
	menu_header("新战役","选择连贯的故事征程，或自由配置双方军阵。")
	button(ui,"故事战役",Rect2(520,290,560,108),campaign_menu)
	button(ui,"遭遇战",Rect2(520,422,560,108),skirmish_menu)

func theatre_menu():
	if mobile_ui:mobile.theatre_menu();return
	clear_ui();screen="theatre";view.menu=true
	menu_header("六张纸场","从矿线、前哨、长坡到纸桥与任务。可直接试演；每局只带2–4个兵种和一个工人。")
	for i in range(6):
		var level: Dictionary=db.campaign[[0,6,10,3,11,5][i]]
		var definition: Dictionary=db.maps[level.map]
		var card_button=button(ui,"",Rect2(86+(i%2)*720,245+(i/2)*196,704,180),func():show_brief(level,"skirmish"))
		label(card_button,definition.name,Rect2(22,12,660,40),29,db.FACTION_COLORS[level.faction],true)
		map_preview(card_button,definition,Rect2(25,57,651,57))
		paragraph(card_button,definition.design_card.question,Rect2(22,119,660,52),23 if mobile_ui else 20)

func credits_menu():
	if mobile_ui:mobile.credits_menu();return
	clear_ui(); screen="credits"; view.menu=true
	menu_header("鸣谢与许可","纸上兵戈 · Paper Warfront  /  "+str(ProjectSettings.get_setting("application/config/version")))
	var p=panel(ui,Rect2(86,190,1428,605))
	paragraph(p,"游戏设计、程序、纸偶素材加工与原创配乐：纸上兵戈制作工程\n美术素材：原创纸雕方案与经加工的生成图像\n引擎：Godot Engine（MIT 许可）\n中文字体：Noto Sans SC 与 Noto Serif SC 的子集（SIL Open Font License 1.1）",Rect2(30,22,1350,150),23)
	var scroll=ScrollContainer.new(); scroll.position=Vector2(30,194); scroll.size=Vector2(1368,382); p.add_child(scroll)
	var text=Label.new(); text.custom_minimum_size=Vector2(1324,0); text.autowrap_mode=TextServer.AUTOWRAP_WORD_SMART
	text.add_theme_font_size_override("font_size",18)
	text.text="Godot Engine\n\n"+FileAccess.get_file_as_string("res://licenses/GODOT-LICENSE.txt")+"\n\nGodot third-party notices\n\n"+FileAccess.get_file_as_string("res://licenses/GODOT-COPYRIGHT.txt")+"\n\nNoto Sans SC\n\n"+FileAccess.get_file_as_string("res://assets/fonts/OFL-NotoSansSC.txt")+"\n\nNoto Serif SC\n\n"+FileAccess.get_file_as_string("res://assets/fonts/OFL-NotoSerifSC.txt")
	scroll.add_child(text)

func campaign_menu(chapter_index: int = -1,page: int = 0):
	if mobile_ui:mobile.campaign_menu(chapter_index,page);return
	clear_ui();screen="campaign";view.menu=true
	if chapter_index>=0:campaign_chapter=clampi(chapter_index,0,9)
	else:campaign_chapter=clampi(int(profile.unlocked)/20,0,9)
	menu_header("战役 · 十院二百折","十位统帅接力保全证据。关卡按剧情开放，已完成的纸页可随时重访。")
	var names: Array = []
	for ch in db.story.chapters:names.append("第 %02d 章  %s"%[int(ch.index)+1,ch.title])
	var chapters=selector(ui,"故事章节",Rect2(87,204,1426,60),names)
	if mobile_ui:chapters.size.y=112;chapters.add_theme_font_size_override("font_size",28)
	chapters.select(campaign_chapter);chapters.item_selected.connect(func(i):campaign_menu(i))
	var f: String = db.FACTIONS[campaign_chapter]
	var left=panel(ui,Rect2(87,326 if mobile_ui else 287,330,548 if mobile_ui else 530))
	image_rect(left,db.art("portrait."+f+".commander",true),Rect2(22,20,285,220))
	label(left,db.factions[f].hero+" · "+db.FACTION_NAMES[f],Rect2(22,247,285,42),24,db.FACTION_COLORS[f],true)
	if mobile_ui:
		page=clampi(page,0,2)
		paragraph(left,"二十折章节故事\n路线按证据分支\n胜利后开放可行动纸页",Rect2(22,293,285,107),25)
		button(ui,"上一页",Rect2(87,739,153,128),func():campaign_menu(campaign_chapter,maxi(0,page-1))).disabled=page==0
		button(ui,"下一页",Rect2(260,739,157,128),func():campaign_menu(campaign_chapter,mini(2,page+1))).disabled=page==2
	else:
		paragraph(left,campaign_route_summary(campaign_chapter),Rect2(22,300,285,148),18)
		paragraph(left,db.mana_hint(f),Rect2(22,463,285,54),18)
	var route_graph=CampaignRouteGraph.new()
	route_graph.chapter=campaign_chapter
	route_graph.levels=[]
	for local in range(20):route_graph.levels.append(db.campaign[campaign_chapter*20+local])
	route_graph.nodes=campaign_progress.nodes
	route_graph.profile=profile
	route_graph.font=body_font
	route_graph.position=Vector2(437,287)
	route_graph.size=Vector2(4*273+257,5*108+34)
	ui.add_child(route_graph)
	for slot in range(9 if mobile_ui else 20):
		var local: int = page*9+slot if mobile_ui else slot
		if local>=20:break
		var index=campaign_chapter*20+local
		var level: Dictionary = db.campaign[index]
		var stars=clampi(int(profile.stars.get(level.id,0)),0,3)
		var rect=Rect2(437+(slot%3)*358,326+(slot/3)*148,336,128) if mobile_ui else Rect2(437+(local%4)*273,287+(local/4)*108,257,96)
		var text: String = "%03d  %s\n%s\n%s"%[index+1,str(level.title).get_slice("·",1),"★".repeat(stars)+"☆".repeat(3-stars),campaign_progress.status(profile,level.id)]
		var b=button(ui,text,rect,func():show_brief(level,"campaign"))
		b.add_theme_font_size_override("font_size",25 if mobile_ui else 18);b.disabled=not campaign_progress.available(profile,level.id)
		b.set_meta("campaign_id",level.id)
		b.tooltip_text=campaign_progress.requirement_hint(level.id)+"\n"+db.map_definition(level.map).decision

func campaign_route_summary(chapter_index: int) -> String:
	return str(db.story.chapters[chapter_index].get("route_summary",db.story.chapters[chapter_index].synopsis))

func mission_brief(level: Dictionary,m: Dictionary) -> String:
	if not db.campaign_narrative.has(level.get("id","")):return "任务："+level.tip+"\n"+m.lesson+" · "+m.regional_rule
	var narrative: Dictionary=db.campaign_narrative[level.id]
	var goal: String=str(narrative.goal)
	var geography: String=str(narrative.geography_reason)
	var condition: String=str({"destroy_base":"摧毁敌方纸城","deliver_gold":"累计真实归仓%d金币"%int(level.get("goal_gold",0)),"survive":"纸城存活%d秒"%int(level.get("duration",0)),"protect":"指定前哨存活%d秒"%int(level.get("duration",0)),"escort":"携证者存活并抵达交接点","intercept":"指定目标越过矿线前将其击倒"}.get(level.win,level.tip))
	return "目标："+goal+"\n地点："+geography+"\n胜利："+condition+"\n战术："+str(m.design_card.question).replace("巨兵","指定目标")

func battle_objective_text() -> String:
	return sim.objective_text().replace("指定巨兵","截证目标")

func show_brief(level: Dictionary, battle_mode: String):
	if mobile_ui:mobile.show_brief(level,battle_mode);return
	mode=battle_mode;options=level.duplicate(true)
	create_overlay("brief",Rect2(246,18 if mobile_ui else 64,1108,866 if mobile_ui else 770))
	var f: String = level.faction
	var m: Dictionary = db.map_definition(level.map)
	label(overlay,("第 %03d 折"%(int(level.get("index",0))+1)) if battle_mode=="campaign" else "战术挑战",Rect2(30,20,1000,40),22,Color("746d61"))
	label(overlay,level.title,Rect2(28,66,1045,58),38,db.FACTION_COLORS[f],true)
	image_rect(overlay,db.art("portrait."+f+".commander",true),Rect2(24,140,285,307))
	paragraph(overlay,"“"+db.factions[f].stake+"”",Rect2(30,472,274,135),22)
	scroll_text(overlay,dialogue_text(level.get("story_before",level.tip)),Rect2(336,141,736,123),22)
	if battle_mode=="campaign":label(overlay,campaign_progress.status(profile,level.id)+" · "+campaign_progress.requirement_hint(level.id),Rect2(336,23,736,24),16,UITheme.MUTED)
	label(overlay,"地图 · "+m.name,Rect2(335,275,730,35),23,Color("343332"),true)
	map_preview(overlay,m,Rect2(336,321,736,132))
	paragraph(overlay,mission_brief(level,m),Rect2(336,471,736,132),19)
	paragraph(overlay,"%s 对 %s   ·   起始金币 %d : %d\n%s"%[db.FACTION_NAMES[f],db.FACTION_NAMES[level.enemy],level.starting_gold,level.enemy_starting_gold,db.mana_hint(f)],Rect2(336,610,736,64),18)
	button(overlay,"调整部署",Rect2(30,720 if mobile_ui else 689,257,128 if mobile_ui else 60),func():loadout_menu(f,func():show_brief(level,battle_mode),level.get("available_roster",db.all_unit_ids(f))))
	button(overlay,"展开战场",Rect2(334,720 if mobile_ui else 689,473,128 if mobile_ui else 60),func():start_battle(options))
	button(overlay,"返回",Rect2(827,720 if mobile_ui else 689,245,128 if mobile_ui else 60),func():
		if screen=="battle":main_menu();campaign_menu()
		else:close_overlay())

func selector(parent: Node, caption: String, rect: Rect2, items: Array) -> OptionButton:
	label(parent,caption,Rect2(rect.position.x,rect.position.y-40,rect.size.x,35),22)
	var option=OptionButton.new(); option.position=rect.position; option.size=rect.size
	if mobile_ui: option.size.y=84
	for item in items: option.add_item(str(item))
	parent.add_child(option); return option

func skirmish_menu():
	if mobile_ui:mobile.skirmish_menu();return
	clear_ui();screen="skirmish";view.menu=true
	menu_header("遭遇战 · 自选纸局","十院公开对弈。双方都需采金归仓、支付费用、等待生产与施工。")
	var p=panel(ui,Rect2(86,204,1428,598))
	var faction_names: Array = []
	for f in db.FACTIONS:faction_names.append(db.FACTION_NAMES[f])
	var ally=selector(p,"我方阵营",Rect2(26,65,400,64),faction_names)
	var enemy=selector(p,"敌方阵营",Rect2(475,65,400,64),faction_names);enemy.select(1)
	var ids: Array = db.maps.keys();var map_names: Array = []
	for id in ids:map_names.append(db.maps[id].name)
	var map_choice=selector(p,"二百张纸面山河",Rect2(924,65,476,64),map_names)
	var difficulty=selector(p,"AI 决策节奏",Rect2(26,201,400,64),["入门 · 慢决策","标准 · 连续调配","强敌 · 快速反制"]);difficulty.select(1)
	var style=selector(p,"AI 战术倾向",Rect2(475,201,400,64),["前期压制","经济攀升","空间反制"]);style.select(2)
	var full=CheckButton.new();full.text="完整科技开局";full.position=Vector2(930,201);full.size=Vector2(460,64);p.add_child(full)
	var preview_holder=Control.new();preview_holder.position=Vector2(26,295);p.add_child(preview_holder)
	var description=paragraph(p,"",Rect2(26,438,876,124),21)
	var refresh=func():
		for child in preview_holder.get_children():child.queue_free()
		var m: Dictionary = db.maps[ids[map_choice.selected]]
		map_preview(preview_holder,m,Rect2(0,0,1374,127))
		description.text=m.decision+"\n"+db.mana_hint(db.FACTIONS[ally.selected])
	map_choice.item_selected.connect(func(_i):refresh.call());ally.item_selected.connect(func(_i):refresh.call());refresh.call()
	button(p,"部署编组",Rect2(952,448,422,59),func():loadout_menu(db.FACTIONS[ally.selected],close_overlay))
	button(p,"本机双人分屏",Rect2(475,521,400,59),func():start_local_duel({"title":"双人对弈","faction":db.FACTIONS[ally.selected],"enemy":db.FACTIONS[enemy.selected],"map":ids[map_choice.selected],"starting_gold":300,"enemy_starting_gold":300,"full_tech":full.button_pressed,"win":"destroy_base"}))
	button(p,"局域网对弈",Rect2(26,521,400,59),func():lan_menu({"faction":db.FACTIONS[ally.selected],"enemy":db.FACTIONS[enemy.selected],"map":ids[map_choice.selected],"starting_gold":300,"enemy_starting_gold":300,"full_tech":full.button_pressed,"win":"destroy_base"}))
	button(p,"开 战",Rect2(952,521,422,59),func():
		mode="skirmish"
		start_battle({"title":"遭遇战","faction":db.FACTIONS[ally.selected],"enemy":db.FACTIONS[enemy.selected],"map":ids[map_choice.selected],"difficulty":difficulty.selected,"ai_style":["rush","economy","counter"][style.selected],"starting_gold":300,"enemy_starting_gold":300,"full_tech":full.button_pressed,"win":"destroy_base"}))

func start_local_duel(settings: Dictionary):
	if ui.size.x<800 or ui.size.y<600:
		toast("双人分屏需要至少800×600的界面空间，请使用电脑或大屏平板。",4);return
	clear_ui();screen="local-duel";sim=null;paused=false;view.visible=false
	local_duel=LocalDuel.new();local_duel.size=ui.size;local_duel.theme=theme;ui.add_child(local_duel)
	local_duel.initialize(db,settings,audio)
	local_duel.exit_requested.connect(func():local_duel.queue_free();local_duel=null;view.visible=true;skirmish_menu())

func lan_menu(settings: Dictionary):
	if mobile_ui:mobile.lan_menu(settings);return
	clear_ui();screen="lan-lobby";view.menu=true
	menu_header("局域网对弈","房主使用当前地图与阵营设置。加入者控制东侧阵营。双方需要位于可互通的网络。")
	var p=panel(ui,Rect2(200,240,1200,420))
	paragraph(p,"房主地址",Rect2(32,36,600,40),24)
	var address=LineEdit.new();address.placeholder_text="例如 192.168.1.20";address.position=Vector2(32,90);address.size=Vector2(1136,64);p.add_child(address)
	button(p,"创建房间",Rect2(32,210,540,64),func():start_lan(settings,""))
	button(p,"加入房间",Rect2(628,210,540,64),func():
		if address.text.strip_edges().is_empty():toast("请输入房主地址");return
		start_lan(settings,address.text.strip_edges()))
func start_lan(settings: Dictionary,address: String):
	clear_ui();screen="lan-match";sim=null;view.visible=false
	var session=LanSession.new();session.name="LanSession";session.size=ui.size;session.theme=theme;ui.add_child(session)
	lan_session=session
	session.initialize(db,settings,address,audio)
	session.exit_requested.connect(func():session.queue_free();lan_session=null;view.visible=true;skirmish_menu())

func challenge_menu():
	if mobile_ui:mobile.challenge_menu();return
	clear_ui(); screen="challenges"; view.menu=true
	menu_header("战术挑战 · 六道纸题","每道题都有明确胜负条件，可以随时重开。")
	var challenges=db.read_json("res://data/campaign.json").challenges
	for i in range(challenges.size()):
		var c=challenges[i]
		var p=panel(ui,Rect2(86+(i%3)*480,190+(i/3)*300,455,276))
		label(p,"%02d  %s"%[i+1,c.title],Rect2(25,19,405,47),28,db.FACTION_COLORS[c.faction],true)
		paragraph(p,c.tip,Rect2(25,89,401,87),21)
		var stars=clampi(int(profile.challenge_stars.get(c.id,0)),0,3)
		label(p,"★".repeat(stars)+"☆".repeat(3-stars),Rect2(25,163,401,35),21,Color("a58137"))
		button(p,"展开纸题",Rect2(25,203,401,53),func():show_brief(c,"challenge"))

func create_overlay(name_value: String, rect: Rect2):
	battle_sheet=null
	dragging=false;drag_minimap=false;view.direct_pan=false
	if touch_input:cancel_mobile_touches()
	modal_focus.capture(ui)
	if overlay and is_instance_valid(overlay):overlay.get_parent().hide();overlay.get_parent().queue_free()
	var layer=Control.new(); layer.name="ModalLayer"; layer.add_to_group("modal_layers"); layer.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT); layer.mouse_filter=Control.MOUSE_FILTER_STOP; ui.add_child(layer)
	var shade=ColorRect.new(); shade.color=Color(.13,.12,.1,.63); shade.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT); layer.add_child(shade)
	overlay=panel(layer,rect); modal=name_value
	modal_focus.enter.call_deferred(overlay)

func close_overlay():
	if touch_input:cancel_mobile_touches()
	if overlay and is_instance_valid(overlay):overlay.get_parent().hide();overlay.get_parent().queue_free()
	modal_focus.release()
	overlay=null; modal=""; tech_buttons.clear();battle_sheet=null
	if mobile:mobile.sheet_restore=Callable()

func start_battle(config: Dictionary):
	db.release_unit_atlases()
	options=config.duplicate(true)
	var faction: String = options.faction
	var available: Array = options.get("available_roster",db.all_unit_ids(faction))
	var slots: int = clampi(options.get("default_roster",db.factions[faction].default_roster).size(),2,4)
	options["combat_slots"]=slots
	var chosen: Array=db.deployments.get(faction,db.factions[faction].default_roster)
	if options.has("default_roster") and chosen==db.factions[faction].default_roster:chosen=options.default_roster
	options["player_roster"]=db.normalize_roster(faction,chosen,available,slots)
	if not options.has("enemy_roster"):options["enemy_roster"]=db.factions[options.enemy].default_roster.duplicate()
	clear_ui();screen="battle";paused=false;result_shown=false;hud_section="units"
	accumulator=0;queue_signature="";toast_text="";toast_left=0;inspect_id=""
	sim=Simulation.new(db);sim.start(options)
	view.reset(sim);view.follow_front=profile.settings.follow_front;view.reduced_motion=profile.settings.reduced_motion
	audio.set_music(options.faction);build_hud()
	view.camera_x=minf(view.width/view.PX*.5,sim.map.length*.5);view.target_camera=view.camera_x
	toast("先招募前排与远程，保护工人运回金币。",4)

func card(parent: Node, id: String, rect: Rect2, magic: bool, action: Callable):
	var c=Card.new(); c.position=rect.position; c.size=rect.size
	c.art=db.art(id,not magic); c.title=db.name_of(id)
	if mobile_ui:
		c.compact_touch=true
		if screen=="battle" and not magic and c.title.length()>5:c.title=c.title.right(4)
	c.accent=UITheme.JADE if magic else UITheme.GOLD
	c.tooltip_text=db.spell_hint(id) if magic else db.unit_hint(id)
	c.accessibility_name=db.name_of(id);c.accessibility_description=c.tooltip_text
	if screen=="battle":
		if parent==ui:c.focus_mode=Control.FOCUS_NONE
		if parent==ui:
			c.battle_layout=true
			c.title=db.name_of(id).right(4 if mobile_ui else 5)
			c.tooltip_text=db.name_of(id)+"\n"+c.tooltip_text
			for state in ["normal","hover","pressed","disabled","focus"]:c.add_theme_stylebox_override(state,StyleBoxEmpty.new())
	c.pressed.connect(func():
		if c.suppress_activation:c.suppress_activation=false
		else:action.call())
	if mobile_ui:c.details_requested.connect(func():mobile.card_info(id,magic))
	parent.add_child(c); return c

func hud_button(text: String,rect: Rect2,action: Callable) -> Button:
	var b=button(ui,text,rect,action)
	b.add_theme_font_size_override("font_size",25 if mobile_ui else 20)
	return b

func build_hud():
	if mobile_ui:mobile.build_hud();return
	queue_signature=""
	var faction: String = sim.players[0].faction
	view.desktop_playfield=Rect2(0,56,1600,754)
	view.desktop_floor=view.desktop_playfield.end.y-sim.map.bounds.end.y*view.PY-maxf(120,view.desktop_playfield.size.y*.20)
	var top=panel(ui,Rect2(0,0,1600,56));top.name="HudTopRail";top.mouse_filter=Control.MOUSE_FILTER_IGNORE
	var bottom=panel(ui,Rect2(0,810,1600,90));bottom.name="HudBottomRail";bottom.mouse_filter=Control.MOUSE_FILTER_IGNORE
	view.desktop_minimap=Rect2(1132,8,304,40)
	var navigation=MiniMap.new();navigation.view=view;navigation.size=Vector2(1600,900);navigation.mouse_filter=Control.MOUSE_FILTER_IGNORE;ui.add_child(navigation)
	image_rect(ui,UITheme.art("icon-gold"),Rect2(16,4,26,26));image_rect(ui,UITheme.art("icon-mana"),Rect2(180,4,26,26))
	resource_label=label(ui,"",Rect2(48,0,128,32),24,UITheme.GOLD)
	mana_label=label(ui,"",Rect2(212,0,250,32),20,UITheme.JADE)
	clock_label=label(ui,"",Rect2(480,0,626,32),20,UITheme.INK)
	base_label=label(ui,"",Rect2(0,0,0,0),18,UITheme.MUTED);base_label.hide()
	hud_button("暂停",Rect2(1468,4,112,48),pause_menu)
	queue_box=HBoxContainer.new();queue_box.visible=false;ui.add_child(queue_box)
	army_label=label(ui,"",Rect2(0,0,0,0),17,UITheme.MUTED);army_label.hide()
	var units_order: Array = sim.players[0].roster.duplicate();units_order.append("unit."+faction+".worker")
	for i in range(units_order.size()):
		var id: String = units_order[i]
		var c=card(ui,id,Rect2(16+i*108,814,100,80),false,func():recruit_action(id))
		c.slim_battle=true;c.detail=str(i+1);unit_cards[id]=c
	var spells_order: Array = db.spell_ids(faction)
	for i in range(spells_order.size()):
		var id: String = spells_order[i]
		var c=card(ui,id,Rect2(790+i*116,814,108,80),true,func():select_spell(id))
		c.slim_battle=true;c.detail=["Q","W","E","R","T"][i];spell_cards[id]=c
	orders_button=hud_button("军令",Rect2(1404,814,176,80),func():cancel_selection() if view.selected_spell!="" or view.selected_building!="" else open_orders())
	orders_button.name="HudOrders"
	hint_back=panel(ui,Rect2(8,32,1098,24));hint_back.mouse_filter=Control.MOUSE_FILTER_IGNORE
	hint_label=label(ui,"",Rect2(16,32,1082,24),15,UITheme.INK)
	status_back=panel(ui,Rect2(8,32,1098,24));status_back.mouse_filter=Control.MOUSE_FILTER_IGNORE
	status_label=label(ui,"",Rect2(16,32,1082,24),15,UITheme.INK)
	update_hud()

func open_orders():
	if mobile_ui:mobile.orders_menu();return
	create_overlay("orders",Rect2(430,225,740,456))
	label(overlay,"军令 · 投资与导航",Rect2(24,16,566,45),28,UITheme.INK,true)
	button(overlay,"关闭",Rect2(610,16,106,48),close_overlay)
	battle_sheet=BattleSheets.new()
	battle_sheet.summary=label(overlay,"",Rect2(24,70,692,48),18,UITheme.MUTED)
	battle_sheet.refresh(sim,0,paused)
	var entries: Array=[["研究科技 F",open_tech],["建造塔灯 B",open_build],["招募队列",open_queue],["返回纸城",func():close_overlay();view.target_camera=sim.bases[0].x+6;view.follow_front=false],["追踪交锋",func():close_overlay();view.follow_front=true;view.target_camera=sim.front(view.player_side)],["取消当前选择",func():close_overlay();cancel_selection()]]
	for i in range(entries.size()):button(overlay,entries[i][0],Rect2(24+(i%3)*236,124+(i/3)*84,220,68),entries[i][1])
	paragraph(overlay,"1–7 招募 · Q/W/E/R/T 选法术 · F 研究 · B 建造\n拖动战场或右上战线图导航，右键 / Esc 取消选择。",Rect2(24,306,692,64),18)
	button(overlay,"返回战场",Rect2(24,388,692,48),close_overlay)

func toast(text: String, duration: float = 2.5):
	toast_text=text; toast_left=duration
	if status_label and is_instance_valid(status_label): status_label.text=text

func execute(kind: String, args: Dictionary) -> bool:
	if paused or sim==null: return false
	var result=sim.request(0,kind,args)
	if not result.ok: audio.play("ui-invalid"); toast(result.error); return false
	return true

func recruit_action(id: String):
	if not sim.players[0].unlocked.has(id):open_tech();toast("在兵书研究「"+db.name_of(id)+"」后即可招募",3);return
	if execute("recruit",{"id":id}): toast(db.name_of(id)+" 已进入招募队列",1.6)

func select_spell(id: String):
	if paused or sim==null: return
	if not sim.players[0].unlocked.has(id):
		toast("先在科技树研究「"+db.name_of(id)+"」"); audio.play("ui-invalid"); return
	if sim.players[0].mana<float(db.balance.spells[id].mana): toast("法力不足"); audio.play("ui-invalid"); return
	if sim.players[0].cooldowns.get(id,0)>0: toast("法术正在冷却"); audio.play("ui-invalid"); return
	view.selected_building=""
	view.selected_spell="" if view.selected_spell==id else id
	view.selected_uid=0
	audio.play("ui-click")
	if view.selected_spell!="": toast(db.name_of(id)+"："+db.spell_hint(id),6)
	update_hud()

func cancel_selection():
	view.selected_spell=""; view.selected_building=""; view.selected_uid=0
	build_focus_slot=-1
	audio.play("ui-cancel"); update_hud()

func update_hud():
	if sim==null or screen!="battle": return
	if battle_sheet!=null and is_instance_valid(overlay):battle_sheet.refresh(sim,0,paused)
	var p=sim.players[0]
	resource_label.text=str(int(p.gold))
	mana_label.text="%d / 100  +%.1f/s"%[int(p.mana),sim.mana_rate(0)]
	clock_label.text="%s  ·  %02d:%02d"%[options.title,int(sim.time)/60,int(sim.time)%60]
	base_label.text="我城 %d   /   敌城 %s"%[int(sim.bases[0].hp),str(int(sim.bases[1].hp)) if sim.visible_to(0,sim.bases[1]) else "未知"]
	army_label.text="兵 %d/60  ·  工 %d/%d  ·  队列 %d/6"%[sim.population(0,false,false),sim.population(0,true,false),int(options.get("worker_limit",10)),p.queue.size()]
	var own_front_distance: float=RecruitmentReadiness.front_distance(sim,0)
	for id in unit_cards:
		var c=unit_cards[id]; c.locked=not p.unlocked.has(id); c.price="%d 金"%int(db.balance.units[id].gold)
		c.affordable=p.gold>=float(db.balance.units[id].gold); c.queue_redraw()
		c.queue_count=p.queue.count(id)
		c.tooltip_text=db.name_of(id)+"\n"+db.unit_hint(id)+"\n"+RecruitmentReadiness.investment_notice(sim,0,id)+"\n"+RecruitmentReadiness.reinforcement_notice(sim,0,id,own_front_distance)
		c.accessibility_description=c.tooltip_text
		c.production_ratio=-1.0 if p.queue.is_empty() or p.queue[0]!=id else p.production/float(db.balance.units[id].get("production_seconds",2))
	for id in spell_cards:
		var c=spell_cards[id]; var def=db.balance.spells[id]
		c.locked=not p.unlocked.has(id); c.price="%d 法"%int(def.mana); c.affordable=p.mana>=float(def.mana)
		c.cooling=p.cooldowns.get(id,0); c.cooldown_total=float(def.cooldown); c.selected=view.selected_spell==id; c.queue_redraw()
	var signature=str(p.queue_revision)+":"+str(p.queue)
	if signature!=queue_signature:
		queue_signature=signature
		for c in queue_box.get_children(): c.queue_free()
		if p.queue.is_empty():
			label(queue_box,"招募队列 · 空",Rect2(0,0,350,36),17,Color("746d61"))
		else:
			for i in range(p.queue.size()):
				var revision: int=int(p.queue_revision)
				var id=p.queue[i]; var b=Button.new(); b.custom_minimum_size=Vector2(46,36); b.icon=db.art(id,true); b.expand_icon=true; b.icon_alignment=HORIZONTAL_ALIGNMENT_CENTER
				b.focus_mode=Control.FOCUS_NONE
				b.tooltip_text=db.name_of(id)+" · 点击取消并退款"
				b.pressed.connect(func():execute("cancel_queue",{"index":i,"id":id,"queue_revision":revision}))
				queue_box.add_child(b)
	if mobile_ui:
		mobile.update_hud()
		if modal=="tech":refresh_tech()
		if sim.bases[0].hp<330 and not paused:audio.danger()
		return
	if hint_label and is_instance_valid(hint_label):
		if view.selected_spell!="": hint_label.text="点选目标施法  ·  右键 / Esc / 取消：撤销选择"
		elif view.selected_building!="": hint_label.text="点击发亮的兼容建造位开始施工  ·  取消不会扣费"
		else: hint_label.text="拖动战场 / 右上战线图导航 · 军令中研究、建造与查队列" if sim.time<8 else ""
		hint_label.visible=not hint_label.text.is_empty();hint_back.visible=hint_label.visible
	if status_label and is_instance_valid(status_label):
		if toast_left>0: status_label.text=toast_text
		elif not p.research.is_empty(): status_label.text="正在研究 %s  ·  %.1f 秒"%[db.name_of(db.tech(p.research.id).grant),p.research.left]
		elif options.get("win","")=="survive": status_label.text="守住纸城  ·  剩余 %d 秒"%maxi(0,int(float(options.duration)-sim.time))
		elif view.selected_uid>0:
			var a=sim.actor(view.selected_uid)
			if not sim.visible_to(0,a):a={};view.selected_uid=0
			var work_names: Dictionary={"mine":"挥镐采矿","queue":"等待矿位","walk":"负重回城" if a.get("cargo",0)>0 else "前往矿点","unload":"卸货入库","load":"装袋"}
			var detail: String=work_names.get(str(a.get("anim","")),"准备运输") if not a.is_empty() and db.balance.units[a.id].get("economy",false) else "" if a.is_empty() else db.unit_hint(a.id)
			status_label.text="" if a.is_empty() else "%s  ·  %s  ·  生命 %d/%d  ·  %s"%["我方" if a.side==0 else "敌方",db.name_of(a.id),int(a.hp),int(a.max_hp),detail]
		else: status_label.text=battle_objective_text()
		var visible_status: bool=toast_left>0 or not p.research.is_empty() or view.selected_uid>0 or str(options.get("win","destroy_base"))!="destroy_base"
		status_label.visible=visible_status and view.selected_spell=="" and view.selected_building=="";status_back.visible=status_label.visible
		if status_label.visible:hint_label.hide();hint_back.hide()
	if orders_button and is_instance_valid(orders_button):orders_button.text="取消选择" if view.selected_spell!="" or view.selected_building!="" else "军令 · 队%d"%p.queue.size()
	if modal=="tech": refresh_tech()
	if sim.bases[0].hp<330 and not paused: audio.danger()

func open_tech(page: int = 0):
	if mobile_ui:mobile.open_tech(page);return
	if paused or sim==null:return
	cancel_selection();create_overlay("tech",Rect2(220,67,1160,766) if mobile_ui else Rect2(562,213,966,570));tech_page=page
	overlay.get_parent().get_child(0).color=Color(.1,.09,.07,.3)
	label(overlay,"科技 · "+db.FACTION_NAMES[sim.players[0].faction],Rect2(26,16,755,56),34,db.FACTION_COLORS[sim.players[0].faction],true)
	button(overlay,"关闭",Rect2(1006,21,128,128) if mobile_ui else Rect2(824,21,116,48),close_overlay)
	var p=sim.players[0];var nodes: Array = []
	for node in db.technology.nodes:
		if node.faction!=p.faction:continue
		if node.grant.begins_with("unit.") and not p.roster.has(node.grant):continue
		nodes.append(node)
	var doctrines: Array = []
	var others: Array = []
	for node in nodes:
		if str(node.id).contains(".doctrine"):doctrines.append(node)
		else:others.append(node)
	nodes=doctrines+others
	var per_page: int = 4 if mobile_ui else 8
	var pages: int = maxi(1,int(ceilf(nodes.size()/float(per_page))))
	tech_page=clampi(page,0,pages-1)
	for local in range(per_page):
		var index=tech_page*per_page+local
		if index>=nodes.size():break
		var node: Dictionary = nodes[index]
		var rect=Rect2(26+(local%2)*576,166+(local/2)*148,552,128) if mobile_ui else Rect2(26+(local%2)*466,92+(local/2)*93,448,80)
		var b=button(overlay,"",rect,func():
			if execute("research",{"id":node.id}):toast("开始研究 "+db.name_of(node.grant)))
		b.add_theme_font_size_override("font_size",26 if mobile_ui else 19)
		var requirements: Array = []
		for req in node.requires:requirements.append(db.name_of(db.tech(req).grant))
		b.tooltip_text="前置："+("无" if requirements.is_empty() else "、".join(requirements));tech_buttons[node.id]=b
	button(overlay,"上一页",Rect2(26,486,260,128) if mobile_ui else Rect2(26,478,155,52),func():open_tech(maxi(0,tech_page-1))).disabled=tech_page==0
	button(overlay,"下一页",Rect2(310,486,260,128) if mobile_ui else Rect2(200,478,155,52),func():open_tech(mini(pages-1,tech_page+1))).disabled=tech_page==pages-1
	paragraph(overlay,"%d / %d  ·  研究与出兵共同消耗金币"%[tech_page+1,pages],Rect2(600,486,534,128) if mobile_ui else Rect2(381,480,550,43),26 if mobile_ui else 20)
	refresh_tech()

func refresh_tech():
	BattleSheets.update_research(sim,0,tech_buttons,paused)

func open_build(slot: int = -1):
	if mobile_ui:mobile.open_build(slot);return
	if paused or sim==null:return
	cancel_selection();create_overlay("build",Rect2(260,140,1080,638) if mobile_ui else Rect2(866,269,656,385))
	build_focus_slot=slot
	var site: Dictionary = sim.slot_anchor(0,slot) if slot>=0 and slot<sim.side_sites(0).size() else {}
	label(overlay,"建造 · "+str(site.get("label","固定塔灯位")),Rect2(25,15,510,55),32,Color("343332"),true)
	var f: String = sim.players[0].faction
	var tower: Dictionary = db.balance.buildings["building."+f+".tower"]
	var lamp: Dictionary = db.balance.buildings["building."+f+".mana"]
	var tower_button=button(overlay,"纸哨塔 · %d 金 · %d 秒施工"%[tower.gold,tower.construction_seconds],Rect2(26,92,602,87),func():choose_building("building."+f+".tower"))
	var lamp_button=button(overlay,"产法纸灯 · %d 金 · %d 秒施工"%[lamp.gold,lamp.construction_seconds],Rect2(26,192,602,87),func():choose_building("building."+f+".mana"))
	battle_sheet=BattleSheets.new()
	battle_sheet.bind_build(tower_button,"building."+f+".tower",slot,true,tower_button.text)
	battle_sheet.bind_build(lamp_button,"building."+f+".mana",slot,true,lamp_button.text)
	battle_sheet.refresh(sim,0,paused)
	var types: Array=site.get("types",["tower","mana"])
	var caption: String = "本图 %d 个我方建造位。选择建筑后，视角会移到兼容空位。"%sim.side_sites(0).size() if site.is_empty() else "这里可建"+("纸哨塔" if types==["tower"] else "产法纸灯" if types==["mana"] else "塔或灯")+"；选好后点发亮位置开始施工。"
	caption+="\n塔完工后覆盖矿路；灯每秒 +%.1f 法力，封禁时停产。"%lamp.mana_per_second
	paragraph(overlay,caption,Rect2(28,293,589,75),18)
	button(overlay,"关闭",Rect2(926,20,128,128) if mobile_ui else Rect2(573,20,55,50),close_overlay)

func choose_building(id: String):
	var error: String=CommandRules.build_selection_error(sim,0,id,build_focus_slot)
	if not error.is_empty():toast(error);audio.play("ui-invalid");return
	var slots: Array = []
	for i in range(sim.side_sites(0).size()):
		var site: Dictionary = sim.slot_anchor(0,i)
		if not site.get("types",["tower","mana"]).has(id.get_slice(".",2)):continue
		var occupied: bool = false
		for b in sim.buildings:
			if b.side==0 and b.slot==i and b.hp>0:occupied=true;break
		if not occupied:slots.append(i)
	if slots.is_empty():toast("没有兼容的空闲建造位");audio.play("ui-invalid");return
	if not slots.has(build_focus_slot):build_focus_slot=slots[0]
	view.selected_building=id;view.selected_spell="";view.target_camera=sim.slot_anchor(0,build_focus_slot).x;view.follow_front=false
	close_overlay();toast("点击发亮的"+str(sim.slot_anchor(0,build_focus_slot).get("label","建造位"))+"开始施工；施工前不会扣费。",6)

func pause_menu(show_help: bool = false):
	if mobile_ui:mobile.pause_menu(show_help);return
	if sim==null or sim.winner!=-2: return
	if mobile_ui:
		paused=true;cancel_selection();create_overlay("pause",Rect2(246,40,1108,820))
		label(overlay,"兵书" if show_help else "战局暂歇",Rect2(35,21,1038,64),42,Color("343332"),true)
		scroll_text(overlay,"军团自行行军与交战。金币由纸工运回；法力用于手动施法。点路标改变后续部队选路，点矿点调整运输优先级，点塔灯位打开建造。\n\n触屏：招募与法术同时显示；选择法术后点目标。拖动战場或点战线图导航，队列面板可取消退款。",Rect2(35,104,1038,186),27)
		button(overlay,"继续对战",Rect2(35,315,1038,128),func():paused=false;close_overlay())
		button(overlay,"重新开局",Rect2(35,467,509,128),func():start_battle(options))
		button(overlay,"声音与显示",Rect2(566,467,507,128),func():settings_menu(true))
		button(overlay,"结束本局并返回主菜单",Rect2(35,619,1038,128),main_menu)
		return
	paused=true; cancel_selection(); create_overlay("pause",Rect2(434,140,732,630))
	label(overlay,"兵书" if show_help else "战局暂歇",Rect2(40,21,652,64),42,Color("343332"),true)
	paragraph(overlay,"军团自行行军与交战。金币由纸工运回入账；法力用于手动施法。常规对战有六个作战兵加纸工，研究开启高阶兵与法术。\n\n电脑：1–7 招募，Q W E R T 施法，F 研究，B 建造，A D 移动，Home 纸城，Space 交锋，P 暂停。\n点矿点、路标和塔灯位作出地图决策。",Rect2(40,107,652,282),22)
	button(overlay,"继续对战",Rect2(40,410,652,64),func():paused=false;close_overlay())
	button(overlay,"重新开局",Rect2(40,488,315,62),func():start_battle(options))
	button(overlay,"声音与显示",Rect2(376,488,316,62),func():settings_menu(true))
	button(overlay,"结束本局并返回主菜单",Rect2(40,563,652,44),main_menu)

func settings_menu(in_battle: bool):
	if mobile_ui:mobile.settings_menu(in_battle);return
	if mobile_ui:
		if in_battle:paused=true
		else:clear_ui();screen="settings";view.menu=true
		create_overlay("settings",Rect2(260,24,1080,852))
		label(overlay,"声音与显示",Rect2(26,20,1028,64),42,Color("343332"),true)
		for i in range(2):
			var key: String = ["music","sfx"][i]
			label(overlay,"音乐音量" if i==0 else "动作与界面音量",Rect2(26,102+i*202,1028,40),29)
			var slider=HSlider.new();slider.position=Vector2(26,156+i*202);slider.size=Vector2(1028,128);slider.min_value=0;slider.max_value=1;slider.step=.01;slider.value=profile.settings[key]
			slider.value_changed.connect(func(value):profile.settings[key]=value;audio.settings=profile.settings);overlay.add_child(slider)
		var reduced=CheckButton.new();reduced.text="减少镜头与背景动效";reduced.position=Vector2(26,522);reduced.size=Vector2(504,128);reduced.button_pressed=profile.settings.reduced_motion
		reduced.toggled.connect(func(value):profile.settings.reduced_motion=value;view.reduced_motion=value);overlay.add_child(reduced)
		var follow=CheckButton.new();follow.text="开局跟随交锋";follow.position=Vector2(554,522);follow.size=Vector2(500,128);follow.button_pressed=profile.settings.follow_front
		follow.toggled.connect(func(value):profile.settings.follow_front=value);overlay.add_child(follow)
		button(overlay,"保存并返回",Rect2(26,698,1028,128),func():
			save_profile()
			if in_battle:pause_menu()
			else:main_menu())
		return
	if in_battle:
		paused=true; create_overlay("settings",Rect2(396,65,808,782))
	else:
		clear_ui(); screen="settings"; view.menu=true
		create_overlay("settings",Rect2(396,65,808,782))
	label(overlay,"声音与显示",Rect2(37,20,730,69),42,Color("343332"),true)
	for i in range(2):
		var key=["music","sfx"][i]
		label(overlay,"音乐音量" if i==0 else "动作与界面音量",Rect2(40,112+i*100,690,38),24)
		var slider=HSlider.new(); slider.position=Vector2(41,164+i*100); slider.size=Vector2(721,31); slider.min_value=0; slider.max_value=1; slider.step=.01; slider.value=profile.settings[key]
		slider.value_changed.connect(func(value):profile.settings[key]=value;audio.settings=profile.settings)
		overlay.add_child(slider)
	var reduced=CheckButton.new(); reduced.text="减少镜头与背景动效"; reduced.position=Vector2(39,322); reduced.size=Vector2(719,65); reduced.button_pressed=profile.settings.reduced_motion
	reduced.toggled.connect(func(value):profile.settings.reduced_motion=value;view.reduced_motion=value); overlay.add_child(reduced)
	var follow=CheckButton.new(); follow.text="开局自动追踪交锋"; follow.position=Vector2(39,397); follow.size=Vector2(719,65); follow.button_pressed=profile.settings.follow_front
	follow.toggled.connect(func(value):profile.settings.follow_front=value); overlay.add_child(follow)
	if not OS.has_feature("android"):
		button(overlay,"切换全屏",Rect2(40,480,722,57),func():
			DisplayServer.window_set_mode(DisplayServer.WINDOW_MODE_WINDOWED if DisplayServer.window_get_mode()==DisplayServer.WINDOW_MODE_FULLSCREEN else DisplayServer.WINDOW_MODE_FULLSCREEN))
	if not in_battle:
		button(overlay,"地图试演",Rect2(40,554,345,52),theatre_menu)
		button(overlay,"操作帮助",Rect2(417,554,345,52),desktop_help)
		button(overlay,"鸣谢与许可",Rect2(40,620,345,52),credits_menu)
		button(overlay,"退出游戏",Rect2(417,620,345,52),func():save_profile();get_tree().quit())
	button(overlay,"保存并返回",Rect2(40,695 if not in_battle else 555,722,62),func():
		save_profile()
		if in_battle: pause_menu()
		else: main_menu())

func archive_menu(faction: String, selected: String, page: int = 0):
	if mobile_ui:mobile.archive_menu(faction,selected,page);return
	clear_ui();screen="archive";view.menu=true
	menu_header("兵书 · 十院军阵","每院六种独特作战兵种。选择编组前先了解装备、能力与反制。")
	var names: Array = []
	for f in db.FACTIONS:names.append(db.FACTION_NAMES[f])
	var factions=selector(ui,"阵营",Rect2(87,207,530,60),names);factions.select(db.FACTIONS.find(faction))
	factions.item_selected.connect(func(i):archive_menu(db.FACTIONS[i],db.all_unit_ids(db.FACTIONS[i])[0],0))
	button(ui,"部署编组",Rect2(644,207,270,60),func():loadout_menu(faction,func():archive_menu(faction,selected,page)))
	var left=panel(ui,Rect2(87,287,389,582 if mobile_ui else 530));var right=panel(ui,Rect2(494,287,1018,582 if mobile_ui else 530))
	label(left,db.name_of(selected),Rect2(21,18,347,54),31,db.FACTION_COLORS[faction],true)
	image_rect(left,db.art(selected),Rect2(20,84,348,309))
	paragraph(left,db.mana_hint(faction),Rect2(21,414,347,97),20)
	var ids: Array = db.all_unit_ids(faction)+["unit."+faction+".worker"]+db.spell_ids(faction)
	var per_page: int = 8 if mobile_ui else 12
	var pages: int = int(ceilf(ids.size()/float(per_page)))
	page=clampi(page,0,pages-1)
	for local in range(per_page):
		var index=page*per_page+local
		if index>=ids.size():break
		var id: String = ids[index];var magic: bool = db.balance.spells.has(id)
		var c=card(right,id,Rect2(20+(local%4)*250,15+(local/4)*(148 if mobile_ui else 122),232,128 if mobile_ui else 113),magic,func():archive_menu(faction,id,page))
		c.selected=selected==id
		c.price=("%d 法"%db.balance.spells[id].mana) if magic else ("%d 金"%db.balance.units[id].gold)
	var detail: String = ""
	if db.balance.units.has(selected):
		var def: Dictionary = db.balance.units[selected]
		detail="生命 %d · 伤害 %d · 射程 %.2f · 速度 %.2f\n%s"%[def.hp,def.damage,def.range,def.speed,db.unit_hint(selected)]
	else:
		var def: Dictionary = db.balance.spells[selected]
		detail="法力 %d · 冷却 %.1f 秒\n%s"%[def.mana,def.cooldown,db.spell_hint(selected)]
	scroll_text(right,detail,Rect2(20,319 if mobile_ui else 389,976,90 if mobile_ui else 70),26 if mobile_ui else 20)
	button(right,"上一页",Rect2(20,452 if mobile_ui else 468,170,128 if mobile_ui else 48),func():archive_menu(faction,selected,maxi(0,page-1))).disabled=page==0
	button(right,"下一页",Rect2(212,452 if mobile_ui else 468,170,128 if mobile_ui else 48),func():archive_menu(faction,selected,mini(pages-1,page+1))).disabled=page==pages-1
	paragraph(right,"%d / %d  ·  6 作战单位 + 工人 + 5 法术"%[page+1,pages],Rect2(407,452 if mobile_ui else 473,574,128 if mobile_ui else 39),25 if mobile_ui else 19)

func show_result():
	if result_shown: return
	result_shown=true; paused=true; cancel_selection(); close_overlay()
	var victory=sim.winner==0
	var draw=sim.winner==-1
	var stars=0
	if victory:
		stars=1
		if sim.bases[0].hp>=sim.bases[0].max_hp*.5: stars+=1
		if sim.time<=float(options.get("star_time",360)): stars+=1
		if mode=="challenge":
			var score: int=sim.ChallengeRules.score(sim)
			stars=sim.ChallengeRules.stars(sim)
			if not profile.has("challenge_scores"):profile["challenge_scores"]={}
			profile.challenge_scores[options.id]=maxi(int(profile.challenge_scores.get(options.id,0)),score)
			profile.challenge_stars[options.id]=maxi(int(profile.challenge_stars.get(options.id,0)),stars)
			save_profile()
		if mode=="campaign":
			campaign_progress.record_victory(profile,str(options.id),stars)
			save_profile()
	if mobile_ui:mobile.show_result();return
	create_overlay("result",Rect2(386,121,828,653))
	image_rect(overlay,UITheme.art("icon-victory" if victory else "icon-defeat"),Rect2(33,30,141,139))
	label(overlay,"纸上得胜" if victory else ("两城同落" if draw else "此局失印"),Rect2(206,41,567,74),48,Color("377b78") if victory else Color("b74532"),true)
	label(overlay,options.title+"  ·  %02d:%02d"%[int(sim.time)/60,int(sim.time)%60],Rect2(207,127,568,40),24)
	if victory: label(overlay,"★".repeat(stars)+"☆".repeat(3-stars),Rect2(47,195,734,66),44,Color("b9964f"))
	else: paragraph(overlay,sim.result_reason+"。保护矿路与任务对象，调整部署再战。",Rect2(46,205,733,82),23)
	var s=sim.stats[0]
	paragraph(overlay,"招募 %d    击倒 %d    损失 %d\n归仓金币 %d    施法 %d    消耗法力 %d\n治疗 %d    召唤 %d    反弹 %d    打断 %d"%[s.recruited,s.killed,s.lost,s.gold_delivered,s.casts,s.mana_spent,s.healed,s.summons,s.reflections,s.interrupts],Rect2(47,310,733,142),24)
	if victory and mode=="campaign": scroll_text(overlay,dialogue_text(options.get("story_after",db.story.ending)),Rect2(47,444,733,59),18)
	var challenge_bonus=""
	if mode=="challenge" and victory:
		challenge_bonus="本局 %d 分 · 最佳 %d 分"%[sim.ChallengeRules.score(sim),int(profile.get("challenge_scores",{}).get(options.id,0))]
	if challenge_bonus!="": label(overlay,challenge_bonus,Rect2(47,449,733,36),22,Color("377b78"))
	if victory and mode=="campaign" and str(options.id)!=campaign_progress.finale:
		button(overlay,"选择下一页",Rect2(47,511,734,64),campaign_menu)
	elif victory and mode=="campaign": button(overlay,"十院留名 · 故事终章",Rect2(47,511,734,64),show_epilogue)
	else:
		var retry=button(overlay,"重新开局",Rect2(47,511,734,64),func():start_battle(options));UITheme.primary(retry)
	if victory:button(overlay,"再战本局",Rect2(47,589,354,46),func():start_battle(options))
	else:button(overlay,"调整部署再战",Rect2(47,589,354,46),func():loadout_menu(options.faction,func():start_battle(options),options.get("available_roster",db.all_unit_ids(options.faction))))
	button(overlay,"主菜单",Rect2(427,589,354,46),main_menu)

func _process(delta):
	if db==null: return
	if mobile_ui:
		mobile_layout_clock+=delta
		if mobile_layout_clock>=.25:mobile_layout_clock=0;refresh_mobile_layout()
	if app_suspended or mobile_blocked:return
	view.menu_characters=not mobile_ui and screen=="menu"
	if not mobile_ui:view.pointer=ui.get_global_mouse_position()
	view.update(minf(delta,.05),paused)
	toast_left=maxf(0,toast_left-delta)
	if screen!="battle" or sim==null: return
	if not paused:
		accumulator+=minf(delta,.15)
		while accumulator>=1.0/60.0:
			sim.tick(1.0/60.0); accumulator-=1.0/60.0
		for e in sim.drain_events():
			if sim.event_visible(0,e):
				view.on_event(e); audio.battle_event(e,view.camera_x)
				if e.kind=="scouted" and int(e.get("observer",-1))==0:toast("侦察发现："+db.name_of(e.id)+" · 根据兵种研究或施法反制",3.0)
				if e.kind=="economy_alarm":toast("纸工遇袭！小地图红圈标出位置，及时施法并补充前排。",4.0)
			if e.kind=="research_done" and e.side==0: toast(db.research_notice(e),3)
		if sim.winner!=-2: show_result()
		footstep_clock-=delta
		if footstep_clock<=0:
			footstep_clock=.24
			for u in sim.units:
				if sim.visible_to(0,u) and u.anim=="walk" and absf(u.x-view.camera_x)<12: audio.play("combat-paper-step",.22);break
		if modal=="":
			var pan=0.0
			if Input.is_physical_key_pressed(KEY_A) or Input.is_physical_key_pressed(KEY_LEFT): pan-=1
			if Input.is_physical_key_pressed(KEY_D) or Input.is_physical_key_pressed(KEY_RIGHT): pan+=1
			if pan!=0: view.target_camera+=pan*delta*14; view.follow_front=false
	hud_clock+=delta
	if hud_clock>=.1: hud_clock=0; update_hud()

func _unhandled_input(event):
	if is_instance_valid(local_duel) and event is InputEventKey and event.pressed and not event.echo and event.keycode==KEY_ESCAPE:
		local_duel.set_paused(not local_duel.halted);get_viewport().set_input_as_handled();return
	if mobile_ui:
		if event is InputEventScreenTouch or event is InputEventScreenDrag:
			touch_input.handle(event);return
		if event is InputEventMouse and event.device==InputEvent.DEVICE_ID_EMULATION:return
		if event is InputEventKey and event.pressed and not event.echo and event.keycode==KEY_ESCAPE:mobile.back();get_viewport().set_input_as_handled();return
		if app_suspended or mobile_blocked:return
		if event is InputEventMouse:
			event=event.duplicate();event.position=view.to_local(event.position)
	if event is InputEventKey and event.pressed and not event.echo:
		if event.keycode==KEY_ESCAPE:
			if screen=="battle":
				if view.selected_spell!="" or view.selected_building!="": cancel_selection()
				elif modal=="pause": paused=false; close_overlay()
				elif modal=="result": main_menu()
				elif modal=="settings": pause_menu()
				elif modal=="brief": main_menu();campaign_menu()
				elif modal!="": close_overlay()
				else: pause_menu()
			elif screen in ["campaign","skirmish"]:new_battle_menu()
			else: main_menu()
			return
		if screen!="battle" or sim==null or sim.winner!=-2: return
		if event.keycode==KEY_P:
			if modal=="pause": paused=false;close_overlay()
			elif not paused: pause_menu()
			return
		if paused or modal!="": return
		if event.keycode in [KEY_1,KEY_2,KEY_3,KEY_4,KEY_5,KEY_6,KEY_7]: recruit_action(sim.production_ids(0)[int(event.keycode)-KEY_1]) if int(event.keycode)-KEY_1<sim.production_ids(0).size() else null
		if event.keycode in [KEY_Q,KEY_W,KEY_E,KEY_R,KEY_T]: select_spell(db.spell_ids(sim.players[0].faction)[[KEY_Q,KEY_W,KEY_E,KEY_R,KEY_T].find(event.keycode)])
		if event.keycode==KEY_F: open_tech()
		if event.keycode==KEY_B: open_build()
		if event.keycode==KEY_HOME: view.target_camera=minf(view.width/view.PX*.5,sim.map.length*.5);view.follow_front=false
		if event.keycode==KEY_SPACE: view.follow_front=true;view.target_camera=sim.front(view.player_side)
	if screen!="battle" or paused or modal!="" or sim==null: return
	if event is InputEventMouseButton:
		if event.button_index==MOUSE_BUTTON_RIGHT and event.pressed: cancel_selection(); return
		if event.button_index==MOUSE_BUTTON_WHEEL_UP and event.pressed: view.target_camera-=3;view.follow_front=false
		if event.button_index==MOUSE_BUTTON_WHEEL_DOWN and event.pressed: view.target_camera+=3;view.follow_front=false
		if event.button_index==MOUSE_BUTTON_LEFT:
			if event.pressed:
				if not view.playfield_rect().has_point(event.position) and not view.minimap_rect().grow(14).has_point(event.position):return
				dragging=true; drag_start=event.position; drag_camera=view.camera_x
				view.target_camera=drag_camera;view.follow_front=false;view.direct_pan=true
				pending_target=view.target_at(event.position) if view.selected_spell!="" else -1
				drag_minimap=view.minimap_rect().grow(32 if mobile_ui else 14).has_point(event.position)
				if drag_minimap: navigate_minimap(event.position.x)
			else:
				if dragging and not drag_minimap and event.position.distance_to(drag_start)<14: battlefield_tap(event.position,pending_target)
				dragging=false; drag_minimap=false; pending_target=-1; view.direct_pan=false
	elif event is InputEventMouseMotion and dragging:
		if drag_minimap: navigate_minimap(event.position.x)
		elif event.position.distance_to(drag_start)>14:
			view.target_camera=drag_camera-(event.position.x-drag_start.x)/view.PX; view.follow_front=false

func _input(event):
	if dragging and (event is InputEventMouseMotion or (event is InputEventMouseButton and event.button_index==MOUSE_BUTTON_LEFT and not event.pressed)):
		_unhandled_input(event);get_viewport().set_input_as_handled();return
	if mobile_ui and (event is InputEventScreenTouch or event is InputEventScreenDrag):
		if event is InputEventScreenTouch and not event.pressed:mobile_touch_points.erase(event.index)
		else:mobile_touch_points[event.index]=event.position
	if mobile_ui and touch_input and touch_input.captured(event):touch_input.handle(event)

func cancel_mobile_touches():
	if touch_input:touch_input.reset()
	var points: Dictionary=mobile_touch_points.duplicate();mobile_touch_points.clear()
	for index in points:
		var event=InputEventScreenTouch.new();event.index=index;event.position=points[index];event.pressed=false;event.canceled=true
		get_viewport().push_input(event,true)

func _exit_tree():
	if mobile:
		mobile.page_restore=Callable();mobile.sheet_restore=Callable();mobile.loadout_return=Callable()
		mobile=null
	touch_input=null

func apply_mobile_quality():
	if not mobile_ui or view==null:return
	var battery: bool=bool(profile.settings.get("battery_saver",false))
	Engine.max_fps=10 if app_suspended else 30 if battery else 60
	view.particle_budget=100 if battery else 240;view.effect_budget=32 if battery else 64;view.float_budget=48 if battery else 80
	db.texture_limit=96 if battery else 128
	while view.particles.size()>view.particle_budget:view.particles.pop_front()
	while view.effects.size()>view.effect_budget:view.effects.pop_front()
	while view.floats.size()>view.float_budget:view.floats.pop_front()

func set_mobile_background(value: bool):
	if app_suspended==value:return
	app_suspended=value;accumulator=0
	if touch_input:cancel_mobile_touches()
	if audio:audio.set_background(value)
	if value:
		if is_instance_valid(local_duel):local_duel.set_paused(true)
		save_profile()
		if sim!=null and screen=="battle" and sim.winner==-2:pause_menu()
	apply_mobile_quality()

func refresh_mobile_layout(rebuild: bool=true):
	if not mobile_ui or mobile==null or mobile_layout_busy:return
	var pixels: Vector2=Vector2(get_window().size)
	if pixels.x<=0 or pixels.y<=0:return
	var args=OS.get_cmdline_user_args()
	var dpi: float=DisplayServer.screen_get_dpi() if OS.has_feature("android") else 160.0
	if args.has("--mobile-density"):dpi=160*float(args[args.find("--mobile-density")+1])
	var safe: Rect2=Rect2(Vector2.ZERO,pixels)
	if OS.has_feature("android"):
		safe=Rect2(DisplayServer.get_display_safe_area())
		safe.position-=Vector2(DisplayServer.window_get_position()-DisplayServer.screen_get_position())
	if args.has("--mobile-insets"):
		var values: PackedStringArray=args[args.find("--mobile-insets")+1].split(",")
		if values.size()==4:safe=Rect2(Vector2(float(values[0]),float(values[1])),pixels-Vector2(float(values[0])+float(values[2]),float(values[1])+float(values[3])))
	var signature: String=str(pixels)+str(dpi)+str(safe)
	if signature==mobile_layout_signature:return
	mobile_layout_signature=signature;mobile_layout_busy=true
	var metrics: Dictionary=MobileLayout.measure(pixels,dpi,safe)
	get_window().content_scale_mode=Window.CONTENT_SCALE_MODE_CANVAS_ITEMS
	get_window().content_scale_aspect=Window.CONTENT_SCALE_ASPECT_EXPAND
	get_window().content_scale_size=Vector2i(metrics.viewport)
	if touch_input:cancel_mobile_touches()
	mobile.configure(metrics)
	var was_blocked: bool=mobile_blocked;mobile_blocked=metrics.portrait or metrics.content.size.x<488 or metrics.content.size.y<240
	if is_instance_valid(local_duel):mobile_blocked=mobile_blocked or metrics.content.size.x<800 or metrics.content.size.y<600;local_duel.set_paused(true)
	if rotation_layer and is_instance_valid(rotation_layer):
		rotation_layer.hide();rotation_layer.queue_free();rotation_layer=null
	ui.visible=not mobile_blocked
	view.visible=not mobile_blocked and not is_instance_valid(local_duel) and not is_instance_valid(lan_session)
	if mobile_blocked:
		rotation_layer=Control.new();rotation_layer.theme=theme;rotation_layer.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT);rotation_layer.mouse_filter=Control.MOUSE_FILTER_STOP;canvas.add_child(rotation_layer)
		var shade=ColorRect.new();shade.color=UITheme.PAPER;shade.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT);rotation_layer.add_child(shade)
		var bounds: Rect2=metrics.content
		paragraph(rotation_layer,"请横屏展开纸上山河\n\n横屏后可继续操作；小窗口请扩大窗口。",Rect2(bounds.position+Vector2(12,bounds.size.y*.3),Vector2(bounds.size.x-24,120)),22)
		button(rotation_layer,"返回主菜单",Rect2(bounds.position+Vector2(12,bounds.size.y*.65),Vector2(bounds.size.x-24,48)),main_menu)
		if not was_blocked and sim and screen=="battle" and sim.winner==-2:pause_menu()
	elif rebuild:
		if is_instance_valid(lan_session):lan_session.relayout(ui.size)
		elif is_instance_valid(local_duel):local_duel.size=ui.size;local_duel.build()
		else:mobile.refresh()
	mobile_layout_busy=false

func navigate_minimap(x: float):
	var box=view.minimap_rect()
	var half: float = minf(view.width/view.PX*.5,sim.map.length*.5)
	view.target_camera=clampf((x-box.position.x)/box.size.x*sim.map.length,half,sim.map.length-half);view.follow_front=false

func battlefield_tap(pos: Vector2, captured_target: int = -1):
	if mobile_ui:
		if not view.mobile_playfield.has_point(pos):return
	elif not view.playfield_rect().has_point(pos):return
	var x: float = view.screen_to_world(pos.x)
	var y: float = (pos.y-view.floor_y())/view.PY
	if view.selected_spell!="":
		var id: String = view.selected_spell
		var target: int = captured_target if captured_target>=0 else view.target_at(pos)
		var a: Dictionary = sim.actor(target)
		if not a.is_empty():
			var body: Vector2=sim.physical_point(a);x=body.x;y=body.y
		if execute("cast",{"id":id,"x":x,"y":y,"target":target}):view.selected_spell="";toast(db.name_of(id)+" 已施放",1.5)
		update_hud()
	elif view.selected_building!="":
		var slot: int = -1
		for i in range(sim.side_sites(0).size()):
			var site: Dictionary = sim.slot_anchor(0,i)
			if view.point_to_screen(site.x,site.y).distance_to(pos)<(maxf(60,24/view.scale.x) if mobile_ui else 46):slot=i
		if execute("build",{"id":view.selected_building,"slot":slot}):toast("已开始施工，保护建筑位。");view.selected_building=""
	else:
		# Adjacent mine and rear facility touch circles may overlap. Resolve the
		# closest visible marker instead of letting array order steal a mine tap.
		var nearest_marker: float=INF
		for i in range(sim.side_sites(0).size()):
			var site: Dictionary=sim.slot_anchor(0,i)
			nearest_marker=minf(nearest_marker,(view.point_to_screen(site.x,site.y)-Vector2(0,18)).distance_to(pos))
		for fork in sim.map.fork_nodes(0):
			var marker: Rect2=view.route_sign_rect(0,fork)
			if marker.has_area():nearest_marker=minf(nearest_marker,marker.get_center().distance_to(pos))
		var nearest_mine: Dictionary={}
		for mine in sim.map.definition.mines:
			if int(mine.owner)!=0:continue
			var distance: float=(view.point_to_screen(mine.x,mine.y)+Vector2(0,-22)).distance_to(pos)
			if distance<nearest_marker and distance<(maxf(60,24/view.scale.x) if mobile_ui else 42):nearest_marker=distance;nearest_mine=mine
		if not nearest_mine.is_empty():
			if execute("mine_priority",{"mine":nearest_mine.id}):toast("运金工下一次出发优先前往此矿；容量 %d。"%nearest_mine.capacity)
			return
		for i in range(sim.side_sites(0).size()):
			var site: Dictionary = sim.slot_anchor(0,i)
			if (view.point_to_screen(site.x,site.y)-Vector2(0,18)).distance_to(pos)<(maxf(55,24/view.scale.x) if mobile_ui else 38):
				var occupied: bool = false
				for b in sim.buildings:
					if b.side==0 and b.slot==i and b.hp>0:occupied=true;break
				if not occupied:open_build(i);return
		for fork in sim.map.fork_nodes(0):
			var node_id: String = fork.node
			var node: Array = sim.map.nodes[node_id].position
			var marker: Rect2=view.route_sign_rect(0,fork)
			if marker.has_area() and marker.grow(10 if mobile_ui else 4).has_point(pos):
				var exits: Array = sim.map.outgoing.get(node_id,[])
				var current: String = sim.map.choices[0].get(node_id,exits[0])
				var edge: String = exits[(exits.find(current)+1)%exits.size()]
				if execute("route",{"node":node_id,"edge":edge}):toast("路标已切换；后续部队在此选路。")
				return
		for mine in sim.map.definition.mines:
			if int(mine.owner)==0 and (view.point_to_screen(mine.x,mine.y)+Vector2(0,-22)).distance_to(pos)<(maxf(60,24/view.scale.x) if mobile_ui else 42):
				if execute("mine_priority",{"mine":mine.id}):toast("运金工下一次出发优先前往此矿；容量 %d。"%mine.capacity)
				return
		view.selected_uid=view.target_at(pos);update_hud()

func _notification(what):
	if is_instance_valid(local_duel):
		if what==NOTIFICATION_WM_GO_BACK_REQUEST:local_duel.set_paused(not local_duel.halted);return
		if what==NOTIFICATION_APPLICATION_PAUSED:local_duel.set_paused(true)
	if mobile_ui and mobile:
		if what==NOTIFICATION_WM_GO_BACK_REQUEST:mobile.back();return
		if what==NOTIFICATION_APPLICATION_PAUSED or (OS.has_feature("android") and what==NOTIFICATION_APPLICATION_FOCUS_OUT):set_mobile_background(true);return
		if what==NOTIFICATION_APPLICATION_RESUMED or (OS.has_feature("android") and what==NOTIFICATION_APPLICATION_FOCUS_IN):set_mobile_background(false);call_deferred("refresh_mobile_layout");return
	if what==NOTIFICATION_APPLICATION_PAUSED and sim!=null and screen=="battle" and sim.winner==-2:
		pause_menu()
	if what==NOTIFICATION_WM_GO_BACK_REQUEST:
		if screen=="battle":
			if modal=="pause": paused=false;close_overlay()
			elif modal=="result": main_menu()
			elif view.selected_spell!="" or view.selected_building!="": cancel_selection()
			elif modal=="settings": pause_menu()
			elif modal=="brief": main_menu();campaign_menu()
			elif modal!="": close_overlay()
			else: pause_menu()
		else: main_menu()

func capture_delayed():
	await get_tree().create_timer(3.0).timeout
	if automation:
		for i in range(60*48):
			sim.tick(1.0/60.0)
			for event in sim.drain_events():
				if sim.event_visible(0,event) and sim.time-float(event.time)<.10 and i>60*47:view.on_event(event)
		view.camera_x=sim.front(view.player_side); view.target_camera=sim.front(view.player_side); view.follow_front=true
		update_hud()
		view.queue_redraw()
	await get_tree().process_frame
	await RenderingServer.frame_post_draw
	var image=get_viewport().get_texture().get_image()
	image.save_png(capture_name)
	print("CAPTURE_SAVED "+capture_name)
	if OS.get_cmdline_user_args().has("--quit-after-capture"): get_tree().quit()

func qa_snapshot(folder: String, name_value: String):
	await get_tree().process_frame
	await get_tree().process_frame
	view.queue_redraw()
	await RenderingServer.frame_post_draw
	var error=get_viewport().get_texture().get_image().save_png(folder+"/"+name_value+".png")
	if error!=OK: capture_errors.append(name_value)

func run_ui_qa(folder: String):
	if ResourceLoader.exists("res://tests/world_ui_qa.gd"):
		load("res://tests/world_ui_qa.gd").run(self,folder)
	else:
		push_error("Development UI QA belongs to the source project; release smoke uses --capture.")
		get_tree().quit(1)

func map_preview(parent: Node,definition: Dictionary,rect: Rect2):
	var preview=preload("res://scripts/map_preview.gd").new()
	preview.definition=definition;preview.font=body_font;preview.position=rect.position;preview.size=rect.size
	preview.mouse_filter=Control.MOUSE_FILTER_IGNORE;parent.add_child(preview)

func dialogue_text(value) -> String:
	if typeof(value)!=TYPE_ARRAY:return str(value)
	var lines: Array = []
	for line in value:lines.append(str(line.get("speaker",""))+"："+str(line.get("text","")))
	return "\n".join(lines)

func show_epilogue():
	if mobile_ui:mobile.show_epilogue();return
	create_overlay("epilogue",Rect2(245,82,1110,734))
	label(overlay,"十院留名",Rect2(35,25,1040,68),46,Color("b74532"),true)
	paragraph(overlay,db.story.ending,Rect2(35,113,1040,102),25)
	var scroll=ScrollContainer.new();scroll.position=Vector2(35,240);scroll.size=Vector2(1040,380);overlay.add_child(scroll)
	var text=Label.new();text.name="ScrollCopy";text.custom_minimum_size=Vector2(990,0);text.size_flags_horizontal=Control.SIZE_EXPAND_FILL;text.autowrap_mode=TextServer.AUTOWRAP_WORD_SMART;text.add_theme_font_size_override("font_size",22)
	var lines: Array = []
	for f in db.FACTIONS:lines.append(db.factions[f].hero+" · "+db.FACTION_NAMES[f]+"\n"+db.factions[f].ending)
	text.text="\n\n".join(lines);scroll.add_child(text)
	button(overlay,"继续阅读兵书",Rect2(35,645,494,64),func():archive_menu("bai",db.all_unit_ids("bai")[0]))
	button(overlay,"返回山河",Rect2(552,645,523,64),main_menu)

func open_queue():
	if mobile_ui:mobile.open_queue();return
	if paused or sim==null:return
	create_overlay("queue",Rect2(220,67,1160,766) if mobile_ui else Rect2(380,195,840,535))
	label(overlay,"招募队列 · 点选取消并退款",Rect2(26,20,1108 if mobile_ui else 779,55),30,Color("343332"),true)
	label(overlay,"实时出仓倒计时 · 出仓后仍需行军，战斗继续进行",Rect2(26,71,779,20),16)
	battle_sheet=BattleSheets.new()
	var empty=label(overlay,"当前没有正在生产的单位。",Rect2(26,190,778,60),25)
	battle_sheet.bind_queue(func(i: int,id: String,revision: int):
		return button(overlay,"",Rect2(26+(i%2)*402,92+(i/2)*112,382,98),func():
			execute("cancel_queue",{"index":i,"id":id,"queue_revision":revision})
			if battle_sheet!=null:battle_sheet.refresh(sim,0,paused)),empty)
	battle_sheet.refresh(sim,0,paused)
	button(overlay,"返回战场",Rect2(26,588,1108,128) if mobile_ui else Rect2(26,443,788,66),close_overlay)

func loadout_menu(faction: String, return_action: Callable, available: Array = [], page: int = 0, chosen: Array = []):
	if mobile_ui:mobile.loadout_menu(faction,return_action,available,page,chosen);return
	if available.is_empty():available=db.all_unit_ids(faction)
	if chosen.is_empty():
		for id in db.deployments.get(faction,db.factions[faction].default_roster):
			if available.has(id):chosen.append(id)
		chosen=db.normalize_roster(faction,chosen,available)
	create_overlay("loadout",Rect2(86,34 if mobile_ui else 61,1428,832 if mobile_ui else 778))
	label(overlay,"部署 · "+db.FACTION_NAMES[faction],Rect2(25,16,1040,53),34,db.FACTION_COLORS[faction],true)
	paragraph(overlay,"选择2–4个开局偏好兵种。常规对战仍可在局内研究全院六兵，加一个运金纸工；高阶兵需要科技投资。",Rect2(25,82,1180 if mobile_ui else 1378,64),24 if mobile_ui else 21)
	var ids: Array = db.all_unit_ids(faction)
	var per_page: int = 10 if mobile_ui else 20
	var pages: int = int(ceilf(ids.size()/float(per_page)))
	page=clampi(page,0,pages-1)
	for local in range(per_page):
		var index=page*per_page+local
		if index>=ids.size():break
		var id: String = ids[index]
		var c=card(overlay,id,Rect2(25+(local%5)*279,161+(local/5)*(148 if mobile_ui else 126),261,128 if mobile_ui else 113),false,func():
			var next: Array = chosen.duplicate()
			if next.has(id):next.erase(id)
			elif next.size()<4:next.append(id)
			else:audio.play("ui-invalid");return
			loadout_menu(faction,return_action,available,page,next))
		c.selected=chosen.has(id);c.price="%d 金  ·  %s"%[db.balance.units[id].gold,"已选" if c.selected else "候选"]
		c.disabled=not available.has(id);c.locked=c.disabled;c.tooltip_text=db.unit_hint(id)
	var selected_names: Array = []
	for id in chosen:selected_names.append(db.name_of(id))
	scroll_text(overlay,"已选 %d / 4：%s"%[chosen.size(),"、".join(selected_names)],Rect2(25,465 if mobile_ui else 670,1378 if mobile_ui else 965,120 if mobile_ui else 80),26 if mobile_ui else 20)
	if mobile_ui:
		button(overlay,"上一页",Rect2(25,620,275,128),func():loadout_menu(faction,return_action,available,maxi(0,page-1),chosen)).disabled=page==0
		button(overlay,"下一页",Rect2(323,620,275,128),func():loadout_menu(faction,return_action,available,mini(pages-1,page+1),chosen)).disabled=page==pages-1
		label(overlay,"%d / %d"%[page+1,pages],Rect2(621,650,482,60),29)
	else:button(overlay,"上一页" if page==1 else "下一页",Rect2(1000,680,185,66),func():loadout_menu(faction,return_action,available,1-page,chosen))
	var confirm=button(overlay,"保存部署",Rect2(1127,620,275,128) if mobile_ui else Rect2(1202,680,200,66),func():
		db.deployments[faction]=chosen.duplicate();profile.loadouts[faction]=chosen.duplicate();save_profile();return_action.call())
	confirm.disabled=chosen.size()<2 or chosen.size()>4
	button(overlay,"返回",Rect2(1255,16,146,128) if mobile_ui else Rect2(1255,22,146,56),return_action)

func desktop_help():
	clear_ui();screen="help";view.menu=true
	menu_header("操作帮助","军团自动行军，玩家决定招募、研究、设施与施法。")
	paragraph(ui,"鼠标左右拖动战场，或拖动小地图导航。\n1–7 招募，Q W E R T 施法，F 研究，B 建造，A D 移动，Home 纸城，Space 交锋，P 暂停。\n金币由工人实际归仓后入账。点矿点、路标与塔灯位作出地图决策。",Rect2(250,230,1100,370),28)
	button(ui,"返回设置",Rect2(500,650,600,68),func():settings_menu(false))
