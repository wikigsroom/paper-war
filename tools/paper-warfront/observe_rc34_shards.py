"""Four serial natural Windows stress observations, after all own QA terminates."""
from pathlib import Path
import hashlib
import json
import statistics
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
QA = ROOT / "output/qa/godot/render-runtime-rc34"
OUT = QA / "shards-r3-natural-observation.json"
assert not OUT.exists()
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
for n in ["shards-r3-source-gates.json", "shards-r3-render/report.json"]:
    assert json.loads((QA / n).read_text("utf-8"))["passed"], n
rows = []
for i, label in enumerate(["baseline", "candidate", "candidate", "baseline"]):
    project = QA / ("baseline-runtime" if label == "baseline" else "shards-r3-runtime")
    dest = QA / f"shards-r3-natural-{i+1}-{label}"
    log = QA / f"shards-r3-natural-{i+1}-{label}-runner.log"
    assert not dest.exists() and not log.exists()
    print(f"Starting natural stress {i+1}/4 {label}", flush=True)
    with log.open("w", encoding="utf-8") as f:
        run = subprocess.run([sys.executable, str(ROOT / "tools/paper-warfront/check_realtime_battle.py"), "--source-project", str(project), "--output", str(dest), "--case", "stress", "--duration", "20", "--profile-layers"], cwd=ROOT, stdout=f, stderr=subprocess.STDOUT, timeout=180)
    assert run.returncode == 0, "Inspect " + str(log)
    receipt = json.loads((dest / "receipt.json").read_text("utf-8"));assert receipt["passed"]
    report = json.loads((dest / "report.json").read_text("utf-8"))
    snapshots = [s["layer_cpu_us"] for s in report["snapshots"] if s["wall_seconds"]>=2]
    row = {"order": i+1, "label": label, "receipt_sha256": sha(dest / "receipt.json"),
        "report_sha256": sha(dest / "report.json"), "fps": 1000/receipt["intervals_steady"]["mean_ms"],
        "p95_frame_ms": receipt["intervals_steady"]["p95_ms"], "draw_mean_ms": receipt["draw_callback_steady"]["mean_ms"],
        "app_mean_ms": receipt["app_process_steady"]["mean_ms"], "units_snapshot_mean_ms": statistics.mean(s["units"] for s in snapshots)/1000,
        "particles_snapshot_mean_ms": statistics.mean(s["particles_numbers_preview"] for s in snapshots)/1000,
        "max_units": receipt["max_units"], "texture_bytes": receipt["max_texture_bytes"],
        "wall_seconds": receipt["wall_seconds"], "simulation_seconds": receipt["simulation_seconds"]}
    rows.append(row);print(json.dumps(row), flush=True)
OUT.write_text(json.dumps({"passed": True, "cases": rows, "runner_sha256": sha(Path(__file__)),
    "source_gate_sha256": sha(QA / "shards-r3-source-gates.json"), "pixel_report_sha256": sha(QA / "shards-r3-render/report.json"),
    "scope": "Native RC33 baseline and view-only shard R3, four serial20-second natural124-actor capacity windows in ABBA order. All own preparation, copying and other QA terminal first. Same source observer/audio/window settings. Layer snapshots are CPU submission, not GPU timing. Fixture directly places high-HP actors and is not normal paid balance. Environmental variability remains; no compiled FPS or Android hardware claim."
}, indent=2)+"\n", "utf-8")
print("Natural geometry observation complete", flush=True)
