"""Capture real native GPU formation evidence with an isolated profile."""
import json, subprocess, sys, hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
QA=ROOT/"output/qa/godot/core-alignment-rc9/mixed-formation-ui"
startup=subprocess.STARTUPINFO();startup.dwFlags=1;startup.wShowWindow=0
for name,flags in (("desktop",[]),("phone",["--mobile-ui","--mobile-density","2","--mobile-insets","0,0,0,0"])):
    folder=QA/name;folder.mkdir(parents=True,exist_ok=True)
    run=subprocess.run([str(ROOT/".tools/godot/Godot_v4.7.2-stable_win64_console.exe"),"--path",str(ROOT/"game"),"--rendering-method","gl_compatibility","--resolution","1280x720","--script","res://tests/mixed_formation_ui_qa.gd","--",*flags,"--output",str(folder),"--profile-path",str(folder/"isolated-profile.json")],cwd=ROOT,capture_output=True,encoding="utf-8",errors="replace",startupinfo=startup,timeout=60)
    log=run.stdout+run.stderr;(folder/"runtime.log").write_text(log,encoding="utf-8")
    report=json.loads((folder/"report.json").read_text(encoding="utf-8")) if (folder/"report.json").exists() else {}
    passed=run.returncode==0 and report.get("passed") and "SCRIPT ERROR" not in log and "ERROR:" not in log
    assert all(hashlib.sha256((ROOT/"game"/p.removeprefix("res://")).read_bytes()).hexdigest()==h for p,h in report.get("inputs",{}).items())
    report["runtime_log_verified"]=bool(passed);(folder/"report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print(name,"passed",bool(passed),flush=True)
    if not passed:print(log[-2000:]);sys.exit(1)
