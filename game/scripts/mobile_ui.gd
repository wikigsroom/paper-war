extends RefCounted
const Layout=preload("res://scripts/mobile_layout.gd")
const UI=preload("res://scripts/ui_theme.gd")
const MiniMap=preload("res://scripts/theatre_minimap.gd")
const RecruitmentReadiness=preload("res://scripts/recruitment_readiness.gd")
var app
var metrics: Dictionary={}
var playfield: Rect2
var page_restore: Callable
var sheet_restore: Callable
var loadout_return: Callable
var settings_in_battle=false
var orders_button: Button
var recruit_scroll: ScrollContainer
var queue_badge: Label
var compact_header: bool=false
var row_height: float=64
var skirmish_values={"ally":0,"enemy":1,"map":0,"difficulty":1,"style":2,"full":false}
var text_scale=1.0

func _init(owner):app=owner

func configure(value: Dictionary):
	metrics=value
	app.ui.set_anchors_and_offsets_preset(Control.PRESET_TOP_LEFT)
	app.ui.position=metrics.content.position;app.ui.size=metrics.content.size
	app.view.scale=Vector2.ONE*clampf(metrics.viewport.y/900.0,.28,.85)
	app.view.width=metrics.viewport.x/app.view.scale.x;app.view.height=metrics.viewport.y/app.view.scale.y
	row_height=48.0
	playfield=Rect2(metrics.content.position,metrics.content.size)
	app.view.mobile_playfield=Rect2(playfield.position/app.view.scale,playfield.size/app.view.scale)

func refresh():
	var restore=sheet_restore
	if page_restore.is_valid():page_restore.call()
	if restore.is_valid():restore.call()

func text(parent: Node,copy: String,font_size: int=16,color: Color=UI.INK) -> Label:
	var l=Label.new();l.text=copy;l.autowrap_mode=TextServer.AUTOWRAP_WORD_SMART;l.size_flags_horizontal=Control.SIZE_EXPAND_FILL
	l.add_theme_font_size_override("font_size",int(font_size*text_scale));l.add_theme_color_override("font_color",color)
	l.mouse_filter=Control.MOUSE_FILTER_IGNORE;parent.add_child(l);return l

func action(parent: Node,caption: String,callback: Callable,primary: bool=false) -> Button:
	var b=Button.new();b.text=caption;b.custom_minimum_size=Vector2(48,48);b.size_flags_horizontal=Control.SIZE_EXPAND_FILL
	b.clip_text=true;b.text_overrun_behavior=TextServer.OVERRUN_TRIM_ELLIPSIS;b.accessibility_name=caption.replace("\n"," · ");b.tooltip_text=b.accessibility_name
	b.add_theme_font_size_override("font_size",int(18*text_scale));b.mouse_filter=Control.MOUSE_FILTER_PASS
	UI.decorate(b,caption)
	if primary:UI.primary(b)
	b.pressed.connect(func():app.audio.play("ui-click");callback.call());parent.add_child(b);return b

func column(parent: Node) -> VBoxContainer:
	var c=VBoxContainer.new();c.mouse_filter=Control.MOUSE_FILTER_PASS;c.size_flags_horizontal=Control.SIZE_EXPAND_FILL;c.add_theme_constant_override("separation",8);parent.add_child(c);return c

func row(parent: Node) -> HBoxContainer:
	var c=HBoxContainer.new();c.mouse_filter=Control.MOUSE_FILTER_PASS;c.size_flags_horizontal=Control.SIZE_EXPAND_FILL;c.add_theme_constant_override("separation",8);parent.add_child(c);return c

func grid(parent: Node,count: int) -> GridContainer:
	var c=GridContainer.new();c.mouse_filter=Control.MOUSE_FILTER_PASS;c.columns=count;c.size_flags_horizontal=Control.SIZE_EXPAND_FILL;c.add_theme_constant_override("h_separation",8);c.add_theme_constant_override("v_separation",8);parent.add_child(c);return c

func scroll(parent: Control,rect: Rect2) -> VBoxContainer:
	var sc=preload("res://scripts/mobile_scroll.gd").new();sc.name="MobileScroll";sc.position=rect.position;sc.size=rect.size
	sc.host=app;sc.sheet_scope=parent==app.overlay;sc.follow_focus=true
	sc.horizontal_scroll_mode=ScrollContainer.SCROLL_MODE_DISABLED;sc.vertical_scroll_mode=ScrollContainer.SCROLL_MODE_SHOW_NEVER
	sc.scroll_deadzone=8;parent.add_child(sc)
	return column(sc)

func block(parent: Node) -> VBoxContainer:
	var p=PanelContainer.new();p.mouse_filter=Control.MOUSE_FILTER_PASS;p.size_flags_horizontal=Control.SIZE_EXPAND_FILL;parent.add_child(p)
	return column(p)

func artwork(parent: Node,texture: Texture2D,height: float=100) -> TextureRect:
	var picture=TextureRect.new();picture.texture=texture;picture.expand_mode=TextureRect.EXPAND_IGNORE_SIZE;picture.stretch_mode=TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	picture.custom_minimum_size=Vector2(48,height);picture.size_flags_horizontal=Control.SIZE_EXPAND_FILL;picture.mouse_filter=Control.MOUSE_FILTER_IGNORE;parent.add_child(picture)
	return picture

func preview(parent: Node,definition: Dictionary,height: float=100):
	var p=preload("res://scripts/map_preview.gd").new();p.definition=definition;p.font=app.body_font
	p.custom_minimum_size=Vector2(48,height);p.size_flags_horizontal=Control.SIZE_EXPAND_FILL;p.mouse_filter=Control.MOUSE_FILTER_IGNORE;parent.add_child(p)

