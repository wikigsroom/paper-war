"""Replace legacy 3-faction menus with authored-world native Godot controls."""
from pathlib import Path
import re
ROOT=Path(__file__).resolve().parents[2]
p=ROOT/'game/scripts/main.gd'
text=p.read_text(encoding='utf-8')
if 'var campaign_chapter:' in text:
    raise SystemExit('World UI is already installed. Edit current GDScript directly; this one-time migration will not overwrite later fixes.')
functions={}
functions['load_profile']=r'''func load_profile():
	var path="user://profile.json"
	if not FileAccess.file_exists(path) and OS.get_name()=="Windows":
		path=OS.get_environment("APPDATA").path_join("Godot/app_userdata/纸上兵戈 · Paper Warfront/profile.json")
	if FileAccess.file_exists(path):
		var saved=JSON.parse_string(FileAccess.get_file_as_string(path))
		if typeof(saved)==TYPE_DICTIONARY:
			if int(saved.get("schema",1))<2:
				profile["legacy_campaign"]={"unlocked":saved.get("unlocked",0),"stars":saved.get("stars",{})}
			else:
				profile.unlocked=clampi(int(saved.get("unlocked",0)),0,db.campaign.size()-1)
				profile.stars=saved.get("stars",{})
				profile.loadouts=saved.get("loadouts",{})
				if saved.has("legacy_campaign"):profile["legacy_campaign"]=saved.legacy_campaign
			profile.challenge_stars=saved.get("challenge_stars",{})
			for key in profile.settings:
				if typeof(saved.get("settings",{}))==TYPE_DICTIONARY and saved.settings.has(key):profile.settings[key]=saved.settings[key]
	profile.settings.music=clampf(float(profile.settings.music),0,1)
	profile.settings.sfx=clampf(float(profile.settings.sfx),0,1)
	profile.settings.reduced_motion=bool(profile.settings.reduced_motion)
	profile.settings.follow_front=bool(profile.settings.follow_front)
	for f in db.FACTIONS:
		var roster: Array = []
		for id in profile.loadouts.get(f,db.factions[f].default_roster):
			if db.all_unit_ids(f).has(id) and not roster.has(id) and roster.size()<8:roster.append(id)
		db.deployments[f]=roster if roster.size()>=4 else db.factions[f].default_roster.duplicate()
	profile.schema=2
	if FileAccess.file_exists(path):save_profile()'''
functions['campaign_menu']=r'''func campaign_menu(chapter_index: int = -1):
	clear_ui();screen="campaign";view.menu=true
	if chapter_index>=0:campaign_chapter=clampi(chapter_index,0,9)
	else:campaign_chapter=clampi(int(profile.unlocked)/20,0,9)
	menu_header("战役 · 十院二百折","十位统帅接力保全证据。按故事顺序解锁，每关胜利后保存进度。")
	var names: Array = []
	for ch in db.story.chapters:names.append("第 %02d 章  %s"%[int(ch.index)+1,ch.title])
	var chapters=selector(ui,"故事章节",Rect2(87,204,1426,60),names)
	chapters.select(campaign_chapter);chapters.item_selected.connect(func(i):campaign_menu(i))
	var f: String = db.FACTIONS[campaign_chapter]
	var left=panel(ui,Rect2(87,287,330,530))
	image_rect(left,db.art("portrait."+f+".commander",true),Rect2(22,20,285,220))
	label(left,db.factions[f].hero+" · "+db.FACTION_NAMES[f],Rect2(22,247,285,42),24,db.FACTION_COLORS[f],true)
	paragraph(left,db.factions[f].premise,Rect2(22,300,285,125),20)
	paragraph(left,db.mana_hint(f),Rect2(22,437,285,78),18)
	for local in range(20):
		var index=campaign_chapter*20+local
		var level: Dictionary = db.campaign[index]
		var stars=clampi(int(profile.stars.get(level.id,0)),0,3)
		var b=button(ui,"%03d  %s\n%s"%[index+1,level.title,"★".repeat(stars)+"☆".repeat(3-stars)],Rect2(437+(local%4)*273,287+(local/4)*108,257,96),func():show_brief(level,"campaign"))
		b.add_theme_font_size_override("font_size",18);b.disabled=index>int(profile.unlocked)
		b.tooltip_text=db.map_definition(level.map).decision'''
