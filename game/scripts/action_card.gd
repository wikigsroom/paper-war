extends Button
const UI=preload("res://scripts/ui_theme.gd")
signal details_requested

var art: Texture2D
var title: String = ""
var detail: String = ""
var price: String = ""
var locked: bool = false
var cooling: float = 0.0
var cooldown_total: float = 1.0
var selected: bool = false
var affordable: bool = true
var accent: Color = Color("b74532")
var compact_touch: bool = false
var battle_layout: bool = false
var queue_count: int = 0
var production_ratio: float = -1.0
var touch_layout: bool=false
var touch_dense: bool=false
var slim_battle: bool=false
var hold_clock: float=0
var suppress_activation: bool=false

func _ready():
	# All layouts share one paper skin; avoid native Button drawing a second
	# background beneath the custom card text, progress and cost.
	for state in ["normal","hover","pressed","disabled","focus","hover_pressed"]:add_theme_stylebox_override(state,StyleBoxEmpty.new())
	mouse_entered.connect(queue_redraw);mouse_exited.connect(queue_redraw)
	focus_entered.connect(queue_redraw);focus_exited.connect(queue_redraw)
	button_down.connect(queue_redraw);button_up.connect(queue_redraw)
	set_process(false)
	button_down.connect(func():
		if touch_dense:hold_clock=0;suppress_activation=false;set_process(true))
	button_up.connect(func():set_process(false))

func _process(delta):
	if not touch_dense or not is_pressed():set_process(false);return
	hold_clock+=delta
	if hold_clock>=.55:
		suppress_activation=true;set_process(false);details_requested.emit()

func _draw():
	draw_skin()
	if slim_battle:
		draw_slim_card();return
	if touch_layout:
		draw_touch_card();return
	if battle_layout:
		draw_battle_card()
		return
	var ink=UI.INK
	var w=size.x
	if art:
		var icon_size=minf(w-22,60)
		draw_texture_rect(art,Rect2((w-icon_size)*.5,6,icon_size,icon_size),false,Color(1,1,1,.35 if locked else 1))
	var font=get_theme_font("font")
	var title_size=24 if compact_touch else 18
	while title_size>13 and font.get_string_size(title,HORIZONTAL_ALIGNMENT_LEFT,-1,title_size).x>w-10: title_size-=1
	var title_width=font.get_string_size(title,HORIZONTAL_ALIGNMENT_LEFT,-1,title_size).x
	draw_string(font,Vector2(maxf(5,(w-title_width)*.5),91 if compact_touch else 82),title,HORIZONTAL_ALIGNMENT_LEFT,w-10,title_size,Color("746d61") if locked else ink)
	var price_size: int = 24 if compact_touch else 18
	var text_width=font.get_string_size(price,HORIZONTAL_ALIGNMENT_LEFT,-1,price_size).x
	draw_string(font,Vector2((w-text_width)*.5,121 if compact_touch else 104),price,HORIZONTAL_ALIGNMENT_LEFT,-1,price_size,Color("746d61") if locked else (accent if affordable else Color("b74532")))
	if locked:
		draw_circle(Vector2(w-14,14),9,Color("746d61"))
		draw_string(font,Vector2(w-21,19),"锁",HORIZONTAL_ALIGNMENT_LEFT,-1,13,Color("f3ebdd"))
	if cooling>0:
		var ratio=clampf(cooling/maxf(.01,cooldown_total),0,1)
		draw_rect(Rect2(4,5,w-8,63*ratio),Color(.12,.2,.23,.5))
		var seconds=str(int(ceilf(cooling)))
		draw_string(font,Vector2(w*.5-11,49),seconds,HORIZONTAL_ALIGNMENT_LEFT,-1,30,Color("f3ebdd"))
	if selected: draw_rect(Rect2(2,2,w-4,size.y-4),accent,false,3)
	if detail!="": draw_string(font,Vector2(6,15),detail,HORIZONTAL_ALIGNMENT_LEFT,-1,12,Color("746d61"))

func draw_skin():
	var style: StyleBox=UI.surface("button-disabled" if locked else "button-pressed" if is_pressed() else "panel-jade" if selected or is_hovered() else "panel-card",7,0)
	draw_style_box(style,Rect2(Vector2.ZERO,size))
	if selected or has_focus():draw_style_box(UI.focus_box(accent),Rect2(1,1,size.x-2,size.y-2))

