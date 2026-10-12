"""Run the established preview observers with at most two native GPU jobs."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
ap = argparse.ArgumentParser()
ap.add_argument("--version", required=True)
ap.add_argument("--qa", type=Path, required=True)
args = ap.parse_args()
qa = args.qa.resolve()
qa.mkdir(parents=True, exist_ok=True)
pack = ROOT / f"release/{args.version}/windows/PaperWarfront.exe"
prerequisite=json.loads((qa/"apk-logic/report.json").read_text(encoding="utf-8"))
assert prerequisite["passed"] and prerequisite["version"]==args.version, "Finish APK bytecode checks before compiled UI observers"
engine = ROOT / ".tools/godot/Godot_v4.7.2-stable_win64_console.exe"
env = dict(os.environ, PAPER_RELEASE_VERSION=args.version,
           PAPER_QA_DIR=qa.relative_to(ROOT).as_posix())
startup = subprocess.STARTUPINFO()
startup.dwFlags = 1
startup.wShowWindow = 0

def py(script, *flags):
    return [sys.executable, str(ROOT / "tools/paper-warfront" / script), *map(str, flags)]

jobs = [("mobile-matrix", py("check_mobile_adaptation.py"))]
for label, script in [
    ("stage-proportions", "check_stage_proportions.py"),
    ("fog-render", "check_fog_rendering.py"),
    ("camera-render", "check_camera_rendering.py"),
    ("modal-navigation", "check_ui_modal_navigation.py"),
    ("live-battle-sheets", "check_live_battle_sheets.py"),
    ("paper-ui", "check_paper_ui.py"),
]:
    jobs.append((label, py(script, "--pack", pack, "--output", qa / label)))
jobs.extend([
    ("recruitment-ui", py("capture_packaged_recruitment_ui.py")),
    ("exe-smoke", py("smoke_mobile_exports.py")),
    ("scythe-gpu", py("capture_premium_reach.py", "--qa", qa.parent / "formal-reach")),
    ("hammer-gpu", py("capture_premium_reach.py", "--qa", qa.parent / "formal-hammer", "--unit-family", "hammer")),
    ("duel-stage", [str(engine), "--headless", "--main-pack", str(pack), "--script",
                    str(ROOT / "tools/paper-warfront/probe_duel_stage.gd"), "--", "--output",
                    str(qa / "duel-stage/report.json"), "--profile-path", str(qa / "duel-stage/profile.json")]),
])

def run(job):
    label, cmd = job
    (qa / label).mkdir(parents=True, exist_ok=True)
    # Observers maintain their detailed logs. Keep a separate orchestration log.
    with (qa / (label + "-runner.log")).open("w", encoding="utf-8") as log:
        completed = subprocess.run(cmd, cwd=ROOT, env=env, startupinfo=startup,
                                   stdout=log, stderr=subprocess.STDOUT, timeout=1800)
    result = {"name": label, "passed": completed.returncode == 0, "exit_code": completed.returncode}
    print(json.dumps(result), flush=True)
    return result

with ThreadPoolExecutor(max_workers=2) as pool:
    results = list(pool.map(run, jobs))
(qa / "runner-report.json").write_text(json.dumps({"passed": all(x["passed"] for x in results),
    "version": args.version, "max_native_gpu_jobs": 2, "jobs": results}, indent=2), encoding="utf-8")
raise SystemExit(0 if all(x["passed"] for x in results) else 1)
