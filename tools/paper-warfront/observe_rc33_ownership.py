"""Serial native source ABBA observations after all own copying and QA terminate."""
from pathlib import Path
import hashlib
import json
import statistics
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
QA = ROOT / "output/qa/godot/phase-runtime-rc33"
OUT = QA / "ownership-r1-natural-observation.json"
assert not OUT.exists()
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
for name in ["ownership-r1-source-gates.json", "ownership-r1-render-expanded/report.json", "native-source-observation.json"]:
    assert json.loads((QA / name).read_text("utf-8"))["passed"], name
rows = []
for index, label in enumerate(["baseline", "candidate", "candidate", "baseline"]):
    project = QA / ("native-baseline-runtime" if label == "baseline" else "native-ownership-r1-runtime")
    dest = QA / f"ownership-r1-natural-{index + 1}-{label}"
    log = QA / f"ownership-r1-natural-{index + 1}-{label}-orchestration.log"
    assert not dest.exists() and not log.exists()
    print(f"Starting natural native stress {index + 1}/4 {label}", flush=True)
    with log.open("w", encoding="utf-8") as f:
        run = subprocess.run([sys.executable, str(ROOT / "tools/paper-warfront/check_realtime_battle.py"), "--source-project", str(project), "--output", str(dest), "--case", "stress", "--duration", "20", "--profile-layers"], cwd=ROOT, stdout=f, stderr=subprocess.STDOUT, timeout=180)
    assert run.returncode == 0, "Inspect " + str(log)
    receipt = json.loads((dest / "receipt.json").read_text("utf-8"))
    assert receipt["passed"]
    report = json.loads((dest / "report.json").read_text("utf-8"))
    snapshots = [s["layer_cpu_us"] for s in report["snapshots"] if s["wall_seconds"] >= 2]
    row = {
        "order": index + 1, "label": label, "receipt_sha256": sha(dest / "receipt.json"),
        "report_sha256": sha(dest / "report.json"), "fps": 1000 / receipt["intervals_steady"]["mean_ms"],
        "p95_frame_ms": receipt["intervals_steady"]["p95_ms"],
        "app_mean_ms": receipt["app_process_steady"]["mean_ms"], "draw_mean_ms": receipt["draw_callback_steady"]["mean_ms"],
        "units_layer_snapshot_mean_ms": statistics.mean(s["units"] for s in snapshots) / 1000,
        "wall_seconds": receipt["wall_seconds"], "simulation_seconds": receipt["simulation_seconds"],
        "max_units": receipt["max_units"], "texture_bytes": receipt["max_texture_bytes"]
    }
    rows.append(row)
    print(json.dumps(row), flush=True)
OUT.write_text(json.dumps({
    "passed": True, "cases": rows, "runner_sha256": sha(Path(__file__)),
    "source_gate_sha256": sha(QA / "ownership-r1-source-gates.json"),
    "expanded_pixel_sha256": sha(QA / "ownership-r1-render-expanded/report.json"),
    "scope": "Four serial naturally processed20-second124-actor source stress windows in ABBA order; baseline fullRC32 and R3 simulation plus ownership mesh candidate. Started only after own preparation and other QA terminal. Layer snapshots are roughly1Hz CPU command submission, not full-frame GPU timing. Adjacent runs retain environmental variability and cannot prove a universal FPS gain. No compiled release, normal gameplay balance,60FPS or Android hardware claim."
}, indent=2) + "\n", "utf-8")
print("Natural native source ABBA observation complete", flush=True)
