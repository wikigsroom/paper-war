extends "res://scripts/battle_view.gd"
var play_time: float=0
var review_ids: Array=[]
func _draw():
	draw_rect(Rect2(0,0,1320,810),Color("f4ead3"))
	draw_string(font,Vector2(26,36),"Whole drawn poses / native Godot / controlled animation review",HORIZONTAL_ALIGNMENT_LEFT,-1,22,Color("25343a"))
	for i in range(review_ids.size()):
		var uid: String=review_ids[i]
		if not db.unit_frames.has(uid):continue
		var d: Dictionary=db.balance.units[uid]
		var meta: Dictionary=db.assets[uid].duplicate(true);meta.world_height=float(db.unit_frames[uid].source_height)*1.05/(PX*PUPPET_SCALE)
		var u={"id":uid,"uid":0,"facing":1,"anim":"idle","anim_t":0.0,"age":play_time,"walk":play_time*float(d.get("speed",1)),"hurt":0.0,"job_time":0.0,"work_duration":1.0,"visual_special":0.0,"visual_load":0.0}
		if play_time>=1 and play_time<2.6:u.anim="walk"
		elif play_time>=2.6 and play_time<4.6:
			if d.get("economy",false):u.anim="mine";u.job_time=play_time-2.6
			else:
				var t: float=fposmod(play_time-2.6,float(d.windup)+float(db.unit_actions[uid].recovery)+.15)
				if t<float(d.windup):u.anim="windup";u.anim_t=t
				else:u.anim="attack";u.anim_t=t-float(d.windup)
		elif play_time>=4.6 and play_time<5.2:u.hurt=.3-fposmod(play_time-4.6,.3)
		elif play_time>=5.2 and play_time<6.2:u.anim="death";u.anim_t=play_time-5.2
		elif play_time>=6.2:
			if d.get("economy",false):u.anim="unload";u.job_time=fposmod(play_time-6.2,1)
			else:u.visual_special=.6-fposmod(play_time-6.2,.6)
		var pos=Vector2(i%4*330+165,(i/4)*238+247)
		draw_line(pos+Vector2(-145,0),pos+Vector2(145,0),Color("c9b88e"),1)
		draw_frame_unit(u,pos,meta,Color.WHITE)
		var timing: Dictionary=db.unit_frames[uid].duplicate(false);timing.windup=d.get("windup",.3)
		var selected: Dictionary=FramePlayer.selection(u,timing,float(db.unit_actions[uid].recovery))
		draw_string(font,pos+Vector2(-145,26),uid+" / "+selected.state+" / "+str(selected.frame),HORIZONTAL_ALIGNMENT_LEFT,-1,15,Color("25343a"))
