extends ScrollContainer
# Godot 4.7.2 ScrollContainer pans with emulated mouse events. Our native touch
# path needs explicit finger capture, cancellation and vertical momentum.
var touch_finger: int=-1
var origin: Vector2
var previous: Vector2
var original_scroll: float=0
var dragging: bool=false
var velocity: float=0
var previous_time: int=0
const SLOP=8.0
var host
var sheet_scope: bool=false
var horizontal: bool=false

func scroll_value() -> float:
	return scroll_horizontal if horizontal else scroll_vertical

func set_scroll_value(value: float):
	if horizontal:scroll_horizontal=roundi(value)
	else:scroll_vertical=roundi(value)

func axis(point: Vector2) -> float:
	return point.x if horizontal else point.y

func _ready():
	set_process(false)
	(get_h_scroll_bar() if horizontal else get_v_scroll_bar()).value_changed.connect(func(_v):queue_redraw())

func excludes(point: Vector2) -> bool:
	for child in find_children("*","HSlider",true,false):
		if child.is_visible_in_tree() and child.get_global_rect().has_point(point):return true
	return false

func input_blocked() -> bool:
	return not is_visible_in_tree() or (host!=null and (host.app_suspended or host.mobile_blocked or (host.modal!="" and not sheet_scope)))

func stop_motion():
	var was_dragging: bool=dragging
	touch_finger=-1;dragging=false;velocity=0;set_process(false)
	if was_dragging:propagate_notification(NOTIFICATION_SCROLL_END);scroll_ended.emit()

func _input(event):
	if event is InputEventScreenTouch and not event.pressed and event.canceled and event.index==touch_finger:
		stop_motion();return
	if input_blocked():stop_motion();return
	if event is InputEventScreenTouch:
		if event.pressed:
			if touch_finger>=0 or not get_global_rect().has_point(event.position) or excludes(event.position):return
			touch_finger=event.index;origin=event.position;previous=origin;original_scroll=scroll_value()
			dragging=absf(velocity)>60;velocity=0;previous_time=Time.get_ticks_msec();set_process(false)
			if dragging:propagate_notification(NOTIFICATION_SCROLL_BEGIN);get_viewport().set_input_as_handled()
		elif event.index==touch_finger:
			if dragging:
				get_viewport().set_input_as_handled();propagate_notification(NOTIFICATION_SCROLL_END);scroll_ended.emit()
			if event.canceled:velocity=0
			touch_finger=-1;dragging=false;set_process(absf(velocity)>8)
	elif event is InputEventScreenDrag and event.index==touch_finger:
		if not dragging and event.position.distance_to(origin)>SLOP:
			dragging=true;propagate_notification(NOTIFICATION_SCROLL_BEGIN);scroll_started.emit()
		if dragging:
			var stamp: int=Time.get_ticks_msec();var elapsed: float=maxf(.008,(stamp-previous_time)/1000.0)
			velocity=clampf((axis(previous)-axis(event.position))/elapsed,-1400,1400)
			set_scroll_value(original_scroll+axis(origin)-axis(event.position))
			previous=event.position;previous_time=stamp
			get_viewport().set_input_as_handled()

func _process(delta):
	if input_blocked():stop_motion();return
	var old: float=scroll_value()
	set_scroll_value(old+velocity*minf(delta,.05))
	velocity*=exp(-minf(delta,.05)*7)
	if old==scroll_value() or absf(velocity)<8:velocity=0;set_process(false)

func _notification(what):
	if what==NOTIFICATION_APPLICATION_PAUSED or (what==NOTIFICATION_VISIBILITY_CHANGED and not is_visible_in_tree()):stop_motion()

func _draw():
	if horizontal:
		var total: float=get_h_scroll_bar().max_value
		if total<=size.x+1:return
		var length: float=maxf(24,size.x*size.x/total)
		var x: float=(size.x-length)*scroll_horizontal/maxf(1,total-size.x)
		draw_line(Vector2(1,size.y-1),Vector2(size.x-1,size.y-1),Color("c4b294"),2,true)
		draw_line(Vector2(x+1,size.y-1),Vector2(x+length-1,size.y-1),Color("31747c"),2,true)
		return
	var bar=get_v_scroll_bar();var total: float=bar.max_value
	if total<=size.y+1:return
	var height: float=maxf(24,size.y*size.y/total)
	var y: float=(size.y-height)*scroll_vertical/maxf(1,total-size.y)
	draw_line(Vector2(size.x-2,2),Vector2(size.x-2,size.y-2),Color("c4b294"),2,true)
	draw_line(Vector2(size.x-2,y+2),Vector2(size.x-2,y+height-2),Color("31747c"),3,true)
