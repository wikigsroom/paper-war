extends SceneTree
const Data=preload("res://scripts/data_store.gd")
const Simulation=preload("res://scripts/battle_sim.gd")
var failures: Array=[]
var checks: int=0
func verify(ok: bool,note: String):
	checks+=1
	if not ok:failures.append(note)
func _initialize():call_deferred("run")
func run():
	var db=Data.new()
	for side in [0,1]:
		var s=Simulation.new(db);s.start({"map":"map.01.04","faction":"mo","enemy":"mo"});s.ai_enabled=[false,false];s.units.clear()
		var direction: float=1 if side==0 else -1
		var u=s.spawn("unit.mo.blade",side,20);u.facing=direction
		var ally=s.spawn("unit.mo.blade",side,20+direction)
		var desired: float=float(u.s)+direction*2
		verify(is_equal_approx(s.leap_landing(u,desired),float(ally.s)-direction*.54),"melee screen clamps closing leap on side "+str(side))
		ally.hp=0
		verify(is_equal_approx(s.leap_landing(u,desired),desired),"dead screen does not block leap")
		ally.hp=100;ally.id="unit.mo.needle"
		verify(is_equal_approx(s.leap_landing(u,desired),desired),"backliner does not prevent melee advance")
		ally.id="unit.mo.blade"
		var enemy=s.spawn("unit.mo.blade",1-side,20+direction*2);enemy.special_cd=100
		s.visibility.refresh();s.tick_unit(u,1.0/60.0)
		verify((float(ally.s)-float(u.s))*direction>=.539,"actual unit tick preserves spacing during closing leap")
	print("LEAP_SPACING: ",checks," checks; failures=",failures);quit(0 if failures.is_empty() else 1)
