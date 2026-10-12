extends RefCounted
# Entire drawn poses. Camera, frame rate and character bones do not select frames.
static func selection(u: Dictionary,p: Dictionary,recovery: float=.30,windup: float=-1) -> Dictionary:
	var state: String="idle"
	var progress: float=0
	var loop: bool=false
	if u.anim=="death":state="death";progress=clampf(float(u.anim_t)/.65,0,1)
	elif u.anim=="windup":state="windup";progress=clampf(float(u.anim_t)/maxf(.01,windup if windup>=0 else float(p.get("windup",.3))),0,1)
	elif u.anim=="attack":state="attack";progress=clampf(float(u.anim_t)/maxf(.01,recovery),0,1)
	elif float(u.get("hurt",0))>0:state="hurt";progress=clampf(1-float(u.hurt)/.30,0,1)
	elif u.anim=="reload":state="special";progress=clampf(1-float(u.get("reload_left",0))/maxf(.01,float(u.get("reload_duration",1))),0,1)
	elif float(u.get("visual_load",0))>0:state="load";progress=clampf(1-float(u.visual_load)/.25,0,1)
	elif float(u.get("visual_special",0))>0:state="special";progress=clampf(1-float(u.visual_special)/.6,0,1)
	elif u.anim=="mine":
		state="mine"
		var cycle: float=minf(.95,maxf(.01,float(u.get("work_duration",1))))
		progress=fposmod(float(u.job_time),cycle)/cycle
	elif u.anim=="unload":state="unload";progress=clampf(float(u.job_time)/maxf(.01,float(u.get("work_duration",1))),0,1)
	elif u.anim in ["bound","queue"]:state=u.anim
	elif u.anim=="walk":state="walk";progress=fposmod(float(u.walk)/.88,1);loop=true
	else:progress=fposmod(float(u.age)*.55+float(u.uid)*.13,1);loop=true
	var clip: Array=p.clips.get(state,p.clips.idle)
	var index: int=mini(clip.size()-1,maxi(0,floori(progress*clip.size())))
	if state=="walk" and u.get("backpedal",false):index=clip.size()-1-index
	return {"frame":int(clip[index]),"state":state,"progress":progress,"loop":loop}

static func region(p: Dictionary,frame: int) -> Rect2:
	var size=Vector2(p.frame_size[0],p.frame_size[1])
	return Rect2(Vector2(frame%int(p.columns),floori(float(frame)/float(p.columns)))*size,size)
