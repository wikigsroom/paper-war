"""Package identical verified RC33 proof, then register the immutable revision."""
from pathlib import Path
import json
import os
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
QA = ROOT / "output/qa/godot/phase-runtime-rc33"
FINAL = QA / "release-final"
VERSION = "3.0.0-rc33-preview"
RELEASE = ROOT / "release" / VERSION
assert json.loads((FINAL / "validation-report.json").read_text("utf-8"))["passed"]
assert not (QA / "packaging-runner.py").exists()
env = dict(os.environ, PAPER_RELEASE_VERSION=VERSION, PAPER_QA_DIR=FINAL.relative_to(ROOT).as_posix())
shutil.copy2(Path(__file__), QA / "packaging-runner.py")

def run(label, tool, *flags):
    log = QA / (label + "-packaging.log")
    assert not log.exists()
    print("Starting " + label, flush=True)
    with log.open("w", encoding="utf-8") as f:
        result = subprocess.run([sys.executable, str(ROOT / "tools/paper-warfront" / tool), *map(str, flags)], cwd=ROOT, env=env, stdout=f, stderr=subprocess.STDOUT, timeout=1200)
    assert result.returncode == 0, "Inspect " + str(log)
    print(label + " completed", flush=True)

run("publication", "publish_phase_release.py")
run("initial-package", "package_preview.py")
saved = QA / "initial-proofless-package"
assert not saved.exists()
saved.mkdir()
for name in ["build-manifest.json", "SHA256SUMS.txt", "PaperWarfront-Windows-" + VERSION + ".zip"]:
    shutil.copy2(RELEASE / name, saved / name)
run("first-audit", "audit_phase_preview.py", "--version", VERSION, "--qa", FINAL)
run("final-package", "package_preview.py")
run("final-audit", "audit_phase_preview.py", "--version", VERSION, "--qa", FINAL, "--require-bundled-proof")
run("registration", "register_phase_release.py")
(QA / "packaging-complete.json").write_text(json.dumps({
    "passed": True, "version": VERSION,
    "scope": "Completed native exports and serial checks; final Windows ZIP includes identical fully audited preview proof. APK/EXE/revision bound. Pending dense60FPS, full balance, human story/network and physical Android."
}, indent=2) + "\n", "utf-8")
print("RC33 final ZIP, APK and immutable revision completed", flush=True)
