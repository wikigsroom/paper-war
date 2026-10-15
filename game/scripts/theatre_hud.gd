extends Control
const UI=preload("res://scripts/ui_theme.gd")
# Quiet paper rails keep the playable stage open. All controls are native Godot UI.
var mobile: bool = false
var accent: Color = Color("d85840")
var grain: Texture2D

func _draw():
	var w=size.x;var h=size.y
	var top: float = 82 if mobile else 64
	var bottom: float = 186 if mobile else 156
	var paper=UI.CARD;var ink=UI.INK
	accent=UI.SEAL
	draw_rect(Rect2(0,0,w,top),paper)
	draw_line(Vector2(0,top+2),Vector2(w,top+2),Color(UI.GOLD,.28),5,true)
	draw_line(Vector2(0,top-2),Vector2(w,top-2),accent,3,true)
	draw_rect(Rect2(0,h-bottom,w,bottom),paper)
	if grain:
		draw_texture_rect(grain,Rect2(0,0,w,top),true,Color(1,1,1,.15))
		draw_texture_rect(grain,Rect2(0,h-bottom,w,bottom),true,Color(1,1,1,.15))
	draw_line(Vector2(0,h-bottom),Vector2(w,h-bottom),UI.GOLD,2,true)
	# The folded ends are the signature of the command strip.
	draw_colored_polygon(PackedVector2Array([Vector2(0,h-bottom),Vector2(16,h-bottom+16),Vector2(0,h-bottom+32)]),UI.SEAL)
	draw_colored_polygon(PackedVector2Array([Vector2(w,h-bottom),Vector2(w-16,h-bottom+16),Vector2(w,h-bottom+32)]),UI.SEAL)
	if not mobile:
		for x in [531.0,1047.0]:draw_line(Vector2(x,h-bottom+12),Vector2(x,h-12),Color(ink,.16),1,true)
	draw_line(Vector2(13,h-bottom+6),Vector2(w-13,h-bottom+6),Color(UI.CARD,.38),1,true)
	for x in [216.0,563.0,1103.0,1447.0]:draw_line(Vector2(x,14),Vector2(x,top-14),Color(ink,.13),1,true)
	for x in [48.0, w-48.0]:
		draw_circle(Vector2(x,top*.5),4,UI.LANTERN)
		draw_circle(Vector2(x,top*.5),9,Color(UI.LANTERN,.12))
