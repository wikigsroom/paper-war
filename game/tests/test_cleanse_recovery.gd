extends SceneTree
const Data=preload("res://scripts/data_store.gd")
const Simulation=preload("res://scripts/battle_sim.gd")
const Abilities=preload("res://scripts/unit_abilities.gd")
var checks: int=0
var failures: Array=[]
func verify(ok: bool,note: String):
	checks+=1
	if not ok:failures.append(note)
func _initialize():call_deferred("run")
func run():
	var db=Data.new();var s=Simulation.new(db)
	s.start({"map":"map.01.01","faction":"mu","enemy":"mo","starting_gold":0});s.ai_enabled=[false,false];s.units.clear();s.buildings.clear()
	var medic=s.spawn("unit.mu.medic",0,20);var guard=s.spawn("unit.mu.guard",0,20.5);var seed=s.spawn("unit.mu.poisoner",0,21)
	seed.hp=10;s.set_status(guard,"poison",3,4,1);medic.ability_clock=0;medic.summon_cd=0
	Abilities.tick(s,medic,db.balance.units[medic.id],.1)
	verify(not guard.statuses.has("poison"),"new full-health poisoned front receives cleanse")
	verify(guard.hp==guard.max_hp and seed.hp==10 and s.stats[0].healed==0,"cleanse invents no health or healed statistics")
	verify(medic.summon_cd==3,"cleanse consumes real support cooldown")
	guard.hp-=20;s.set_status(guard,"burn",3,4,1);medic.ability_clock=0;medic.summon_cd=0
	Abilities.tick(s,medic,db.balance.units[medic.id],.1)
	verify(not guard.statuses.has("burn") and guard.hp==guard.max_hp,"afflicted ally receives capped healing and cleanse")
	medic.ability_clock=0;medic.summon_cd=0
	Abilities.tick(s,medic,db.balance.units[medic.id],.1)
	verify(seed.hp==33,"ordinary wounds still selected without affliction")
	guard.hp-=20;guard.hurt=0;s.players[0].mana=0
	Abilities.tick(s,guard,db.balance.units[guard.id],1)
	verify(is_equal_approx(guard.hp,guard.max_hp-17.5) and s.players[0].mana>0,"cleansed wounded front resumes growth recovery and mana")
	print("CLEANSE_RECOVERY: ",checks," checks; failures=",failures);quit(0 if failures.is_empty() else 1)
