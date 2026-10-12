extends RefCounted
# All poses come from simulation age/walk/anim_t, never camera position or draw FPS.
# Tool ownership and damage remain in BattleSim. These are render-only joints.
static func pose(u: Dictionary,p: Dictionary) -> Dictionary:
	var walk: float=float(u.walk)*9.0+float(u.uid)*.65
	var breath: float=sin(float(u.age)*2.3+float(u.uid)*.8)
	var v={"body":breath*.012,"leg":0.0,"bob":breath*.8,"dx":0.0,"dy":0.0,
		"upper":0.0,"fore":0.0,"tool":0.0,"back_upper":0.0,"back_fore":0.0,"back_tool":0.0,
		"tool_visible":true,"draw":0.0,"recoil":0.0,"trail":0.0,"stretch":Vector2.ONE,"charge":0.0,"anticipation":0.0,"strike":0.0,"gesture":p.gesture}
	var g: String=p.gesture
	if u.anim=="walk":
		v.leg=sin(walk)*.23;v.bob=-absf(cos(walk))*3.5;v.body=sin(walk)*.025
		v.upper=sin(walk)*.10;v.fore=-sin(walk)*.07;v.back_upper=-v.upper
		if g in ["cannon","mortar","ram"]:v.bob*=.3;v.upper=0;v.fore=0
		if g=="wing_strike":v.upper=sin(walk)*.18;v.back_upper=-sin(walk)*.22;v.dy=-absf(sin(walk)) *5
	var recovering: bool=u.anim=="attack"
	var winding: bool=u.anim=="windup"
	if winding or recovering:
		var t: float=clampf(float(u.anim_t)/maxf(.016,float(p.windup)),0,1) if winding else clampf(float(u.anim_t)/float(p.recovery),0,1)
		# Short final stroke ends at the actual attack tick; recovery begins there.
		var prepare: float=smoothstep(0,.68,t) if winding else 0
		var strike: float=smoothstep(.68,1,t) if winding else 1-smoothstep(.12,1,t)
		var anticipation: float=prepare*(1-strike)
		v.anticipation=anticipation;v.strike=strike
		v.charge=prepare if winding else 0;v.trail=strike if recovering and t<.40 else 0
		v.body=-.12*anticipation+.13*strike;v.bob=2*anticipation+2*strike
		v.dx=-3*anticipation+5*strike;v.back_upper=-.10*anticipation
		match g:
			"slash","guard_slash","reflect_slash","crescent":
				v.upper=-1.30*anticipation+1.15*strike;v.fore=-.40*anticipation+.42*strike;v.tool=.16*strike
			"dual_slash","dual_axe":
				v.upper=-1.35*anticipation+1.00*strike;v.fore=-.50*anticipation+.50*strike
				v.back_upper=1.10*anticipation-1.05*strike;v.back_fore=.34*anticipation-.42*strike
			"cleave","reap","hammer","bomb_bash":
				v.upper=-1.0*anticipation+1.40*strike;v.fore=-.22*anticipation+.34*strike
				v.body=-.17*anticipation+.24*strike;v.bob=6*strike;v.dx=8*strike;v.stretch=Vector2(1+.025*strike,1-.035*strike)
			"fence","stab","ambush":
				v.upper=.48*anticipation-.22*strike;v.fore=-.65*anticipation+.19*strike
				v.dx=-7*anticipation+15*strike;v.body=.18*strike
			"hook","lance","pike","shield_thrust","staff_push","banner_bash":
				v.upper=.30*anticipation-.50*strike;v.fore=-.38*anticipation+.48*strike;v.dx=-6*anticipation+13*strike
				v.tool=-.18*anticipation+.16*strike
			"punch":
				v.upper=-.50*anticipation+.28*strike;v.fore=-.72*anticipation+.38*strike;v.dx=8*strike;v.bob=4*strike
				if int(u.get("attack_serial",0))%2==1:
					v.back_upper=-v.upper;v.back_fore=-v.fore;v.upper*=.45;v.fore*=.45
			"throw":
				v.upper=-1.45*anticipation-.08*strike;v.fore=-.56*anticipation+.45*strike
				v.dx=-4*anticipation+7*strike;v.body=-.14*anticipation+.22*strike
				v.tool_visible=not recovering or t>.66;v.tool=-.10*anticipation
			"bow":
				v.upper=-.06*prepare;v.fore=.06*prepare;v.body=-.035*prepare
				v.draw=prepare if winding else exp(-float(u.anim_t)*28)*.85
				v.back_upper=-.25*prepare;v.back_fore=.28*prepare;v.recoil=sin(t*PI)*3 if recovering else 0
			"repeater","sniper","blowpipe":
				v.upper=-.09*anticipation+.10*strike;v.fore=.07*anticipation-.04*strike
				v.recoil=7*strike if g=="sniper" else 4*strike;v.body=-.055*strike;v.dx=-v.recoil
			"cannon","mortar":
				v.tool=-.12*anticipation+(.08 if g=="cannon" else .13)*strike
				v.recoil=11*strike if g=="mortar" else 8*strike;v.dx=-3*strike;v.bob=2*strike;v.body=0
			"ram":
				v.dx=-6*anticipation+17*strike;v.tool=-.03*anticipation;v.bob=sin(t*PI)*2;v.body=0
			"wing_strike":
				v.upper=-.58*anticipation+.65*strike;v.back_upper=.55*anticipation-.55*strike
				v.dy=-9*anticipation;v.dx=12*strike;v.body=.17*strike
			"drum":
				v.upper=-.85*anticipation+.32*strike;v.fore=-.30*anticipation+.50*strike
				v.back_upper=.55*anticipation-.45*strike;v.bob=3*strike
			_:
				v.upper=-.42*anticipation+.25*strike;v.fore=-.22*anticipation+.22*strike;v.tool=-.12*anticipation+.20*strike
				if g=="fan_cast":v.tool=-.40*anticipation+.60*strike
				if g=="brush_cast":v.upper=-.68*anticipation+.64*strike;v.tool=.30*strike
				if g=="wrench":v.upper=-.75*anticipation+.75*strike
	if u.hurt>0:
		var h: float=clampf(float(u.hurt)/.13,0,1)
		v.dx-=5*h;v.body=-.12*h;v.upper-=.15*h;v.tool_visible=true
	if u.anim=="bound":v.body=-.025;v.upper=.07;v.fore=-.07;v.dx=0;v.dy=0;v.leg=0
	if u.anim=="death":
		var t: float=clampf(float(u.anim_t)/.44,0,1)
		v.body=.65*t;v.dx=-12*t;v.dy=t*t*14;v.upper=.45*t;v.fore=.45*t;v.leg=-.22*t
		v.back_upper=-.4*t;v.back_fore=-.25*t;v.tool=-.3*t;v.bob=0
	var special: float=float(u.get("visual_special",0))
	if special>0 and not winding and not recovering and u.hurt<=0 and u.anim not in ["bound","death"]:
		var wave: float=sin(clampf(special/.45,0,1)*PI)
		v.upper=-.35*wave;v.fore=.22*wave;v.tool=-.2*wave;v.charge=wave;v.body=-.035*wave
	return v

