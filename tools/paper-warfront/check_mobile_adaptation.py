"""Native Windows Godot screen/touch matrix; never an Android emulator."""
from pathlib import Path
import argparse, subprocess, json, sys, time, re, os

ROOT=Path(__file__).resolve().parents[2]
ENGINE=ROOT/'.tools/godot/Godot_v4.7.2-stable_win64_console.exe'
QA=ROOT/os.environ.get('PAPER_QA_DIR','output/qa/godot/frame-rebuild')/'mobile'
CASES=[
    ('compact-16x9','1136x640','2','0,0,0,0'),
    ('phone-16x9','1280x720','2','0,0,0,0'),
    ('phone-high-density','1920x1080','3','0,0,0,0'),
    ('phone-notch','2340x1080','3','72,0,24,18'),
    ('phone-reverse-notch','2400x1080','3','24,0,96,18'),
    ('tablet-4x3','1600x1200','2','0,24,0,24'),
    ('tablet-16x10','1920x1200','2','0,32,0,32'),
    ('portrait-recovery','960x1280','2','0,0,0,0'),
]

def main():
    sys.stdout.reconfigure(encoding='utf-8')
    project=(ROOT/'game/project.godot').read_text(encoding='utf-8')
    match=re.search(r'^config/version="([^"]+)"$',project,re.M)
    assert match,'Project version is required for mobile evidence'
    version=os.environ.get('PAPER_RELEASE_VERSION',match.group(1))
    assert version==match.group(1),'Requested mobile QA version must match the actual project'
    parser=argparse.ArgumentParser();parser.add_argument('--case');args=parser.parse_args()
    startup=subprocess.STARTUPINFO();startup.dwFlags=1;startup.wShowWindow=0
    selected=[c for c in CASES if not args.case or args.case==c[0]]
    assert selected,'Unknown case'
    outcomes=[]
    for name,resolution,density,insets in selected:
        folder=QA/name;folder.mkdir(parents=True,exist_ok=True)
        (folder/'report.json').unlink(missing_ok=True)
        stamp=time.monotonic()
        try:
            run=subprocess.run([str(ENGINE),'--path',str(ROOT/'game'),'--rendering-method','gl_compatibility','--resolution',resolution,'--','--mobile-ui','--mobile-density',density,'--mobile-insets',insets,'--qa-mobile',str(folder),'--profile-path',str(folder/'isolated-profile.json')],cwd=ROOT,capture_output=True,encoding='utf-8',errors='replace',startupinfo=startup,timeout=240)
        except subprocess.TimeoutExpired as error:
            def decoded(value):
                return value.decode('utf-8', errors='replace') if isinstance(value, bytes) else value or ''
            (folder/'native.log').write_text(decoded(error.stdout)+'\n'+decoded(error.stderr),encoding='utf-8')
            print(json.dumps({'name':name,'passed':False,'reason':'native process exceeded 240 seconds','log':str(folder/'native.log')}),flush=True)
            sys.exit(1)
        log=run.stdout+'\n'+run.stderr;(folder/'native.log').write_text(log,encoding='utf-8')
        report=json.loads((folder/'report.json').read_text(encoding='utf-8')) if (folder/'report.json').exists() else {}
        coverage=report.get('battlefield_coverage',[])
        coverage_ok=len(coverage)==10 and all(row['passed'] and row['details']['visible_ratio']>=.70 for row in coverage)
        requested=tuple(map(int,resolution.split('x')))
        expected=(max(requested),min(requested)) if name=='portrait-recovery' else requested
        observed=tuple(map(float,re.findall(r'[-\d.]+',report.get('metrics',{}).get('pixels',''))))
        passed=run.returncode==0 and report.get('passed',False) and report.get('version')==version and observed==expected and coverage_ok and not any(line.startswith(('ERROR:','SCRIPT ERROR:')) for line in log.splitlines())
        outcome={'name':name,'physical_resolution':resolution,'density':density,'safe_insets_px':insets,'passed':passed,'exit_code':run.returncode,'checks':len(report.get('checks',[])),'seconds':round(time.monotonic()-stamp,2),'failures':report.get('failures',[]),'metrics':report.get('metrics',{})}
        outcome['minimum_battlefield_ratio']=min((row['details']['visible_ratio'] for row in coverage),default=0)
        outcomes.append(outcome)
        print(json.dumps(outcome,ensure_ascii=False),flush=True)
        if not passed:print(log[-4500:],flush=True)
    if not args.case:
        (QA/'mobile-matrix.json').write_text(json.dumps({'version':version,'passed':all(r['passed'] for r in outcomes),'checks':sum(r['checks'] for r in outcomes),'cases':outcomes,'scope':'Actual native Windows Godot GPU and touch events, injected display metrics. Android hardware is unverified.'},ensure_ascii=False,indent=2),encoding='utf-8')
    sys.exit(0 if all(r['passed'] for r in outcomes) else 1)

if __name__=='__main__':main()
