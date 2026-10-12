"""Prepare independent all-map blocker and full-closure phase checks outside the trial."""
from pathlib import Path
import hashlib
import json

ROOT=Path(__file__).resolve().parents[2]
QA=ROOT/"output/qa/godot/phase-runtime-rc33"
old=ROOT/"output/qa/godot/contact-runtime-rc32/answers-phase-observer.gd"
phase=QA/"marching-phase-observer.gd"
boundary=QA/"marching-boundary-observer.gd"
assert not phase.exists() and not boundary.exists()
s=old.read_text("utf-8")
s=s.replace('check(b.target_answers.size()<=256,"bounded references")','check(b.target_answers.size()<=256,"bounded references")\n\t\t\t\tcheck(b.marching_answers.size()<=256,"bounded marching references")\n\t\t\t\tcheck(not b.marching_answers_active,"outside phase marching bypass")')
s=s.replace('check(b.target_answers.size()<=256,"300-source cap bound")','check(b.target_answers.size()<=256,"300-source cap bound");check(b.marching_answers.size()<=256,"300-source marching cap")')
s=s.replace('check(b.target_answers.is_empty() and not b.target_answers_active and b.target_answer_hits==0,"restart releases references and counters")','check(b.target_answers.is_empty() and not b.target_answers_active and b.target_answer_hits==0,"restart releases references and counters")\n\tcheck(b.marching_answers.is_empty() and not b.marching_answers_active and b.marching_snapshot==null and b.marching_answer_hits==0,"restart releases marching references and counters")')
s=s.replace("Frozen RC31 complete closure","Frozen RC32 complete closure")
phase.write_text(s,"utf-8")
boundary.write_text('''extends SceneTree
const Data=preload("res://scripts/data_store.gd")
const Simulation=preload("res://scripts/battle_sim.gd")
var checks: int=0
var failures: Array=[]
func _initialize():call_deferred("run")
func check(ok: bool,label: String):
\tchecks+=1
\tif not ok and failures.size()<20:failures.append(label)
# Independently retained pre-index linear collision rule; no candidate helpers.
func reference(s,u: Dictionary,d: Dictionary,enemy: Dictionary,step: float,forward: float) -> float:
\tfor a in s.units if step>0 else []:
\t\tif a.uid==u.uid or a.side!=u.side or a.hp<=0 or a.edge!=u.edge or s.db.balance.units[a.id].get("economy",false):continue
\t\tvar other: Dictionary=s.db.balance.units[a.id]
\t\tif float(d.range)<=1.5 and (float(other.range)>1.5 or other.get("role","") in ["medic","engineer","necromancer","summoner","oracle","scribe"]):continue
\t\tif not enemy.is_empty() and float(d.range)>1.5 and float(other.range)>float(d.range)+.05:continue
\t\tvar ahead: float=(float(a.s)-float(u.s))*forward
\t\tif ahead>0:
\t\t\tvar gap: float=.72 if d.get("role","")=="colossus" else .54
\t\t\tstep=minf(step,maxf(0,ahead-gap))
\t\t\tif step==0:break
\treturn step
func prepare(s):
\ts.prepare_movement_sides();s.movement_sides_active=true;s.target_answers_active=true;s.marching_answers_active=true
func compare(s,u: Dictionary,enemy: Dictionary,step: float,label: String,forward: float=NAN):
\tvar d: Dictionary=s.db.balance.units[u.id]
\tif is_nan(forward):forward=1 if int(u.side)==0 else -1
\tvar expected: float=reference(s,u,d,enemy,step,forward)
\tvar actual: float=s.marching_step(u,d,enemy,step,forward)
\tcheck(actual==expected or (is_nan(actual) and is_nan(expected)),label+" actual="+str(actual)+" expected="+str(expected))
func series(s,actors: Array,count: int,label: String):
\tfor i in range(mini(count,actors.size())):
\t\tfor step in [.00000001,.05,2.0,.01,3.0,.001]:
\t\t\tcompare(s,actors[i],{} if i%2==0 else s.bases[1-int(actors[i].side)],step,label+"/"+str(i)+"/"+str(step))
func run():
\tvar db=Data.new();var maps: int=0;var fixtures: int=0
\tfor definition in db.maps.values():
\t\tmaps+=1
\t\tfor side in [0,1]:
\t\t\tfixtures+=1
\t\t\tvar s=Simulation.new(db);s.start({"map":definition.id,"faction":"yin","enemy":"mo","full_tech":true});s.ai_enabled=[false,false];s.units.clear()
\t\t\tvar ids: Array=db.all_unit_ids("yin" if side==0 else "mo");var actors: Array=[];var edges: Array=s.map.edges.keys()
\t\t\tfor i in range(60):
\t\t\t\tvar u=s.spawn(ids[i%ids.size()],side,3);var edge: String=edges[i%edges.size()]
\t\t\t\ts.map.apply_anchor(u,s.map.anchor(edge,float(s.map.edges[edge].length)*(.2+float(i%4)*.15)));actors.append(u)
\t\t\tprepare(s);series(s,actors,60,definition.id+" initial")
\t\t\tprepare(s);series(s,actors,12,definition.id+" unchanged phase")
\t\t\t# Real lethal damage must invalidate already-proven collision limits immediately.
\t\t\ts.damage(actors[3],1000000,1-int(actors[3].side),false);series(s,actors,12,definition.id+" lethal same phase")
\t\t\tactors[7].side=1-int(actors[7].side);prepare(s);series(s,actors,12,definition.id+" ownership")
\t\t\tvar born=s.spawn(ids[1],side,3);s.map.apply_anchor(born,s.map.anchor(actors[5].edge,float(actors[5].s)+(.55 if side==0 else -.55)));series(s,actors,12,definition.id+" phase-born")
\t\t\tactors[5].s=float(actors[5].s)+.0000000001;prepare(s);series(s,actors,12,definition.id+" exact float64 position")
\t\t\ts.units=s.units.map(func(a):return a.duplicate(true));s.units.reverse();actors=s.units.slice(0,12);prepare(s);series(s,actors,12,definition.id+" replacement reorder")
\t\t\tactors[0].uid=actors[1].uid;actors[2].uid=float(actors[3].uid)+.25;prepare(s);series(s,actors,12,definition.id+" duplicate floating UID")
\t\t\t# Explicit dirty-index requests during a phase must also recheck cached answers.
\t\t\tactors[1].s=float(actors[1].s)+.0000000001;s.blocker_roads_dirty=true;series(s,actors,12,definition.id+" explicit dirty position")
\t\t\tactors[1].s=INF;prepare(s);series(s,actors,12,definition.id+" nonfinite fallback")
\t\t\ts.marching_answers_active=false;s.movement_sides_active=false;series(s,actors,12,definition.id+" outside phase")
\t\t\tcheck(s.marching_answers.size()<=256,"bounded cache")
\t\tif maps%20==0:print("MARCHING_BOUNDARIES maps=",maps," checks=",checks," failures=",failures.size())
\t# The old index treats even nonblocking economy offsets as validity input.
\tvar s=Simulation.new(db);s.start({"map":"map.01.04","faction":"yin","enemy":"mu"});s.ai_enabled=[false,false];s.units.clear()
\tvar worker_ids: Array=db.all_unit_ids("yin").filter(func(id):return db.balance.units[id].get("economy",false))
\tvar worker=s.spawn(worker_ids[0],0,3);var a=s.spawn("unit.yin.axe",0,3);var front=s.spawn("unit.yin.axe",0,3.55)
\tprepare(s);compare(s,a,{},.1,"initial worker validity")
\tworker.s=INF;prepare(s);compare(s,a,{},.1,"nonblocking worker INF")
\tcheck(not s.blocker_roads_valid,"worker nonfinite retains old fallback")
\tworker.s=3;worker.id="unit.yin.axe";prepare(s);compare(s,a,{},.1,"economy becomes combat blocker")
\tfront.s=float(a.s)+.54+.0000000001;prepare(s)
\tfor step in [.05,.000000001,.00000000001,.0000001,.2,0.0,-.1,INF,NAN]:compare(s,a,{},step,"gap precision and step ordering")
\tfor forward in [0.0,.5,-.5]:compare(s,a,{},.1,"nonstandard direction",forward)
\tvar output: String=OS.get_cmdline_user_args()[0]
\tFileAccess.open(output,FileAccess.WRITE).store_string(JSON.stringify({"passed":failures.is_empty(),"checks":checks,"failures":failures,"maps":maps,"fixtures":fixtures,"observer_sha256":FileAccess.get_sha256(get_script().resource_path),"simulation_sha256":FileAccess.get_sha256("res://scripts/battle_sim.gd"),"scope":"All200 authored maps and both directions against independently retained full linear blocker rule. Cache hits across varying requested steps; liveness via real damage, ownership, phase spawn, exact float64 changes, dirty-index requests, replacement/reorder, duplicate/floating UIDs, invalid offsets including nonblocking economy, economy-to-combat classification, precision, nonstandard direction and outside-phase API. Controlled phase fixtures, not paid balance/FPS/hardware."},"  "))
\tprint("MARCHING_BOUNDARIES: ",checks," checks; failures=",failures)
\tquit(0 if failures.is_empty() else 1)
''',"utf-8")
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
(QA/"marching-observers-generation.json").write_text(json.dumps({"generator_sha256":sha(Path(__file__)),"original_phase_observer_sha256":sha(old),"phase_observer_sha256":sha(phase),"boundary_observer_sha256":sha(boundary),"scope":"New uninstrumented semantic observers, stored outside all frozen trial projects; no runtime/source mutations."},indent=2)+"\n","utf-8")
print("Prepared all-map independent blocker and30 full-closure faction phase observers")
