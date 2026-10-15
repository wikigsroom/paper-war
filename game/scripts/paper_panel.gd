extends Panel
const UI=preload("res://scripts/ui_theme.gd")
var grain: Texture2D

func _ready():
	# Small rails use quiet single-layer paper. All texture pixels stay within
	# the Control rectangle, preserving the measured battlefield area.
	# Callers often assign the semantic name immediately after add_child(); defer
	# one idle tick so HudTopRail/HudBottomRail is visible to the style resolver.
	call_deferred("_apply_runtime_style")

func _apply_runtime_style():
	var rail: bool=name.begins_with("Hud") or name.ends_with("Rail")
	if rail:
		add_theme_stylebox_override("panel",UI.rail_box())
	else:
		add_theme_stylebox_override("panel",UI.surface("panel-card" if size.y<=96 else "panel-ledger",6 if size.y<=32 else 10,16))
	queue_redraw()

func _draw():
	if name in ["Modal_brief","Modal_result"]:
		var c=Color(UI.GOLD,.72)
		var d: float=15.0
		var inset: float=8.0
		for side in [1,-1]:
			var x: float=inset if side==1 else size.x-inset
			draw_line(Vector2(x,inset),Vector2(x+float(side)*d,inset),c,2,true)
			draw_line(Vector2(x,inset),Vector2(x,inset+d),c,2,true)
			var y: float=size.y-inset
			draw_line(Vector2(x,y),Vector2(x+float(side)*d,y),c,2,true)
			draw_line(Vector2(x,y),Vector2(x,y-float(d)),c,2,true)