func begin(name_value: String,title: String,restore: Callable) -> VBoxContainer:
	app.clear_ui();app.screen=name_value;app.view.menu=true;page_restore=restore;sheet_restore=Callable()
	app.ui.position=metrics.content.position;app.ui.size=metrics.content.size
	var width: float=app.ui.size.x;var height: float=app.ui.size.y
	var cap: float=minf(width,960);var x: float=(width-cap)*.5
	app.panel(app.ui,Rect2(x,0,cap,height)).mouse_filter=Control.MOUSE_FILTER_IGNORE
	app.label(app.ui,title,Rect2(x+12,7,cap-124,44),24,UI.INK,true)
	var back=app.button(app.ui,"返回",Rect2(x+cap-100,4,88,48),app.new_battle_menu if name_value in ["campaign","skirmish"] else app.main_menu);back.add_theme_font_size_override("font_size",18)
	return scroll(app.ui,Rect2(x+12,64,cap-24,maxf(48,height-72)))

func sheet(name_value: String,title: String,restore: Callable,buttons: Array) -> VBoxContainer:
	var area: Rect2=Rect2(metrics.content.position-app.ui.position,metrics.content.size)
	var width: float=minf(area.size.x,960);var height: float=area.size.y
	app.create_overlay(name_value,Rect2(area.position+Vector2((area.size.x-width)*.5,0),Vector2(width,height)));sheet_restore=restore
	app.label(app.overlay,title,Rect2(12,6,width-112,44),22,UI.INK,true)
	app.button(app.overlay,"返回",Rect2(width-92,4,80,48),back).add_theme_font_size_override("font_size",18)
	var bottom: float=64 if not buttons.is_empty() else 8
	var body=scroll(app.overlay,Rect2(12,64,width-24,maxf(48,height-64-bottom)))
	if not buttons.is_empty():
		var footer=HBoxContainer.new();footer.position=Vector2(12,height-56);footer.size=Vector2(width-24,48);footer.add_theme_constant_override("separation",8);app.overlay.add_child(footer)
		for entry in buttons:action(footer,entry[0],entry[1],bool(entry[2]) if entry.size()>2 else false)
	return body

func main_menu():
	app.paused=false;app.result_shown=false;app.sim=null;app.view.sim=null;app.view.selected_spell="";app.view.selected_building="";app.view.direct_pan=false
	var body=begin("menu","纸上兵戈 · 一纸山河",main_menu)
	for b in app.ui.get_children():
		if b is Button:b.hide()
		elif b is Label:b.position.y=2;b.size.y=28;b.add_theme_font_size_override("font_size",20)
		elif b is ScrollContainer:b.position.y=32;b.size.y=app.ui.size.y-32
	body.size_flags_vertical=Control.SIZE_SHRINK_BEGIN
	var next: Dictionary=app.campaign_progress.recommended(app.profile)
	for entry in [["继续战役",func():app.show_brief(next,"campaign")],["新战役",app.new_battle_menu],["成就挑战",app.challenge_menu],["兵书",func():app.archive_menu("yin","unit.yin.axe")],["设置",func():app.settings_menu(false)]]:
		var b=action(body,entry[0],entry[1],entry[0]=="继续战役")
		b.custom_minimum_size.y=clampf(floorf((app.ui.size.y-68)/5),48,72)

func new_battle_menu():
	var body=begin("new-battle","新战役",new_battle_menu)
	action(body,"故事战役",app.campaign_menu,true)
	text(body,"按剧情展开十院二百折，可重访已完成纸页。",16,UI.MUTED)
	action(body,"遭遇战",app.skirmish_menu)
	text(body,"自由选择双方阵营、地图与军阵。",16,UI.MUTED)

func for_connection(button: Button,callback: Callable):
	for connection in button.pressed.get_connections():button.pressed.disconnect(connection.callable)
	button.pressed.connect(callback)

func theatre_menu():
	var body=begin("theatre","六张纸场 · 地图试演",theatre_menu)
	text(body,"六类空间取舍：归仓、前沿投资、援军距离、分岔、截矿与护送。",16,UI.MUTED)
	var g=grid(body,Layout.columns(app.ui.size.x-24,260,2))
	for index in [0,6,10,3,11,5]:
		var level: Dictionary=app.db.campaign[index];var definition: Dictionary=app.db.maps[level.map]
		var card=block(g);text(card,definition.name,20,app.db.FACTION_COLORS[level.faction]);preview(card,definition,80)
		text(card,definition.design_card.question,16);action(card,"展开纸场",func():app.show_brief(level,"skirmish"))

func campaign_menu(chapter_index: int=-1,_page: int=0):
	if chapter_index<0:chapter_index=clampi(int(app.profile.unlocked)/20,0,9)
	app.campaign_chapter=chapter_index
	var body=begin("campaign","战役 · 十院二百折",func():campaign_menu(chapter_index))
	var names: Array=[]
	for ch in app.db.story.chapters:names.append("第 %02d 章 · %s"%[int(ch.index)+1,ch.title])
	action(body,names[chapter_index]+" · 选择章节",func():choices("故事章节",names,chapter_index,func(i):campaign_menu(i),func():campaign_menu(chapter_index)))
	text(body,app.campaign_route_summary(chapter_index),16,UI.MUTED)
	text(body,"上下滑动浏览本章二十折 · 卡片显示前置与完成状态",14,UI.MUTED)
	var g=grid(body,Layout.columns(app.ui.size.x-24,210,3))
	for local in range(20):
		var index: int=chapter_index*20+local;var level: Dictionary=app.db.campaign[index]
		var stars: int=clampi(int(app.profile.stars.get(level.id,0)),0,3)
		var b=action(g,"%03d · %s\n%s\n%s"%[index+1,str(level.title).get_slice("·",1),"★".repeat(stars)+"☆".repeat(3-stars),app.campaign_progress.status(app.profile,level.id)],func():app.show_brief(level,"campaign"))
		b.custom_minimum_size.y=96;b.add_theme_font_size_override("font_size",16);b.disabled=not app.campaign_progress.available(app.profile,level.id)
		b.set_meta("campaign_id",level.id)

