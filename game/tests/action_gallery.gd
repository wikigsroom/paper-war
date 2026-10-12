extends "res://scripts/battle_view.gd"
# Isolated native renderer fixture. All limbs are the shipped draw_unit code.
var positions: Dictionary={}
var captions: Dictionary={}
var page_title: String=""
func unit_position(u: Dictionary) -> Vector2:return positions.get(u.uid,Vector2.ZERO)
func _draw():
	canvas_shift=Vector2.ZERO
	draw_rect(Rect2(0,0,1600,900),Color("f6ecd3"))
	draw_string(font,Vector2(28,40),page_title,HORIZONTAL_ALIGNMENT_LEFT,-1,26,INK)
	for u in sim.units:
		var pos: Vector2=unit_position(u)
		draw_rect(Rect2(pos-Vector2(172,232),Vector2(344,272)),Color("eadfc4"))
		draw_line(pos+Vector2(-158,4),pos+Vector2(158,4),Color("c2b393"),1,true)
		draw_unit(u)
		draw_string(font,pos+Vector2(-151,32),captions[u.uid],HORIZONTAL_ALIGNMENT_LEFT,-1,18,INK)
	draw_set_transform(Vector2.ZERO)
