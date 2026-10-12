extends RefCounted
# Economy animation is driven by real service time. Queue/bind never mine.
static func pose(u: Dictionary) -> Dictionary:
	var phase: float=float(u.walk)*9+float(u.uid)*.65
	var breath: float=sin(float(u.age)*2+float(u.uid))
	var v={"leg":0.0,"bob":breath*.8,"body":0.0,"arm":.12,"dx":0.0,"dy":0.0}
	if u.anim=="walk":v.leg=sin(phase)*.20;v.bob=-absf(cos(phase))*3.5;v.body=sin(phase)*.022;v.arm=sin(phase)*.045
	if u.anim=="mine":
		var cycle: float=minf(.95,maxf(.01,float(u.get("work_duration",1))))
		var p: float=fmod(float(u.job_time),cycle)/cycle
		if p<.40:v.arm=lerpf(.28,-1.30,smoothstep(0,.4,p))
		elif p<.57:v.arm=lerpf(-1.30,1.12,pow((p-.40)/.17,2))
		else:v.arm=lerpf(1.12,.28,smoothstep(.57,1,p))
		v.body=.11*sin(p*TAU-.9);v.bob=3+5*maxf(0,sin(p*TAU-1));v.leg=.025*sin(p*TAU)
	elif u.anim=="unload":
		var progress: float=clampf(float(u.job_time),0,1)
		v.body=.20*sin(progress*PI);v.bob=4*sin(progress*PI);v.arm=.30*sin(progress*PI)
	elif u.anim=="queue":v.body=-.025;v.arm=.35;v.bob=breath*.5
	var pickup: float=float(u.get("visual_load",0))
	if pickup>0 or u.anim=="load":
		var p: float=clampf(pickup/.25,0,1) if pickup>0 else clampf(1-float(u.anim_t)/.25,0,1)
		v.body=.16*sin(p*PI);v.arm=.40*sin(p*PI);v.bob=3*sin(p*PI)
	if u.hurt>0:v.dx=-3;v.body=-.08;v.arm=-.10
	if u.anim=="bound":v.leg=0;v.arm=.18;v.body=-.03;v.bob=0
	if u.anim=="death":
		var t: float=clampf(float(u.anim_t)/.44,0,1)
		v.leg=-.18*t;v.arm=.45*t;v.body=.62*t;v.dx=-10*t;v.dy=16*t*t;v.bob=0
	return v
