"""Complete a confirmed stopped native observation without repeating passed cases."""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
QA = ROOT / "output/qa/godot/pressure-runtime-rc31"
FINAL = QA / "release-final"
FOLDER = FINAL / "realtime"
VERSION = "3.0.0-rc31-preview"
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
read = lambda p: json.loads(p.read_text("utf-8"))
assert not (FOLDER / "report.json").exists() and not (FINAL / "validation-report.json").exists()
assert not (FOLDER / "long").exists() and not (FOLDER / "phone").exists()
assert (FOLDER / "interrupted-long-r1/01-battle.png").is_file()
assert not (FOLDER / "interrupted-long-r1/receipt.json").exists()
progress = read(QA / "validation-progress-before-resume.json")
assert all(r["passed"] for r in progress["jobs"]) and progress["jobs"][-1]["name"] == "formal-hammer"
# Inspect actual OS process state, rather than inferring exit from a log/lock.
result = subprocess.run(["powershell", "-NoProfile", "-Command",
    "$terrainActive = @(Get-CimInstance Win32_Process -Filter \"Name LIKE 'Godot%' OR Name = 'python.exe'\" | Where-Object { ($_.CommandLine -like '*pressure-runtime-rc31*' -or $_.CommandLine -like '*run_terrain_release_validation*' -or $_.CommandLine -like '*run_realtime_release*') -and $_.CommandLine -notlike '*resume_terrain_native_validation.py*' } | Select-Object ProcessId,Name,CommandLine); ConvertTo-Json -InputObject $terrainActive -Depth 3"],
    cwd=ROOT, capture_output=True, encoding="utf-8", errors="replace", timeout=30)
assert result.returncode == 0
active = json.loads(result.stdout)
assert active == [], active
shutil.copy2(Path(__file__), QA / "native-resume-runner.py")
resume = {"confirmed_no_matching_processes": True, "process_query": result.stdout,
    "reason": "Original tool handle disappeared; OS inspection confirms no corresponding validation/realtime/native processes. Long observation has one image but no report/frames/receipt. No timeout alone was used to restart.",
    "retained_cases": {}, "interrupted_directory": "release-final/realtime/interrupted-long-r1",
    "old_auditor_sha256": sha(QA / "auditor-r1-before-resume.py"),
    "new_auditor_sha256": sha(ROOT / "tools/paper-warfront/audit_terrain_preview.py"),
    "observer_unchanged": True, "runner_sha256": sha(Path(__file__))}
for name in ["before-stress", "stress", "bridge"]:
    receipt = read(FOLDER / name / "receipt.json")
    native = read(FOLDER / name / "report.json")
    assert receipt["passed"] and native["passed"]
    assert receipt["report_sha256"] == sha(FOLDER / name / "report.json")
    assert native["frames_sha256"] == sha(FOLDER / name / "frames.csv")
    resume["retained_cases"][name] = sha(FOLDER / name / "receipt.json")
(QA / "native-resume.json").write_text(json.dumps(resume, indent=2) + "\n", "utf-8")
for name in ["long", "phone"]:
    print("Completing native " + name, flush=True)
    cmd = [sys.executable, str(ROOT / "tools/paper-warfront/check_realtime_battle.py"),
        "--pack", str(ROOT / "release" / VERSION / "windows/PaperWarfront.exe"),
        "--output", str(FOLDER / name), "--case", name, "--duration", "160"]
    result = subprocess.run(cmd, cwd=ROOT, capture_output=True, encoding="utf-8", errors="replace", timeout=280)
    (FOLDER / (name + "-runner.log")).write_text(result.stdout + result.stderr, "utf-8")
    assert result.returncode == 0, result.stdout[-1500:] + result.stderr[-1500:]
    print(name + " native capture completed", flush=True)
rows = []
for name in ["before-stress", "stress", "bridge", "long", "phone"]:
    receipt = read(FOLDER / name / "receipt.json")
    assert receipt["passed"]
    rows.append({"case": name, "version": "3.0.0-rc30-preview" if name == "before-stress" else VERSION,
        "receipt_sha256": sha(FOLDER / name / "receipt.json"), "report_sha256": sha(FOLDER / name / "report.json"),
        "fps_from_mean_interval": 1000 / receipt["intervals_steady"]["mean_ms"], "p95_frame_ms": receipt["intervals_steady"]["p95_ms"],
        "app_cpu_mean_ms": receipt["app_process_steady"]["mean_ms"], "draw_cpu_mean_ms": receipt["draw_callback_steady"]["mean_ms"],
        "wall_seconds": receipt["wall_seconds"], "simulation_seconds": receipt["simulation_seconds"],
        "max_units": receipt["max_units"], "max_texture_bytes": receipt["max_texture_bytes"]})
(FOLDER / "report.json").write_text(json.dumps({"passed": True, "version": VERSION,
    "runner_sha256": sha(Path(__file__)), "original_runner_sha256": sha(ROOT / "tools/paper-warfront/run_realtime_release.py"),
    "resumed_after_confirmed_exit": True, "resume_proof_sha256": sha(QA / "native-resume.json"), "cases": rows,
    "normal_55fps_target_met": all(r["fps_from_mean_interval"] >= 55 and r["p95_frame_ms"] <= 25 for r in rows if r["case"] in ["bridge", "long", "phone"]),
    "capacity_60fps_target_met": rows[1]["fps_from_mean_interval"] >= 59 and rows[1]["p95_frame_ms"] <= 25,
    "scope": "Three immutable completed observations retained; only stopped incomplete long case and not-started phone case completed after OS-confirmed absence. Natural native Windows compiled App, no concurrent own QA/hash/copy work; interrupted image excluded. Phone is not Android hardware."
}, indent=2) + "\n", "utf-8")
jobs = progress["jobs"] + [{"name": "native-realtime", "passed": True, "exit_code": 0, "resumed_after_confirmed_exit": True}]
(FINAL / "validation-report.json").write_text(json.dumps({"passed": True, "version": VERSION,
    "runner_sha256": sha(Path(__file__)), "original_runner_sha256": sha(FINAL / "validation-runner.py"), "jobs": jobs,
    "resume_proof_sha256": sha(QA / "native-resume.json"),
    "scope": "Original export/compiled/UI/render phases retained as completed jobs; confirmed-stopped natural frame phase completed with distinct interrupted evidence and fresh remaining captures. No Android hardware/full balance or dense60FPS claim."
}, indent=2) + "\n", "utf-8")
print("Completed all remaining native RC31 observations", flush=True)
