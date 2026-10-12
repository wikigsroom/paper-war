"""Serial backend ABBA on one existing pack after own QA/preparation terminates."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
QA = ROOT / "output/qa/godot/render-runtime-rc34"
OUT = QA / "compiled-backend-natural-observation.json"
PACK = ROOT / "release/3.0.0-rc33-preview/windows/PaperWarfront.exe"
assert not OUT.exists()
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert json.loads((QA / "shards-r3-natural-observation.json").read_text("utf-8"))["passed"]
rows=[]
for i, backend in enumerate(["mobile","gl_compatibility","gl_compatibility","mobile"]):
    dest = QA/f"compiled-backend-{i+1}-{backend}"
    log = QA/f"compiled-backend-{i+1}-{backend}-runner.log"
    assert not dest.exists() and not log.exists()
    print(f"Starting identical-pack backend {i+1}/4 {backend}",flush=True)
    with log.open("w",encoding="utf-8") as f:
        run=subprocess.run([sys.executable,str(ROOT/"tools/paper-warfront/check_rc34_backend_realtime.py"),"--pack",str(PACK),"--native-backend",backend,"--case","stress","--duration","20","--output",str(dest)],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,timeout=180)
    assert run.returncode==0,"Inspect "+str(log)
    receipt=json.loads((dest/"receipt.json").read_text("utf-8"));assert receipt["passed"]
    report=json.loads((dest/"report.json").read_text("utf-8"))
    assert report["renderer"]==backend and report["capacity_fixture"] and not report["audio_silent"]
    rows.append({"order":i+1,"backend":backend,"fps":1000/receipt["intervals_steady"]["mean_ms"],
        "p95_frame_ms":receipt["intervals_steady"]["p95_ms"],"draw_mean_ms":receipt["draw_callback_steady"]["mean_ms"],"app_mean_ms":receipt["app_process_steady"]["mean_ms"],
        "max_units":receipt["max_units"],"texture_bytes":receipt["max_texture_bytes"],
        "wall_seconds":receipt["wall_seconds"],"simulation_seconds":receipt["simulation_seconds"],
        "report_sha256":sha(dest/"report.json"),"receipt_sha256":sha(dest/"receipt.json")})
    print(json.dumps(rows[-1]),flush=True)
OUT.write_text(json.dumps({"passed":True,"runner_sha256":sha(Path(__file__)),"pack_sha256":sha(PACK),"cases":rows,
    "scope":"Same exported RC33 code/art/settings apart from explicit native renderer override, four serial natural20-second124-actor desktop/audio-on stress runs in ABBA order. No manual simulation ticks, own parallel work, source candidate adoption or Android hardware claim. Backend performance and image fidelity are separate gates; environment variability remains."
},indent=2)+"\n", "utf-8")
print("Compiled backend observations complete",flush=True)
