"""Run strong semantic gates for the isolated R3 marching optimization in order."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2]
QA=ROOT/"output/qa/godot/phase-runtime-rc33"
TRIAL=QA/"marching-r3-runtime"
ENGINE=ROOT/".tools/godot/Godot_v4.7.2-stable_win64_console.exe"
ORACLE=QA/"oracle-runtime/scripts/battle_sim.gd"
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
manifest=json.loads((QA/"marching-r3-manifest.json").read_text("utf-8"))
freeze=json.loads((QA/"freeze.json").read_text("utf-8"))
assert json.loads((QA/"marching-capacity-r3-receipt.json").read_text("utf-8"))["passed"]
assert all(sha(TRIAL/n)==d for n,d in manifest["candidate_inputs"].items())
assert all(sha(QA/"oracle-runtime/scripts"/n)==v["oracle_sha256"] for n,v in freeze["oracle_scripts"].items())
receipt=QA/"marching-r3-semantic-r3-receipt.json"
progress=QA/"marching-r3-semantic-r3-progress.json"
assert not receipt.exists() and not progress.exists()
base=[str(ENGINE),"--headless","--path",str(TRIAL),"--script"]
jobs=[
    ("boundary",base+[str(QA/"marching-boundary-observer-r3.gd"),"--",str(QA/"marching-boundary-r3-r3.json"),str(ORACLE)],QA/"marching-boundary-r3-r3.json",432427),
    ("phase",base+[str(QA/"marching-phase-observer-r2.gd"),"--","--baseline",str(ORACLE),"--output",str(QA/"marching-phase-r3.json")],QA/"marching-phase-r3.json",28811),
    ("paid",base+[str(QA/"marching-paid-observer.gd"),"--","--baseline",str(ORACLE),"--output",str(QA/"marching-paid-r3.json")],QA/"marching-paid-r3.json",73103),
    ("regression",[sys.executable,str(ROOT/"tools/paper-warfront/check_ai_engagement.py"),"--mechanisms-only","--project",str(TRIAL),"--output",str(QA/"candidate-regression-r3")],QA/"candidate-regression-r3/report.json",195435),
]
records=[]
for label,args,out,expected in jobs:
    log=QA/("marching-"+label+"-r3-r3-orchestration.log")
    assert not log.exists() and not out.exists()
    print("Starting "+label,flush=True)
    progress.write_text(json.dumps({"running":label,"completed":records},indent=2)+"\n","utf-8")
    with log.open("w",encoding="utf-8") as f:
        x=subprocess.run(args,cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,timeout=1800)
    d=json.loads(out.read_text("utf-8")) if out.exists() else {}
    text=log.read_text("utf-8")
    count=sum(v["checks"] for v in d.get("tests",[])) if label=="regression" else d.get("checks",0)
    passed=x.returncode==0 and d.get("passed") and count==expected and "ERROR:" not in text and "SCRIPT ERROR" not in text
    record={"job":label,"passed":bool(passed),"exit_code":x.returncode,"checks":count,"log_sha256":sha(log),"report_sha256":sha(out) if out.exists() else None}
    records.append(record)
    progress.write_text(json.dumps({"running":None,"completed":records},indent=2)+"\n","utf-8")
    print(json.dumps(record),flush=True)
    if not passed:
        receipt.write_text(json.dumps({"passed":False,"jobs":records,"runner_sha256":sha(Path(__file__)),"scope":"Candidate-only native semantic gates; failed check retained."},indent=2)+"\n","utf-8")
        raise SystemExit("Inspect "+str(log))
unchanged=all(sha(TRIAL/n)==d for n,d in manifest["candidate_inputs"].items())
original_unchanged=all(sha(QA/"oracle-runtime/scripts"/n)==v["oracle_sha256"] for n,v in freeze["oracle_scripts"].items())
receipt.write_text(json.dumps({"passed":unchanged and original_unchanged,"jobs":records,"source_unchanged":unchanged,"original_closure_unchanged":original_unchanged,
    "runner_sha256":sha(Path(__file__)),"candidate_manifest_sha256":sha(QA/"marching-r3-manifest.json"),"freeze_sha256":sha(QA/"freeze.json"),
    "observers":{n:sha(QA/n) for n in ["marching-boundary-observer-r3.gd","marching-phase-observer-r2.gd","marching-paid-observer.gd"]},
    "scope":"Isolated R3, all200-map independent collision boundaries,30 all-roster dense faction cases and six normal paid full RC32-closure comparisons, plus existing78 native controlled tests. Neither formal adoption/export, rendered FPS, whole campaign balance nor physical Android validation."},indent=2)+"\n","utf-8")
assert unchanged and original_unchanged
print("All R3 source semantic gates completed",flush=True)
