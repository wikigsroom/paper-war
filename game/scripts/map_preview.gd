extends Control
var definition: Dictionary = {}
var font: Font
var y_origin: float = 0
var y_scale: float = 1

func fit_height():
	var low: float = -.5
	var high: float = .5
	for edge in definition.edges:
		for p in edge.points:
			low=minf(low,float(p[1]));high=maxf(high,float(p[1]))
	var compact: bool = size.y<95
	var top: float = 10 if compact else 22
	var bottom: float = size.y-(10 if compact else 48)
	y_scale=minf(18,(bottom-top)/maxf(1,high-low))
	y_origin=(top+bottom)*.5-(low+high)*.5*y_scale

func point(x: float,y: float) -> Vector2:
	var margin: float = 16 if size.y<95 else 28
	return Vector2(margin+x/maxf(1,float(definition.length))*(size.x-margin*2),y_origin+y*y_scale)

func _draw():
	if definition.is_empty() or font==null:return
	fit_height()
	draw_rect(Rect2(Vector2.ZERO,size),Color("e8deca"))
	for edge in definition.edges:
		var points=PackedVector2Array()
		for p in edge.points:points.append(point(float(p[0]),float(p[1])))
		draw_polyline(points,Color("8e7859"),5,true)
	for mine in definition.mines:
		var p=point(mine.x,mine.y)
		draw_circle(p,7,Color("aa8a32"))
		if size.y>=95:draw_string(font,p+Vector2(-16,26),str(int(mine.capacity))+"工",HORIZONTAL_ALIGNMENT_LEFT,-1,14,Color("343332"))
	for site in definition.build_sites:
		var p=point(site.x,site.y)
		draw_rect(Rect2(p-Vector2(5,5),Vector2(10,10)),Color("397e9e"),false,2)
	for node in definition.nodes:
		var p=point(float(node.position[0]),float(node.position[1]))
		draw_circle(p,4,Color("343332"))
	if size.y>=95:draw_string(font,Vector2(18,size.y-9),"金点：矿位容量   方框：施工位置   分岔：后续部队按路标进军",HORIZONTAL_ALIGNMENT_LEFT,size.x-36,15,Color("746d61"))
