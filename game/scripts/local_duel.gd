extends Control
const Simulation=preload("res://scripts/battle_sim.gd")
const View=preload("res://scripts/battle_view.gd")
const Card=preload("res://scripts/action_card.gd")
const MiniMap=preload("res://scripts/theatre_minimap.gd")
const PaperPanel=preload("res://scripts/paper_panel.gd")
const StripScroll=preload("res://scripts/duel_scroll.gd")
const FocusScope=preload("res://scripts/ui_focus_scope.gd")
const BattleSheets=preload("res://scripts/ui_battle_sheets.gd")
signal exit_requested
var db
var sim
var panels: Array=[]
var halted: bool=false
var clock: Label
var accumulator: float=0
var setup: Dictionary
var audio
var controlled_side: int=-1
var command_sender: Callable
var external_driver: bool=false
var network_status: String=""
func _exit_tree():
	release_sheets()

func release_sheets():
	# Queue factories capture the per-side dictionary. Break its ownership cycle
	# when leaving a match, including network disconnect and scene replacement.
	for p in panels:
		if p.is_empty():continue
		p["battle_sheet"]=null
		if p.get("focus_scope")!=null:p.focus_scope.release(false)

func initialize_network(data,battle,side: int,sender: Callable):
	db=data;sim=battle;controlled_side=side;command_sender=sender;external_driver=true
	build()

func initialize(data,options: Dictionary,sound=null):
	audio=sound
	db=data;setup=options.duplicate(true)
	sim=Simulation.new(db);sim.start(setup);sim.ai_enabled=[false,false]
	build()

func button(parent: Control,caption: String,rect: Rect2,action: Callable) -> Button:
	var b=Button.new();b.text=caption;b.position=rect.position;b.size=rect.size
	b.add_theme_font_size_override("font_size",14);b.pressed.connect(action);parent.add_child(b);return b