func choices(title: String,items: Array,selected: int,choose: Callable,restore: Callable):
	var body=sheet("choice",title,func():choices(title,items,selected,choose,restore),[])
	loadout_return=restore
	text(body,"点选条目 · 长列表可上下滑动",14,UI.MUTED)
	for i in range(items.size()):action(body,("已选 · " if i==selected else "")+str(items[i]),func():app.close_overlay();choose.call(i),i==selected)

func show_brief(level: Dictionary,battle_mode: String):
	app.mode=battle_mode;app.options=level.duplicate(true)
	var body=sheet("brief",level.title,func():show_brief(level,battle_mode),[["调整部署",func():app.loadout_menu(level.faction,func():show_brief(level,battle_mode),level.get("available_roster",app.db.all_unit_ids(level.faction)))],["展开战场",func():app.start_battle(app.options),true]])
	var f: String=level.faction;var definition: Dictionary=app.db.map_definition(level.map)
	text(body,app.dialogue_text(level.get("story_before",level.tip)),17)
	if battle_mode=="campaign":text(body,app.campaign_progress.status(app.profile,level.id)+" · "+app.campaign_progress.requirement_hint(level.id),14,UI.MUTED)
	text(body,"地图 · "+definition.name,20);preview(body,definition,120)
	text(body,app.mission_brief(level,definition))
	text(body,"%s 对 %s · 起始金币 %d : %d\n%s"%[app.db.FACTION_NAMES[f],app.db.FACTION_NAMES[level.enemy],level.starting_gold,level.enemy_starting_gold,app.db.mana_hint(f)],16,UI.MUTED)

func skirmish_menu():
	var body=begin("skirmish","遭遇战 · 自选纸局",skirmish_menu)
	var names: Array=[]
	for f in app.db.FACTIONS:names.append(app.db.FACTION_NAMES[f])
	var ids: Array=app.db.maps.keys();var maps: Array=[]
	for id in ids:maps.append(app.db.maps[id].name)
	var g=grid(body,Layout.columns(app.ui.size.x-24,230,2))
	for entry in [["ally","我方阵营",names],["enemy","敌方阵营",names],["map","纸面山河",maps],["difficulty","AI 决策",["入门 · 慢决策","标准 · 连续调配","强敌 · 快速反制"]],["style","AI 战术",["前期压制","经济攀升","空间反制"]]]:
		var key: String=entry[0];var caption: String=entry[1];var values: Array=entry[2]
		action(g,caption+" · "+str(values[skirmish_values[key]]),func():choices(caption,values,skirmish_values[key],func(i):skirmish_values[key]=i;skirmish_menu(),skirmish_menu))
	var full=CheckButton.new();full.mouse_filter=Control.MOUSE_FILTER_PASS;full.text="完整科技开局";full.custom_minimum_size=Vector2(48,48);full.button_pressed=skirmish_values.full;g.add_child(full)
	full.toggled.connect(func(value):skirmish_values.full=value)
	var definition: Dictionary=app.db.maps[ids[skirmish_values.map]]
	preview(body,definition,100);text(body,definition.decision+"\n"+app.db.mana_hint(app.db.FACTIONS[skirmish_values.ally]))
	var buttons=row(body)
	action(buttons,"部署编组",func():app.loadout_menu(app.db.FACTIONS[skirmish_values.ally],app.close_overlay))
	var duel=action(body,"本机双人分屏 · 大屏对弈",func():app.start_local_duel({"title":"双人对弈","faction":app.db.FACTIONS[skirmish_values.ally],"enemy":app.db.FACTIONS[skirmish_values.enemy],"map":ids[skirmish_values.map],"starting_gold":300,"enemy_starting_gold":300,"full_tech":skirmish_values.full,"win":"destroy_base"}))
	duel.disabled=app.ui.size.x<800 or app.ui.size.y<600
	action(body,"局域网对弈",func():lan_menu({"faction":app.db.FACTIONS[skirmish_values.ally],"enemy":app.db.FACTIONS[skirmish_values.enemy],"map":ids[skirmish_values.map],"starting_gold":300,"enemy_starting_gold":300,"full_tech":skirmish_values.full,"win":"destroy_base"}))
	action(buttons,"展开战场",func():
		app.mode="skirmish";app.start_battle({"title":"遭遇战","faction":app.db.FACTIONS[skirmish_values.ally],"enemy":app.db.FACTIONS[skirmish_values.enemy],"map":ids[skirmish_values.map],"difficulty":skirmish_values.difficulty,"ai_style":["rush","economy","counter"][skirmish_values.style],"starting_gold":300,"enemy_starting_gold":300,"full_tech":skirmish_values.full,"win":"destroy_base"}),true)

func lan_menu(settings: Dictionary):
	var body=begin("lan-lobby","局域网对弈",func():lan_menu(settings))
	text(body,"房主选择地图与双方阵营；加入者控制东侧阵营。输入房主在同一网络中的地址。")
	var address=LineEdit.new();address.placeholder_text="房主地址，例如192.168.1.20";address.custom_minimum_size=Vector2(48,48);body.add_child(address)
	action(body,"创建房间",func():app.start_lan(settings,""))
	action(body,"加入房间",func():
		if address.text.strip_edges().is_empty():app.toast("请输入房主地址");return
		app.start_lan(settings,address.text.strip_edges()))

func challenge_menu():
	var body=begin("challenges","六道战术挑战",challenge_menu)
	var g=grid(body,Layout.columns(app.ui.size.x-24,240,2))
	for c in app.db.read_json("res://data/campaign.json").challenges:
		var p=block(g);text(p,c.title,20,app.db.FACTION_COLORS[c.faction]);text(p,c.tip)
		var stars: int=clampi(int(app.profile.challenge_stars.get(c.id,0)),0,3)
		text(p,"★".repeat(stars)+"☆".repeat(3-stars),16,UI.GOLD);action(p,"展开纸题",func():app.show_brief(c,"challenge"))

