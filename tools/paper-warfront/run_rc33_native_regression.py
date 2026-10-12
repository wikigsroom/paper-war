"""Complete missing-resource regression and seal the complete source-gate receipt."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2]
QA=ROOT/"output/qa/godot/phase-runtime-rc33"
TRIAL=QA/"native-marching-r3-runtime"
OUTPUT=QA/"native-regression-r3"
LOG=QA/"native-regression-r3-orchestration.log"
RECEIPT=QA/"source-gates-final.json"
assert not any(p.exists() for p in [OUTPUT,LOG,RECEIPT])
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
preparation=json.loads((QA/"native-preparation.json").read_text("utf-8"));assert preparation["passed"]
before={str(p.relative_to(TRIAL)):sha(p) for folder in ["scripts","data","tests"] for p in (TRIAL/folder).glob("*") if p.is_file()}
print("Starting full78-test regression with actual frozen RC32 fonts/atlases/native imports",flush=True)
with LOG.open("w",encoding="utf-8") as f:
    x=subprocess.run([sys.executable,str(ROOT/"tools/paper-warfront/check_ai_engagement.py"),"--mechanisms-only","--project",str(TRIAL),"--output",str(OUTPUT)],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,timeout=1800)
report=OUTPUT/"report.json"
d=json.loads(report.read_text("utf-8"));text=LOG.read_text("utf-8")
unchanged=all(sha(TRIAL/n)==h for n,h in before.items())
freeze=json.loads((QA/"freeze.json").read_text("utf-8"))
original_unchanged=all(sha(QA/"oracle-runtime/scripts"/n)==v["oracle_sha256"] for n,v in freeze["oracle_scripts"].items())
same={p.name:sha(p) for p in (QA/"marching-r3-runtime/scripts").glob("*.gd")}=={p.name:sha(p) for p in (TRIAL/"scripts").glob("*.gd")}
count=sum(t["checks"] for t in d["tests"])
passed=x.returncode==0 and d["passed"] and count==195435 and len(d["tests"])==78 and unchanged and original_unchanged and same and "ERROR:" not in text
receipt={"passed":bool(passed),"full_source_tests":78,"full_source_checks":count,"source_unchanged":unchanged,"original_closure_unchanged":original_unchanged,"candidate_script_closure_same":same,
    "runner_sha256":sha(Path(__file__)),"regression_report_sha256":sha(report),"regression_log_sha256":sha(LOG),"preparation_sha256":sha(QA/"native-preparation.json"),
    "partial_semantic_receipt_sha256":sha(QA/"marching-r3-semantic-r3-receipt.json"),"capacity_receipt_sha256":sha(QA/"marching-capacity-r3-receipt.json"),
    "source_inputs_before":before,"scope":"Full resource-complete78-test native source regression plus retained successful432427 boundary,28811 mixed all-faction phase and73103 paid exact-state checks. Same44-script candidate closure, complete independent RC32 oracle. Failed resource-free regression and prior observer/reference errors preserved. Candidate only; no formal adoption/export, FPS, whole balance or Android hardware claim."}
RECEIPT.write_text(json.dumps(receipt,indent=2)+"\n","utf-8")
print(json.dumps({k:v for k,v in receipt.items() if k!="source_inputs_before"}),flush=True)
assert passed,"Inspect "+str(LOG)
