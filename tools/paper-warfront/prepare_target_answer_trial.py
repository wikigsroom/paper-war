"""Prototype bounded nearest-target answers only inside the native dense unit phase."""
from pathlib import Path
import hashlib
import json
import shutil

ROOT = Path(__file__).resolve().parents[2]
QA = ROOT / "output/qa/godot/contact-runtime-rc32"
TRIAL = QA / "answers-r1-runtime"
assert not TRIAL.exists()
shutil.copytree(QA / "lookup-r1-runtime", TRIAL)
p = TRIAL / "scripts/battle_sim.gd"
s = p.read_text("utf-8")
declarations = '''# Answers are used only inside tick's dense simultaneous unit phase.
# Geometry comes from the exact existing snapshots; eligibility is separate.
var target_answers_active: bool=false
var target_answers: Dictionary={}
var target_answers_generation: int=-1
var target_answers_revision: int=-1
var target_answers_eligibility: Array=[]
var target_answer_hits: int=0
var target_answer_misses: int=0

class TargetAnswer:
\textends RefCounted
\tvar source: Dictionary={}
\tvar target: Dictionary={}
\tvar edge: String=""
\tvar offset: float=0
\tvar point: Vector2=Vector2.ZERO
\tvar side: int=0
\tvar melee: bool=false
\tvar priority: bool=false
\tvar reach: float=0

func prepare_target_answers():
\tif target_answers_revision==visibility.revision:return
\tprepare_target_snapshot()
\tvar eligibility: Array=[]
\tfor side in [0,1]:
\t\tvar flags: PackedInt32Array=PackedInt32Array()
\t\tfor a in visibility.enemies[side]:flags.append(int(a.side)*2+(1 if a.hp>0 else 0))
\t\teligibility.append(flags)
\tif target_answers_generation!=target_snapshot_generation or eligibility!=target_answers_eligibility:target_answers.clear()
\ttarget_answers_generation=target_snapshot_generation
\ttarget_answers_eligibility=eligibility;target_answers_revision=visibility.revision

'''
s = s.replace("class TargetGeometrySnapshot:", declarations+"class TargetGeometrySnapshot:")
start = "\tmelee_snapshot_generation=-1;ranged_snapshot_generation=-1;target_snapshot_reuses=0;target_snapshot_rebuilds=0"
assert s.count(start)==1
s = s.replace(start,start+"\n\ttarget_answers.clear();target_answers_active=false;target_answers_generation=-1;target_answers_revision=-1;target_answers_eligibility=[];target_answer_hits=0;target_answer_misses=0")
phase = "\tprepare_movement_sides();movement_sides_active=true"
assert s.count(phase)==1
s = s.replace(phase,phase+";target_answers_active=units.size()>=40")
s = s.replace("\tcollecting_attacks=false;movement_sides_active=false", "\tcollecting_attacks=false;movement_sides_active=false;target_answers_active=false")
s = s.replace("\tblocker_roads_dirty=true\n\tmelee_query_revision=-1", "\tblocker_roads_dirty=true;target_answers_revision=-1\n\tmelee_query_revision=-1")
# Eligibility changes within the controlled phase invalidate every prior answer.
s = s.replace("\ttarget.hp=maxf(0.0,target.hp-actual)", "\ttarget.hp=maxf(0.0,target.hp-actual)\n\tif target_answers_active and target.hp<=0:target_answers.clear()")
s = s.replace("\tu.hp=0.0\n\tvar def = db.balance.units[u.id]", "\tu.hp=0.0\n\tif target_answers_active:target_answers.clear()\n\tvar def = db.balance.units[u.id]")
wrapper = '''func nearest_enemy(u: Dictionary) -> Dictionary:
\tif not target_answers_active:return nearest_enemy_uncached(u)
\tprepare_target_answers()
\tvar def: Dictionary=db.balance.buildings[u.id] if u.get("building",false) else db.balance.units[u.id]
\tvar anchor: Dictionary=physical_anchor(u)
\tvar melee: bool=str(def.get("attack","projectile")).begins_with("melee")
\tvar priority: bool=bool(def.get("support_priority",false)) and not u.get("building",false)
\tvar reach: float=float(def.range) if priority else 0.0
\tvar point: Vector2=Vector2.ZERO if melee else Vector2(anchor.x,anchor.y)
\tvar side: int=int(u.side)
\tvar memo: TargetAnswer=target_answers.get(u.uid)
\tif memo!=null and is_same(memo.source,u) and memo.side==side and memo.melee==melee and memo.priority==priority and memo.reach==reach and memo.edge==anchor.edge and memo.offset==float(anchor.s) and memo.point==point:
\t\tif memo.target.is_empty() or (memo.target.hp>0 and int(memo.target.side)!=side):
\t\t\ttarget_answer_hits+=1;return memo.target
\tvar result: Dictionary=nearest_enemy_uncached(u)
\tmemo=TargetAnswer.new();memo.source=u;memo.target=result;memo.side=side;memo.melee=melee;memo.priority=priority;memo.reach=reach;memo.edge=anchor.edge;memo.offset=float(anchor.s);memo.point=point
\t# At most256 source references, regardless of a long match's UID growth.
\tif target_answers.size()>=256 and not target_answers.has(u.uid):target_answers.clear()
\ttarget_answers[u.uid]=memo;target_answer_misses+=1
\treturn result

func nearest_enemy_uncached(u: Dictionary) -> Dictionary:
'''
old = "func nearest_enemy(u: Dictionary) -> Dictionary:\n"
assert s.count(old)==1
s = s.replace(old,wrapper)
p.write_text(s,"utf-8")
observer = (QA / "lookup-capacity-observer.gd").read_text("utf-8")
observer = observer.replace('"snapshot_reuses":b.target_snapshot_reuses', '"answer_hits":b.target_answer_hits,"answer_misses":b.target_answer_misses,"snapshot_reuses":b.target_snapshot_reuses')
(QA / "answers-capacity-observer.gd").write_text(observer,"utf-8")
sha = lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
(QA / "answers-r1-manifest.json").write_text(json.dumps({"generator_sha256":sha(Path(__file__)),
    "original_simulation_sha256":sha(QA / "lookup-r1-runtime/scripts/battle_sim.gd"),"candidate_simulation_sha256":sha(p),
    "candidate_inputs":{p.relative_to(TRIAL).as_posix():sha(p) for p in TRIAL.rglob("*") if p.is_file()},
    "scope":"Isolated candidate only. Existing geometry snapshots plus per-phase live eligibility; source anchor/side/weapon parameters exact; phase-only bounded answers and immediate lethal-damage/TTL invalidation. Normal small armies and all external queries use original uncached selector."
},indent=2)+"\n","utf-8")
print("Prepared dense target-answer R1")
