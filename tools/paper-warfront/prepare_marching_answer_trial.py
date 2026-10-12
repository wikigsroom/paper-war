"""Try bounded marching answers against the complete frozen RC32 closure."""
from pathlib import Path
import hashlib
import json
import shutil

ROOT = Path(__file__).resolve().parents[2]
QA = ROOT / "output/qa/godot/phase-runtime-rc33"
TRIAL = QA / "marching-r1-runtime"
assert not TRIAL.exists()
shutil.copytree(QA / "baseline-runtime", TRIAL)
p = TRIAL / "scripts/battle_sim.gd"
s = p.read_text("utf-8")
declarations = '''# Marching answers are confined to the dense simultaneous unit phase.
# The exact ordered blocker geometry and eligibility are checked each phase.
var marching_answers_active: bool=false
var marching_answers_ready: bool=false
var marching_answers: Dictionary={}
var marching_snapshot: MarchingSnapshot
var marching_answer_hits: int=0
var marching_answer_misses: int=0
var marching_snapshot_reuses: int=0
var marching_snapshot_rebuilds: int=0

class MarchingAnswer:
\textends RefCounted
\tvar source: Dictionary={}
\tvar uid
\tvar side: int=0
\tvar edge: String=""
\tvar offset: float=0
\tvar reach: float=0
\tvar giant: bool=false
\tvar sees_enemy: bool=false
\tvar forward: float=0
\tvar requested: float=0
\tvar limit: float=0

class MarchingSnapshot:
\textends RefCounted
\tvar actors: Array[Dictionary]=[]
\tvar uids: Array=[]
\tvar edges: Array[String]=[]
\tvar offsets: PackedFloat64Array=PackedFloat64Array()
\tvar sides: PackedInt32Array=PackedInt32Array()
\tvar eligibility: PackedByteArray=PackedByteArray()
\tvar ranges: PackedFloat64Array=PackedFloat64Array()
\tfunc flags(a: Dictionary,d: Dictionary) -> int:
\t\treturn (1 if a.hp>0 else 0)+(2 if d.get("economy",false) else 0)+(4 if d.get("role","") in ["medic","engineer","necromancer","summoner","oracle","scribe"] else 0)
\tfunc matches(simulation) -> bool:
\t\tif actors.size()!=simulation.units.size():return false
\t\tfor index in range(actors.size()):
\t\t\tvar a: Dictionary=simulation.units[index]
\t\t\tif not is_same(a,actors[index]) or a.uid!=uids[index] or int(a.side)!=sides[index]:return false
\t\t\tvar anchor: Dictionary=simulation.movement_current_anchor if int(a.uid)==simulation.movement_current_uid else a
\t\t\tif anchor.edge!=edges[index] or float(anchor.s)!=offsets[index]:return false
\t\t\tvar d: Dictionary=simulation.db.balance.units[a.id]
\t\t\tif float(d.range)!=ranges[index] or flags(a,d)!=eligibility[index]:return false
\t\treturn true
\tfunc capture(simulation):
\t\tfor a in simulation.units:
\t\t\tvar anchor: Dictionary=simulation.movement_current_anchor if int(a.uid)==simulation.movement_current_uid else a
\t\t\tvar d: Dictionary=simulation.db.balance.units[a.id]
\t\t\tactors.append(a);uids.append(a.uid);edges.append(anchor.edge);offsets.append(float(anchor.s));sides.append(int(a.side))
\t\t\tranges.append(float(d.range));eligibility.append(flags(a,d))

func prepare_marching_answers():
\tif marching_answers_ready:return
\tif marching_snapshot!=null and marching_snapshot.matches(self):marching_snapshot_reuses+=1
\telse:
\t\tmarching_answers.clear();marching_snapshot=MarchingSnapshot.new();marching_snapshot.capture(self);marching_snapshot_rebuilds+=1
\tmarching_answers_ready=true

'''
assert s.count("class TargetAnswer:")==1
s=s.replace("class TargetAnswer:",declarations+"class TargetAnswer:")
start="\ttarget_answers.clear();target_answers_active=false;target_answers_generation=-1;target_answers_revision=-1;target_answers_eligibility=[];target_answer_hits=0;target_answer_misses=0"
assert s.count(start)==1
s=s.replace(start,start+"\n\tmarching_answers.clear();marching_answers_active=false;marching_answers_ready=false;marching_snapshot=null;marching_answer_hits=0;marching_answer_misses=0;marching_snapshot_reuses=0;marching_snapshot_rebuilds=0")
phase="\tprepare_movement_sides();movement_sides_active=true;target_answers_active=units.size()>=40"
assert s.count(phase)==1
s=s.replace(phase,phase+";marching_answers_active=target_answers_active")
end="\tcollecting_attacks=false;movement_sides_active=false;target_answers_active=false"
assert s.count(end)==1
s=s.replace(end,end+";marching_answers_active=false")
s=s.replace("\tblocker_roads_dirty=true;target_answers_revision=-1", "\tblocker_roads_dirty=true;target_answers_revision=-1;marching_answers_ready=false")
s=s.replace("\t\tmovement_side_units[side].append(u);blocker_roads_dirty=true", "\t\tmovement_side_units[side].append(u);blocker_roads_dirty=true;marching_answers_ready=false")
s=s.replace("\tif target_answers_active and target.hp<=0:target_answers.clear()", "\tif target_answers_active and target.hp<=0:target_answers.clear();marching_answers.clear()")
s=s.replace("\tif target_answers_active:target_answers.clear()", "\tif target_answers_active:target_answers.clear();marching_answers.clear()")
wrapper='''func marching_step(u: Dictionary,def: Dictionary,enemy: Dictionary,step: float,forward: float) -> float:
\tif not marching_answers_active or not movement_sides_active or step<=0 or not is_finite(step) or forward not in [-1.0,1.0]:return marching_step_uncached(u,def,enemy,step,forward)
\tif blocker_roads_dirty:prepare_blocker_roads()
\tif not blocker_roads_valid or not is_finite(float(u.s)):return marching_step_uncached(u,def,enemy,step,forward)
\tprepare_marching_answers()
\tvar side: int=int(u.side);var edge: String=u.edge;var offset: float=float(u.s)
\tvar reach: float=float(def.range);var giant: bool=def.get("role","")=="colossus";var sees_enemy: bool=not enemy.is_empty()
\tvar memo: MarchingAnswer=marching_answers.get(u.uid)
\tif memo!=null and is_same(memo.source,u) and memo.uid==u.uid and memo.side==side and memo.edge==edge and memo.offset==offset and memo.reach==reach and memo.giant==giant and memo.sees_enemy==sees_enemy and memo.forward==forward:
\t\tif memo.limit<memo.requested or step<=memo.requested:
\t\t\tmarching_answer_hits+=1;return minf(step,memo.limit) if memo.limit<memo.requested else step
\tvar result: float=marching_step_uncached(u,def,enemy,step,forward)
\tmemo=MarchingAnswer.new();memo.source=u;memo.uid=u.uid;memo.side=side;memo.edge=edge;memo.offset=offset;memo.reach=reach;memo.giant=giant;memo.sees_enemy=sees_enemy;memo.forward=forward;memo.requested=step;memo.limit=result
\tif marching_answers.size()>=256 and not marching_answers.has(u.uid):marching_answers.clear()
\tmarching_answers[u.uid]=memo;marching_answer_misses+=1
\treturn result

func marching_step_uncached(u: Dictionary,def: Dictionary,enemy: Dictionary,step: float,forward: float) -> float:
'''
old="func marching_step(u: Dictionary,def: Dictionary,enemy: Dictionary,step: float,forward: float) -> float:\n"
assert s.count(old)==1
s=s.replace(old,wrapper)
p.write_text(s,"utf-8")
old_qa=ROOT/"output/qa/godot/contact-runtime-rc32"
observer=(old_qa/"answers-capacity-observer.gd").read_text("utf-8")
observer=observer.replace('"answer_hits":b.target_answer_hits','"marching_hits":b.marching_answer_hits,"marching_misses":b.marching_answer_misses,"marching_snapshot_reuses":b.marching_snapshot_reuses,"marching_snapshot_rebuilds":b.marching_snapshot_rebuilds,"answer_hits":b.target_answer_hits')
observer=observer.replace("frozen complete rc31 script closure","frozen complete rc32 script closure")
(QA/"marching-capacity-observer.gd").write_text(observer,"utf-8")
paid=(old_qa/"lookup-paid-observer.gd").read_text("utf-8").replace("frozen complete rc31 script closure","frozen complete rc32 script closure")
(QA/"marching-paid-observer.gd").write_text(paid,"utf-8")
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
(QA/"marching-r1-manifest.json").write_text(json.dumps({"generator_sha256":sha(Path(__file__)),
    "baseline_simulation_sha256":sha(QA/"baseline-runtime/scripts/battle_sim.gd"),"candidate_simulation_sha256":sha(p),
    "candidate_inputs":{p.relative_to(TRIAL).as_posix():sha(p) for p in TRIAL.rglob("*") if p.is_file() and ".godot" not in p.parts},
    "scope":"Isolated candidate, no formal changes. Exact ordered unit/blocker snapshot once per dense phase; bounded256 source answers, exact source/query parameters, spawn/reorder/class/side/liveness geometry checks and lethal damage/TTL invalidation. Positive finite ordinary directions only; original scalar/index query retained for misses and all external or small-army calls. Result-step memo reuses only a proven collision limit or a no-clamp request of equal/smaller step."
},indent=2)+"\n","utf-8")
print("Prepared isolated dense marching-answer R1 against RC32")
