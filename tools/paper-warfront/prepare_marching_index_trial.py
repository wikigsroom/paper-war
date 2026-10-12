"""Keep R1/R2 evidence; let R3 reuse the exact matching sorted blocker index too."""
from pathlib import Path
import hashlib
import json
import shutil

ROOT=Path(__file__).resolve().parents[2]
QA=ROOT/"output/qa/godot/phase-runtime-rc33"
TRIAL=QA/"marching-r3-runtime"
assert not TRIAL.exists()
shutil.copytree(QA/"marching-r2-runtime",TRIAL,ignore=shutil.ignore_patterns(".godot"))
p=TRIAL/"scripts/battle_sim.gd"
s=p.read_text("utf-8")
head="class MarchingSnapshot:\n\textends RefCounted\n"
assert s.count(head)==1
s=s.replace(head,head+"\tvar roads: Array=[{},{}]\n\tvar valid: bool=true\n")
start=s.index("\tfunc matches(simulation) -> bool:\n",s.index("class MarchingSnapshot:"))
end=s.index("\nclass TargetAnswer:",start)
replacement='''\tfunc matches(simulation) -> bool:
\t\tvar index: int=0;var current_valid: bool=true
\t\tfor a in simulation.units:
\t\t\tvar anchor: Dictionary=simulation.movement_current_anchor if int(a.uid)==simulation.movement_current_uid else a
\t\t\tif not is_finite(float(anchor.s)):current_valid=false
\t\t\tvar d: Dictionary=simulation.db.balance.units[a.id]
\t\t\tif a.hp<=0 or d.get("economy",false):continue
\t\t\tif index>=actors.size() or not is_same(a,actors[index]) or a.uid!=uids[index] or int(a.side)!=sides[index]:return false
\t\t\tif anchor.edge!=edges[index] or float(anchor.s)!=offsets[index]:return false
\t\t\tif float(d.range)!=ranges[index] or flags(a,d)!=eligibility[index]:return false
\t\t\tindex+=1
\t\treturn index==actors.size() and current_valid==valid
\tfunc capture(simulation):
\t\troads=simulation.blocker_roads;valid=simulation.blocker_roads_valid
\t\tfor a in simulation.units:
\t\t\tvar d: Dictionary=simulation.db.balance.units[a.id]
\t\t\tif a.hp<=0 or d.get("economy",false):continue
\t\t\tvar anchor: Dictionary=simulation.movement_current_anchor if int(a.uid)==simulation.movement_current_uid else a
\t\t\tactors.append(a);uids.append(a.uid);edges.append(anchor.edge);offsets.append(float(anchor.s));sides.append(int(a.side))
\t\t\tranges.append(float(d.range));eligibility.append(flags(a,d))

func prepare_marching_answers():
\tif marching_answers_ready:return
\tif marching_snapshot!=null and marching_snapshot.matches(self):
\t\tmarching_snapshot_reuses+=1;blocker_roads=marching_snapshot.roads;blocker_roads_valid=marching_snapshot.valid;blocker_roads_dirty=false
\telse:
\t\tmarching_answers.clear()
\t\tif blocker_roads_dirty:prepare_blocker_roads()
\t\tmarching_snapshot=MarchingSnapshot.new();marching_snapshot.capture(self);marching_snapshot_rebuilds+=1
\tmarching_answers_ready=true
'''
s=s[:start]+replacement+s[end:]
old="\tif blocker_roads_dirty:prepare_blocker_roads()\n\tif not blocker_roads_valid or not is_finite(float(u.s)):return marching_step_uncached(u,def,enemy,step,forward)\n\tprepare_marching_answers()"
new="\tif blocker_roads_dirty and marching_answers_ready:marching_answers_ready=false\n\tprepare_marching_answers()\n\tif not blocker_roads_valid or not is_finite(float(u.s)):return marching_step_uncached(u,def,enemy,step,forward)"
assert s.count(old)==1
s=s.replace(old,new)
p.write_text(s,"utf-8")
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
(QA/"marching-r3-manifest.json").write_text(json.dumps({"generator_sha256":sha(Path(__file__)),
    "parent_manifest_sha256":sha(QA/"marching-r2-manifest.json"),"parent_capacity_receipt_sha256":sha(QA/"marching-capacity-r2-receipt.json"),
    "baseline_simulation_sha256":sha(QA/"baseline-runtime/scripts/battle_sim.gd"),"candidate_simulation_sha256":sha(p),
    "candidate_inputs":{p.relative_to(TRIAL).as_posix():sha(p) for p in TRIAL.rglob("*") if p.is_file() and ".godot" not in p.parts},
    "scope":"Isolated R3: reuse the separately retained sorted blocker roads only after exact ordered live blocker identity/UID/edge/float64 offset/side/range/role match. Include original all-unit nonfinite validity behavior, even dead/economic actors. Explicit dirty-index requests revalidate a ready snapshot. Other bounded phase-only R2 answer contracts retained; no formal changes."
},indent=2)+"\n","utf-8")
runner=ROOT/"tools/paper-warfront/run_rc33_marching_filtered_capacity.py"
new=ROOT/"tools/paper-warfront/run_rc33_marching_index_capacity.py"
assert not new.exists()
new.write_text(runner.read_text("utf-8").replace("marching-r2","marching-r3").replace("marching-capacity-r2","marching-capacity-r3").replace("marching R2","marching R3"),"utf-8")
(QA/"marching-r3-runner-generation.json").write_text(json.dumps({"original_runner_sha256":sha(runner),"runner_sha256":sha(new),"generator_sha256":sha(Path(__file__))},indent=2)+"\n","utf-8")
print("Prepared R3 with matched sorted-index reuse and original nonfinite fallback")
