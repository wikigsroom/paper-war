"""Native Windows Godot QA runner for the frame-based asymmetric revision."""
from pathlib import Path
import argparse,subprocess,json,sys
ROOT=Path(__file__).resolve().parents[2];GAME=ROOT/'game';ENGINE=ROOT/'.tools/godot/Godot_v4.7.2-stable_win64_console.exe';QA=ROOT/'output/qa/godot/frame-rebuild'
def run(args,label):
    QA.mkdir(parents=True,exist_ok=True)
    r=subprocess.run([str(a) for a in args],cwd=ROOT,capture_output=True,text=True,encoding='utf-8',errors='replace',creationflags=subprocess.CREATE_NO_WINDOW)
    s=r.stdout+'\n'+r.stderr;(QA/(label+'.log')).write_text(s,encoding='utf-8')
    errors=[line for line in s.splitlines() if line.startswith(('ERROR:','SCRIPT ERROR:'))]
    print(json.dumps({'run':label,'exit':r.returncode,'errors':errors},ensure_ascii=False),flush=True)
    if r.returncode or errors:print(s[-5000:]);raise SystemExit(1)
def main():
    sys.stdout.reconfigure(encoding='utf-8');p=argparse.ArgumentParser();p.add_argument('mode',choices=['import','gallery','contracts','pan','audio','duels','motion']);args=p.parse_args()
    if args.mode=='import':run([ENGINE,'--headless','--path',GAME,'--editor','--import','--quit'],'import')
    elif args.mode=='gallery':
        out=QA/'native-frames';out.mkdir(parents=True,exist_ok=True)
        run([ENGINE,'--path',GAME,'--script','res://tests/record_frame_review.gd','--','--out',out],'gallery')
    elif args.mode in ['pan','audio','duels','motion']:
        script={'pan':'test_pan_and_menu.gd','audio':'test_weapon_audio.gd','duels':'record_weapon_duels.gd','motion':'record_frame_motion.gd'}[args.mode]
        out=QA/args.mode;out.mkdir(parents=True,exist_ok=True)
        flags=['--headless'] if args.mode=='audio' else ['--rendering-method','gl_compatibility']
        if args.mode=='pan':flags+=['--resolution','1600x900']
        run([ENGINE,*flags,'--path',GAME,'--script','res://tests/'+script,'--','--output',out,'--profile-path',out/'isolated-profile.json'],args.mode)
    else:
        for script,label in [('test_distinct_factions.gd','factions'),('test_frame_contracts.gd','frames'),('test_combat_ownership.gd','ownership'),('test_worker_actions.gd','workers'),('test_world_foundation.gd','foundation')]:
            option='--report' if label in ['factions','frames'] else '--output'
            run([ENGINE,'--headless','--path',GAME,'--script','res://tests/'+script,'--',option,QA/(label+'-report.json')],label)
if __name__=='__main__':main()