functions['map_preview']=r'''func map_preview(parent: Node,definition: Dictionary,rect: Rect2):
	var preview=preload("res://scripts/map_preview.gd").new()
	preview.definition=definition;preview.font=body_font;preview.position=rect.position;preview.size=rect.size
	preview.mouse_filter=Control.MOUSE_FILTER_IGNORE;parent.add_child(preview)'''
functions['show_brief']=r'''func show_brief(level: Dictionary, battle_mode: String):
	mode=battle_mode;options=level.duplicate(true)
	create_overlay("brief",Rect2(246,64,1108,770))
	var f: String = level.faction
	var m: Dictionary = db.map_definition(level.map)
	label(overlay,("第 %03d 折"%(int(level.get("index",0))+1)) if battle_mode=="campaign" else "战术挑战",Rect2(30,20,1000,40),22,Color("746d61"))
	label(overlay,level.title,Rect2(28,66,1045,58),38,db.FACTION_COLORS[f],true)
	image_rect(overlay,db.art("portrait."+f+".commander",true),Rect2(24,140,285,307))
	paragraph(overlay,"“"+level.line+"”",Rect2(30,472,274,135),22)
	paragraph(overlay,level.get("story_before",level.tip),Rect2(336,141,736,123),22)
	label(overlay,"地图 · "+m.name,Rect2(335,275,730,35),23,Color("343332"),true)
	map_preview(overlay,m,Rect2(336,321,736,132))
	paragraph(overlay,"任务："+level.tip+"\n空间决策："+m.decision,Rect2(336,471,736,118),21)
	paragraph(overlay,"%s 对 %s   ·   起始金币 %d : %d\n%s"%[db.FACTION_NAMES[f],db.FACTION_NAMES[level.enemy],level.starting_gold,level.enemy_starting_gold,db.mana_hint(f)],Rect2(336,600,736,74),19)
	button(overlay,"调整部署",Rect2(30,689,257,60),func():loadout_menu(f,func():show_brief(level,battle_mode),level.get("available_units",db.all_unit_ids(f))))
	button(overlay,"展开战场",Rect2(334,689,473,60),func():start_battle(options))
	button(overlay,"返回",Rect2(827,689,245,60),func():
		if screen=="battle":main_menu();campaign_menu()
		else:close_overlay())'''
functions['skirmish_menu']=r'''func skirmish_menu():
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
	button(p,"开 战",Rect2(952,521,422,59),func():
		mode="skirmish"
		start_battle({"title":"遭遇战","faction":db.FACTIONS[ally.selected],"enemy":db.FACTIONS[enemy.selected],"map":ids[map_choice.selected],"difficulty":difficulty.selected,"ai_style":["rush","economy","counter"][style.selected],"starting_gold":300,"enemy_starting_gold":300,"full_tech":full.button_pressed,"win":"destroy_base"}))'''
functions['loadout_menu']=r'''func loadout_menu(faction: String, return_action: Callable, available: Array = [], page: int = 0, chosen: Array = []):
	if available.is_empty():available=db.all_unit_ids(faction)
	if chosen.is_empty():
		for id in db.deployments.get(faction,db.factions[faction].default_roster):
			if available.has(id):chosen.append(id)
		if chosen.size()<4:chosen=available.slice(0,mini(8,available.size()))
	create_overlay("loadout",Rect2(86,61,1428,778))
	label(overlay,"部署 · "+db.FACTION_NAMES[faction],Rect2(25,16,1040,53),34,db.FACTION_COLORS[faction],true)
	paragraph(overlay,"从四十兵种中选择 4–8 个作战单位。工人另占一个招募位；编组决定本局能招募哪些单位。战役按进度开放兵种。",Rect2(25,82,1378,64),21)
	var ids: Array = db.all_unit_ids(faction)
	for local in range(20):
		var index=page*20+local
		if index>=ids.size():break
		var id: String = ids[index]
		var c=card(overlay,id,Rect2(25+(local%5)*279,161+(local/5)*126,261,113),false,func():
			var next: Array = chosen.duplicate()
			if next.has(id):next.erase(id)
			elif next.size()<8:next.append(id)
			else:audio.play("ui-invalid");return
			loadout_menu(faction,return_action,available,page,next))
		c.selected=chosen.has(id);c.price="%d 金  ·  %s"%[db.balance.units[id].gold,"已选" if c.selected else "候选"]
		c.disabled=not available.has(id);c.locked=c.disabled;c.tooltip_text=db.unit_hint(id)
	var selected_names: Array = []
	for id in chosen:selected_names.append(db.name_of(id))
	paragraph(overlay,"已选 %d / 8：%s"%[chosen.size(),"、".join(selected_names)],Rect2(25,670,965,80),20)
	button(overlay,"上一页" if page==1 else "下一页",Rect2(1000,680,185,66),func():loadout_menu(faction,return_action,available,1-page,chosen))
	var confirm=button(overlay,"保存部署",Rect2(1202,680,200,66),func():
		db.deployments[faction]=chosen.duplicate();profile.loadouts[faction]=chosen.duplicate();save_profile();return_action.call())
	confirm.disabled=chosen.size()<4 or chosen.size()>8
	button(overlay,"返回",Rect2(1255,22,146,56),return_action)'''
