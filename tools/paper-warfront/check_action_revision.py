"""Native Windows rc4 checks. No virtualization and no Android emulator."""
from pathlib import Path
import argparse, subprocess, json, sys, shutil
ROOT=Path(__file__).resolve().parents[2]
QA=ROOT/'output/qa/godot/actions-rc4'
ENGINE=ROOT/'.tools/godot/Godot_v4.7.2-stable_win64_console.exe'

def run(name,args,timeout=300):
    startup=subprocess.STARTUPINFO();startup.dwFlags=1;startup.wShowWindow=0
    r=subprocess.run([str(ENGINE),'--path',str(ROOT/'game'),*map(str,args)],cwd=ROOT,capture_output=True,text=True,encoding='utf-8',errors='replace',startupinfo=startup,timeout=timeout)
    log=r.stdout+'\n'+r.stderr;(QA/(name+'.log')).write_text(log,encoding='utf-8')
    errors=[x for x in log.splitlines() if x.startswith(('ERROR:','SCRIPT ERROR:'))]
    print(json.dumps({'run':name,'exit':r.returncode,'errors':errors[:5]},ensure_ascii=False),flush=True)
    if r.returncode or errors:print(log[-2500:]);raise RuntimeError(name+' failed')

def main():
    sys.stdout.reconfigure(encoding='utf-8');p=argparse.ArgumentParser();p.add_argument('mode',choices=['import','preview','gallery','pan','contracts','audio','duels']);args=p.parse_args();QA.mkdir(parents=True,exist_ok=True)
    if args.mode=='import':run('import',['--headless','--editor','--import','--quit'],600)
    elif args.mode=='contracts':
        for script,name in [('test_unit_actions','actions'),('test_combat_ownership','ownership'),('test_worker_actions','workers'),('test_world_foundation','foundation')]:
            path=QA/(name+'-report.json')
            run(name,['--headless','-s','res://tests/'+script+'.gd','--','--output',path])
    elif args.mode in ['audio','duels']:
        folder=QA/('audio' if args.mode=='audio' else 'weapon-duels');folder.mkdir(exist_ok=True)
        run(args.mode,[*(['--headless'] if args.mode=='audio' else ['--rendering-method','gl_compatibility','--resolution','1600x900']),'-s','res://tests/'+('test_weapon_audio' if args.mode=='audio' else 'record_weapon_duels')+'.gd','--','--output',folder,'--profile-path',folder/'isolated-profile.json'])
    elif args.mode=='pan':
        folder=QA/'pan';folder.mkdir(exist_ok=True)
        run('pan',['--rendering-method','gl_compatibility','--resolution','1600x900','-s','res://tests/test_pan_and_menu.gd','--','--output',folder,'--profile-path',folder/'isolated-profile.json'])
    else:
        folder=QA/args.mode;folder.mkdir(exist_ok=True)
        run(args.mode,['--rendering-method','gl_compatibility','--resolution','1600x900','-s','res://tests/record_unit_actions.gd','--','--output',folder,*(['--preview'] if args.mode=='preview' else [])],600)
        report=json.loads((folder/'gallery-report.json').read_text(encoding='utf-8'))
        assert report['units']==(12 if args.mode=='preview' else 412)
        if report['frames']:
            ffmpeg=shutil.which('ffmpeg');assert ffmpeg
            r=subprocess.run([ffmpeg,'-y','-loglevel','error','-framerate','15','-i',str(folder/'frames/frame-%04d.png'),'-frames:v',str(report['frames']),'-c:v','libx264','-crf','19','-pix_fmt','yuv420p','-movflags','+faststart',str(folder/'unit-actions.mp4')],capture_output=True,timeout=90)
            assert r.returncode==0,r.stderr.decode('utf-8','replace')

if __name__=='__main__':main()
