extends HSlider
# Keep native Range signals, keyboard and mouse behavior. Godot's HSlider in
# this build needs an explicit ScreenTouch adapter, unlike its BaseButton.
const UI=preload("res://scripts/ui_theme.gd")
var touch_finger: int=-1

func _ready():value_changed.connect(func(_value):queue_redraw())

func set_touch_value(point: Vector2):
	value=min_value+clampf((point.x-12)/maxf(1,size.x-24),0,1)*(max_value-min_value)

func _gui_input(event):
	if event is InputEventScreenTouch and event.pressed and touch_finger<0:
		touch_finger=event.index;set_touch_value(event.position);accept_event()

func _input(event):
	if touch_finger<0:return
	if event is InputEventScreenDrag and event.index==touch_finger:
		set_touch_value(get_global_transform_with_canvas().affine_inverse()*event.position);get_viewport().set_input_as_handled()
	elif event is InputEventScreenTouch and event.index==touch_finger and not event.pressed:
		if not event.canceled:set_touch_value(get_global_transform_with_canvas().affine_inverse()*event.position)
		touch_finger=-1;get_viewport().set_input_as_handled()

func _draw():
	var ratio: float=(value-min_value)/maxf(.001,max_value-min_value)
	var y: float=size.y*.5;var x: float=12+(size.x-24)*ratio
	draw_line(Vector2(12,y),Vector2(size.x-12,y),UI.DISABLED,6,true)
	draw_line(Vector2(12,y),Vector2(x,y),UI.JADE,6,true)
	draw_texture_rect(UI.art("slider-thumb-hover" if has_focus() or touch_finger>=0 else "slider-thumb"),Rect2(x-12,y-12,24,24),false)
	if has_focus():draw_rect(Rect2(Vector2.ZERO,size),UI.JADE,false,2)
