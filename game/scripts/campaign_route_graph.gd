extends Control

# The chapter page is a story map, not a replacement progression system.  It
# only visualizes the same campaign-flow graph used by CampaignProgress; the
# buttons above it remain the only activation surface.
var chapter: int = 0
var levels: Array = []
var nodes: Dictionary = {}
var profile: Dictionary = {}
var font: Font
const GAP_X: float = 273.0
const GAP_Y: float = 108.0
const CARD_W: float = 257.0
const CARD_H: float = 96.0
const INK = Color("343332")
const MUTED = Color("a79a89")
const JADE = Color("397e9e")
const GOLD = Color("b9964f")
const PAPER = Color("f3ebdd")

func _ready():
	mouse_filter = Control.MOUSE_FILTER_IGNORE

func card_center(local: int) -> Vector2:
	return Vector2(float(local % 4) * GAP_X + CARD_W * .5,
		float(local / 4) * GAP_Y + CARD_H * .5)

func local_index(id: String) -> int:
	for i in range(levels.size()):
		if str(levels[i].get("id", "")) == id:return i
	return -1

func completed(id: String) -> bool:
	return bool(profile.get("campaign_completed", {}).get(id, false))

func available(id: String) -> bool:
	if completed(id):return true
	var node: Dictionary = nodes.get(id, {})
	for parent in node.get("unlock_all", []):
		if not completed(str(parent)):return false
	var alternatives: Array = node.get("unlock_any", [])
	if alternatives.is_empty():return true
	for parent in alternatives:
		if completed(str(parent)):return true
	return false

func _draw():
	if levels.is_empty() or nodes.is_empty():return
	# Connectors are drawn first so the actual paper cards stay legible and
	# clickable. Only same-chapter edges belong on this page; cross-chapter edges
	# are represented by the chapter selector and the story summary.
	for local in range(levels.size()):
		var source: Dictionary = levels[local]
		var source_id: String = str(source.get("id", ""))
		var source_node: Dictionary = nodes.get(source_id, {})
		var start: Vector2 = card_center(local)
		for successor in source_node.get("successors", []):
			var child_id: String = str(successor)
			if not nodes.has(child_id) or int(nodes[child_id].get("chapter", -1)) != chapter:continue
			var child_local: int = local_index(child_id)
			if child_local<0:continue
			var end: Vector2 = card_center(child_local)
			# A completed parent alone does not unlock a conjunction child; color the
			# edge by the destination's real status so a missing sibling remains grey.
			var active: bool = available(child_id) or completed(child_id)
			var edge_color: Color = GOLD if active else MUTED
			var delta: Vector2 = end-start
			var direction: Vector2 = delta.normalized()
			var from_point: Vector2 = start+direction*42.0
			var to_point: Vector2 = end-direction*48.0
			draw_line(from_point,to_point,Color(edge_color,.78 if active else .48),3.0,true)
			var wing: Vector2 = direction.rotated(PI*.78)*9.0
			draw_line(to_point,to_point-wing,Color(edge_color,.88 if active else .58),3.0,true)
			draw_line(to_point,to_point+wing,Color(edge_color,.88 if active else .58),3.0,true)
	# A compact legend sits in the unused lower margin of the chapter grid.
	var legend_rect := Rect2(0,5*GAP_Y+4,4*GAP_X+CARD_W,30)
	draw_rect(legend_rect,Color(PAPER,.92))
	draw_line(legend_rect.position+Vector2(12,15),legend_rect.position+Vector2(39,15),GOLD,3,true)
	if font!=null:draw_string(font,legend_rect.position+Vector2(48,21),"金线：已完成或当前可行动 · 灰线：等待前置证据 · 章节图可回访",HORIZONTAL_ALIGNMENT_LEFT,-1,15,INK)
