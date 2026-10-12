extends SceneTree
const Data=preload("res://scripts/data_store.gd")
const Simulation=preload("res://scripts/battle_sim.gd")
var checks: int=0
var failures: Array=[]
func verify(value: bool,note: String):
	checks+=1
	if not value:failures.append(note)
func run():
	var db=Data.new()
	var s=Simulation.new(db)
	s.start({"map":"map.01.01","faction":"yin","enemy":"mo","full_tech":true,"fog":false})
	s.ai_enabled=[false,false]
	var a=s.spawn("unit.yin.axe",0,18)
	var b=s.spawn("unit.yin.spear",0,19)
	a.windup=.4;a.cooldown=1.0
	verify(s.request(0,"cast",{"id":"spell.yin.fury","target":a.uid}).ok,"rage legal")
	verify(a.windup<=.08 and a.cooldown<=.08,"initiative affects current attack")
	verify(b.statuses.has("fury"),"nearby formation joins charge")
	s.players[1].mana=100
	verify(s.request(1,"cast",{"id":"spell.mo.poison","x":20,"y":s.map.ground_y_at(20)}).ok,"zone legal")
	verify(s.spell_areas.size()==1,"lasting zone exists")
	var late=s.spawn("unit.yin.axe",0,20)
	late["speed_override"]=0.0
	var outside=s.spawn("unit.yin.axe",0,10)
	outside["speed_override"]=0.0
	var hp: float=late.hp
	for i in range(60):s.tick(1.0/60.0)
	verify(late.statuses.has("poison") and late.hp<hp,"later entrant takes poison")
	verify(not outside.statuses.has("poison"),"outside radius unaffected")
	for i in range(360):s.tick(1.0/60.0)
	verify(s.spell_areas.is_empty(),"area expires")
	print("CORE_SPELL_WINDOWS: ",checks," checks; failures=",failures)
	quit(0 if failures.is_empty() else 1)
func _initialize():call_deferred("run")
