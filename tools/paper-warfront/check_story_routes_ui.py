"""Native story selection/save/input QA against the actual exported EXE pack."""
from pathlib import Path
import argparse,hashlib,json,shutil,subprocess
ROOT=Path(__file__).resolve().parents[2]
p=argparse.ArgumentParser();p.add_argument('--pack',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
dest=a.output.resolve();assert not dest.exists(), 'Completed story UI observations are immutable'
dest.mkdir(parents=True)
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
observer=dest/'observer.gd';shutil.copyfile(ROOT/'tools/paper-warfront/probe_story_routes_ui.gd',observer)
shutil.copyfile(Path(__file__),dest/'runner.py')
startup=subprocess.STARTUPINFO();startup.dwFlags=1;startup.wShowWindow=0
cases=[]
for name,resolution,flags,backend in [('desktop','1280x720',[],[]),('phone','1136x640',['--mobile-ui','--mobile-density','2'],['--rendering-method','gl_compatibility'])]:
 folder=dest/name;folder.mkdir()
 cmd=[str(ROOT/'.tools/godot/Godot_v4.7.2-stable_win64_console.exe'),*backend,'--main-pack',str(a.pack.resolve()),'--resolution',resolution,'--script',str(observer),'--',*flags,'--output',str(folder),'--profile-path',str(folder/'profile.json')]
 (folder/'request.json').write_text(json.dumps({'command':cmd,'pack_sha256':sha(a.pack),'observer_sha256':sha(observer)},ensure_ascii=False,indent=2),'utf-8')
 run=subprocess.run(cmd,cwd=ROOT,capture_output=True,encoding='utf-8',errors='replace',timeout=120,startupinfo=startup)
 log=run.stdout+run.stderr;(folder/'runtime.log').write_text(log,'utf-8')
 report=json.loads((folder/'report.json').read_text('utf-8'))
 assert run.returncode==0 and report['passed'] and 'SCRIPT ERROR' not in log and 'ERROR:' not in log,log[-3000:]
 assert report['observer_sha256']==sha(observer) and len(report['captures'])==8 and report['authored_briefs_checked']==200
 assert all(name.endswith('.gdc') for name in report['inputs']), 'Never substitute source UI/gameplay'
 for capture in report['captures']:assert sha(folder/capture['path'])==capture['sha256']
 cases.append({'name':name,'checks':report['checks'],'passed':report['passed'],'report_sha256':sha(folder/'report.json')})
 print(json.dumps(cases[-1]),flush=True)
(dest/'report.json').write_text(json.dumps({'passed':True,'cases':cases,'pack_sha256':sha(a.pack),'observer_sha256':sha(observer),'runner_sha256':sha(dest/'runner.py'),'scope':'Actual compiled EXE App/UI, native Windows mouse/ScreenTouch, isolated save and forced result transitions. Not paid victories or Android hardware.'},indent=2),'utf-8')
