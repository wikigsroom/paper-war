"""Render actual EXE pack UI with external read-only native test scaffolding."""
import hashlib
import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VERSION = os.environ["PAPER_RELEASE_VERSION"]
QA = ROOT / os.environ["PAPER_QA_DIR"] / "packaged-recruitment-ui"
QA.mkdir(parents=True, exist_ok=True)
EXE = ROOT / "release" / VERSION / "windows/PaperWarfront.exe"
original = ROOT / "game/tests/recruitment_ui_qa.gd"
touch = ROOT / "game/tests/mobile_ui_qa.gd"
fixture = QA / "packaged_recruitment_ui_qa.gd"
source = original.read_text(encoding="utf-8").replace("res://tests/mobile_ui_qa.gd", touch.as_posix())
old_paths = '"res://scripts/main.gd","res://scripts/mobile_ui.gd","res://scripts/recruitment_readiness.gd","res://scripts/battle_view.gd","res://scripts/action_card.gd","res://scripts/mobile_scroll.gd","res://scripts/local_duel.gd","res://scripts/duel_scroll.gd","res://tests/recruitment_ui_qa.gd"'
new_paths = '"res://scripts/main.gdc","res://scripts/mobile_ui.gdc","res://scripts/recruitment_readiness.gdc","res://scripts/battle_view.gdc","res://scripts/action_card.gdc","res://scripts/mobile_scroll.gdc","res://scripts/local_duel.gdc","res://scripts/duel_scroll.gdc"'
assert old_paths in source
source = source.replace(old_paths, new_paths)
source = source.replace('var report={"passed":passed', 'verify(not FileAccess.file_exists("res://scripts/main.gd"),"Compiled app source isolation")\n\tpassed=passed and checks[-1].passed\n\tvar report={"passed":passed')
fixture.write_text(source, encoding="utf-8")
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
apk_proof = json.loads((QA.parent / "apk-logic/report.json").read_text(encoding="utf-8"))
startup = subprocess.STARTUPINFO()
startup.dwFlags = 1
startup.wShowWindow = 0
reports = []
for name, resolution, flags in (
    ("desktop", "1280x720", []),
    ("phone", "1280x720", ["--mobile-ui", "--mobile-density", "2"]),
    ("compact", "1136x640", ["--mobile-ui", "--mobile-density", "2"]),
    ("short", "1136x512", ["--mobile-ui", "--mobile-density", "2"]),
):
    folder = QA / name
    folder.mkdir(parents=True, exist_ok=True)
    result = subprocess.run([
        str(ROOT / ".tools/godot/Godot_v4.7.2-stable_win64_console.exe"),
        "--main-pack", str(EXE), "--rendering-method", "gl_compatibility",
        "--resolution", resolution, "--script", str(fixture), "--", *flags,
        "--output", str(folder), "--profile-path", str(folder / "profile.json"),
    ], cwd=ROOT, capture_output=True, encoding="utf-8", errors="replace", startupinfo=startup, timeout=90)
    log = result.stdout + result.stderr
    (folder / "runtime.log").write_text(log, encoding="utf-8")
    report = json.loads((folder / "report.json").read_text(encoding="utf-8")) if (folder / "report.json").exists() else {}
    assert result.returncode == 0 and report.get("passed") and "SCRIPT ERROR" not in log and "ERROR:" not in log, log[-3000:]
    assert report.get("inputs") and all(apk_proof["extracted_inputs"][path.removeprefix("res://")] == digest for path, digest in report["inputs"].items())
    coverage=[c for c in report["checks"] if "70 percent" in c["name"]]
    assert len(coverage)==(4 if name=="desktop" else 3) and all(c["passed"] and c["details"]["visible_ratio"]>=.70 for c in coverage)
    reports.append({"name": name, "passed": True, "checks": len(report["checks"]), "inputs": report["inputs"], "battlefield_coverage":coverage})
    print(name, "actual EXE pack recruitment UI passed", flush=True)
report = {"passed": True, "version": VERSION, "executable_sha256": sha(EXE),
          "source_harness_sha256": sha(original), "external_touch_harness_sha256": sha(touch),
          "generated_harness_sha256": sha(fixture), "cases": reports,
          "scope": "Native Windows GPU renders actual EXE embedded compiled app with external UI test scaffolding; four sizes, single-player and shared-controller area, paid queue cancellation and scrollable travel info. Compiled app bytes match actual APK. LAN UI uses a real-fee sender fixture; no human, TCP or Android hardware claim."}
(QA / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
