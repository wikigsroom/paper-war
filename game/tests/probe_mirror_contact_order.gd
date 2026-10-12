extends SceneTree
const Data=preload("res://scripts/data_store.gd")
const Simulation=preload("res://scripts/battle_sim.gd")
func _initialize():call_deferred("run")
func run():
	var db=Data.new();var records: Array=[]
	for distance in [.5,8.0]:
		for first in [0,1]:
			var s=Simulation.new(db);s.start({"map":"map.01.04","faction":"qi","enemy":"qi"});s.ai_enabled=[false,false];s.units.clear();s.buildings.clear()
			var a=s.spawn("unit.qi.vanguard",0,22-distance*.5);var b=s.spawn("unit.qi.vanguard",1,22+distance*.5)
			var hits: Array=[];var contact: Array=[]
			for step in range(30*60):
				s.units.sort_custom(func(u,v):return int(u.side)==first if u.side!=v.side else int(u.uid)<int(v.uid))
				s.tick(1.0/60.0)
				if contact.is_empty() and (a.windup>0 or b.windup>0):contact.append({"time":s.time,"x":[a.x,b.x],"windup":[a.windup,b.windup]})
				for e in s.drain_events():
					if e.kind=="hit":hits.append({"time":s.time,"side":e.side,"amount":e.amount})
				if a.hp<=0 or b.hp<=0:break
			records.append({"initial_distance":distance,"first":first,"end":s.time,"hp":[a.hp,b.hp],"first_contact":contact,"hits":hits})
	var report={"scope":"Isolated equal qi melee pair; controlled unit traversal order and spawn gap, no AI/economy/spells. Not paid-game balance.","records":records,"inputs":{}}
	for path in ["res://scripts/battle_sim.gd","res://scripts/unit_abilities.gd","res://data/balance-prototype.json","res://tests/probe_mirror_contact_order.gd"]:report.inputs[path]=FileAccess.get_sha256(path)
	var file=FileAccess.open(OS.get_cmdline_user_args()[0],FileAccess.WRITE);file.store_string(JSON.stringify(report,"  "));file.close();print("MIRROR_CONTACT_ORDER ",records.size());quit()