func archive_menu(faction: String,selected: String,page: int=0):
	var body=begin("archive","兵书 · 十院军阵",func():archive_menu(faction,selected,page))
	var names: Array=[]
	for f in app.db.FACTIONS:names.append(app.db.FACTION_NAMES[f])
	var actions=row(body)
	action(actions,app.db.FACTION_NAMES[faction]+" · 选择阵营",func():choices("阵营",names,app.db.FACTIONS.find(faction),func(i):archive_menu(app.db.FACTIONS[i],app.db.all_unit_ids(app.db.FACTIONS[i])[0]),func():archive_menu(faction,selected,page)))
	action(actions,"部署编组",func():app.loadout_menu(faction,func():archive_menu(faction,selected,page)))
	text(body,app.db.name_of(selected),22,app.db.FACTION_COLORS[faction])
	if app.db.balance.units.has(selected):
		var def: Dictionary=app.db.balance.units[selected]
		text(body,"生命 %d · 伤害 %d · 射程 %.2f · 速度 %.2f\n%s"%[def.hp,def.damage,def.range,def.speed,app.db.unit_hint(selected)])
	else:
		var def: Dictionary=app.db.balance.spells[selected]
		text(body,"法力 %d · 冷却 %.1f 秒\n%s"%[def.mana,def.cooldown,app.db.spell_hint(selected)])
	var ids: Array=app.db.all_unit_ids(faction)+["unit."+faction+".worker"]+app.db.spell_ids(faction)
	var per_page=8;var pages: int=int(ceilf(ids.size()/float(per_page)));page=clampi(page,0,pages-1)
	var g=grid(body,Layout.columns(app.ui.size.x-24,170,4))
	for index in range(page*per_page,mini(ids.size(),(page+1)*per_page)):
		var id: String=ids[index];var magic: bool=app.db.balance.spells.has(id)
		var c=app.card(g,id,Rect2(0,0,0,0),magic,func():archive_menu(faction,id,page));c.touch_layout=true;c.battle_layout=false
		c.mouse_filter=Control.MOUSE_FILTER_PASS
		c.custom_minimum_size=Vector2(160,88);c.size_flags_horizontal=Control.SIZE_EXPAND_FILL;c.selected=id==selected;c.price="%d 法"%app.db.balance.spells[id].mana if magic else "%d 金"%app.db.balance.units[id].gold
	var footer=row(body)
	action(footer,"上一页",func():archive_menu(faction,selected,page-1)).disabled=page==0
	action(footer,"%d / %d · 下一页"%[page+1,pages],func():archive_menu(faction,selected,page+1)).disabled=page==pages-1

func loadout_menu(faction: String,return_action: Callable,available: Array=[],page: int=0,chosen: Array=[]):
	if available.is_empty():available=app.db.all_unit_ids(faction)
	if chosen.is_empty():chosen=app.db.normalize_roster(faction,app.db.deployments.get(faction,app.db.factions[faction].default_roster),available)
	loadout_return=return_action
	var save=func():app.db.deployments[faction]=chosen.duplicate();app.profile.loadouts[faction]=chosen.duplicate();app.save_profile();return_action.call()
	var body=sheet("loadout","部署 · "+app.db.FACTION_NAMES[faction],func():loadout_menu(faction,return_action,available,page,chosen),[["保存部署",save,true]])
	for b in app.overlay.find_children("*","Button",true,false):
		if b.text=="保存部署":b.disabled=chosen.size()<2 or chosen.size()>4
	text(body,"选择 2–4 个互补兵种，另带运金纸工。点击已选兵种可移除。",16,UI.MUTED)
	var selected_names: Array=[]
	for id in chosen:selected_names.append(app.db.name_of(id))
	text(body,"已选 %d / 4：%s"%[chosen.size(),"、".join(selected_names)],17)
	var ids: Array=app.db.all_unit_ids(faction);var pages: int=int(ceilf(ids.size()/8.0));page=clampi(page,0,pages-1)
	var g=grid(body,Layout.columns(app.ui.size.x-24,170,4))
	for index in range(page*8,mini(ids.size(),(page+1)*8)):
		var id: String=ids[index]
		var c=app.card(g,id,Rect2(0,0,0,0),false,func():
			var next: Array=chosen.duplicate()
			if next.has(id):next.erase(id)
			elif next.size()<4:next.append(id)
			else:app.toast("最多携带四个作战兵种");return
			loadout_menu(faction,return_action,available,page,next))
		c.touch_layout=true;c.battle_layout=false;c.custom_minimum_size=Vector2(160,88);c.size_flags_horizontal=Control.SIZE_EXPAND_FILL;c.selected=chosen.has(id)
		c.mouse_filter=Control.MOUSE_FILTER_PASS
		c.price="%d 金 · %s"%[app.db.balance.units[id].gold,"已选" if c.selected else "候选"];c.disabled=not available.has(id);c.locked=c.disabled
	var paging=row(body)
	action(paging,"上一页",func():loadout_menu(faction,return_action,available,page-1,chosen)).disabled=page==0
	action(paging,"%d / %d · 下一页"%[page+1,pages],func():loadout_menu(faction,return_action,available,page+1,chosen)).disabled=page==pages-1

