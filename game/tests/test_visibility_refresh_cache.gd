extends SceneTree

const Data=preload("res://scripts/data_store.gd")
const Simulation=preload("res://scripts/battle_sim.gd")

var checks: int=0
var failures: Array=[]

func verify(value: bool,note: String):
	checks+=1
	if not value:failures.append(note)

func _initialize():call_deferred("run")

func run():
	var db=Data.new()
	var sim=Simulation.new(db)
	sim.start({"map":"map.01.01","faction":"yin","enemy":"mo","full_tech":true,"starting_gold":1000})
	sim.ai_enabled=[false,false]

	var initial_revision: int=sim.visibility.revision
	verify(not sim.visibility.dirty,"start refresh clears dirty flag")
	verify(not sim.visibility.refresh(false),"clean non-forced refresh is skipped")
	verify(sim.visibility.revision==initial_revision,"skipped refresh keeps revision")

	var scout: Dictionary=sim.spawn("unit.yin.axe",0,sim.bases[0].x+2.0)
	verify(sim.visibility.dirty,"spawn invalidates visibility")
	var spawned_revision: int=sim.visibility.revision
	verify(sim.visibility.refresh(false),"spawned unit refreshes visibility")
	verify(sim.visibility.revision==spawned_revision+1,"spawn refresh advances revision")
	verify(not sim.visibility.refresh(false),"second clean refresh is skipped")

	sim.visibility.mark_dirty()
	verify(sim.visibility.refresh(false),"explicit geometry invalidation refreshes")
	verify(not sim.visibility.refresh(false),"explicit invalidation is consumed")

	var enemy: Dictionary=sim.spawn("unit.mo.giant",1,sim.bases[1].x-2.0)
	sim.visibility.refresh()
	sim.visibility.reveal_attack(enemy,scout)
	verify(sim.visibility.dirty,"firing reveal invalidates visibility")
	verify(sim.visibility.refresh(false),"firing reveal refreshes immediately")
	sim.time+=1.5
	verify(sim.visibility.refresh_needed(),"expired firing reveal requests refresh")
	verify(sim.visibility.refresh(false),"expired firing reveal is consumed")

	var forced_revision: int=sim.visibility.revision
	verify(sim.visibility.refresh(),"forced refresh always runs")
	verify(sim.visibility.revision==forced_revision+1,"forced refresh advances revision")

	print("VISIBILITY_REFRESH_CACHE: ",checks," checks; failures=",failures)
	quit(0 if failures.is_empty() else 1)