functions['start_battle']=r'''func start_battle(config: Dictionary):
	options=config.duplicate(true)
	var faction: String = options.faction
	var available: Array = options.get("available_units",db.all_unit_ids(faction))
	var roster: Array = []
	for id in db.deployments.get(faction,db.factions[faction].default_roster):
		if available.has(id):roster.append(id)
	for id in db.factions[faction].default_roster:
		if roster.size()>=4:break
		if available.has(id) and not roster.has(id):roster.append(id)
	options["player_roster"]=roster.slice(0,8)
	if not options.has("enemy_roster"):options["enemy_roster"]=db.factions[options.enemy].default_roster.duplicate()
	clear_ui();screen="battle";paused=false;result_shown=false;hud_section="units"
	accumulator=0;queue_signature="";toast_text="";toast_left=0;inspect_id=""
	sim=Simulation.new(db);sim.start(options)
	view.reset(sim);view.follow_front=profile.settings.follow_front;view.reduced_motion=profile.settings.reduced_motion
	audio.set_music(options.faction);build_hud()
	toast("点击路标改变后续部队路线；点击我方矿点设置采矿优先级。",7)'''
functions['build_hud']=r'''func build_hud():
	var p=panel(ui,Rect2(0,0,1600,178))
	p.add_theme_stylebox_override("panel",box(Color("e8deca"),Color("baa994"),0))
	resource_label=label(p,"",Rect2(22 if not mobile_ui else 357,7,650,37),20)
	clock_label=label(p,"",Rect2(1150,7,427,37),18,Color("746d61"))
	queue_box=HBoxContainer.new();queue_box.position=Vector2(714,6);queue_box.size=Vector2(426,38);queue_box.add_theme_constant_override("separation",6);p.add_child(queue_box)
	if mobile_ui:
		queue_box.visible=false
		button(p,"招募编组",Rect2(14,4,156,44),func():hud_section="units";clear_ui();build_hud())
		button(p,"阵营法术",Rect2(182,4,156,44),func():hud_section="spells";clear_ui();build_hud())
	var faction: String = sim.players[0].faction
	var units_order: Array = sim.players[0].roster.duplicate();units_order.append("unit."+faction+".worker")
	for i in range(units_order.size()):
		var id: String = units_order[i]
		var c=card(p,id,Rect2(14+i*(134 if mobile_ui else 86),55,124 if mobile_ui else 78,113),false,func():recruit_action(id))
		c.visible=not mobile_ui or hud_section=="units";c.detail=str(i+1);unit_cards[id]=c
	var spells_order: Array = db.spell_ids(faction)
	for i in range(spells_order.size()):
		var id: String = spells_order[i]
		var c=card(p,id,Rect2((14+i*230) if mobile_ui else (800+i*86),55,212 if mobile_ui else 78,113),true,func():select_spell(id))
		c.visible=not mobile_ui or hud_section=="spells";c.detail=["Q","W","E","R","T"][i];spell_cards[id]=c
	button(p,"科技" if mobile_ui else "科技 F",Rect2(1242,55,154,51),open_tech)
	button(p,"建造" if mobile_ui else "建造 B",Rect2(1242,117,154,51),open_build)
	button(p,"暂停" if mobile_ui else "暂停 P",Rect2(1408,55,178,51),pause_menu)
	button(p,"兵书",Rect2(1408,117,178,51),func():pause_menu(true))
	button(ui,"纸城",Rect2(22,823,131,54),func():view.target_camera=10;view.follow_front=false)
	button(ui,"交锋",Rect2(165,823,131,54),func():view.follow_front=true;view.target_camera=sim.front())
	button(ui,"取消",Rect2(1368,823,112,54),cancel_selection)
	button(ui,"‹",Rect2(1224,823,59,54),func():view.target_camera-=6;view.follow_front=false)
	button(ui,"›",Rect2(1293,823,59,54),func():view.target_camera+=6;view.follow_front=false)
	hint_label=label(ui,"",Rect2(340,863,1010,29),17,Color("746d61"))
	status_label=label(ui,"",Rect2(25,185,1545,44),21,Color("343332"))
	update_hud()'''