func build_hud():
	app.clear_ui();page_restore=build_hud;sheet_restore=Callable();app.screen="battle";app.view.menu=false;app.queue_signature=""
	# Battle uses the safe area's full height; page gutters belong to menus.
	app.ui.position=Vector2(metrics.content.position.x,metrics.safe.position.y)
	app.ui.size=Vector2(metrics.content.size.x,metrics.safe.size.y)
	var w: float=app.ui.size.x;var h: float=app.ui.size.y
	compact_header=h<320
	playfield=Rect2(app.ui.position+Vector2(0,0 if compact_header else 24),Vector2(w,h-52-(0 if compact_header else 24)))
	fit_stage()
	var top=app.panel(app.ui,Rect2(0,0,minf(288,w) if compact_header else w,24));top.name="HudTopRail";top.mouse_filter=Control.MOUSE_FILTER_IGNORE
	var bottom=app.panel(app.ui,Rect2(0,h-52,w,52));bottom.name="HudBottomRail";bottom.mouse_filter=Control.MOUSE_FILTER_IGNORE
	app.resource_label=app.label(app.ui,"",Rect2(4,0,78,24),16,UI.GOLD)
	app.mana_label=app.label(app.ui,"",Rect2(86,0,120,24),15,UI.JADE)
	var notice_width: float=minf(76,w-212) if compact_header else w-212-160
	app.clock_label=app.label(app.ui,"",Rect2(212,0,notice_width,24),14,UI.INK)
	app.base_label=app.label(app.ui,"",Rect2(0,0,0,0),13,UI.MUTED);app.base_label.hide()
	app.army_label=app.label(app.ui,"",Rect2(0,0,0,0),13,UI.MUTED);app.army_label.hide()
	if not compact_header:
		var pause=app.button(app.ui,"暂停",Rect2(w-48,0,48,48),app.pause_menu);pause.name="HudPause";pause.add_theme_font_size_override("font_size",16)
	app.queue_box=HBoxContainer.new();app.queue_box.visible=false;app.ui.add_child(app.queue_box)
	var units: Array=app.sim.players[0].roster.duplicate();units.append("unit."+app.sim.players[0].faction+".worker")
	# Starter preferences and the worker are first; the full roster stays a swipe away.
	var preferred: Array=app.sim.players[0].get("quick_roster",app.options.player_roster).duplicate()
	preferred=preferred.filter(func(id):return units.has(id))
	preferred.append(units.back())
	for id in units:
		if not preferred.has(id):preferred.append(id)
	units=preferred
	var spells: Array=app.db.spell_ids(app.sim.players[0].faction)
	var card_width: float=56 if w>=640 else 48
	var spell_bank: float=spells.size()*card_width+(spells.size()-1)*8
	var unit_bank: float=w-spell_bank-48-16
	recruit_scroll=preload("res://scripts/mobile_scroll.gd").new();recruit_scroll.name="RecruitScroll";recruit_scroll.host=app;recruit_scroll.horizontal=true
	recruit_scroll.position=Vector2(0,h-48);recruit_scroll.size=Vector2(unit_bank,48);recruit_scroll.clip_contents=true
	recruit_scroll.horizontal_scroll_mode=ScrollContainer.SCROLL_MODE_SHOW_NEVER;recruit_scroll.vertical_scroll_mode=ScrollContainer.SCROLL_MODE_DISABLED
	app.ui.add_child(recruit_scroll)
	var recruits=HBoxContainer.new();recruits.name="RecruitStrip";recruits.add_theme_constant_override("separation",8);recruit_scroll.add_child(recruits)
	for i in range(units.size()):
		var id: String=units[i]
		var c=app.card(recruits,id,Rect2(0,0,card_width,48),false,func():app.recruit_action(id))
		c.custom_minimum_size=Vector2(card_width,48);c.touch_layout=true;c.battle_layout=true;c.touch_dense=true;c.slim_battle=true;c.focus_mode=Control.FOCUS_NONE;app.unit_cards[id]=c
	for i in range(spells.size()):
		var id: String=spells[i]
		var c=app.card(app.ui,id,Rect2(unit_bank+8+i*(card_width+8),h-48,card_width,48),true,func():app.select_spell(id))
		c.touch_layout=true;c.battle_layout=true;c.touch_dense=true;c.slim_battle=true;app.spell_cards[id]=c
	orders_button=app.button(app.ui,"军令",Rect2(w-48,h-48,48,48),func():app.cancel_selection() if app.view.selected_spell!="" or app.view.selected_building!="" else orders_menu());orders_button.name="HudOrders";orders_button.add_theme_font_size_override("font_size",14)
	queue_badge=app.label(orders_button,"",Rect2(31,0,16,16),10,UI.JADE)
	var map_rect: Rect2=Rect2(w-152,0,96,48) if not compact_header else Rect2()
	app.view.mobile_minimap=Rect2((app.ui.position+map_rect.position)/app.view.scale,map_rect.size/app.view.scale)
	var map_region=Control.new();map_region.name="HudMiniMap";map_region.position=map_rect.position;map_region.size=map_rect.size;map_region.mouse_filter=Control.MOUSE_FILTER_IGNORE;app.ui.add_child(map_region)
	var navigation=MiniMap.new();navigation.view=app.view;navigation.position=-app.ui.position;navigation.scale=app.view.scale;navigation.size=metrics.viewport/app.view.scale;navigation.mouse_filter=Control.MOUSE_FILTER_IGNORE;app.ui.add_child(navigation)
	app.hint_back=app.panel(app.ui,Rect2(212,0,notice_width,24));app.hint_back.mouse_filter=Control.MOUSE_FILTER_IGNORE
	app.hint_label=app.label(app.ui,"",Rect2(212,0,notice_width,24),12,UI.INK)
	app.status_back=app.panel(app.ui,Rect2(212,0,notice_width,24));app.status_back.mouse_filter=Control.MOUSE_FILTER_IGNORE
	app.status_label=app.label(app.ui,"",Rect2(212,0,notice_width,24),12,UI.INK)
	app.update_hud()

