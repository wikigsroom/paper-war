"""Export and validate RC32 serially around actual native frame observations."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
VERSION = "3.0.0-rc32-preview"
QA = ROOT / "output/qa/godot/contact-runtime-rc32"
FINAL = QA / "release-final"
assert not FINAL.exists()
assert json.loads((QA / "adoption.json").read_text("utf-8"))["passed"]
FINAL.mkdir()
shutil.copy2(Path(__file__), FINAL / "validation-runner.py")
env = dict(os.environ, PAPER_RELEASE_VERSION=VERSION, PAPER_QA_DIR=FINAL.relative_to(ROOT).as_posix())
pack = ROOT / "release" / VERSION / "windows/PaperWarfront.exe"
apk = ROOT / "release" / VERSION / "android" / ("PaperWarfront-" + VERSION + ".apk")
rows = []


def run(label, tool, *flags):
    assert not (FINAL / (label + "-orchestration.log")).exists()
    print("Starting " + label, flush=True)
    with (FINAL / (label + "-orchestration.log")).open("w", encoding="utf-8") as log:
        result = subprocess.run([sys.executable, str(ROOT / "tools/paper-warfront" / tool), *map(str, flags)],
            cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT, timeout=2400)
    row = {"name": label, "passed": result.returncode == 0, "exit_code": result.returncode}
    rows.append(row)
    (FINAL / "validation-progress.json").write_text(json.dumps({"version": VERSION, "jobs": rows}, indent=2), "utf-8")
    print(json.dumps(row), flush=True)
    assert row["passed"], "Inspect preserved " + label + " orchestration log"


run("build", "build_game.py")
run("apk-logic", "check_packaged_apk_logic.py")
run("windows-logic", "check_packaged_windows_logic.py")
for platform, flags, artifact in [
    ("windows", ["--pack", pack], pack),
    ("apk", ["--apk-runtime", FINAL / "apk-logic/extracted-runtime"], apk),
]:
    run("dense-" + platform, "check_dense_packaged_logic.py", *flags, "--artifact", artifact, "--output", FINAL / ("dense-" + platform))
    run("terrain-" + platform, "check_terrain_packaged_logic.py", *flags, "--artifact", artifact, "--output", FINAL / ("terrain-" + platform))
    run("answers-" + platform, "check_answers_packaged_logic.py", *flags, "--artifact", artifact, "--output", FINAL / ("answers-" + platform))
run("paid-recipes", "run_paid_release_recipes.py", "--qa", QA)
run("preview-checks", "run_preview_checks.py", "--version", VERSION, "--qa", FINAL)
run("native-extras", "run_query_native_extras.py", "--version", VERSION, "--before-version", "3.0.0-rc31-preview", "--qa", FINAL)
run("paper-ui-assets", "verify_paper_ui_assets.py", "--version", VERSION, "--qa", FINAL)
run("formal-reach", "verify_formal_premium_reach.py", "--qa", QA / "formal-reach")
run("formal-hammer", "verify_formal_hammer_reach.py", "--qa", QA / "formal-hammer", "--regression", QA / "source-final/report.json")
# All this task's copy/hash/export/other QA jobs are terminal before natural FPS.
snapshot = subprocess.run(["powershell", "-NoProfile", "-Command",
    "Get-CimInstance Win32_Process -Filter \"Name LIKE 'Godot%'\" | Select-Object ProcessId,Name,CommandLine | ConvertTo-Json -Depth 3"],
    cwd=ROOT, capture_output=True, encoding="utf-8", errors="replace", timeout=30)
(FINAL / "before-realtime-processes.json").write_text(snapshot.stdout, "utf-8")
run("native-realtime", "run_realtime_release.py", "--version", VERSION, "--before-version", "3.0.0-rc31-preview", "--qa", FINAL / "realtime")
(FINAL / "validation-report.json").write_text(json.dumps({"passed": True, "version": VERSION,
    "runner_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), "jobs": rows,
    "scope": "Fresh actual RC32 exports, compiled code and native UI/render checks. Natural frame observations run after own export/copy/hash/other QA jobs are terminal. External user processes preserved. No Android hardware or completed dense FPS/global balance claim."
}, indent=2) + "\n", "utf-8")
print("All RC32 native export and validation phases completed", flush=True)