functions['open_tech']=r'''func open_tech(page: int = 0):
	if paused or sim==null:return
	cancel_selection();create_overlay("tech",Rect2(562,213,966,570));tech_page=page
	overlay.get_parent().get_child(0).color=Color(.1,.09,.07,.3)
	label(overlay,"科技 · "+db.FACTION_NAMES[sim.players[0].faction],Rect2(26,16,755,56),34,db.FACTION_COLORS[sim.players[0].faction],true)
	button(overlay,"关闭",Rect2(824,21,116,48),close_overlay)
	var p=sim.players[0];var nodes: Array = []
	for node in db.technology.nodes:
		if node.faction!=p.faction:continue
		if node.grant.begins_with("unit.") and not p.roster.has(node.grant):continue
		nodes.append(node)
	var pages: int = maxi(1,int(ceilf(nodes.size()/8.0)))
	tech_page=clampi(page,0,pages-1)
	for local in range(8):
		var index=tech_page*8+local
		if index>=nodes.size():break
		var node: Dictionary = nodes[index]
		var b=button(overlay,"",Rect2(26+(local%2)*466,92+(local/2)*93,448,80),func():
			if execute("research",{"id":node.id}):toast("开始研究 "+db.name_of(node.grant)))
		b.add_theme_font_size_override("font_size",19)
		var requirements: Array = []
		for req in node.requires:requirements.append(db.name_of(db.tech(req).grant))
		b.tooltip_text="前置："+("无" if requirements.is_empty() else "、".join(requirements));tech_buttons[node.id]=b
	button(overlay,"上一页",Rect2(26,478,155,52),func():open_tech(maxi(0,tech_page-1))).disabled=tech_page==0
	button(overlay,"下一页",Rect2(200,478,155,52),func():open_tech(mini(pages-1,tech_page+1))).disabled=tech_page==pages-1
	label(overlay,"%d / %d  ·  兵法阶位开放编组内的高阶兵种"%[tech_page+1,pages],Rect2(381,480,550,43),20,Color("746d61"))
	refresh_tech()'''
functions['open_build']=r'''func open_build():
	if paused or sim==null:return
	cancel_selection();create_overlay("build",Rect2(866,269,656,385))
	label(overlay,"建造 · 地图固定纸位",Rect2(25,15,591,55),32,Color("343332"),true)
	var f: String = sim.players[0].faction
	var tower: Dictionary = db.balance.buildings["building."+f+".tower"]
	var lamp: Dictionary = db.balance.buildings["building."+f+".mana"]
	button(overlay,"纸哨塔 · %d 金 · %d 秒施工\n保护施工期，完工后守住运输线"%[tower.gold,tower.construction_seconds],Rect2(26,92,602,87),func():choose_building("building."+f+".tower"))
	button(overlay,"产法纸灯 · %d 金 · %d 秒施工\n完工且未被封禁时，每秒 +%.1f 法力"%[lamp.gold,lamp.construction_seconds,lamp.mana_per_second],Rect2(26,192,602,87),func():choose_building("building."+f+".mana"))
	paragraph(overlay,"本图有 %d 个我方建筑位。前置更接近交锋，也更容易在施工时被拆除。"%sim.side_sites(0).size(),Rect2(28,293,589,75),20)
	button(overlay,"×",Rect2(573,20,55,50),close_overlay)'''