func fit_stage():
	var bounds: Rect2=app.sim.map.bounds
	var tallest: float=310.0 # Paper bases, their health bar and name also fit.
	for p in app.sim.players:
		for id in p.roster:tallest=maxf(tallest,float(app.db.assets[id].world_height)*app.view.PX*app.view.PUPPET_SCALE)
	var desired: float=clampf(metrics.viewport.y/900.0,.28,.85)
	var earth_depth: float=maxf(52,playfield.size.y*.17)
	var fit: float=maxf(1,playfield.size.y-earth_depth-36)/(tallest+bounds.size.y*app.view.PY)
	fit=minf(fit,maxf(1,playfield.size.y-earth_depth-60)/(176+bounds.size.y*app.view.PY))
	app.view.scale=Vector2.ONE*minf(desired,fit)
	app.view.width=metrics.viewport.x/app.view.scale.x;app.view.height=metrics.viewport.y/app.view.scale.y
	app.view.mobile_playfield=Rect2(playfield.position/app.view.scale,playfield.size/app.view.scale)
	app.view.mobile_floor=app.view.mobile_playfield.end.y-bounds.end.y*app.view.PY-earth_depth/app.view.scale.y

func update_hud():
	var p: Dictionary=app.sim.players[0]
	app.resource_label.text="金 %d"%int(p.gold);app.mana_label.text="法 %d · +%.1f/s"%[int(p.mana),app.sim.mana_rate(0)]
	app.clock_label.text="%02d:%02d"%[int(app.sim.time)/60,int(app.sim.time)%60]
	app.base_label.text="我城 %d · 敌城 %s"%[int(app.sim.bases[0].hp),str(int(app.sim.bases[1].hp)) if app.sim.visible_to(0,app.sim.bases[1]) else "未知"]
	app.army_label.text="兵%d · 工%d · 队%d"%[app.sim.population(0,false,false),app.sim.population(0,true,false),p.queue.size()]
	orders_button.text="取消" if app.view.selected_spell!="" or app.view.selected_building!="" else "军令"
	orders_button.accessibility_description="招募队列 %d / 6 · 打开科技、建造和导航"%p.queue.size()
	queue_badge.text=str(p.queue.size()) if not p.queue.is_empty() else ""
	app.hint_label.text="点目标施法" if app.view.selected_spell!="" else "点建造位施工" if app.view.selected_building!="" else ""
	app.hint_label.tooltip_text="拖动只移动镜头，点取消撤销。" if not app.hint_label.text.is_empty() else ""
	app.status_label.text=app.toast_text if app.toast_left>0 else app.battle_objective_text()
	if app.view.selected_uid>0:
		var a: Dictionary=app.sim.actor(app.view.selected_uid)
		if not app.sim.visible_to(0,a):a={};app.view.selected_uid=0
		if not a.is_empty():app.status_label.text=("我方 · " if a.side==0 else "敌方 · ")+app.db.name_of(a.id)+" · 生命 %d/%d"%[a.hp,a.max_hp]
	elif not p.research.is_empty():app.status_label.text="研究 %s · %.1f 秒"%[app.db.name_of(app.db.tech(p.research.id).grant),p.research.left]
	var show: bool=app.toast_left>0 or app.view.selected_uid>0 or not p.research.is_empty() or app.options.get("win","destroy_base")!="destroy_base"
	app.status_label.tooltip_text=app.status_label.text;app.status_label.accessibility_description=app.status_label.text
	app.hint_label.visible=not app.hint_label.text.is_empty();app.hint_back.visible=app.hint_label.visible
	app.status_label.visible=show and not app.hint_label.visible;app.status_back.visible=app.status_label.visible
	app.clock_label.visible=not app.hint_label.visible and not app.status_label.visible

func orders_menu():
	var body=sheet("orders","军令 · 投资与导航",orders_menu,[["返回战场",app.close_overlay]])
	app.battle_sheet=app.BattleSheets.new()
	app.battle_sheet.summary=text(body,"",17)
	app.battle_sheet.refresh(app.sim,0,app.paused)
	if not app.toast_text.is_empty() and app.toast_left>0:text(body,app.toast_text,16,UI.MUTED)
	var g=grid(body,Layout.columns(app.ui.size.x-24,160,3))
	for entry in [["研究科技",app.open_tech],["建造塔灯",app.open_build],["招募队列",app.open_queue],["返回纸城",func():app.close_overlay();app.view.target_camera=app.sim.bases[0].x+6;app.view.follow_front=false],["追踪交锋",func():app.close_overlay();app.view.follow_front=true;app.view.target_camera=app.sim.front(app.view.player_side)],["取消当前选择",func():app.close_overlay();app.cancel_selection()],["向左移动",func():app.view.target_camera-=6;app.view.follow_front=false],["向右移动",func():app.view.target_camera+=6;app.view.follow_front=false],["操作帮助",help_menu],["暂停对战",app.pause_menu]]:action(g,entry[0],entry[1])
	text(body,"金币在运金纸工卸货后入账。研究、建造和队列界面打开时，对战继续进行。",16,UI.MUTED)

func card_info(id: String,magic: bool):
	var body=sheet("info",app.db.name_of(id),func():card_info(id,magic),[["返回战场",app.close_overlay]])
	artwork(body,app.db.art(id,true),96)
	if magic:
		var def: Dictionary=app.db.balance.spells[id]
		text(body,"%d 法力 · 冷却 %.1f 秒\n%s"%[def.mana,def.cooldown,app.db.spell_hint(id)],18)
	else:
		var def: Dictionary=app.db.balance.units[id]
		text(body,"%d 金币 · 生命 %d · 伤害 %d\n%s"%[def.gold,def.hp,def.damage,app.db.unit_hint(id)],18)
		if app.sim!=null:text(body,"打开时估算 · "+RecruitmentReadiness.investment_notice(app.sim,0,id)+"\n"+RecruitmentReadiness.reinforcement_notice(app.sim,0,id),14,UI.MUTED)
	text(body,"轻点卡片招募或选择法术，长按查看资料。查看资料不会付费或施法。",14,UI.MUTED)

