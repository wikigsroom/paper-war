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
	var db=Data.new()
	for gap in [.5,8.0]:
		var contacts: Array=[]
		for first in [0,1]:
			var s=Simulation.new(db)
			s.start({"map":"map.01.04","faction":"qi","enemy":"qi"})
			s.ai_enabled=[false,false];s.units.clear();s.buildings.clear()
			var a=s.spawn("unit.qi.vanguard",0,22-gap*.5)
			var b=s.spawn("unit.qi.vanguard",1,22+gap*.5)
			var contact: Dictionary={}
			for step in range(600):
				s.units.sort_custom(func(u,v):return int(u.side)==first if u.side!=v.side else int(u.uid)<int(v.uid))
				s.tick(1.0/60.0)
				if a.windup>0 or b.windup>0:
					contact={"time":s.time,"a":a.x,"b":b.x}
					verify(a.windup>0 and b.windup>0,"equal opponents acquire contact together gap=%s first=%s"%[gap,first])
					verify(is_equal_approx(a.windup,b.windup),"equal windup at contact")
					break
			verify(not contact.is_empty(),"contact reached within ten seconds")
			contacts.append(contact)
		if not contacts[0].is_empty() and not contacts[1].is_empty():
			for key in ["time","a","b"]:
				verify(is_equal_approx(contacts[0][key],contacts[1][key]),"contact invariant under traversal reversal: "+key)
	print("MOVEMENT_PHASE_FAIRNESS: ",checks," checks; failures=",failures)
	quit(0 if failures.is_empty() else 1)
