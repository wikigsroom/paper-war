extends RefCounted
# Native Controls own their touches. Only an unhandled battlefield press starts
# this gesture; its finger stays captured even when it crosses a HUD or modal.
var app
var finger: int=-1
var origin: Vector2
var camera: float=0
var moved: bool=false
var minimap: bool=false
var target: int=-1
const SLOP=8.0

func _init(owner):app=owner

func reset():
	finger=-1;moved=false;minimap=false;target=-1
	if app.view:app.view.mobile_pointer_active=false;app.view.direct_pan=false

func captured(event: InputEvent) -> bool:
	return finger>=0 and (event is InputEventScreenTouch or event is InputEventScreenDrag) and event.index==finger

func handle(event: InputEvent):
	if event is InputEventScreenTouch:
		if event.pressed:
			if finger>=0 or app.screen!="battle" or app.paused or app.modal!="" or app.mobile_blocked or app.app_suspended:return
			var p: Vector2=app.view.to_local(event.position)
			var on_map: bool=app.view.minimap_rect().has_point(p)
			if not on_map and not app.mobile.playfield.has_point(event.position):return
			finger=event.index;origin=event.position;camera=app.view.camera_x;moved=false;minimap=on_map
			app.view.target_camera=camera;app.view.follow_front=false;app.view.direct_pan=true
			target=app.view.target_at(p) if app.view.selected_spell!="" else -1
			app.view.pointer=p;app.view.mobile_pointer_active=true
			if minimap:app.navigate_minimap(p.x)
			app.get_viewport().set_input_as_handled()
		elif event.index==finger:
			var tap: bool=not event.canceled and not moved and not minimap and app.mobile.playfield.has_point(event.position)
			var captured_target: int=target
			reset()
			if tap and not app.paused and app.modal=="" and not app.mobile_blocked:app.battlefield_tap(app.view.to_local(event.position),captured_target)
			app.get_viewport().set_input_as_handled()
	elif event is InputEventScreenDrag and event.index==finger:
		var p: Vector2=app.view.to_local(event.position)
		app.view.pointer=p
		moved=moved or event.position.distance_to(origin)>SLOP
		if minimap:app.navigate_minimap(p.x)
		elif moved:
			app.view.target_camera=camera-(event.position.x-origin.x)/(app.view.PX*app.view.scale.x)
			app.view.follow_front=false
		app.get_viewport().set_input_as_handled()
