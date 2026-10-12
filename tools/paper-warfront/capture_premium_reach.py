"""Capture a native paid scythe exchange on desktop and injected phone UI."""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
parser=argparse.ArgumentParser()
parser.add_argument("--qa",type=Path,default=ROOT / "output/qa/godot/core-alignment-rc14/formal-reach")
parser.add_argument("--unit-family",choices=["scythe","hammer"],default="scythe")
args=parser.parse_args()
QA = args.qa.resolve() / "gpu"
script="hammer_screen_ui_qa.gd" if args.unit_family=="hammer" else "premium_reach_ui_qa.gd"
startup = subprocess.STARTUPINFO()
startup.dwFlags = 1
startup.wShowWindow = 0
for name, resolution, flags in [
    ("desktop", "1280x720", []),
    ("phone", "1136x640", ["--mobile-ui", "--mobile-density", "2"]),
]:
    folder = QA / name
    folder.mkdir(parents=True, exist_ok=True)
    run = subprocess.run([
        str(ROOT / ".tools/godot/Godot_v4.7.2-stable_win64_console.exe"),
        "--path", str(ROOT / "game"), "--rendering-method", "gl_compatibility", "--resolution", resolution,
        "--script", "res://tests/"+script, "--", *flags,
        "--output", str(folder), "--profile-path", str(folder / "profile.json"),
    ], cwd=ROOT, capture_output=True, encoding="utf-8", errors="replace", startupinfo=startup, timeout=90)
    log = run.stdout + run.stderr
    (folder / "runtime.log").write_text(log, encoding="utf-8")
    report = json.loads((folder / "report.json").read_text(encoding="utf-8")) if (folder / "report.json").exists() else {}
    passed = run.returncode == 0 and report.get("passed") and bool(report.get("inputs")) and "SCRIPT ERROR" not in log and "ERROR:" not in log
    passed = passed and all(hashlib.sha256((ROOT / "game" / path.removeprefix("res://")).read_bytes()).hexdigest() == value for path, value in report.get("inputs", {}).items())
    print(name, "passed", bool(passed), "frames", len(report.get("captures", [])), "hits", report.get("hit_events"), flush=True)
    if not passed:
        print(log[-3000:])
        raise SystemExit(1)