func open_tech(page: int=0):
	if app.paused or app.sim==null:return
	app.cancel_selection();app.tech_page=page
	var body=sheet("tech","科技 · "+app.db.FACTION_NAMES[app.sim.players[0].faction],func():open_tech(page),[["返回战场",app.close_overlay]])
	text(body,"研究与出兵共同消耗金币。已完成、研究中或未满足前置的项目不可重复提交。",16,UI.MUTED)
	app.tech_buttons.clear()
	for node in app.db.technology.nodes:
		if node.faction!=app.sim.players[0].faction:continue
		if node.grant.begins_with("unit.") and not app.sim.players[0].roster.has(node.grant):continue
		var b=action(body,"",func():
			if app.execute("research",{"id":node.id}):app.toast("开始研究 "+app.db.name_of(node.grant)))
		b.custom_minimum_size.y=64;b.add_theme_font_size_override("font_size",17);app.tech_buttons[node.id]=b
	app.refresh_tech()

func open_build(slot: int=-1):
	if app.paused or app.sim==null:return
	app.cancel_selection();app.build_focus_slot=slot
	var site: Dictionary=app.sim.slot_anchor(0,slot) if slot>=0 and slot<app.sim.side_sites(0).size() else {}
	var body=sheet("build","建造 · "+str(site.get("label","固定塔灯位")),func():open_build(slot),[["返回战场",app.close_overlay]])
	app.battle_sheet=app.BattleSheets.new()
	var f: String=app.sim.players[0].faction
	for kind in ["tower","mana"]:
		var id: String="building."+f+"."+kind;var def: Dictionary=app.db.balance.buildings[id]
		var b=action(body,"%s · %d 金 · %d 秒施工"%[app.db.name_of(id),def.gold,def.construction_seconds],func():app.choose_building(id))
		b.custom_minimum_size.y=64;b.add_theme_font_size_override("font_size",17)
		app.battle_sheet.bind_build(b,id,slot,true,b.text)
		text(body,"覆盖前哨与矿路，施工期间不会攻击。" if kind=="tower" else "完工后增加法力产量，封禁时暂停产法。")
	text(body,"选择建筑后点发亮的兼容空位才会付费。取消选择不会扣费。",16,UI.MUTED)
	app.battle_sheet.refresh(app.sim,0,app.paused)

func open_queue():
	if app.paused or app.sim==null:return
	var body=sheet("queue","招募队列 · 取消并退款",open_queue,[["返回战场",app.close_overlay]])
	text(body,"实时出仓倒计时 · 出仓后仍需行军，战斗继续进行。",14,UI.MUTED)
	var rows=column(body)
	var empty=text(body,"当前没有正在生产的单位。")
	app.battle_sheet=app.BattleSheets.new()
	app.battle_sheet.bind_queue(func(i: int,id: String,revision: int):
		var b=action(rows,"",func():
			app.execute("cancel_queue",{"index":i,"id":id,"queue_revision":revision})
			if app.battle_sheet!=null:app.battle_sheet.refresh(app.sim,0,app.paused))
		b.custom_minimum_size.y=64;b.add_theme_font_size_override("font_size",17);return b,empty)
	app.battle_sheet.refresh(app.sim,0,app.paused)

func pause_menu(show_help: bool=false):
	if app.sim==null or app.sim.winner!=-2:return
	app.paused=true;app.cancel_selection()
	var body=sheet("pause","战局暂歇",func():pause_menu(show_help),[["继续对战",func():app.paused=false;app.close_overlay(),true]])
	text(body,"对战已暂停。你可以调整声音与显示、阅读帮助或重新开始。",17)
	var g=grid(body,Layout.columns(app.ui.size.x-24,210,2))
	action(g,"声音与显示",func():app.settings_menu(true));action(g,"操作帮助",help_menu)
	action(g,"重新开局",func():app.start_battle(app.options));action(g,"结束本局 · 返回主菜单",app.main_menu)
	if show_help:text(body,help_text())

func help_text() -> String:
	return "军团自动行军和交战。金币由纸工采矿、负重回城、卸货后入账。\n\n底部一排同时显示招募和五个法术。招募区可左右滑动，开局偏好和工人排在前面，六兵种均可找到。轻点卡片招募或选择法术，长按查看完整资料；滑动兵卡不会招募。点选法术后轻点战场目标施放；拖动会移动镜头，不会释放法术。\n\n「军令」中可查看城池、兵力、研究、建造和队列，并可返回纸城、追踪交锋或暂停。点矿设运输优先级，点路标改变后续部队路线。\n\n左右滑动战场或拖动右上小地图导航。另一根手指可以操作 HUD。返回键先撤销选择，再关闭面板，再暂停。后台恢复时需手动继续对战。"

func help_menu():
	var body=sheet("help","操作帮助",help_menu,[["返回",func():app.pause_menu() if app.paused and app.screen=="battle" else app.close_overlay()]])
	text(body,help_text(),18)

func settings_menu(in_battle: bool):
	settings_in_battle=in_battle
	if in_battle:app.paused=true
	else:begin("settings","声音与显示",func():settings_menu(false))
	var body=sheet("settings","声音与显示",func():settings_menu(in_battle),[["保存并返回",save_settings,true]])
	for key in ["music","sfx"]:
		var caption=text(body,"音乐音量" if key=="music" else "动作与界面音量",18)
		var slider=preload("res://scripts/mobile_slider.gd").new();slider.name="MobileVolume_"+key;slider.custom_minimum_size=Vector2(48,48);slider.size_flags_horizontal=Control.SIZE_EXPAND_FILL
		slider.min_value=0;slider.max_value=1;slider.step=.01;slider.value=app.profile.settings[key];slider.accessibility_name=caption.text;body.add_child(slider)
		slider.value_changed.connect(func(value):app.profile.settings[key]=value;app.audio.settings=app.profile.settings;caption.text=("音乐音量" if key=="music" else "动作与界面音量")+" · %d%%"%roundi(value*100))
	for entry in [["reduced_motion","减少镜头与背景动效"],["follow_front","开局追踪交锋"],["battery_saver","省电模式 · 30 帧与精简粒子"]]:
		var key: String=entry[0];var b=CheckButton.new();b.mouse_filter=Control.MOUSE_FILTER_PASS;b.text=entry[1];b.custom_minimum_size=Vector2(48,48);b.button_pressed=app.profile.settings.get(key,false);body.add_child(b)
		b.toggled.connect(func(value):app.profile.settings[key]=value;app.apply_mobile_quality();app.view.reduced_motion=app.profile.settings.reduced_motion)
	text(body,"横屏游玩 · 支持正反横屏、安全区与触屏导航。减少动效仍保留采矿、攻击与受击反馈。",14,UI.MUTED)

	if not in_battle:
		action(body,"地图试演",app.theatre_menu);action(body,"操作帮助",help_menu)
		action(body,"鸣谢与许可",app.credits_menu);action(body,"退出游戏",exit_menu)

