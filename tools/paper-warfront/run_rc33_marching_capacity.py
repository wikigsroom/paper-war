"""Run the isolated marching candidate once, retaining native receipt and inputs."""
from pathlib import Path
import hashlib
import json
import subprocess

ROOT=Path(__file__).resolve().parents[2]
QA=ROOT/"output/qa/godot/phase-runtime-rc33"
TRIAL=QA/"marching-r1-runtime"
out=QA/"marching-capacity-r1.json"
log=QA/"marching-capacity-r1.log"
receipt=QA/"marching-capacity-r1-receipt.json"
assert not any(p.exists() for p in [out,log,receipt])
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
manifest=json.loads((QA/"marching-r1-manifest.json").read_text("utf-8"))
assert all(sha(TRIAL/n)==d for n,d in manifest["candidate_inputs"].items())
args=[str(ROOT/".tools/godot/Godot_v4.7.2-stable_win64_console.exe"),"--headless","--path",str(TRIAL),
    "--script",str(QA/"marching-capacity-observer.gd"),"--","--baseline",str(QA/"oracle-runtime/scripts/battle_sim.gd"),"--output",str(out)]
print("Starting three-map complete RC32 versus marching R1 capacity comparison",flush=True)
with log.open("w",encoding="utf-8") as f:
    result=subprocess.run(args,cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,timeout=900)
source_unchanged=all(sha(TRIAL/n)==d for n,d in manifest["candidate_inputs"].items())
text=log.read_text("utf-8")
d=json.loads(out.read_text("utf-8")) if out.exists() else {}
passed=result.returncode==0 and "ERROR:" not in text and "SCRIPT ERROR:" not in text and source_unchanged and d.get("passed") and d.get("checks")==3600
e={"passed":bool(passed),"exit_code":result.returncode,"source_unchanged":source_unchanged,
   "runner_sha256":sha(Path(__file__)),"manifest_sha256":sha(QA/"marching-r1-manifest.json"),
   "observer_sha256":sha(QA/"marching-capacity-observer.gd"),"log_sha256":sha(log),"report_sha256":sha(out) if out.exists() else None,
   "scope":"Native Windows headless same-process alternating exact state comparison,1200 steps each of three maps. Candidate only; not rendered FPS, ordinary paid balance or Android hardware."}
receipt.write_text(json.dumps(e,indent=2)+"\n","utf-8")
print(json.dumps(e),flush=True)
if passed:
    for case in d["cases"]:
        rows=[x for x in d["paired_cpu"] if x["map"]==case["map"]]
        a=sum(x["baseline_us"] for x in rows)/len(rows)
        b=sum(x["candidate_us"] for x in rows)/len(rows)
        print(json.dumps({"case":case,"baseline_ms":a/1000,"candidate_ms":b/1000,"decrease_percent":(a-b)/a*100}),flush=True)
assert passed,"Inspect "+str(log)