func build():
	release_sheets()
	for child in get_children():child.hide();child.queue_free()
	panels.clear()
	panels=[{},{}]
	var w: float=size.x;var h: float=size.y
	var short_header: bool=external_driver and h<320
	var heading: float=0 if external_driver else 48
	var panel_width: int=int(w if controlled_side>=0 else (w-12)*.5);var panel_height: int=int(h-heading)
	for side in range(2):
		if controlled_side>=0 and side!=controlled_side:continue
		var container=SubViewportContainer.new();container.position=Vector2(0 if controlled_side>=0 else side*(panel_width+12),heading);container.size=Vector2(panel_width,panel_height);container.stretch=false;add_child(container)
		var viewport=SubViewport.new();viewport.size=Vector2i(panel_width,panel_height);viewport.render_target_update_mode=SubViewport.UPDATE_ALWAYS;container.add_child(viewport)
		var root_control=Control.new();root_control.size=Vector2(panel_width,panel_height);root_control.theme=theme;viewport.add_child(root_control)
		var view=View.new();view.db=db;view.player_side=side;view.mobile_ui=true;view.particle_budget=180;root_control.add_child(view);view.reset(sim)
		var stage=Rect2(0,0 if short_header else 24,panel_width,panel_height-52-(0 if short_header else 24))
		var bounds: Rect2=sim.map.bounds
		var tallest: float=310
		for p in sim.players:
			for id in p.get("roster",[]):tallest=maxf(tallest,float(db.assets[id].world_height)*view.PX*view.PUPPET_SCALE)
		var earth_depth: float=maxf(28,stage.size.y*.14)
		var zoom: float=minf(.85,maxf(1,stage.size.y-earth_depth-36)/(tallest+bounds.size.y*view.PY))
		view.scale=Vector2.ONE*zoom;view.width=panel_width/zoom;view.height=panel_height/zoom
		view.mobile_playfield=Rect2(stage.position/zoom,stage.size/zoom);view.mobile_floor=view.mobile_playfield.end.y-bounds.end.y*view.PY-earth_depth/zoom
		view.camera_x=sim.bases[side].x;view.target_camera=view.camera_x
		view.mobile_minimap=Rect2() if short_header else Rect2(Vector2(panel_width-(152 if external_driver else 96),0)/zoom,Vector2(96,48)/zoom)
		var hud=Control.new();hud.mouse_filter=Control.MOUSE_FILTER_IGNORE;hud.size=root_control.size;root_control.add_child(hud)
		var rails: Array=[]
		for rect in [Rect2(0,0,minf(288,panel_width) if short_header else panel_width,24),Rect2(0,panel_height-52,panel_width,52)]:
			var rail=PaperPanel.new();rail.position=rect.position;rail.size=rect.size;rail.mouse_filter=Control.MOUSE_FILTER_IGNORE;hud.add_child(rail)
			rails.append(rail)
		var minimap=MiniMap.new();minimap.view=view;minimap.scale=view.scale;minimap.size=root_control.size/view.scale;minimap.mouse_filter=Control.MOUSE_FILTER_IGNORE;hud.add_child(minimap)
		var status=Label.new();status.position=Vector2(4,0);status.size=Vector2(176 if external_driver else panel_width-104,24);status.clip_text=true;status.mouse_filter=Control.MOUSE_FILTER_IGNORE;status.add_theme_font_size_override("font_size",14);hud.add_child(status)
		var panel={"side":side,"container":container,"viewport":viewport,"root":root_control,"rails":rails,"view":view,"stage":stage,"status":status,"cards":{},"spells":{},"overlay":null,"message":"","message_left":0.0,"finger":-1,"pressed":false,"origin":Vector2.ZERO,"camera_start":view.camera_x,"dragged":false}
		panels[side]=panel
		panel["focus_scope"]=FocusScope.new()
		var ids: Array=sim.production_ids(side)
		var spells: Array=db.spell_ids(sim.players[side].faction)
		var card_width: float=56 if panel_width>=640 else 48
		var spell_bank: float=spells.size()*card_width+(spells.size()-1)*8
		var recruit_width: float=panel_width-spell_bank-64
		var sc=StripScroll.new();sc.name="RecruitScroll";sc.horizontal=true;sc.position=Vector2(0,panel_height-48);sc.size=Vector2(recruit_width,48);sc.clip_contents=true
		sc.horizontal_scroll_mode=ScrollContainer.SCROLL_MODE_SHOW_NEVER;sc.vertical_scroll_mode=ScrollContainer.SCROLL_MODE_DISABLED;sc.block_input=func():return halted or is_instance_valid(panel.overlay)
		hud.add_child(sc);panel["recruit_scroll"]=sc
		var recruits=HBoxContainer.new();recruits.add_theme_constant_override("separation",8);sc.add_child(recruits)
		for i in range(ids.size()):
			var id: String=ids[i];var c=Card.new();c.title=db.name_of(id);c.art=db.art(id);c.touch_layout=true;c.touch_dense=true;c.slim_battle=true
			c.custom_minimum_size=Vector2(card_width,48);c.size=Vector2(card_width,48);recruits.add_child(c);panel.cards[id]=c
			c.tooltip_text=c.title+"\n"+db.unit_hint(id)
			c.details_requested.connect(func():open_sheet(side,"info",id))
			c.pressed.connect(func():
				if not c.suppress_activation:issue(side,"recruit",{"id":id}))
		for i in range(spells.size()):
			var id: String=spells[i];var c=Card.new();c.title=db.name_of(id);c.art=db.art(id);c.touch_layout=true;c.touch_dense=true;c.slim_battle=true
			c.position=Vector2(recruit_width+8+i*(card_width+8),panel_height-48);c.size=Vector2(card_width,48);hud.add_child(c);panel.spells[id]=c
			c.tooltip_text=c.title+"\n"+db.spell_hint(id)
			c.details_requested.connect(func():open_sheet(side,"info",id))
			c.pressed.connect(func():
				if not c.suppress_activation:view.selected_spell=id;close_sheet(side))
		panel["orders"]=button(hud,"军令",Rect2(panel_width-48,panel_height-48,48,48),func():
			if view.selected_spell!="":view.selected_spell=""
			else:open_sheet(side,"orders"))
		root_control.gui_input.connect(func(e):field_input(side,e))
	if external_driver and not short_header:
		button(self,"返回",Rect2(w-48,0,48,48),func():exit_requested.emit())
	elif not external_driver:
		button(self,"返回选局",Rect2(0,0,120,48),func():exit_requested.emit())
		button(self,"暂停 / 继续",Rect2(128,0,132,48),func():set_paused(not halted))
	clock=Label.new();clock.mouse_filter=Control.MOUSE_FILTER_IGNORE;clock.position=Vector2(184 if external_driver else 276,0 if external_driver else 8);clock.size=Vector2(maxf(0,w-(344 if external_driver else 276)),24 if external_driver else 36);clock.clip_text=true;clock.add_theme_font_size_override("font_size",12 if external_driver else 20);add_child(clock)
	if short_header:clock.size.x=104

