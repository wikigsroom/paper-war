"""Retain rejected R1; exclude non-blockers from R2 geometry comparison."""
from pathlib import Path
import hashlib
import json
import shutil

ROOT=Path(__file__).resolve().parents[2]
QA=ROOT/"output/qa/godot/phase-runtime-rc33"
SOURCE=QA/"marching-r1-runtime"
TRIAL=QA/"marching-r2-runtime"
assert not TRIAL.exists()
shutil.copytree(SOURCE,TRIAL,ignore=shutil.ignore_patterns(".godot"))
p=TRIAL/"scripts/battle_sim.gd"
s=p.read_text("utf-8")
start=s.index("\tfunc matches(simulation) -> bool:\n",s.index("class MarchingSnapshot:"))
end=s.index("\nfunc prepare_marching_answers():",start)
replacement='''\tfunc matches(simulation) -> bool:
\t\tvar index: int=0
\t\tfor a in simulation.units:
\t\t\tvar d: Dictionary=simulation.db.balance.units[a.id]
\t\t\t# Economy bodies and dead actors never enter the original blocker index.
\t\t\tif a.hp<=0 or d.get("economy",false):continue
\t\t\tif index>=actors.size() or not is_same(a,actors[index]) or a.uid!=uids[index] or int(a.side)!=sides[index]:return false
\t\t\tvar anchor: Dictionary=simulation.movement_current_anchor if int(a.uid)==simulation.movement_current_uid else a
\t\t\tif anchor.edge!=edges[index] or float(anchor.s)!=offsets[index]:return false
\t\t\tif float(d.range)!=ranges[index] or flags(a,d)!=eligibility[index]:return false
\t\t\tindex+=1
\t\treturn index==actors.size()
\tfunc capture(simulation):
\t\tfor a in simulation.units:
\t\t\tvar d: Dictionary=simulation.db.balance.units[a.id]
\t\t\tif a.hp<=0 or d.get("economy",false):continue
\t\t\tvar anchor: Dictionary=simulation.movement_current_anchor if int(a.uid)==simulation.movement_current_uid else a
\t\t\tactors.append(a);uids.append(a.uid);edges.append(anchor.edge);offsets.append(float(anchor.s));sides.append(int(a.side))
\t\t\tranges.append(float(d.range));eligibility.append(flags(a,d))
'''
s=s[:start]+replacement+s[end:]
p.write_text(s,"utf-8")
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
(QA/"marching-r2-manifest.json").write_text(json.dumps({"generator_sha256":sha(Path(__file__)),
    "parent_manifest_sha256":sha(QA/"marching-r1-manifest.json"),"rejected_parent_receipt_sha256":sha(QA/"marching-capacity-r1-receipt.json"),
    "baseline_simulation_sha256":sha(QA/"baseline-runtime/scripts/battle_sim.gd"),"candidate_simulation_sha256":sha(p),
    "candidate_inputs":{p.relative_to(TRIAL).as_posix():sha(p) for p in TRIAL.rglob("*") if p.is_file() and ".godot" not in p.parts},
    "scope":"R2 isolated trial: live combat blockers only in ordered geometry snapshot. All units are reclassified each phase, so death/worker-to-combat changes still invalidate. Other R1 contracts unchanged. Rejected slower R1 and all evidence preserved; formal game/release untouched."
},indent=2)+"\n","utf-8")
runner=ROOT/"tools/paper-warfront/run_rc33_marching_capacity.py"
new=ROOT/"tools/paper-warfront/run_rc33_marching_filtered_capacity.py"
assert not new.exists()
text=runner.read_text("utf-8").replace("marching-r1","marching-r2").replace("marching-capacity-r1","marching-capacity-r2").replace("marching R1","marching R2")
new.write_text(text,"utf-8")
(QA/"marching-r2-runner-generation.json").write_text(json.dumps({"original_runner_sha256":sha(runner),"runner_sha256":sha(new),"generator_sha256":sha(Path(__file__))},indent=2)+"\n","utf-8")
print("Prepared R2 excluding economic transport and dead actors from blocker geometry")
