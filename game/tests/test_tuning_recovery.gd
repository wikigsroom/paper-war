extends SceneTree
const Data=preload("res://scripts/data_store.gd")
const Simulation=preload("res://scripts/battle_sim.gd")
const View=preload("res://scripts/battle_view.gd")
var checks: int=0
var failures: Array=[]
func _initialize():call_deferred("run")
func check(ok: bool,note: String):
	checks+=1
	if not ok:failures.append(note)
func run():
	var db=Data.new()
	for id in db.balance.units:
		if db.balance.units[id].get("economy",false):continue
		var s=Simulation.new(db)
		s.start({"map":"map.01.01","faction":id.split(".")[1],"enemy":"yin","full_tech":true})
		s.units.clear();s.ai_enabled=[false,false]
		var u=s.spawn(id,0,20)
		u.anim="attack";u.anim_t=0;u.cooldown=2;u.windup=0
		var position: Vector2=s.physical_point(u)
		var recovery: float=db.unit_actions[id].recovery
		for i in range(maxi(1,int(ceilf(recovery*60))-1)):
			s.tick_unit(u,1.0/60)
			check(u.anim=="attack" and s.physical_point(u).is_equal_approx(position),id+" keeps released recovery with no remaining target")
		s.tick_unit(u,recovery+.01)
		check(u.anim!="attack",id+" resumes after recovery")
		u.anim="attack";u.anim_t=0;u.statuses["stun"]={"left":1.0,"source":1,"source_uid":0,"potency":1.0}
		s.tick_unit(u,1.0/60)
		check(u.anim=="bound",id+" stun still interrupts recovery")
	var view=View.new();root.add_child(view)
	view.menu=true
	for i in range(650):
		view.particles.append({"life":.01 if i%2==0 else 1.0,"v":Vector2.ZERO,"pos":Vector2.ZERO,"angle":0.0,"spin":0.0,"serial":i})
		view.effects.append({"life":.01 if i%2==0 else 1.0,"serial":i})
		view.floats.append({"life":.01 if i%2==0 else 1.0,"serial":i})
	view.update(.02)
	for items in [view.particles,view.effects,view.floats]:
		check(items.size()==325,"all expired feedback removed in one update")
		for i in range(items.size()):check(items[i].serial==i*2+1,"survivor order preserved without skips")
	view.update(2)
	check(view.particles.is_empty() and view.effects.is_empty() and view.floats.is_empty(),"all feedback drains to empty")
	view.queue_free()
	var args=OS.get_cmdline_user_args()
	var out: String=args[args.find("--report")+1]
	FileAccess.open(out,FileAccess.WRITE).store_string(JSON.stringify({"passed":failures.is_empty(),"checks":checks,"failures":failures,"scope":"72-definition recovery, stun interruption and stable dense feedback cleanup; Windows native headless, not Android hardware."},"\t"))
	print("TUNING ",checks," failures ",failures);quit(0 if failures.is_empty() else 1)
