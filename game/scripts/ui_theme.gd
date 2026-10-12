extends RefCounted
# Live text and hit targets. Generated paper provides only the skin.
const PAPER=Color("f6edda")
const CARD=Color("fff8e9")
const INK=Color("24343c")
const MUTED=Color("615b50")
const EDGE=Color("c4b294")
const CONTROL_EDGE=Color("978b73")
const SEAL=Color("a83c35")
const GOLD=Color("92682a")
const JADE=Color("31747c")
const DISABLED=Color("ddd4c2")
static var textures: Dictionary={}
static var surfaces: Dictionary={}

static func art(name: String) -> Texture2D:
	if not textures.has(name):textures[name]=load("res://assets/ui/paper/"+name+".png")
	return textures[name]

static func paper_box(color: Color,border: Color,radius: int=4) -> StyleBoxFlat:
	var style=StyleBoxFlat.new();style.bg_color=color;style.border_color=border
	style.set_border_width_all(1);style.set_corner_radius_all(radius)
	style.content_margin_left=16;style.content_margin_right=16;style.content_margin_top=8;style.content_margin_bottom=8
	style.shadow_color=Color(INK,.16);style.shadow_size=4;style.shadow_offset=Vector2(0,3)
	return style

static func surface(name: String,edge: float=12,margin: float=8) -> StyleBoxTexture:
	var key: String=name+":"+str(edge)+":"+str(margin)
	if not surfaces.has(key):
		var style=StyleBoxTexture.new();style.texture=art(name)
		for side in [SIDE_LEFT,SIDE_TOP,SIDE_RIGHT,SIDE_BOTTOM]:
			style.set_texture_margin(side,12);style.set_expand_margin(side,0)
			style.set_content_margin(side,margin if side in [SIDE_LEFT,SIDE_RIGHT] else minf(6,margin))
		style.axis_stretch_horizontal=StyleBoxTexture.AXIS_STRETCH_MODE_STRETCH
		style.axis_stretch_vertical=StyleBoxTexture.AXIS_STRETCH_MODE_STRETCH
		surfaces[key]=style
	return surfaces[key]

static func focus_box(color: Color=JADE) -> StyleBoxFlat:
	var focus=paper_box(Color(0,0,0,0),color,0);focus.set_border_width_all(2);focus.shadow_size=0
	focus.content_margin_left=0;focus.content_margin_right=0;focus.content_margin_top=0;focus.content_margin_bottom=0
	return focus

static func primary(button: Button):
	if button.icon==art("icon-flag"):button.icon=art("icon-flag-light")
	button.add_theme_stylebox_override("normal",surface("button-primary"))
	var hover=surface("button-primary").duplicate();hover.modulate_color=Color(1.12,1.08,1.05)
	button.add_theme_stylebox_override("hover",hover)
	button.add_theme_stylebox_override("pressed",surface("button-primary-pressed"))
	button.add_theme_stylebox_override("focus",focus_box(GOLD))
	for state in ["font_color","font_hover_color","font_pressed_color","font_focus_color"]:button.add_theme_color_override(state,CARD)
	button.add_theme_color_override("font_disabled_color",MUTED)

static func mark_selected(button: Button,selected: bool):
	button.add_theme_stylebox_override("normal",surface("button-selected" if selected else "button-normal"))
	button.add_theme_stylebox_override("hover",surface("button-selected" if selected else "button-hover"))
	for state in ["font_color","font_focus_color","font_hover_color"]:button.add_theme_color_override(state,CARD if selected else INK)

static func decorate(button: Button,caption: String):
	var key: String=""
	if caption.begins_with("继续战役") or caption in ["展开战场","展开纸场","线性战役","新战役"]:key="flag"
	elif caption=="成就挑战":key="victory"
	elif caption in ["兵书","操作帮助","部署编组"]:key="scroll"
	elif caption in ["设置","调整设置"]:key="settings"
	elif caption in ["保存部署","保存并返回"]:key="check"
	elif caption in ["研究科技"]:key="seal"
	elif caption in ["建造塔灯"]:key="tower"
	elif caption in ["招募队列"]:key="hourglass"
	elif caption in ["返回","返回纸城","返回战场"]:key="back"
	elif caption in ["关闭","取消当前选择"]:key="close"
	elif caption in ["暂停对战"]:key="pause"
	if not key.is_empty():
		button.icon=art("icon-"+key);button.expand_icon=true
		button.add_theme_constant_override("icon_max_width",22);button.add_theme_constant_override("h_separation",10)

