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
			# The current resource must work without a QA reach override.
			if legacy:db.balance.units["unit.qi.executioner"].range=.85
			var sim=Simulation.new(db)
			sim.start({"map":"map.01.04","faction":"qi","enemy":"qi","starting_gold":300,"enemy_starting_gold":300,"full_tech":false})
			sim.ai_enabled=[false,false]
			var study: Dictionary=sim.request(side,"research",{"id":"tech.qi.unit.executioner"})
			var escort: Dictionary=sim.request(side,"recruit",{"id":"unit.qi.vanguard"})
			for i in range(310):sim.tick(1.0/60.0)
			var premium: Dictionary=sim.request(side,"recruit",{"id":"unit.qi.executioner"})
			for i in range(150):sim.tick(1.0/60.0)
			check(study.ok and escort.ok and premium.ok,"Both units use original paid research and production")
			var soldier: Dictionary={};var guard: Dictionary={}
			for u in sim.units:
				if u.side!=side:continue
				if u.id=="unit.qi.executioner":soldier=u
				if u.id=="unit.qi.vanguard":guard=u
			check(not soldier.is_empty() and not guard.is_empty(),"Real paid orders produced both actors")
			var direction: float=1.0 if side==0 else -1.0
			var base: Dictionary=sim.bases[1-side]
			# Controlled placement reproduces the recorded frontline gap; not normal play.
			sim.map.apply_anchor(guard,sim.map.project(Vector2(float(base.x)-direction*.65,float(base.y))))
			sim.map.apply_anchor(soldier,sim.map.project(Vector2(float(base.x)-direction*1.1733,float(base.y))))
			sim.visibility.refresh();sim.drain_events()
			var hp: float=guard.hp;var hits: int=0
			for i in range(120):
				sim.tick(1.0/60.0)
				for e in sim.drain_events():
					if e.kind=="hit" and int(e.get("source_uid",0))==int(soldier.uid) and int(e.uid)==int(base.uid):hits+=1
			check(hits==0 if legacy else hits>0,"Historical rear melee gap excludes .85; formal default reaches it")
			check(guard.hp==hp,"Reach never turns friendly contact into damage")
	print("PREMIUM_REACH: ",checks," checks; failures=",failures)
	quit(0 if failures.is_empty() else 1)
