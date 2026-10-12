"""Run one native mobile adaptation case against an isolated source project."""
from pathlib import Path
import os
import subprocess
import sys
import argparse

ROOT=Path(__file__).resolve().parents[2]
ENGINE=ROOT/'.tools/godot/Godot_v4.7.2-stable_win64_console.exe'
from check_mobile_adaptation import CASES
ap=argparse.ArgumentParser();ap.add_argument('--project',type=Path,required=True);ap.add_argument('--case',required=True);ap.add_argument('--output',type=Path,required=True)
a=ap.parse_args()
project=a.project.resolve();selected=[c for c in CASES if c[0]==a.case];assert selected
name,resolution,density,insets=selected[0]
folder=a.output.resolve()/name;folder.mkdir(parents=True,exist_ok=True)
env=dict(os.environ,PAPER_QA_DIR=str(a.output.resolve().parent.relative_to(ROOT)).replace('\\','/'),PAPER_RELEASE_VERSION='3.0.0-rc33-preview')
run=subprocess.run([str(ENGINE),'--path',str(project),'--rendering-method','gl_compatibility','--resolution',resolution,'--','--mobile-ui','--mobile-density',density,'--mobile-insets',insets,'--qa-mobile',str(folder),'--profile-path',str(folder/'isolated-profile.json')],cwd=ROOT,capture_output=True,encoding='utf-8',errors='replace',timeout=300)
(folder/'native.log').write_text(run.stdout+'\n'+run.stderr,'utf-8')
report=folder/'report.json';assert report.exists(),(folder/'native.log').read_text('utf-8')[-4000:]
print(report.read_text('utf-8'),flush=True)
raise SystemExit(0 if run.returncode==0 else run.returncode)