func issue(side: int,kind: String,args: Dictionary) -> Dictionary:
	if halted or sim.winner!=-2:return {"ok":false,"error":"对局已暂停或结束"}
	if external_driver:
		if side!=controlled_side:return {"ok":false,"error":"不是己方操作面板"}
		command_sender.call(kind,args)
		panels[side].message="指令已提交";panels[side].message_left=2
		return {"ok":true,"error":""}
	var result: Dictionary=sim.request(side,kind,args)
	panels[side].message="已执行" if result.ok else result.error;panels[side].message_left=2.0
	return result

func set_paused(value: bool):
	halted=value;accumulator=0
	if not value:return
	for p in panels:
		if p.is_empty():continue
		p.pressed=false;p.finger=-1;p.view.mobile_pointer_active=false
		for card in p.cards.values()+p.spells.values():card.set_pressed_no_signal(false)
		p.recruit_scroll.touch_finger=-1;p.recruit_scroll.dragging=false;p.recruit_scroll.velocity=0;p.recruit_scroll.set_process(false)

func sheet_action(parent: Node,caption: String,callback: Callable) -> Button:
	var b=Button.new();b.text=caption;b.clip_text=true;b.text_overrun_behavior=TextServer.OVERRUN_TRIM_ELLIPSIS;b.tooltip_text=caption;b.accessibility_name=caption
	preload("res://scripts/ui_theme.gd").decorate(b,caption)
	b.custom_minimum_size=Vector2(48,48);b.size_flags_horizontal=Control.SIZE_EXPAND_FILL;b.add_theme_font_size_override("font_size",14);parent.add_child(b);b.pressed.connect(callback);return b

func close_sheet(side: int,restore_focus: bool=true):
	var p: Dictionary=panels[side]
	if is_instance_valid(p.overlay):p.overlay.hide();p.overlay.queue_free()
	p.overlay=null
	p["battle_sheet"]=null
	if restore_focus:p.focus_scope.release()

