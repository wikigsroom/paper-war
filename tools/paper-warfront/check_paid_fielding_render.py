"""Observe actual exported AI recruitment and battle under normal menu settings."""
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
startup=subprocess.STARTUPINFO();startup.dwFlags=1;startup.wShowWindow=0
observer=ROOT/'tools/paper-warfront/probe_paid_fielding_render.gd'
cases=[]
for name,resolution,flags in [('desktop','1280x720',[]),('phone','1136x640',['--mobile-ui','--mobile-density','2'])]:
    folder=args.output.resolve()/name;folder.mkdir(parents=True,exist_ok=True)
    cmd=[str(ROOT/'.tools/godot/Godot_v4.7.2-stable_win64_console.exe'),'--main-pack',str(args.pack.resolve()),
         '--rendering-method','gl_compatibility','--resolution',resolution,'--script',str(observer),'--',*flags,
         '--output',str(folder),'--profile-path',str(folder/'profile.json')]
    run=subprocess.run(cmd,cwd=ROOT,capture_output=True,encoding='utf-8',errors='replace',timeout=180,startupinfo=startup)
    log=run.stdout+run.stderr;(folder/'runtime.log').write_text(log,encoding='utf-8')
    path=folder/'report.json'
    if not path.exists() or 'SCRIPT ERROR' in log or 'ERROR:' in log:raise RuntimeError(log[-3500:])
    report=json.loads(path.read_text('utf-8'))
    assert all(p.endswith('.gdc') for p in report['inputs']), 'Source gameplay isolation failed'
    for capture in report['captures']:
        assert hashlib.sha256(Path(capture['path']).read_bytes()).hexdigest()==capture['sha256']
    cases.append({'name':name,'passed':report['passed'] and run.returncode==0,'checks':len(report['checks']),
                  'failed':[c for c in report['checks'] if not c['passed']]})
    print(json.dumps(cases[-1]),flush=True)
    if not cases[-1]['passed']:raise RuntimeError(log[-3500:])
proof={'passed':all(c['passed'] for c in cases),'cases':cases,
       'observer_sha256':hashlib.sha256(observer.read_bytes()).hexdigest(),
       'pack_sha256':hashlib.sha256(args.pack.read_bytes()).hexdigest()}
(args.output/'report.json').write_text(json.dumps(proof,indent=2),encoding='utf-8')
raise SystemExit(0 if proof['passed'] else 1)
