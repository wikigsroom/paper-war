extends SceneTree
const Data=preload("res://scripts/data_store.gd")
const Simulation=preload("res://scripts/battle_sim.gd")
var failures: Array=[]
var checks: int=0
func verify(ok: bool,note: String):
	checks+=1
	if not ok:failures.append(note)
func own_alerts(s) -> Array:
	return s.drain_events().filter(func(e):return e.kind=="scouted" and int(e.observer)==0)
func run():
	var db=Data.new();var s=Simulation.new(db)
	s.start({"map":"map.01.01","faction":"yin","enemy":"mo","starting_gold":1000,"full_tech":true})
	s.ai_enabled=[false,false];s.units.clear();s.drain_events();s.time=10
	var giant=s.spawn("unit.mo.giant",1,25);s.visibility.refresh()
	verify(own_alerts(s).is_empty(),"hidden giant emits no own scouting alert")
	var scout=s.spawn("unit.yin.axe",0,23);s.visibility.refresh()
	var alerts: Array=own_alerts(s)
	verify(alerts.size()==1 and alerts[0].id==giant.id,"real reveal identifies giant once")
	verify(s.event_visible(0,alerts[0]),"scouting event obeys normal information gate")
	s.visibility.refresh();verify(own_alerts(s).is_empty(),"repeated information queries do not duplicate alerts")
	s.map.apply_anchor(scout,s.map.at_node(s.map.definition.bases[0].node,0));s.visibility.refresh();s.drain_events()
	verify(not s.visible_to(0,giant),"retreat loses real-time enemy visibility")
	s.map.apply_anchor(scout,s.map.project(Vector2(23,0)));s.time=30;s.visibility.refresh()
	verify(own_alerts(s).is_empty(),"revisiting same actor does not imply a new enemy arrival")
	s.spawn("unit.mo.giant",1,26);s.visibility.refresh()
	verify(own_alerts(s).size()==1,"a newly revealed threat can alert after cooldown")
	print("SCOUT_ALERTS: ",checks," checks; failures=",failures)
	quit(0 if failures.is_empty() else 1)
func _initialize():call_deferred("run")
