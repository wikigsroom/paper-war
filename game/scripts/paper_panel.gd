extends Panel
const UI=preload("res://scripts/ui_theme.gd")
var grain: Texture2D

func _ready():
	# Small rails use quiet single-layer paper. All texture pixels stay within
	# the Control rectangle, preserving the measured battlefield area.
	add_theme_stylebox_override("panel",UI.surface("panel-card" if size.y<=96 else "panel-ledger",6 if size.y<=32 else 10,16))
