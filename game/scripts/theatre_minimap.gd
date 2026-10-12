extends Control
var view

func _process(_delta):
	queue_redraw()

func _draw():
	if view!=null and view.sim!=null and not view.menu:view.draw_minimap(self)
