"""Exercise actual native keyboard focus and touch momentum, optionally in a compiled pack."""
from pathlib import Path
import argparse,hashlib,json,subprocess,time
from PIL import Image

ROOT=Path(__file__).resolve().parents[2]
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--pack',type=Path);ap.add_argument('--output',type=Path,required=True);args=ap.parse_args()
    output=args.output.resolve();output.mkdir(parents=True,exist_ok=True)
    observer=ROOT/'tools/paper-warfront/probe_ui_modal_navigation.gd'
    helper=ROOT/'game/tests/mobile_ui_qa.gd'
    startup=subprocess.STARTUPINFO();startup.dwFlags=1;startup.wShowWindow=0
    cases=[]
    for name,resolution,extra in [('desktop','1280x720',[]),('phone','1280x720',['--mobile-ui','--mobile-density','2']),('compact','1136x640',['--mobile-ui','--mobile-density','2'])]:
        folder=output/name;folder.mkdir(parents=True,exist_ok=True);(folder/'report.json').unlink(missing_ok=True)
        command=[str(ROOT/'.tools/godot/Godot_v4.7.2-stable_win64_console.exe')]
        command+=['--main-pack',str(args.pack.resolve())] if args.pack else ['--path',str(ROOT/'game')]
        started=time.time()
        with (folder/'native.log').open('w',encoding='utf-8') as stream:
            proc=subprocess.Popen([*command,'--rendering-method','gl_compatibility','--resolution',resolution,'--script',str(observer),'--',*extra,'--output',str(folder),'--touch-helper',helper.as_posix(),'--profile-path',str(folder/'profile.json')],cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT,startupinfo=startup)
            try:code=proc.wait(timeout=90)
            except subprocess.TimeoutExpired:
                subprocess.run(['taskkill','/PID',str(proc.pid),'/T','/F'],capture_output=True)
                code=-1
        log=(folder/'native.log').read_text(encoding='utf-8',errors='replace')
        report=json.loads((folder/'report.json').read_text(encoding='utf-8')) if (folder/'report.json').exists() else {}
        passed=code==0 and report.get('passed',False) and 'SCRIPT ERROR' not in log and 'ERROR:' not in log
        images=[]
        for filename in report.get('shots',[]):
            path=folder/filename;assert path.is_file() and path.stat().st_mtime>=started
            with Image.open(path) as image:image.verify()
            images.append({'file':path.relative_to(ROOT).as_posix(),'sha256':sha(path)})
        inputs=report.get('inputs',{})
        if args.pack and inputs:assert all(p.endswith('.gdc') for p in inputs)
        passed=passed and bool(inputs)
        case={'name':name,'passed':passed,'checks':len(report.get('checks',[])),'failures':[c for c in report.get('checks',[]) if not c['passed']],'inputs':inputs,'images':images,'version':report.get('version')}
        cases.append(case);print(json.dumps({'name':name,'passed':passed,'checks':case['checks'],'failure_count':len(case['failures']),'failures':case['failures'][:3]},ensure_ascii=True),flush=True)
        if not report:print(log[-1800:],flush=True)
    proof={'passed':all(c['passed'] for c in cases),'compiled_pack':bool(args.pack),'pack_sha256':sha(args.pack) if args.pack else None,'observer_sha256':sha(observer),'touch_helper_sha256':sha(helper),'runner_sha256':sha(Path(__file__)),'cases':cases,'scope':'Native Windows rendered game. Keyboard and injected mobile metrics, no Android hardware.'}
    (output/'report.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return 0 if proof['passed'] else 1

if __name__=='__main__':raise SystemExit(main())