func open_sheet(side: int,kind: String,asset_id: String=""):
	if halted or sim.winner!=-2:return
	close_sheet(side,false)
	var p: Dictionary=panels[side];var player: Dictionary=sim.players[side]
	p.focus_scope.capture(p.root)
	p["sheet_kind"]=kind
	var overlay=PaperPanel.new();overlay.position=Vector2(8,32);overlay.size=Vector2(p.viewport.size.x-16,p.viewport.size.y-40);p.root.add_child(overlay);p.overlay=overlay
	p.focus_scope.enter.call_deferred(overlay)
	button(overlay,"返回战场",Rect2(8,8,overlay.size.x-16,48),func():close_sheet(side))
	var scroll=StripScroll.new();scroll.position=Vector2(8,64);scroll.size=Vector2(overlay.size.x-16,overlay.size.y-72);scroll.follow_focus=true;scroll.horizontal_scroll_mode=ScrollContainer.SCROLL_MODE_DISABLED;scroll.vertical_scroll_mode=ScrollContainer.SCROLL_MODE_SHOW_NEVER
	scroll.block_input=func():return halted
	overlay.add_child(scroll)
	var list=VBoxContainer.new();list.add_theme_constant_override("separation",8);list.size_flags_horizontal=Control.SIZE_EXPAND_FILL;scroll.add_child(list)
	p["battle_sheet"]=BattleSheets.new()
	match kind:
		"orders":
			var copy=Label.new();copy.add_theme_font_size_override("font_size",14);copy.mouse_filter=Control.MOUSE_FILTER_IGNORE;list.add_child(copy)
			p.battle_sheet.summary=copy;p.battle_sheet.summary_side=true
			if p.message_left>0:
				var notice=Label.new();notice.text=p.message;notice.autowrap_mode=TextServer.AUTOWRAP_WORD_SMART;notice.size_flags_horizontal=Control.SIZE_EXPAND_FILL;list.add_child(notice)
			var study=Label.new();study.autowrap_mode=TextServer.AUTOWRAP_WORD_SMART;study.size_flags_horizontal=Control.SIZE_EXPAND_FILL;list.add_child(study);p.battle_sheet.study=study
			for entry in [["研究科技","research"],["建造塔灯","build"],["招募队列","queue"]]:sheet_action(list,entry[0],open_sheet.bind(side,str(entry[1])))
			sheet_action(list,"返回纸城",func():view_home(side);close_sheet(side))
			sheet_action(list,"追踪交锋",func():p.view.target_camera=sim.front(side);p.view.follow_front=true;close_sheet(side))
			sheet_action(list,"取消当前选择",func():p.view.selected_spell="";close_sheet(side))
			if external_driver:sheet_action(list,"返回选局",func():exit_requested.emit())
		"info":
			var copy=Label.new();copy.text=db.name_of(asset_id)+"\n"+(db.unit_hint(asset_id) if asset_id.begins_with("unit.") else db.spell_hint(asset_id));copy.autowrap_mode=TextServer.AUTOWRAP_WORD_SMART;copy.size_flags_horizontal=Control.SIZE_EXPAND_FILL;list.add_child(copy)
		"research":
			for node in db.technology.nodes:
				if node.faction!=player.faction:continue
				if node.grant.begins_with("unit.") and not player.roster.has(node.grant):continue
				var b=sheet_action(list,"",func():
					issue(side,"research",{"id":node.id})
					if p.battle_sheet!=null:p.battle_sheet.refresh(sim,side,halted))
				b.custom_minimum_size.y=64;p.battle_sheet.research_buttons[node.id]=b
		"build":
			for slot in range(sim.side_sites(side).size()):
				var site: Dictionary=sim.slot_anchor(side,slot)
				for tail in site.get("types",["tower","mana"]):
					var id: String="building."+player.faction+"."+str(tail)
					var b=sheet_action(list,"",func():
						issue(side,"build",{"id":id,"slot":slot})
						if p.battle_sheet!=null:p.battle_sheet.refresh(sim,side,halted))
					b.custom_minimum_size.y=64;p.battle_sheet.bind_build(b,id,slot)
		"queue":
			var rows=VBoxContainer.new();rows.add_theme_constant_override("separation",8);rows.size_flags_horizontal=Control.SIZE_EXPAND_FILL;list.add_child(rows)
			var empty=Label.new();empty.text="当前没有正在生产的单位。";empty.mouse_filter=Control.MOUSE_FILTER_IGNORE;empty.autowrap_mode=TextServer.AUTOWRAP_WORD_SMART;list.add_child(empty)
			p.battle_sheet.bind_queue(func(i: int,id: String,revision: int):
				var b=sheet_action(rows,"",func():
					issue(side,"cancel_queue",{"index":i,"id":id,"queue_revision":revision})
					if p.battle_sheet!=null:p.battle_sheet.refresh(sim,side,halted))
				b.custom_minimum_size.y=64;return b,empty)
	p.battle_sheet.refresh(sim,side,halted)
	p["sheet_clock"]=0.0

func view_home(side: int):
	panels[side].view.target_camera=sim.bases[side].x;panels[side].view.follow_front=false

func field_input(side: int,event: InputEvent):
	var p: Dictionary=panels[side];var view=p.view
	if is_instance_valid(p.overlay) or halted or sim.winner!=-2:return
	var position: Vector2
	var down: bool=false;var up: bool=false;var moving: bool=false
	if event is InputEventMouseButton and event.button_index==MOUSE_BUTTON_LEFT:
		position=event.position;down=event.pressed;up=not event.pressed
	elif event is InputEventMouseMotion:position=event.position;moving=true
	elif event is InputEventScreenTouch:
		position=event.position;down=event.pressed;up=not event.pressed
		if down:
			if p.finger!=-1:return
			p.finger=event.index
		elif p.finger!=event.index:return
		if event.canceled:p.pressed=false;p.finger=-1;return
	elif event is InputEventScreenDrag:
		if p.finger!=event.index:return
		position=event.position;moving=true
	else:return
	view.pointer=position/view.scale;view.mobile_pointer_active=true
	if down:
		if view.minimap_rect().has_point(position/view.scale):
			var rect: Rect2=view.minimap_rect();view.target_camera=(position.x/view.scale.x-rect.position.x)/rect.size.x*sim.map.length;view.follow_front=false
			p.pressed=false;p.finger=-1;return
		if not p.stage.has_point(position):return
		p.pressed=true;p.origin=position;p.camera_start=view.camera_x;p.dragged=false
	elif moving and p.pressed:
		if position.distance_to(p.origin)>12:p.dragged=true;view.follow_front=false;view.target_camera=p.camera_start-(position.x-p.origin.x)/view.scale.x/view.PX
	elif up:
		p.finger=-1
		if not p.pressed:return
		p.pressed=false
		if not p.dragged:tap_field(side,position/view.scale)

