"""Resume unchanged RC32 artifacts after repairing the compiled observer loader/count."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2];QA=ROOT/"output/qa/godot/contact-runtime-rc32"
FINAL=QA/"release-final";VERSION="3.0.0-rc32-preview"
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text("utf-8"))
assert not (FINAL/"validation-report.json").exists() and not (QA/"compiled-observer-repair.json").exists()
manifest=read(ROOT/"release"/VERSION/"build-manifest.json")
assert all(sha(ROOT/n)==d for n,d in manifest["source_inputs"].items())
assert all(sha(ROOT/r["path"])==r["sha256"] for r in manifest["builds"])
first=read(FINAL/"validation-progress-r1.json")
assert first["version"]==VERSION and first["jobs"][-1]=={"name":"answers-windows","passed":False,"exit_code":1}
assert all(r["passed"] for r in first["jobs"][:-1])
retained={}
for n in ["apk-logic/report.json","windows-logic/report.json","dense-windows/report.json","terrain-windows/report.json"]:
    p=FINAL/n;assert read(p)["passed"];retained[n]=sha(p)
assert read(FINAL/"apk-logic/report.json")["apk_sha256"]==manifest["builds"][1]["sha256"]
assert read(FINAL/"windows-logic/report.json")["executable_sha256"]==manifest["builds"][0]["sha256"]
fixed=read(FINAL/"answers-windows/report.json")
assert fixed["passed"] and fixed["checks"]==640706 and fixed["artifact_sha256"]==manifest["builds"][0]["sha256"]
shutil.copy2(ROOT/"release"/VERSION/"build-manifest.json",QA/"compiled-observer-repair-build-manifest.json")
repair={"passed":True,"unchanged_manifest_sha256":sha(ROOT/"release"/VERSION/"build-manifest.json"),
    "manifest_snapshot":"compiled-observer-repair-build-manifest.json",
    "retained_passed_reports":retained,"repaired_windows_report_sha256":sha(FINAL/"answers-windows/report.json"),
    "original_runner_sha256":sha(ROOT/"tools/paper-warfront/run_answers_release_validation.py"),
    "resume_runner_sha256":sha(Path(__file__)),
    "failed_compiled_runner_sha256":{"r1":sha(QA/"compiled-check-runner-r1.py"),"r2":sha(QA/"compiled-check-runner-r2.py")},
    "current_compiled_runner_sha256":sha(ROOT/"tools/paper-warfront/check_answers_packaged_logic.py"),
    "scope":"First wrapper rejected direct-GDC type errors; second native states passed but raw44 vs exported42 script count was wrong. Both failed directories preserved. Third observation passed with original resource remaps and exact exported42 set. Runtime/source/artifact bytes unchanged; already passed foundation/dense/terrain preserved by hash. Remaining jobs fresh, FPS not yet started."}
(QA/"compiled-observer-repair.json").write_text(json.dumps(repair,indent=2)+"\n","utf-8")
shutil.copy2(Path(__file__),FINAL/"resume-validation-runner.py")
env=dict(os.environ,PAPER_RELEASE_VERSION=VERSION,PAPER_QA_DIR=FINAL.relative_to(ROOT).as_posix())
pack=ROOT/"release"/VERSION/"windows/PaperWarfront.exe"
apk=ROOT/"release"/VERSION/"android"/("PaperWarfront-"+VERSION+".apk")
rows=first["jobs"][:-1]+[{"name":"answers-windows","passed":True,"exit_code":0,"observer_repaired":True}]
def run(label,tool,*flags):
    log=FINAL/(label+"-orchestration.log");assert not log.exists()
    print("Starting "+label,flush=True)
    with log.open("w",encoding="utf-8") as f:
        x=subprocess.run([sys.executable,str(ROOT/"tools/paper-warfront"/tool),*map(str,flags)],cwd=ROOT,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=2400)
    row={"name":label,"passed":x.returncode==0,"exit_code":x.returncode};rows.append(row)
    (FINAL/"validation-progress.json").write_text(json.dumps({"version":VERSION,"jobs":rows},indent=2),"utf-8")
    print(json.dumps(row),flush=True);assert row["passed"],"Inspect "+str(log)
for prefix,tool in [("dense","check_dense_packaged_logic.py"),("terrain","check_terrain_packaged_logic.py"),("answers","check_answers_packaged_logic.py")]:
    run(prefix+"-apk",tool,"--apk-runtime",FINAL/"apk-logic/extracted-runtime","--artifact",apk,"--output",FINAL/(prefix+"-apk"))
run("paid-recipes","run_paid_release_recipes.py","--qa",QA)
run("preview-checks","run_preview_checks.py","--version",VERSION,"--qa",FINAL)
run("native-extras","run_query_native_extras.py","--version",VERSION,"--before-version","3.0.0-rc31-preview","--qa",FINAL)
run("paper-ui-assets","verify_paper_ui_assets.py","--version",VERSION,"--qa",FINAL)
run("formal-reach","verify_formal_premium_reach.py","--qa",QA/"formal-reach")
run("formal-hammer","verify_formal_hammer_reach.py","--qa",QA/"formal-hammer","--regression",QA/"source-final/report.json")
snapshot=subprocess.run(["powershell","-NoProfile","-Command","Get-CimInstance Win32_Process -Filter \"Name LIKE 'Godot%'\" | Select-Object ProcessId,Name,CommandLine | ConvertTo-Json -Depth 3"],cwd=ROOT,capture_output=True,encoding="utf-8",errors="replace",timeout=30)
(FINAL/"before-realtime-processes.json").write_text(snapshot.stdout,"utf-8")
run("native-realtime","run_realtime_release.py","--version",VERSION,"--before-version","3.0.0-rc31-preview","--qa",FINAL/"realtime")
(FINAL/"validation-report.json").write_text(json.dumps({"passed":True,"version":VERSION,"runner_sha256":sha(Path(__file__)),
    "observer_repair_proof_sha256":sha(QA/"compiled-observer-repair.json"),"jobs":rows,
    "scope":"Actual unchanged RC32 exports: passed foundations retained after tool-only repair; remaining compiled/native UI/render checks fresh. Serial natural frame observation starts after own copy/hash/export/other QA is terminal. External user processes preserved. Android hardware and dense60FPS/global balance not claimed."
},indent=2)+"\n","utf-8")
print("All RC32 native export and validation phases completed",flush=True)
