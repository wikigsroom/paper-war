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
	for legacy in [true,false]:
		for side in [0,1]:
			var db=Data.new()
			if legacy:db.balance.units["unit.yin.hammer"].range=.82
			var sim=Simulation.new(db)
			sim.start({"map":"map.01.01","faction":"yin","enemy":"yin","starting_gold":300,"enemy_starting_gold":300,"full_tech":false})
			sim.ai_enabled=[false,false]
			var study: Dictionary=sim.request(side,"research",{"id":"tech.yin.unit.hammer"})
			var escort: Dictionary=sim.request(side,"recruit",{"id":"unit.yin.axe"})
			for i in range(310):sim.tick(1.0/60.0)
			var heavy: Dictionary=sim.request(side,"recruit",{"id":"unit.yin.hammer"})
			for i in range(150):sim.tick(1.0/60.0)
			check(study.ok and escort.ok and heavy.ok,"Original fees, unlock and production produce the hammer and its escort")
			var hammer: Dictionary={};var guard: Dictionary={}
			for u in sim.units:
				if u.side!=side:continue
				if u.id=="unit.yin.hammer":hammer=u
				if u.id=="unit.yin.axe":guard=u
			check(not hammer.is_empty() and not guard.is_empty(),"Both contact actors came from real paid orders")
			var direction: float=1 if side==0 else -1
			var base: Dictionary=sim.bases[1-side]
			# Controlled placement reproduces the 1.182-distance second rank from
			# the independent auto-marching paid recipe. This is a boundary fixture,
			# not a normal opponent battle or a rendering acceptance test.
			sim.map.apply_anchor(guard,sim.map.project(Vector2(float(base.x)-direction*.642,float(base.y))))
			sim.map.apply_anchor(hammer,sim.map.project(Vector2(float(base.x)-direction*1.182,float(base.y))))
			sim.visibility.refresh();sim.drain_events()
			var hp: float=guard.hp;var hits: int=0
			for i in range(180):
				sim.tick(1.0/60.0)
				for e in sim.drain_events():
					if e.kind=="hit" and int(e.get("source_uid",0))==int(hammer.uid) and int(e.uid)==int(base.uid):hits+=1
			check(hits==0 if legacy else hits>0,"Historical hammer reach excludes the screened target; formal default must hit it")
			check(guard.hp==hp,"The wider swing still never damages the friendly escort")
	print("HAMMER_SCREEN_REACH: ",checks," checks; failures=",failures)
	quit(0 if failures.is_empty() else 1)