func draw_battle_card():
	var ink=UI.INK;var paper=UI.CARD
	var w=size.x;var h=size.y
	var hover: bool = is_hovered() or has_focus()
	var pressed: bool=is_pressed()
	draw_line(Vector2(0,h-3),Vector2(w,h-3),accent if selected or hover else UI.EDGE,3,true)
	var icon: float = 78 if compact_touch else 62
	if art:draw_texture_rect(art,Rect2((w-icon)*.5,5,icon,icon),false,Color(1,1,1,.38 if locked else 1))
	var font=get_theme_font("font")
	var title_size: int = 23 if compact_touch else 18
	while title_size>14 and font.get_string_size(title,HORIZONTAL_ALIGNMENT_LEFT,-1,title_size).x>w-10:title_size-=1
	var title_width: float = font.get_string_size(title,HORIZONTAL_ALIGNMENT_LEFT,-1,title_size).x
	draw_string(font,Vector2((w-title_width)*.5,h-30),title,HORIZONTAL_ALIGNMENT_LEFT,-1,title_size,UI.MUTED if locked else paper if pressed else ink)
	var price_size: int = 23 if compact_touch else 18
	var price_width: float = font.get_string_size(price,HORIZONTAL_ALIGNMENT_LEFT,-1,price_size).x
	draw_string(font,Vector2((w-price_width)*.5,h-8),price,HORIZONTAL_ALIGNMENT_LEFT,-1,price_size,UI.MUTED if locked else paper if pressed else UI.GOLD if affordable and not selected else accent if affordable else UI.SEAL)
	if locked:
		draw_string(font,Vector2(w-23,22),"锁",HORIZONTAL_ALIGNMENT_LEFT,-1,16,ink)
	elif queue_count>0:
		draw_circle(Vector2(w-16,16),12,accent)
		draw_string(font,Vector2(w-21,22),str(queue_count),HORIZONTAL_ALIGNMENT_LEFT,-1,16,paper)
	if cooling>0:
		var ratio: float = clampf(cooling/maxf(.01,cooldown_total),0,1)
		draw_rect(Rect2(4,4,w-8,icon*ratio),Color(.16,.15,.21,.52))
		draw_string(font,Vector2(w*.5-10,icon*.65),str(int(ceilf(cooling))),HORIZONTAL_ALIGNMENT_LEFT,-1,28,paper)
	if selected:draw_rect(Rect2(1,1,w-2,h-4),accent,false,3)
	if production_ratio>=0:
		draw_rect(Rect2(0,h-5,w,3),Color(ink,.24))
		draw_rect(Rect2(0,h-5,w*clampf(production_ratio,0,1),3),UI.JADE)
	if detail!="" and not compact_touch:draw_string(font,Vector2(5,16),detail,HORIZONTAL_ALIGNMENT_LEFT,-1,12,Color("8e826b"))

