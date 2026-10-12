extends SceneTree
const Data=preload("res://scripts/data_store.gd")
const Simulation=preload("res://scripts/battle_sim.gd")
func _initialize():call_deferred("run")
func run():
	var db=Data.new();var records: Array=[]
	for side in [0,1]:
		for count in [2,4,5]:
			var s=Simulation.new(db)
			s.start({"map":"map.01.01","faction":"mu" if side==0 else "yin","enemy":"yin" if side==0 else "mu"})
			s.ai_enabled=[false,false];s.units.clear();s.buildings.clear()
			var direction: float=1 if side==0 else -1
			var target=s.spawn("unit.yin.axe",1-side,20)
			target.hp=10000;target.max_hp=10000;target.cooldown=1000;target.special_cd=1000;target.speed_override=0
			var front=s.spawn("unit.mu.guard",side,20-direction*.65)
			s.map.apply_anchor(front,s.map.anchor(target.edge,float(target.s)-direction*.65))
			front.cooldown=1000;front.speed_override=0
			var shooters: Array=[]
			for i in range(count):shooters.append(s.spawn("unit.mu.poisoner",side,20-direction*(6+i*.8)))
			var medic=s.spawn("unit.mu.medic",side,20-direction*(6+count*.8))
			var releases: Dictionary={};var hits: Dictionary={};var healing: float=0
			for step in range(18*60):
				if step==10*60:front.hp=50;front.hurt=100
				s.visibility.refresh();s.tick(1.0/60.0)
				for e in s.drain_events():
					if e.kind=="attack":releases[e.uid]=int(releases.get(e.uid,0))+1
					if e.kind=="hit" and int(e.get("source_uid",0))!=0:hits[e.source_uid]=int(hits.get(e.source_uid,0))+1
					if e.kind=="heal" and int(e.uid)==int(front.uid):healing+=float(e.amount)
			var units: Array=[]
			for u in shooters+[medic]:units.append({"id":u.id,"uid":u.uid,"distance_to_enemy":s.combat_distance(u,target,db.balance.units[u.id]),"distance_to_guard":s.melee_distance(u,front),"releases":int(releases.get(u.uid,0)),"hits":int(hits.get(u.uid,0))})
			records.append({"side":side,"shooters":count,"units":units,"guard_healing":healing,"guard_final_hp":front.hp})
	var report={"scope":"Geometry-only preassembled formation facing an inert durable target, formal fog, 18s native simulation. No AI, research or budget balance claim.","records":records,"inputs":{}}
	for path in ["res://scripts/battle_sim.gd","res://scripts/unit_abilities.gd","res://data/balance-prototype.json","res://tests/probe_formation_fire.gd"]:report.inputs[path]=FileAccess.get_sha256(path)
	var out=OS.get_cmdline_user_args()[0];FileAccess.open(out,FileAccess.WRITE).store_string(JSON.stringify(report,"  "))
	print("FORMATION_FIRE ",records.size());quit()