static func make(font: Font) -> Theme:
	var theme=Theme.new();theme.default_font=font;theme.default_font_size=22
	for type in ["Label","Button","OptionButton","PopupMenu","CheckButton","CheckBox","TooltipLabel","LineEdit","SpinBox"]:theme.set_color("font_color",type,INK)
	for type in ["Button","OptionButton"]:
		for state in ["normal","hover","pressed","disabled"]:theme.set_stylebox(state,type,surface("button-"+state))
		var hover_pressed=surface("button-pressed").duplicate();hover_pressed.modulate_color=Color(1.1,1.1,1.1)
		theme.set_stylebox("hover_pressed",type,hover_pressed);theme.set_stylebox("focus",type,focus_box())
		theme.set_color("font_hover_color",type,INK);theme.set_color("font_focus_color",type,INK)
		theme.set_color("font_pressed_color",type,CARD);theme.set_color("font_hover_pressed_color",type,CARD)
		theme.set_color("font_disabled_color",type,MUTED);theme.set_constant("outline_size",type,0);theme.set_constant("h_separation",type,8)
	theme.set_icon("arrow","OptionButton",art("arrow-down"));theme.set_constant("arrow_margin","OptionButton",10)
	for type in ["Panel","PanelContainer","PopupMenu","TooltipPanel"]:theme.set_stylebox("panel",type,surface("panel-ledger",10,16))
	theme.set_stylebox("hover","PopupMenu",surface("button-hover",8,6))
	theme.set_color("font_hover_color","PopupMenu",INK);theme.set_color("font_disabled_color","PopupMenu",MUTED);theme.set_constant("v_separation","PopupMenu",16)
	for type in ["CheckButton","CheckBox"]:
		for state in ["normal","hover","pressed","disabled","hover_pressed"]:theme.set_stylebox(state,type,StyleBoxEmpty.new())
		theme.set_stylebox("focus",type,focus_box());theme.set_color("font_hover_color",type,INK);theme.set_color("font_pressed_color",type,INK);theme.set_constant("h_separation",type,12)
		for checked in [true,false]:
			var key: String="on" if checked else "off"
			var icon_key: String="checked" if checked else "unchecked"
			theme.set_icon(icon_key,type,art("toggle-"+key));theme.set_icon(icon_key+"_disabled",type,art("toggle-"+key+"-disabled"))
			theme.set_icon(icon_key+"_mirrored",type,art("toggle-"+key));theme.set_icon(icon_key+"_disabled_mirrored",type,art("toggle-"+key+"-disabled"))
	for type in ["HSlider","VSlider"]:
		var track=paper_box(DISABLED,EDGE,0);track.shadow_size=0;track.set_content_margin_all(3)
		var fill=paper_box(JADE,JADE,0);fill.shadow_size=0;fill.set_content_margin_all(3)
		theme.set_stylebox("slider",type,track)
		for state in ["grabber_area","grabber_area_highlight"]:theme.set_stylebox(state,type,fill)
		for state in ["grabber","grabber_highlight","grabber_disabled"]:theme.set_icon(state,type,art("slider-thumb-hover" if state=="grabber_highlight" else "slider-thumb"))
	for type in ["HScrollBar","VScrollBar"]:
		var track=paper_box(DISABLED,EDGE,0);track.shadow_size=0;track.set_content_margin_all(3)
		var fill=paper_box(JADE,JADE,0);fill.shadow_size=0;fill.set_content_margin_all(3)
		theme.set_stylebox("scroll",type,track)
		for state in ["grabber","grabber_highlight","grabber_pressed"]:theme.set_stylebox(state,type,fill)
		theme.set_icon("increment",type,art("arrow-right" if type=="HScrollBar" else "arrow-down"));theme.set_icon("decrement",type,art("icon-back" if type=="HScrollBar" else "arrow-up"))
	theme.set_stylebox("normal","LineEdit",surface("button-normal"));theme.set_stylebox("focus","LineEdit",focus_box())
	theme.set_color("caret_color","LineEdit",JADE);theme.set_color("selection_color","LineEdit",JADE);theme.set_color("font_selected_color","LineEdit",CARD)
	theme.set_stylebox("background","ProgressBar",surface("button-disabled",3,0));theme.set_stylebox("fill","ProgressBar",surface("button-selected",3,0))
	theme.set_font_size("font_size","TooltipLabel",19)
	return theme

static func make_mobile(font: Font) -> Theme:
	var theme=make(font);theme.default_font_size=16
	for type in ["Button","OptionButton","CheckButton","CheckBox"]:theme.set_font_size("font_size",type,18)
	for type in ["Button","OptionButton"]:
		for state in ["normal","hover","pressed","disabled","focus","hover_pressed"]:
			var style=theme.get_stylebox(state,type).duplicate()
			style.content_margin_left=6;style.content_margin_right=6;style.content_margin_top=4;style.content_margin_bottom=4
			theme.set_stylebox(state,type,style)
	theme.set_constant("v_separation","PopupMenu",26)
	return theme
