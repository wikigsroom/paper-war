"""Finish RC32 package, identical bundled proof and revision after validation."""
from pathlib import Path
import json
import os
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2]
QA=ROOT/"output/qa/godot/contact-runtime-rc32";FINAL=QA/"release-final"
VERSION="3.0.0-rc32-preview";RELEASE=ROOT/"release"/VERSION
assert json.loads((FINAL/"validation-report.json").read_text("utf-8"))["passed"]
env=dict(os.environ,PAPER_RELEASE_VERSION=VERSION,PAPER_QA_DIR=FINAL.relative_to(ROOT).as_posix())
shutil.copy2(Path(__file__),QA/"packaging-runner.py")
def run(label,tool,*flags):
    log=QA/(label+"-packaging.log");assert not log.exists()
    print("Starting "+label,flush=True)
    with log.open("w",encoding="utf-8") as f:
        x=subprocess.run([sys.executable,str(ROOT/"tools/paper-warfront"/tool),*map(str,flags)],cwd=ROOT,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=1200)
    assert x.returncode==0,"Inspect "+str(log)
    print(label+" completed",flush=True)
run("publication","publish_answers_release.py")
run("initial-package","package_preview.py")
saved=QA/"initial-proofless-package";assert not saved.exists();saved.mkdir()
for n in ["build-manifest.json","SHA256SUMS.txt","PaperWarfront-Windows-"+VERSION+".zip"]:shutil.copy2(RELEASE/n,saved/n)
run("first-audit","audit_answers_preview.py","--version",VERSION,"--qa",FINAL)
run("final-package","package_preview.py")
run("final-audit","audit_answers_preview.py","--version",VERSION,"--qa",FINAL,"--require-bundled-proof")
run("registration","register_answers_release.py")
(QA/"packaging-complete.json").write_text(json.dumps({"passed":True,"version":VERSION,
    "scope":"Completed exports and serial native checks; final Windows ZIP contains identical fully audited preview verification. APK, EXE and immutable revision bound. Dense60FPS/balance/human/hardware remain pending."
},indent=2)+"\n","utf-8")
print("RC32 final ZIP, APK and immutable revision completed",flush=True)