func draw_slim_card():
	var w: float=size.x;var h: float=size.y;var font: Font=get_theme_font("font")
	var paper: Color=UI.DISABLED if locked else UI.INK if is_pressed() else UI.PAPER if is_hovered() else UI.CARD
	var ink: Color=UI.MUTED if locked else UI.CARD if is_pressed() else UI.INK
	var icon: float=24 if touch_layout else 42
	if art:draw_texture_rect(art,Rect2((w-icon)*.5,1,icon,icon),false,Color(1,1,1,.4 if locked else 1))
	var copy: String=title.right(2) if touch_layout else title
	var fs: int=11 if touch_layout else 15
	while fs>10 and font.get_string_size(copy,HORIZONTAL_ALIGNMENT_LEFT,-1,fs).x>w-8:fs-=1
	draw_string(font,Vector2((w-font.get_string_size(copy,HORIZONTAL_ALIGNMENT_LEFT,-1,fs).x)*.5,h-15 if touch_layout else h-22),copy,HORIZONTAL_ALIGNMENT_LEFT,w-8,fs,ink)
	var cost: String=price.replace(" 金","").replace(" 法","") if touch_layout else price
	var pf: int=12 if touch_layout else 16
	draw_string(font,Vector2((w-font.get_string_size(cost,HORIZONTAL_ALIGNMENT_LEFT,-1,pf).x)*.5,h-2 if touch_layout else h-3),cost,HORIZONTAL_ALIGNMENT_LEFT,w-8,pf,UI.MUTED if locked else UI.CARD if is_pressed() else accent if affordable else UI.SEAL)
	if not touch_layout and not detail.is_empty():draw_string(font,Vector2(4,14),detail,HORIZONTAL_ALIGNMENT_LEFT,-1,11,UI.MUTED)
	if locked:draw_texture_rect(UI.art("icon-lock"),Rect2(w-14,1,12,12),false)
	elif queue_count>0:
		draw_texture_rect(UI.art("icon-seal"),Rect2(w-16,0,16,16),false);draw_string(font,Vector2(w-11,12),str(queue_count),HORIZONTAL_ALIGNMENT_LEFT,-1,10,UI.CARD)
	if cooling>0:
		draw_rect(Rect2(2,2,w-4,icon*clampf(cooling/maxf(.01,cooldown_total),0,1)),Color(UI.INK,.45))
		draw_rect(Rect2(w-22,1,21,15),UI.INK)
		draw_string(font,Vector2(w-21,13),str(int(ceilf(cooling))),HORIZONTAL_ALIGNMENT_LEFT,-1,11,UI.CARD)
	if production_ratio>=0:draw_rect(Rect2(0,h-2,w*clampf(production_ratio,0,1),2),UI.JADE)

func draw_touch_card():
	var w=size.x;var h=size.y;var font=get_theme_font("font")
	var paper: Color=UI.DISABLED if locked else UI.INK if is_pressed() else UI.PAPER if is_hovered() else UI.CARD
	var icon: float=minf(32,maxf(12,h-44)) if touch_dense else 48
	var pos: Vector2=Vector2((w-icon)*.5,3) if touch_dense else Vector2(8,(h-icon)*.5)
	if art:draw_texture_rect(art,Rect2(pos,Vector2.ONE*icon),false,Color(1,1,1,.4 if locked else 1))
	var ink: Color=UI.MUTED if locked else UI.CARD if is_pressed() else UI.INK
	var copy: String=title;var fs: int=14 if touch_dense else 16
	var available: float=w-8 if touch_dense else w-72
	while copy.length()>1 and font.get_string_size(copy,HORIZONTAL_ALIGNMENT_LEFT,-1,fs).x>available:copy=copy.left(copy.length()-1)
	var tx: float=maxf(4,(w-font.get_string_size(copy,HORIZONTAL_ALIGNMENT_LEFT,-1,fs).x)*.5) if touch_dense else 64
	draw_string(font,Vector2(tx,h-20 if touch_dense else h*.5-4),copy,HORIZONTAL_ALIGNMENT_LEFT,available,fs,ink)
	var px: float=(w-font.get_string_size(price,HORIZONTAL_ALIGNMENT_LEFT,-1,14).x)*.5 if touch_dense else 64
	draw_string(font,Vector2(maxf(4,px),h-5 if touch_dense else h*.5+21),price,HORIZONTAL_ALIGNMENT_LEFT,w-8 if touch_dense else w-72,14,UI.MUTED if locked else UI.CARD if is_pressed() else UI.GOLD if affordable else UI.SEAL)
	if locked:draw_string(font,Vector2(w-20,18),"锁",HORIZONTAL_ALIGNMENT_LEFT,-1,14,ink)
	elif queue_count>0:
		draw_circle(Vector2(w-12,12),10,accent);draw_string(font,Vector2(w-16,17),str(queue_count),HORIZONTAL_ALIGNMENT_LEFT,-1,13,UI.CARD)
	if cooling>0:
		draw_rect(Rect2(2,2,w-4,(16 if touch_dense else 32)*clampf(cooling/maxf(.01,cooldown_total),0,1)),Color(UI.INK,.5))
		draw_rect(Rect2(w-25,2,23,16),UI.INK)
		draw_string(font,Vector2(w-23,15),str(int(ceilf(cooling))),HORIZONTAL_ALIGNMENT_LEFT,-1,13,UI.CARD)
	if production_ratio>=0:draw_rect(Rect2(0,h-3,w*clampf(production_ratio,0,1),3),UI.JADE)
