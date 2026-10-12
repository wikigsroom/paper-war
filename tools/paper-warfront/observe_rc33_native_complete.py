"""Observe source GPU frames serially after RC33 preparation and semantic QA ends."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2]
QA=ROOT/"output/qa/godot/phase-runtime-rc33"
semantic=QA/"source-gates-final.json"
preparation=QA/"native-preparation.json"
assert json.loads(semantic.read_text("utf-8"))["passed"]
assert json.loads(preparation.read_text("utf-8"))["passed"]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
out=QA/"native-source-observation.json"
assert not out.exists()
rows=[]
for label,project in [("baseline",QA/"native-baseline-runtime"),("candidate",QA/"native-marching-r3-runtime")]:
    folder=QA/("native-"+label+"-stress")
    assert not folder.exists()
    log=QA/("native-"+label+"-stress-orchestration.log")
    assert not log.exists()
    args=[sys.executable,str(ROOT/"tools/paper-warfront/check_realtime_battle.py"),"--source-project",str(project),"--output",str(folder),"--case","stress","--duration","20","--profile-layers"]
    print("Starting natural native source "+label+" stress",flush=True)
    with log.open("w",encoding="utf-8") as f:
        x=subprocess.run(args,cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,timeout=180)
    assert x.returncode==0,"Inspect "+str(log)
    d=json.loads((folder/"receipt.json").read_text("utf-8"));assert d["passed"]
    row={"case":label,"receipt_sha256":sha(folder/"receipt.json"),"report_sha256":sha(folder/"report.json"),"fps":1000/d["intervals_steady"]["mean_ms"],"p95_frame_ms":d["intervals_steady"]["p95_ms"],
         "app_cpu_mean_ms":d["app_process_steady"]["mean_ms"],"draw_cpu_mean_ms":d["draw_callback_steady"]["mean_ms"],"wall_seconds":d["wall_seconds"],"simulation_seconds":d["simulation_seconds"],"max_units":d["max_units"],"max_texture_bytes":d["max_texture_bytes"]}
    rows.append(row);print(json.dumps(row),flush=True)
out.write_text(json.dumps({"passed":True,"cases":rows,"runner_sha256":sha(Path(__file__)),"source_gates_sha256":sha(semantic),"preparation_sha256":sha(preparation),
    "scope":"Two isolated Windows native source projects, serial naturally processed20-second124-actor stress windows with layer diagnostics after own preparation and other QA was terminal. Source observation is not compiled release FPS, normal balance or Android hardware; adjacent observations are not a controlled causal FPS gain."},indent=2)+"\n","utf-8")
print("Both natural native source observations completed",flush=True)
