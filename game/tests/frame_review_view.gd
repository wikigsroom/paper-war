extends "res://scripts/battle_view.gd"
var unit_id: String="unit.yin.axe"

func _draw():
	draw_rect(Rect2(0,0,1320,1080),Color("f4ead3"))
	if not db.unit_frames.has(unit_id):return
	var p: Dictionary=db.unit_frames[unit_id]
	var d: Dictionary=db.balance.units[unit_id]
	var meta: Dictionary=db.assets[unit_id].duplicate(true)
	meta.world_height=float(p.source_height)*.88/(PX*PUPPET_SCALE)
	for frame in range(36):
		var row: int=frame/6;var col: int=frame%6
		var progress: float=float(col)/6+.001
		var u={"id":unit_id,"uid":0,"facing":1,"anim":"idle","anim_t":0.0,"age":progress/.55,"walk":0.0,"hurt":0.0,"job_time":0.0,"work_duration":1.0,"visual_special":0.0,"visual_load":0.0}
		match row:
			1:u.anim="walk";u.walk=progress*.88
			2:
				if d.get("economy",false):u.anim="mine";u.job_time=progress*.95
				elif col<3:u.anim="windup";u.anim_t=(float(col)/3+.001)*float(d.windup)
				else:u.anim="attack";u.anim_t=(float(col-3)/3+.001)*float(db.unit_actions[unit_id].recovery)
			3:u.hurt=.30*(1-progress)
			4:u.anim="death";u.anim_t=progress*.65
			5:
				if d.get("economy",false):u.anim="unload";u.job_time=progress
				else:u.visual_special=.6*(1-progress)
		var pos=Vector2(col*220+110,row*180+158)
		draw_line(pos+Vector2(-92,0),pos+Vector2(92,0),Color("c9b88e"),1)
		draw_frame_unit(u,pos,meta,Color.WHITE)
		draw_string(font,Vector2(col*220+6,row*180+177),unit_id+" / "+str(frame),HORIZONTAL_ALIGNMENT_LEFT,-1,12,Color("25343a"))
