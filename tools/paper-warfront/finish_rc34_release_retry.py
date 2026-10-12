"""Package RC34 after publication was already written by the first packaging attempt."""
from pathlib import Path
import json
import os
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2]
QA=ROOT/"output/qa/godot/render-runtime-rc34"
FINAL=QA/"release-final"
VERSION="3.0.0-rc34-preview"
RELEASE=ROOT/"release"/VERSION
assert json.loads((FINAL/"validation-report.json").read_text("utf-8"))["passed"]
assert json.loads((QA/"publication.json").read_text("utf-8"))["passed"]
assert not (QA/"packaging-runner-r4d.py").exists()
env=dict(os.environ,PAPER_RELEASE_VERSION=VERSION,PAPER_QA_DIR=FINAL.relative_to(ROOT).as_posix())
shutil.copy2(Path(__file__),QA/"packaging-runner-r4d.py")
def run(label,tool,*flags):
    log=QA/(label+"-r4d-packaging.log");assert not log.exists()
    print("Starting "+label,flush=True)
    with log.open("w",encoding="utf-8") as stream:
        result=subprocess.run([sys.executable,str(ROOT/"tools/paper-warfront"/tool),*map(str,flags)],cwd=ROOT,env=env,stdout=stream,stderr=subprocess.STDOUT,timeout=1200)
    assert result.returncode==0,"Inspect "+str(log)
    print(label+" completed",flush=True)
run("initial-package","package_rc34_preview.py")
saved=QA/"initial-proofless-package-r4d";assert not saved.exists();saved.mkdir()
for name in ["build-manifest.json","SHA256SUMS.txt","PaperWarfront-Windows-"+VERSION+".zip"]:shutil.copy2(RELEASE/name,saved/name)
run("first-audit","audit_rc34_preview.py","--version",VERSION,"--qa",FINAL)
run("final-package","package_rc34_preview.py")
run("final-audit","audit_rc34_preview.py","--version",VERSION,"--qa",FINAL,"--require-bundled-proof")
run("registration","register_rc34_release.py")
(QA/"packaging-complete.json").write_text(json.dumps({"passed":True,"version":VERSION,"scope":"Completed RC34 native exports, R4d visibility correction, compiled/UI/story/map/render checks and final ZIP binding. Dense60FPS, complete balance, human story/network and physical Android remain pending."},indent=2)+"\n","utf-8")
print("RC34 final ZIP, APK and immutable revision completed",flush=True)