functions['archive_menu']=r'''func archive_menu(faction: String, selected: String, page: int = 0):
	clear_ui();screen="archive";view.menu=true
	menu_header("兵书 · 十院军阵","每院四十作战兵种。选择编组前先了解职责、能力与反制。")
	var names: Array = []
	for f in db.FACTIONS:names.append(db.FACTION_NAMES[f])
	var factions=selector(ui,"阵营",Rect2(87,207,530,60),names);factions.select(db.FACTIONS.find(faction))
	factions.item_selected.connect(func(i):archive_menu(db.FACTIONS[i],db.all_unit_ids(db.FACTIONS[i])[0],0))
	button(ui,"部署编组",Rect2(644,207,270,60),func():loadout_menu(faction,func():archive_menu(faction,selected,page)))
	var left=panel(ui,Rect2(87,287,389,530));var right=panel(ui,Rect2(494,287,1018,530))
	label(left,db.name_of(selected),Rect2(21,18,347,54),31,db.FACTION_COLORS[faction],true)
	image_rect(left,db.art(selected),Rect2(20,84,348,309))
	paragraph(left,db.mana_hint(faction),Rect2(21,414,347,97),20)
	var ids: Array = db.all_unit_ids(faction)+["unit."+faction+".worker"]+db.spell_ids(faction)
	var pages: int = int(ceilf(ids.size()/12.0))
	for local in range(12):
		var index=page*12+local
		if index>=ids.size():break
		var id: String = ids[index];var magic: bool = db.balance.spells.has(id)
		var c=card(right,id,Rect2(20+(local%4)*250,15+(local/4)*122,232,113),magic,func():archive_menu(faction,id,page))
		c.selected=selected==id
		c.price=("%d 法"%db.balance.spells[id].mana) if magic else ("%d 金"%db.balance.units[id].gold)
	var detail: String = ""
	if db.balance.units.has(selected):
		var def: Dictionary = db.balance.units[selected]
		detail="生命 %d · 伤害 %d · 射程 %.2f · 速度 %.2f\n%s"%[def.hp,def.damage,def.range,def.speed,db.unit_hint(selected)]
	else:
		var def: Dictionary = db.balance.spells[selected]
		detail="法力 %d · 冷却 %.1f 秒\n%s"%[def.mana,def.cooldown,db.SPELL_HINTS.get(selected.get_slice(".",2),"")]
	paragraph(right,detail,Rect2(20,389,976,70),20)
	button(right,"上一页",Rect2(20,468,170,48),func():archive_menu(faction,selected,maxi(0,page-1))).disabled=page==0
	button(right,"下一页",Rect2(209,468,170,48),func():archive_menu(faction,selected,mini(pages-1,page+1))).disabled=page==pages-1
	label(right,"%d / %d  ·  40 作战单位 + 工人 + 5 法术"%[page+1,pages],Rect2(407,473,574,39),19,Color("746d61"))'''
functions['navigate_minimap']=r'''func navigate_minimap(x: float):
	var box=view.minimap_rect()
	var half: float = minf(view.width/view.PX*.5,sim.map.length*.5)
	view.target_camera=clampf((x-box.position.x)/box.size.x*sim.map.length,half,sim.map.length-half);view.follow_front=false'''
functions['battlefield_tap']=r'''func battlefield_tap(pos: Vector2, captured_target: int = -1):
	if pos.y<178 or pos.y>810:return
	var ground: Dictionary = view.screen_to_ground(pos)
	var x: float = view.screen_to_world(pos.x)
	var y: float = (pos.y-view.floor_y())/view.PY
	if view.selected_spell!="":
		var id: String = view.selected_spell
		var target: int = captured_target if captured_target>=0 else view.target_at(pos)
		var a: Dictionary = sim.actor(target)
		if not a.is_empty():x=a.x;y=a.y
		if execute("cast",{"id":id,"x":x,"y":y,"target":target}):view.selected_spell="";toast(db.name_of(id)+" 已施放",1.5)
		update_hud()
	elif view.selected_building!="":
		var slot: int = -1
		for i in range(sim.side_sites(0).size()):
			var site: Dictionary = sim.slot_anchor(0,i)
			if view.point_to_screen(site.x,site.y).distance_to(pos)<46:slot=i
		if execute("build",{"id":view.selected_building,"slot":slot}):toast("已开始施工，保护建筑位。");view.selected_building=""
	else:
		for node_id in sim.map.fork_nodes(0):
			var node: Array = sim.map.nodes[node_id].position
			if (view.point_to_screen(node[0],node[1])+Vector2(0,-38)).distance_to(pos)<40:
				var exits: Array = sim.map.adjacency[0].get(node_id,[])
				var current: String = sim.map.choices[0].get(node_id,exits[0])
				var edge: String = exits[(exits.find(current)+1)%exits.size()]
				if execute("route",{"node":node_id,"edge":edge}):toast("路标已切换；后续部队在此选路。")
				return
		for mine in sim.map.definition.mines:
			if int(mine.owner)==0 and (view.point_to_screen(mine.x,mine.y)+Vector2(0,-22)).distance_to(pos)<42:
				if execute("mine_priority",{"mine":mine.id}):toast("运金工下一次出发优先前往此矿；容量 %d。"%mine.capacity)
				return
		view.selected_uid=view.target_at(pos);update_hud()'''

