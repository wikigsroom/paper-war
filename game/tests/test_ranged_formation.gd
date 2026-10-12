extends SceneTree
const Data=preload("res://scripts/data_store.gd")
const Simulation=preload("res://scripts/battle_sim.gd")
var checks: int=0
var failures: Array=[]
func verify(value: bool,label: String):
	checks+=1
	if not value:failures.append(label)
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
			var illegal_release: bool=false;var crossed_screen: bool=false
			for step in range(18*60):
				if step==10*60:front.hp=50;front.hurt=100
				s.visibility.refresh();s.tick(1.0/60.0)
				for u in shooters+[medic]:
					if (float(u.s)-float(front.s))*direction>-.5:crossed_screen=true
				for e in s.drain_events():
					if e.kind=="attack":
						releases[e.uid]=int(releases.get(e.uid,0))+1
						for u in shooters+[medic]:
							if int(u.uid)==int(e.uid) and s.combat_distance(u,target,db.balance.units[u.id])>float(db.balance.units[u.id].range)+.01:illegal_release=true
					if e.kind=="hit" and int(e.get("source_uid",0))!=0:hits[e.source_uid]=int(hits.get(e.source_uid,0))+1
					if e.kind=="heal" and int(e.uid)==int(front.uid):healing+=float(e.amount)
			verify(not illegal_release,"no attack beyond real weapon range side=%s count=%s"%[side,count])
			verify(not crossed_screen,"backline preserves melee screen spacing")
			verify(healing>0,"medic actually heals injured front")
			for u in shooters:
				verify(int(releases.get(u.uid,0))>=5,"each packed shooter repeatedly fires uid=%s"%u.uid)
				verify(int(hits.get(u.uid,0))>0,"each shooter lands actual damage uid=%s"%u.uid)
			var units: Array=[]
			for u in shooters+[medic]:units.append({"id":u.id,"uid":u.uid,"distance_to_enemy":s.combat_distance(u,target,db.balance.units[u.id]),"distance_to_guard":s.melee_distance(u,front),"releases":int(releases.get(u.uid,0)),"hits":int(hits.get(u.uid,0))})
			records.append({"side":side,"shooters":count,"units":units,"guard_healing":healing,"guard_final_hp":front.hp})
	print("RANGED_FORMATION: ",checks," checks; failures=",failures)
	quit(0 if failures.is_empty() else 1)
