"""Actual native UI skins, input states, menus and optional compiled EXE pack."""
from pathlib import Path
import argparse, hashlib, json, subprocess, sys, time
from PIL import Image
ROOT=Path(__file__).resolve().parents[2]

def main():
    sys.stdout.reconfigure(encoding='utf-8')
    ap=argparse.ArgumentParser();ap.add_argument('--pack',type=Path);ap.add_argument('--output',type=Path,default=ROOT/'output/qa/godot/ui-rc16/style');args=ap.parse_args()
    output=args.output.resolve();output.mkdir(parents=True,exist_ok=True)
    startup=subprocess.STARTUPINFO();startup.dwFlags=1;startup.wShowWindow=0
    test=ROOT/'game/tests/paper_ui_qa.gd'
    if args.pack:
        # Test scaffold stays external. res:// App and theme resolve through the
        # actual EXE's compiled remaps, never a source project added to the pack.
        source=test.read_text('utf-8').replace('res://tests/mobile_ui_qa.gd',(ROOT/'game/tests/mobile_ui_qa.gd').as_posix())
        test=output/'packaged_paper_ui_qa.gd';test.write_text(source,encoding='utf-8')
    results=[]
    for name,extra in [('desktop',[]),('phone',['--mobile-ui','--mobile-density','2'])]:
        folder=output/name;folder.mkdir(parents=True,exist_ok=True);(folder/'report.json').unlink(missing_ok=True)
        engine=[str(ROOT/'.tools/godot/Godot_v4.7.2-stable_win64_console.exe')]
        engine+=['--main-pack',str(args.pack.resolve())] if args.pack else ['--path',str(ROOT/'game')]
        started=time.time()
        run=subprocess.run([*engine,'--rendering-method','gl_compatibility','--script',str(test),'--',*extra,'--output',str(folder),'--profile-path',str(folder/'profile.json')],cwd=ROOT,encoding='utf-8',errors='replace',capture_output=True,startupinfo=startup,timeout=120)
        log=run.stdout+run.stderr;(folder/'native.log').write_text(log,encoding='utf-8')
        report=json.loads((folder/'report.json').read_text('utf-8')) if (folder/'report.json').exists() else {}
        passed=run.returncode==0 and report.get('passed',False) and 'SCRIPT ERROR' not in log and 'ERROR:' not in log
        frames=[]
        for filename in report.get('shots',[]):
            path=folder/filename
            assert path.is_file() and path.stat().st_mtime>=started,(name,filename,'Screenshot must come from this run')
            with Image.open(path) as image:
                image.verify()
            frames.append({'file':path.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
        result={'case':name,'passed':passed,'checks':len(report.get('checks',[])),'screenshots':len(frames),'image_files':frames,'inputs':report.get('inputs',{}),'failures':[c for c in report.get('checks',[]) if not c['passed']]}
        if args.pack:assert all(not p.endswith('.gd') for p in result['inputs']), 'Source isolation failed'
        results.append(result);print(json.dumps({key:result[key] for key in ['case','passed','checks','screenshots','failures']},ensure_ascii=False),flush=True)
        if not passed:print(log[-1800:],flush=True)
    proof={'passed':all(r['passed'] for r in results),'cases':results,'compiled_pack':bool(args.pack),'pack_sha256':hashlib.sha256(args.pack.read_bytes()).hexdigest() if args.pack else None,'scope':'Native Windows GPU UI. Injected mobile metrics, not Android hardware.'}
    (output/'report.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return 0 if proof['passed'] else 1

if __name__=='__main__':sys.exit(main())