for name,body in functions.items():
    if re.search(r'^func '+re.escape(name)+r'\(',text,re.M):
        text,count=re.subn(r'^func '+re.escape(name)+r'\([^\n]*(?:\n(?!func )[^\n]*)*',lambda _:body+'\n',text,count=1,flags=re.M)
        assert count==1,name
    else:text+='\n'+body+'\n'
text=text.replace('"schema":1,"unlocked":0','"schema":2,"loadouts":{},"unlocked":0')
if 'var campaign_chapter:' not in text:text=text.replace('var db\n','var campaign_chapter: int = 0\nvar tech_page: int = 0\nvar hud_section: String = "units"\nvar db\n',1)
text=text.replace('三军对弈','十院对弈').replace('十五折','二百折').replace('三军异法','路线与矿路').replace('v1.0.0','v2.0.0-dev').replace('/  1.0.0','/  2.0.0-dev')
text=text.replace('三支军团，一条战线。每次招募与施法都要算准。','十院军阵，二百纸局。投资、选路、护矿与施法互相牵制。')
text=text.replace('db.UNIT_HINTS.get(id.get_slice(".",2),"")','db.unit_hint(id)')
text=text.replace('工 %d/6','工 %d/10')
text=text.replace('db.UNIT_HINTS.get(a.id.get_slice(".",2),"自动进军")','db.unit_hint(a.id)')
text=text.replace('else: status_label.text=options.get("tip","摧毁敌方纸城。保护经济，选择兵种搭配与施法时机。")','else: status_label.text=sim.objective_text()')
text=text.replace('view.selected_building=id; view.selected_spell=""; view.target_camera=10; view.follow_front=false','view.selected_building=id; view.selected_spell=""; view.target_camera=sim.slot_anchor(0,0).x; view.follow_front=false')
text=text.replace('纸工运金 → 招募前排 → 解锁后排与法术 → 保护后排推进。','纸工归仓 → 选择路线 → 保护矿路与施工 → 组织兵种交换 → 把握施法窗口。')
text=text.replace('1–5 招募','1–9 招募').replace('[KEY_1,KEY_2,KEY_3,KEY_4,KEY_5]','[KEY_1,KEY_2,KEY_3,KEY_4,KEY_5,KEY_6,KEY_7,KEY_8,KEY_9]')
text=text.replace('recruit_action(db.unit_ids(sim.players[0].faction)[int(event.keycode)-KEY_1])','recruit_action((sim.players[0].roster+["unit."+sim.players[0].faction+".worker"])[int(event.keycode)-KEY_1]) if int(event.keycode)-KEY_1<sim.players[0].roster.size()+1 else null')
text=text.replace('mini(14,int(options.index)+1)','mini(db.campaign.size()-1,int(options.index)+1)').replace('int(options.index)<14','int(options.index)<db.campaign.size()-1')
text=text.replace('三军战役完成 · 返回兵书','十院留名 · 故事终章')
text=text.replace('"纸城已失守。增加纸工、保护后排，或用法术打断敌方推进，再折一局。"','sim.result_reason+"。保护矿路与任务对象，调整部署再战。"')
text=text.replace('var challenge_bonus=""','if victory and mode=="campaign": paragraph(overlay,options.get("story_after",db.story.ending),Rect2(47,444,733,59),18)\n\tvar challenge_bonus=""')
p.write_text(text,encoding='utf-8',newline='\n')
print('Native world UI updated.')
