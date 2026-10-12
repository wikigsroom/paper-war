extends SceneTree
const Data=preload("res://scripts/data_store.gd")
const Simulation=preload("res://scripts/battle_sim.gd")
const Reference=preload("reference_target_search.gd")
var checks: int=0
var failures: Array=[]
func verify(value: bool,label: String):
	checks+=1
	if not value:failures.append(label)
func _initialize():call_deferred("run")
func make(db,fixture: String,indexed: bool):
	var s=Simulation.new(db) if indexed else Reference.new(db)
	s.start({"map":"map.01.04","faction":"deng" if fixture=="summons" else "yin","enemy":"bai" if fixture=="summons" else "mo","full_tech":true})
	s.ai_enabled=[false,false];s.units.clear();s.buildings.clear()
	for side in [0,1]:
		for i in range(60 if fixture=="army" else 12):
			var ids: Array=s.players[side].roster
			var u=s.spawn(ids[i%ids.size()],side,18+float(i%12)*.25+side*7)
			u.hp=10000;u.max_hp=u.hp
		if fixture=="workers":
			for i in range(3):s.spawn("unit."+s.players[side].faction+".worker",side,s.bases[side].x)
	s.visibility.refresh();s.drain_events()
	return s
func run():
	var db=Data.new()
	for fixture in ["army","workers","summons"]:
		var a=make(db,fixture,false);var b=make(db,fixture,true);var spawned: bool=false
		for step in range(120):
			a.tick(1.0/60.0);b.tick(1.0/60.0)
			var ea: Array=a.drain_events();var eb: Array=b.drain_events()
			for e in ea:
				if e.kind=="spawn":spawned=true
			verify(a.units==b.units,"all actor state identical %s step=%s"%[fixture,step])
			verify(ea==eb,"event order and contents identical")
			verify(a.players==b.players and a.stats==b.stats,"economic and ability state identical")
			verify(a.projectiles==b.projectiles and a.corpses==b.corpses,"projectile and corpse state identical")
		if fixture=="summons":verify(spawned,"fixture includes spawn during unit phase")
	print("TARGET_SEARCH_EQUIVALENCE: ",checks," checks; failures=",failures)
	quit(0 if failures.is_empty() else 1)
