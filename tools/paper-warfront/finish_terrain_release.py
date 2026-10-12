"""Package the completed native RC31 observations and identical verification."""
from pathlib import Path
import json
import os
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
QA = ROOT / "output/qa/godot/pressure-runtime-rc31"
FINAL = QA / "release-final"
VERSION = "3.0.0-rc31-preview"
RELEASE = ROOT / "release" / VERSION
assert json.loads((FINAL / "validation-report.json").read_text("utf-8"))["passed"]
env = dict(os.environ, PAPER_RELEASE_VERSION=VERSION, PAPER_QA_DIR=FINAL.relative_to(ROOT).as_posix())
shutil.copy2(Path(__file__), QA / "packaging-runner.py")


def run(label, script, *flags):
    path = QA / (label + "-packaging.log")
    assert not path.exists()
    print("Starting " + label, flush=True)
    with path.open("w", encoding="utf-8") as log:
        result = subprocess.run([sys.executable, str(ROOT / "tools/paper-warfront" / script), *map(str, flags)],
            cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT, timeout=1200)
    assert result.returncode == 0, "Inspect " + str(path)
    print(label + " completed", flush=True)


run("publication", "publish_terrain_release.py")
run("initial-package", "package_preview.py")
saved = QA / "initial-proofless-package"
saved.mkdir()
for name in ["build-manifest.json", "SHA256SUMS.txt", "PaperWarfront-Windows-" + VERSION + ".zip"]:
    shutil.copy2(RELEASE / name, saved / name)
run("first-audit", "audit_terrain_preview.py", "--version", VERSION, "--qa", FINAL)
run("final-package", "package_preview.py")
run("final-audit", "audit_terrain_preview.py", "--version", VERSION, "--qa", FINAL, "--require-bundled-proof")
run("registration", "register_terrain_release.py")
(QA / "packaging-complete.json").write_text(json.dumps({"passed": True, "version": VERSION,
    "scope": "Actual artifacts and identical ZIP verification audited after completed native tests; immutable system revision registered. Original proofless ZIP preserved, not delivered as the final ZIP."
}, indent=2) + "\n", "utf-8")
print("RC31 final ZIP, APK and immutable revision completed", flush=True)
