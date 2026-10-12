extends SceneTree
# Runtime action-frame contract. The shipped renderer uses one authored 6x6
# atlas per unit; this test intentionally exercises the same FramePlayer path
# that battle_view.gd uses, so it can run against the compiled APK/EXE pack.
const Data=preload("res://scripts/data_store.gd")
const Sim=preload("res://scripts/battle_sim.gd")
const FramePlayer=preload("res://scripts/unit_frame_player.gd")
const Projectile=preload("res://scripts/unit_projectile.gd")
var checks: Array=[]
func _initialize():call_deferred("run")
func check(name_value: String,passed: bool,details: Dictionary={}):
	checks.append({"name":name_value,"passed":passed,"details":details})
	if not passed:print("ACTION_FAIL ",name_value," ",details)
func run():
	var db=Data.new();var roles: Dictionary={};var outputs: Dictionary={};var attacks: int=0;var combat_units: int=0
	check("Every runtime unit has its own action binding",db.unit_actions.size()==db.balance.units.size())
	for uid in db.balance.units:
		var def: Dictionary=db.balance.units[uid];var profile: Dictionary=db.unit_actions[uid];var frame_profile: Dictionary=db.unit_frames[uid]
		check(uid+" correct stable ID",profile.id==uid and frame_profile.id==uid and db.assets[uid].action_profile==uid)
		check(uid+" windup matches gameplay",is_equal_approx(float(profile.windup),float(def.windup)))
		check(uid+" authored 36-frame atlas",int(frame_profile.get("frame_count",0))==36 and int(frame_profile.get("columns",0))==6 and int(frame_profile.get("rows",0))==6 and ResourceLoader.exists(str(frame_profile.get("atlas",""))))
		for state in ["idle","walk","windup","attack","hurt","death","special","bound"]:
			var clip: Array=frame_profile.get("clips",{}).get(state,[])
			check(uid+" authored clip "+state,not clip.is_empty() and clip.all(func(index):return int(index)>=0 and int(index)<36))
		if def.get("economy",false):
			check(uid+" real miner clips",frame_profile.clips.has("mine") and frame_profile.clips.has("load") and frame_profile.clips.has("unload"))
			var worker: Dictionary={"id":uid,"uid":1,"age":1.0,"walk":0.0,"anim":"mine","anim_t":0.0,"job_time":.0,"work_duration":2.4,"hurt":0.0}
			for state in ["idle","walk","mine","load","unload","queue","hurt","bound","death"]:
				worker.anim=state;worker.anim_t=.22
				for t in range(8):
					worker.job_time=float(t)/8*.95
					var selected: Dictionary=FramePlayer.selection(worker,frame_profile,.3,float(profile.windup));var clip: Array=frame_profile.clips.get(selected.state,frame_profile.clips.idle)
					check(uid+" worker frame "+state+str(t),is_finite(float(selected.progress)) and clip.any(func(index):return int(index)==int(selected.frame)))
			continue
		combat_units+=1;roles[profile.role]=true
		var u: Dictionary={"id":uid,"uid":1,"age":1.0,"walk":.0,"anim":"idle","anim_t":0.0,"hurt":0.0,"facing":1,"attack_serial":0}
		for state in ["idle","walk","windup","attack","hurt","bound"]:
			for step in range(8):
				u.anim=state;u.walk=step*.13;u.anim_t=float(profile.windup if state=="windup" else profile.recovery)*step/7;u.hurt=.13 if state=="hurt" else 0
				var selected: Dictionary=FramePlayer.selection(u,frame_profile,float(profile.recovery),float(profile.windup));var clip: Array=frame_profile.clips.get(selected.state,frame_profile.clips.idle)
				check(uid+" frame selection "+state+str(step),is_finite(float(selected.progress)) and clip.any(func(index):return int(index)==int(selected.frame)))
		u.anim="windup";u.anim_t=float(profile.windup)*.5;var prepared: Dictionary=FramePlayer.selection(u,frame_profile,float(profile.recovery),float(profile.windup))
		u.anim="attack";u.anim_t=float(profile.recovery)*.5;var striking: Dictionary=FramePlayer.selection(u,frame_profile,float(profile.recovery),float(profile.windup))
		check(uid+" anticipation and strike use separate clips",prepared.state=="windup" and striking.state=="attack" and prepared.frame!=striking.frame)
		var sim=Sim.new(db);sim.start({"faction":uid.get_slice(".",1),"enemy":"yin","map":"map.01.01","full_tech":true})
		sim.ai_enabled=[false,false];sim.units.clear();sim.projectiles.clear();sim.events.clear()
		var source: Dictionary=sim.spawn(uid,0,20);var target: Dictionary=sim.spawn("unit.yin.guard",1,20.35)
		target.hp=100000;target.max_hp=100000
		var hp: float=target.hp;sim.drain_events();sim.attack(source,target);attacks+=1
		if str(def.attack).begins_with("projectile"):
			var style: String=Projectile.projectile(def,uid);outputs[style]=int(outputs.get(style,0))+1
			check(uid+" actual projectile type",not sim.projectiles.is_empty() and sim.projectiles[0].style==style,{"expected":style})
			check(uid+" ranged damage waits for impact",is_equal_approx(target.hp,hp))
			for p in sim.projectiles:sim.projectile_hit(p)
		check(uid+" hostile damage",target.hp<hp)
		var ally: Dictionary=sim.spawn("unit.yin.worker",0,20.35);hp=ally.hp;var count: int=sim.projectiles.size()
		sim.attack(source,ally);check(uid+" never attacks allied worker",is_equal_approx(hp,ally.hp) and count==sim.projectiles.size())
	check("All non-worker combat units have action/atlas coverage",combat_units==62)
	check("Arrow, spear and bolt are distinct",outputs.has("arrow") and outputs.has("spear") and outputs.has("bolt"))
	var failed: Array=checks.filter(func(c):return not c.passed)
	var args=OS.get_cmdline_user_args();var path: String=args[args.find("--output")+1] if args.has("--output") else "user://unit-actions.json"
	var report={"passed":failed.is_empty(),"checks":checks,"failures":failed,"units":db.unit_actions.size(),"attacks":attacks,"roles":roles.keys(),"projectiles":outputs,"scope":"Shipped 6x6 unit atlas and FramePlayer selection with real hostile/friendly simulation; not visual quality or device FPS.","inputs":{}}
	for p in ["res://scripts/unit_frame_player.gd","res://scripts/battle_sim.gd","res://data/unit-actions.json","res://data/unit-frames.json","res://tests/test_unit_actions.gd"]:report.inputs[p]=FileAccess.get_sha256(p)
	var file=FileAccess.open(path,FileAccess.WRITE);file.store_string(JSON.stringify(report,"\t"));file.close()
	print("UNIT_ACTIONS: ",checks.size()," checks; failures=",JSON.stringify(failed))
	quit(0 if report.passed else 1)
