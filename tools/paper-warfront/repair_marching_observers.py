"""Preserve the failed observer; use actual economic IDs and mixed-worker fixtures."""
from pathlib import Path
import hashlib
import json

ROOT=Path(__file__).resolve().parents[2]
QA=ROOT/"output/qa/godot/phase-runtime-rc33"
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
failed=json.loads((QA/"marching-r3-semantic-receipt.json").read_text("utf-8"))
assert failed["passed"] is False and failed["jobs"][0]["job"]=="boundary"
old=QA/"marching-boundary-observer.gd"
new=QA/"marching-boundary-observer-r2.gd"
assert not new.exists()
s=old.read_text("utf-8")
s=s.replace('var ids: Array=db.all_unit_ids("yin" if side==0 else "mo");', 'var faction: String="yin" if side==0 else "mo";var ids: Array=db.all_unit_ids(faction)+db.unit_ids(faction).filter(func(id):return db.balance.units[id].get("economy",false));')
s=s.replace('var worker_ids: Array=db.all_unit_ids("yin").filter', 'var worker_ids: Array=db.unit_ids("yin").filter')
new.write_text(s,"utf-8")
old_phase=QA/"marching-phase-observer.gd"
phase=QA/"marching-phase-observer-r2.gd"
assert not phase.exists()
s=old_phase.read_text("utf-8")
s=s.replace('var ids: Array=s.db.all_unit_ids(west if side==0 else east)','var faction: String=west if side==0 else east\n\t\tvar ids: Array=s.db.all_unit_ids(faction)+s.db.unit_ids(faction).filter(func(id):return s.db.balance.units[id].get("economy",false))')
s=s.replace("dense all-roster faction cases", "dense mixed-combat-and-economic all-roster faction cases")
phase.write_text(s,"utf-8")
runner=ROOT/"tools/paper-warfront/run_rc33_marching_semantics.py"
out=ROOT/"tools/paper-warfront/run_rc33_marching_semantics_repaired.py"
assert not out.exists()
s=runner.read_text("utf-8")
s=s.replace("marching-r3-semantic-receipt.json","marching-r3-semantic-r2-receipt.json").replace("marching-r3-semantic-progress.json","marching-r3-semantic-r2-progress.json")
s=s.replace("marching-boundary-observer.gd","marching-boundary-observer-r2.gd").replace("marching-phase-observer.gd","marching-phase-observer-r2.gd")
s=s.replace("marching-boundary-r3.json","marching-boundary-r3-r2.json").replace('label+"-r3-orchestration.log"','label+"-r3-r2-orchestration.log"')
out.write_text(s,"utf-8")
(QA/"marching-observer-repair.json").write_text(json.dumps({"passed":True,
    "failed_receipt_sha256":sha(QA/"marching-r3-semantic-receipt.json"),"failed_log_sha256":sha(QA/"marching-boundary-r3-orchestration.log"),
    "old_observer_sha256":sha(old),"observer_sha256":sha(new),"old_phase_observer_sha256":sha(old_phase),"phase_observer_sha256":sha(phase),
    "old_runner_sha256":sha(runner),"runner_sha256":sha(out),"generator_sha256":sha(Path(__file__)),
    "candidate_manifest_sha256":sha(QA/"marching-r3-manifest.json"),
    "scope":"Harness-only repair. all_unit_ids is combat-only; economic worker IDs now come from actual unit_ids. All200-map fixtures and dense10-faction phase fixtures explicitly include workers. Failed432400-map-check observer then crashed in tail and was stopped by its verified own PID; no failed check counted as a final pass. Game/candidate/RC32 bytes unchanged."
},indent=2)+"\n","utf-8")
print("Preserved failed harness; repaired economic selection and mixed-worker fixtures")
