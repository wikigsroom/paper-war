"""Native GPU capture of production and reinforcement feedback."""
import os
import json
import hashlib
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
QA = ROOT / os.environ.get("PAPER_QA_DIR", "output/qa/godot/recruitment-readiness")
startup = subprocess.STARTUPINFO()
startup.dwFlags = 1
startup.wShowWindow = 0
for name, resolution, flags in (
    ("desktop", "1280x720", []),
    ("phone", "1280x720", ["--mobile-ui", "--mobile-density", "2"]),
    ("compact", "1136x640", ["--mobile-ui", "--mobile-density", "2"]),
):
    folder = QA / name
    folder.mkdir(parents=True, exist_ok=True)
    result = subprocess.run([
        str(ROOT / ".tools/godot/Godot_v4.7.2-stable_win64_console.exe"),
        "--path", str(ROOT / "game"), "--rendering-method", "gl_compatibility",
        "--resolution", resolution, "--script", "res://tests/recruitment_ui_qa.gd",
        "--", *flags, "--output", str(folder), "--profile-path", str(folder / "profile.json"),
    ], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace", startupinfo=startup, timeout=60)
    log = result.stdout + result.stderr
    (folder / "runtime.log").write_text(log, encoding="utf-8")
    report_path = folder / "report.json"
    report = json.loads(report_path.read_text(encoding="utf-8")) if report_path.exists() else {}
    passed = result.returncode == 0 and report.get("passed") and "SCRIPT ERROR" not in log and "ERROR:" not in log
    passed = passed and bool(report.get("inputs")) and all(
        hashlib.sha256((ROOT / "game" / path.removeprefix("res://")).read_bytes()).hexdigest() == digest
        for path, digest in report.get("inputs", {}).items()
    )
    print(name, "passed", bool(passed), flush=True)
    if not passed:
        print(log[-5000:])
        raise SystemExit(1)
