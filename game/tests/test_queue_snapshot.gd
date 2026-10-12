extends SceneTree
const Data=preload("res://scripts/data_store.gd")
const Simulation=preload("res://scripts/battle_sim.gd")
var checks: int=0
var failures: Array=[]
func check(ok: bool,note: String):
	checks+=1
	if not ok:failures.append(note)
func _initialize():call_deferred("run")
func run():
	for side in [0,1]:
		var s=Simulation.new(Data.new())
		s.start({"map":"map.01.01","faction":"yin","enemy":"yin","starting_gold":1000,"enemy_starting_gold":1000})
		s.ai_enabled=[false,false]
		var id: String="unit.yin.worker"
		for i in range(3):check(s.recruit(side,id)=="","Paid identical orders")
		var p: Dictionary=s.players[side]
		var snapshot: int=int(p.queue_revision)
		var elapsed: float=0
		while p.queue.size()==3 and elapsed<5:
			s.tick(1.0/60.0);elapsed+=1.0/60.0
		check(p.queue.size()==2 and p.queue_revision==snapshot+1,"Actual production invalidates snapshot")
		var before: String=JSON.stringify(p)
		var reply: Dictionary=s.request(side,"cancel_queue",{"index":1,"id":id,"queue_revision":snapshot})
		check(not reply.ok,"Stale duplicate cancellation refused")
		var after: Dictionary=p.duplicate(true);after.sequence-=1
		check(JSON.stringify(after)==before,"Refusal preserves queue gold and progress")
		var gold: float=p.gold
		var progress: float=p.production
		reply=s.request(side,"cancel_queue",{"index":1,"id":id,"queue_revision":p.queue_revision})
		check(reply.ok and p.queue.size()==1,"Fresh tail cancellation accepted")
		check(is_equal_approx(p.gold,gold+float(s.db.balance.units[id].gold)) and p.production==progress,"Refund exact; tail preserves head progress")
		snapshot=p.queue_revision
		check(s.recruit(side,id)=="","New paid order")
		reply=s.request(side,"cancel_queue",{"index":0,"id":id,"queue_revision":snapshot})
		check(not reply.ok and p.queue.size()==2,"Recruit invalidates old snapshot")
		reply=s.request(side,"cancel_queue",{"index":0,"id":id,"queue_revision":p.queue_revision})
		check(reply.ok and p.production==0,"Fresh head resets production")
	print("QUEUE_SNAPSHOT: ",checks," checks; failures=",failures)
	quit(0 if failures.is_empty() else 1)
