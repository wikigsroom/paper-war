"""Repair only the derived receipt metadata after the completed R4b regression."""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[2]
QA = ROOT / "output/qa/godot/render-runtime-rc34"
PROJECT = QA / "visibility-r4b-runtime"
BASE = QA / "baseline-runtime"
OUT = QA / "visibility-r4b-source-gates.json"
assert not OUT.exists()
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
report = json.loads((QA / "visibility-r4b-regression/report.json").read_text("utf-8"))
prep = json.loads((QA / "visibility-r4b-preparation.json").read_text("utf-8"))
assert report["passed"] and len(report["tests"]) == 78 and sum(r["checks"] for r in report["tests"]) == 195435
assert report["source_unchanged"]
changed=[]
for p in (BASE / "scripts").glob("*.gd"):
    trial=PROJECT / "scripts" / p.name
    if sha(p)!=sha(trial):changed.append(p.name)
assert changed==["battle_view.gd"], changed
for part in ["data","tests"]:
    for p in (BASE/part).rglob("*"):
        if p.is_file():assert sha(p)==sha(PROJECT/part/p.relative_to(BASE/part))
for p in (QA/"visibility-r4b-regression").glob("*.log"):
    assert "SCRIPT ERROR" not in p.read_text("utf-8") and "ERROR:" not in p.read_text("utf-8")
trial_scripts={p.name:sha(p) for p in (PROJECT/"scripts").glob("*.gd")}
OUT.write_text(json.dumps({"passed":True,"jobs":[{"job":"regression","passed":True,"checks":195435,"groups":78,"report_sha256":sha(QA/"visibility-r4b-regression/report.json"),"log_sha256":sha(QA/"visibility-r4b-regression-runner.log")}],"source_unchanged":True,
    "changed_scripts":changed,"trial_scripts":trial_scripts,"runner_sha256":sha(Path(__file__)),"preparation_sha256":sha(QA/"visibility-r4b-preparation.json"),
    "retained_failed_gate_sha256":sha(QA/"visibility-r4b-source-gates.json") if False else None,
    "scope":"Repaired receipt only: the original regression process completed and report passed; the first derived runner failed after the test because its preparation JSON uses trial_view_sha256 instead of trial_scripts. This file verifies the completed report, every data/test hash, and the one intended view change. No gameplay process was rerun or hidden."
},indent=2)+"\n","utf-8")
print("Repaired completed R4b source receipt",flush=True)