func tap_field(side: int,position: Vector2):
	var p: Dictionary=panels[side];var view=p.view
	if view.selected_spell!="":
		var target: int=view.target_at(position);var anchor: Dictionary=view.screen_to_ground(position)
		var actor: Dictionary=sim.actor(target)
		if not actor.is_empty():anchor=sim.physical_anchor(actor)
		if issue(side,"cast",{"id":view.selected_spell,"target":target,"x":anchor.x,"y":anchor.y}).ok:view.selected_spell=""
		return
	for fork in sim.map.fork_nodes(side):
		var marker: Rect2=view.route_sign_rect(side,fork)
		if marker.has_area() and marker.has_point(position):
			var exits: Array=sim.map.outgoing[fork.node] if side==0 else sim.map.incoming[fork.node]
			issue(side,"route",{"node":fork.node,"edge":exits[(exits.find(sim.map.choices[side][fork.node])+1)%exits.size()]});return
	for mine in sim.map.definition.mines:
		if int(mine.owner)==side and (view.point_to_screen(mine.x,mine.y)+Vector2(0,-22)).distance_to(position)<32/view.scale.x:
			issue(side,"mine_priority",{"mine":mine.id});return
	view.selected_uid=view.target_at(position)

func consume_event(side: int,event: Dictionary):
	if not sim.event_visible(side,event) or panels[side].is_empty():return
	var panel: Dictionary=panels[side]
	panel.view.on_event(event)
	if event.kind=="research_done" and int(event.side)==side:
		panel.message=db.research_notice(event)
		panel.message_left=3.0
	if event.kind=="economy_alarm":
		panel.message="纸工遇袭 · 查看小地图红圈，施法并补充前排"
		panel.message_left=4.0

func _process(delta: float):
	if sim==null:return
	if not external_driver and not halted and sim.winner==-2:
		accumulator+=minf(delta,.15)
		while accumulator>=1.0/60.0:sim.tick(1.0/60.0);accumulator-=1.0/60.0
		for event in sim.drain_events():
			for p in panels:consume_event(int(p.side),event)
			if audio!=null:
				for p in panels:
					if sim.event_visible(p.side,event):audio.battle_event(event,p.view.camera_x);break
	clock.text=("联机对弈" if external_driver else "双人对弈")+" · %.0f秒"%sim.time if sim.winner==-2 else "平局" if sim.winner==-1 else "玩家%d获胜"%(sim.winner+1)
	if not network_status.is_empty():clock.text=network_status
	for p in panels:
		if p.is_empty():continue
		var player: Dictionary=sim.players[p.side]
		p.message_left=maxf(0,p.message_left-delta)
		if is_instance_valid(p.overlay) and p.get("battle_sheet")!=null:
			p["sheet_clock"]=float(p.get("sheet_clock",0))+delta
			if delta==0 or p.sheet_clock>=.1:p.sheet_clock=0;p.battle_sheet.refresh(sim,int(p.side),halted)
		p.status.text="玩家%d 金%d · 法%d"%[p.side+1,player.gold,player.mana]
		p.status.tooltip_text=p.message if p.message_left>0 else "城%d · 兵%d · 工%d · 队%d"%[sim.bases[p.side].hp,sim.population(p.side,false,false),sim.population(p.side,true,false),player.queue.size()]
		if p.message_left>0:
			if external_driver:clock.text=p.message
			else:p.status.text=p.message
		p.orders.text="取消" if p.view.selected_spell!="" else "军令"
		for id in p.cards:
			var c=p.cards[id];c.disabled=halted or sim.winner!=-2;c.locked=not player.unlocked.has(id);c.price="%d金"%db.balance.units[id].gold;c.affordable=player.gold>=float(db.balance.units[id].gold);c.queue_count=player.queue.count(id);c.queue_redraw()
			c.production_ratio=-1.0 if player.queue.is_empty() or player.queue[0]!=id else player.production/float(db.balance.units[id].get("production_seconds",2))
		for id in p.spells:
			var c=p.spells[id];c.disabled=halted or sim.winner!=-2;c.locked=not player.unlocked.has(id);c.price="%d法"%db.balance.spells[id].mana;c.affordable=player.mana>=float(db.balance.spells[id].mana);c.cooling=player.cooldowns.get(id,0);c.cooldown_total=db.balance.spells[id].cooldown;c.selected=p.view.selected_spell==id;c.queue_redraw()
		p.view.update(delta,halted or sim.winner!=-2)
