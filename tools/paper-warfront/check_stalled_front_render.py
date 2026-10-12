"""Verify paid control-lock response in the actual exported App on Windows GPU."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[2]
ap=argparse.ArgumentParser()
ap.add_argument('--pack',type=Path,required=True)
ap.add_argument('--output',type=Path,required=True)
args=ap.parse_args()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
observer=ROOT/'tools/paper-warfront/probe_stalled_front_render.gd'
startup=subprocess.STARTUPINFO();startup.dwFlags=1;startup.wShowWindow=0
args.output.mkdir(parents=True,exist_ok=True)
cases=[]
for name,resolution,flags in [('desktop','1280x720',[]),('phone','1136x640',['--mobile-ui','--mobile-density','2'])]:
    folder=args.output.resolve()/name
    assert not (folder/'report.json').exists(), 'Never overwrite completed observations'
    folder.mkdir(parents=True,exist_ok=True)
    cmd=[str(ROOT/'.tools/godot/Godot_v4.7.2-stable_win64_console.exe'),'--main-pack',str(args.pack.resolve()),
         '--rendering-method','gl_compatibility','--resolution',resolution,'--script',str(observer),'--',*flags,
         '--output',str(folder),'--profile-path',str(folder/'profile.json')]
    run=subprocess.run(cmd,cwd=ROOT,capture_output=True,encoding='utf-8',errors='replace',timeout=180,startupinfo=startup)
    log=run.stdout+run.stderr
    (folder/'runtime.log').write_text(log,'utf-8')
    path=folder/'report.json'
    assert path.exists() and 'SCRIPT ERROR' not in log and 'ERROR:' not in log,log[-2500:]
    report=json.loads(path.read_text('utf-8'))
    assert all(p.endswith('.gdc') for p in report['inputs'])
    assert report['config']['faction']=='yin' and report['config']['enemy']=='mu'
    assert report['observer_sha256']==sha(observer)
    for shot in report['captures']:assert sha(Path(shot['path']))==shot['sha256']
    result={'name':name,'passed':report['passed'] and run.returncode==0,'checks':len(report['checks']),
            'failed':[c for c in report['checks'] if not c['passed']]}
    cases.append(result);print(json.dumps(result),flush=True)
    assert result['passed'],log[-2500:]
(args.output/'report.json').write_text(json.dumps({'passed':True,'cases':cases,'observer_sha256':sha(observer),
    'runner_sha256':sha(Path(__file__)),'pack_sha256':sha(args.pack),
    'scope':'Actual exported App compiled scripts on native Windows GPU; paid Yin/Mu normal300/4s entry, owned control victim and two production/positive-hit chains. Phone metrics injected; not Android hardware or real-time FPS.'},indent=2),'utf-8')