static func chain(j: Dictionary,p: Dictionary,back: bool=false) -> Dictionary:
	var shoulder=Vector2(j.shoulder[0],j.shoulder[1])
	var elbow=Vector2(j.elbow[0],j.elbow[1]);var grip=Vector2(j.grip[0],j.grip[1])
	var prefix: String="back_" if back else ""
	var a: float=p.body+p[prefix+"upper"]
	var b: float=a+p[prefix+"fore"]
	var e: Vector2=shoulder+(elbow-shoulder).rotated(a)
	var w: Vector2=e+(grip-elbow).rotated(b)
	var tool_angle: float=b+p[prefix+"tool"]
	var gesture: String=p.gesture
	var blade: bool=gesture in ["slash","guard_slash","reflect_slash","crescent","dual_slash","dual_axe","cleave","reap"]
	var heavy: bool=gesture in ["hammer","bomb_bash"]
	var thrust: bool=gesture in ["pike","lance","hook"]
	if (blade or heavy or thrust or gesture=="throw") and p.anticipation+p.strike>.001:
		var l1: float=(elbow-shoulder).length();var l2: float=(grip-elbow).length();var reach: float=l1+l2
		if l1>.001 and l2>.001:
			var resting: Vector2=grip-shoulder
			var ready=Vector2(-.30 if resting.x<0 else .15,-.80)*reach
			var impact=Vector2(.80,.15)*reach
			if heavy:ready=Vector2(0,-.91)*reach;impact=Vector2(.72,.28)*reach
			if thrust:ready=resting+Vector2(-.20,0)*reach;impact=Vector2(.93,-.06)*reach
			if gesture=="throw":ready=Vector2(-.64,-.50)*reach;impact=Vector2(.91,-.13)*reach
			var local: Vector2=(resting+(ready-resting)*p.anticipation+(impact-resting)*p.strike).rotated(p.body)
			var distance: float=clampf(local.length(),absf(l1-l2)+.001,reach-.001)
			local=local.normalized()*distance
			var bend: float=-1 if (elbow-shoulder).cross(resting)>0 else 1
			var angle: float=local.angle()+bend*acos(clampf((distance*distance+l1*l1-l2*l2)/(2*distance*l1),-1,1))
			e=shoulder+Vector2.from_angle(angle)*l1;w=shoulder+local
			a=angle-(elbow-shoulder).angle();b=(w-e).angle()-(grip-elbow).angle()
			var tip=Vector2(j.tip[0],j.tip[1]);var original: float=(tip-grip).angle()
			var ready_angle: float=wrapf(-PI*.5-original,-PI,PI) if blade or heavy else -.15
			var hit_angle: float=wrapf((.40 if blade else .75 if heavy else 0)-original,-PI,PI)
			if gesture=="throw":ready_angle=-.18;hit_angle=0
			tool_angle=p.body+ready_angle*p.anticipation+hit_angle*p.strike
	return {"shoulder":shoulder,"elbow":e,"grip":w,"upper_angle":a,"fore_angle":b,"tool_angle":tool_angle}

static func projectile(def: Dictionary,id: String="") -> String:
	if def.has("projectile_style"):return str(def.projectile_style)
	if def.get("building",false) or id.begins_with("building."):return "bolt"
	match str(def.get("role","")):
		"archer":return "arrow"
		"sniper","repeater":return "bolt"
		"javelin":return "spear"
		"artillery":return "cannon"
		"mortar":return "mortar"
		"poisoner":return "needle"
		"burner":return "fire"
		"chain":return "chain"
		"drummer":return "sound"
		"engineer":return "gear"
		"medic":return "leaf"
		"necromancer":return "soul"
		"oracle":return "orb"
		"scribe":return "ink"
		"summoner":return "paper"
		"illusionist":return "fan"
		"caravan":return "seal"
	return "bolt"