func save_settings():
	app.save_profile()
	if settings_in_battle:app.pause_menu()
	else:app.main_menu()

func show_result():
	var victory: bool=app.sim.winner==0;var stars: int=int(app.profile.stars.get(app.options.get("id",""),0)) if app.mode=="campaign" else int(app.profile.challenge_stars.get(app.options.get("id",""),0))
	var next_action: Callable=func():app.start_battle(app.options)
	var next_text: String="重新开局"
	if victory and app.mode=="campaign":
		next_text="选择下一页" if str(app.options.id)!=app.campaign_progress.finale else "故事终章"
		next_action=app.campaign_menu if str(app.options.id)!=app.campaign_progress.finale else app.show_epilogue
	var body=sheet("result","纸上得胜" if victory else "两城同落" if app.sim.winner==-1 else "此局失印",show_result,[[next_text,next_action,true],["主菜单",app.main_menu]])
	var summary=row(body);var emblem=artwork(summary,UI.art("icon-victory" if victory else "icon-defeat"),48);emblem.size_flags_horizontal=Control.SIZE_SHRINK_BEGIN
	text(summary,app.options.title+" · %02d:%02d"%[int(app.sim.time)/60,int(app.sim.time)%60],20)
	if victory:text(body,"★".repeat(stars)+"☆".repeat(3-stars),26,UI.GOLD)
	else:text(body,app.sim.result_reason+"。保护矿路与任务对象，调整部署再战。",18)
	var s: Dictionary=app.sim.stats[0]
	if app.mode=="challenge":text(body,"本局 %d 分 · 最佳 %d 分"%[app.sim.ChallengeRules.score(app.sim),int(app.profile.get("challenge_scores",{}).get(app.options.id,0))],20,UI.GOLD)
	text(body,"招募 %d · 击倒 %d · 损失 %d\n归仓金币 %d · 施法 %d · 消耗法力 %d\n治疗 %d · 召唤 %d · 反弹 %d · 打断 %d"%[s.recruited,s.killed,s.lost,s.gold_delivered,s.casts,s.mana_spent,s.healed,s.summons,s.reflections,s.interrupts],18)
	if victory and app.mode=="campaign":text(body,app.dialogue_text(app.options.get("story_after",app.db.story.ending)),17)
	action(body,"再战本局" if victory else "调整部署再战",func():app.start_battle(app.options) if victory else app.loadout_menu(app.options.faction,func():app.start_battle(app.options),app.options.get("available_roster",app.db.all_unit_ids(app.options.faction))))

func show_epilogue():
	var body=sheet("epilogue","十院留名",show_epilogue,[["返回山河",app.main_menu,true]])
	text(body,app.db.story.ending,20)
	for f in app.db.FACTIONS:text(body,app.db.factions[f].hero+" · "+app.db.FACTION_NAMES[f]+"\n"+app.db.factions[f].ending,17)
	action(body,"继续阅读兵书",func():app.archive_menu("bai",app.db.all_unit_ids("bai")[0]))

func credits_menu():
	var body=begin("credits","鸣谢与许可",credits_menu)
	text(body,"纸上兵戈 / "+ProjectSettings.get_setting("application/config/version"),20)
	text(body,"原创纸雕题材、生成美术与纸偶加工。Godot Engine 使用 MIT 许可；中文字体采用 Noto Sans SC 与 Noto Serif SC（SIL OFL）。",17)
	for path in ["res://licenses/GODOT-LICENSE.txt","res://licenses/GODOT-COPYRIGHT.txt","res://assets/fonts/OFL-NotoSansSC.txt","res://assets/fonts/OFL-NotoSerifSC.txt"]:text(body,FileAccess.get_file_as_string(path),14,UI.MUTED)

func exit_menu():
	var body=sheet("exit","结束游戏",exit_menu,[["继续留在游戏",app.close_overlay,true],["退出",func():app.save_profile();app.get_tree().quit()]])
	text(body,"战役进度和设置已保存在本机。结束后可从主菜单继续。",18)

func back():
	if app.mobile_blocked:
		if app.screen=="menu":app.save_profile();app.get_tree().quit()
		else:app.main_menu()
		return
	if app.screen=="battle" and (app.view.selected_spell!="" or app.view.selected_building!=""):app.cancel_selection();return
	if app.modal=="settings":save_settings()
	elif app.modal in ["loadout","choice"] and loadout_return.is_valid():loadout_return.call()
	elif app.modal=="pause":app.paused=false;app.close_overlay()
	elif app.modal=="result":app.main_menu()
	elif app.modal=="help" and app.paused and app.screen=="battle":app.pause_menu()
	elif app.modal=="brief" and app.screen=="battle":app.main_menu();app.campaign_menu()
	elif app.modal!="":app.close_overlay()
	elif app.screen=="battle":
		if app.view.selected_spell!="" or app.view.selected_building!="":app.cancel_selection()
		else:app.pause_menu()
	elif app.screen in ["campaign","skirmish"]:app.new_battle_menu()
	elif app.screen=="menu":exit_menu()
	else:app.main_menu()
