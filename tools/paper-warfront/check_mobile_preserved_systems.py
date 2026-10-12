"""Current desktop pointer regression and ordinary paid native mobile replay."""
from pathlib import Path
import json,subprocess,shutil,sys

ROOT=Path(__file__).resolve().parents[2]
QA=ROOT/'output/qa/godot/frame-rebuild/mobile'
ENGINE=ROOT/'.tools/godot/Godot_v4.7.2-stable_win64_console.exe'

def main():
    sys.stdout.reconfigure(encoding='utf-8')
    startup=subprocess.STARTUPINFO();startup.dwFlags=1;startup.wShowWindow=0
    runs=[('desktop',['--','--qa-theatre',str(QA/'desktop'),'--profile-path',str(QA/'desktop/isolated-profile.json')],[]),
          ('native-play',['-s','res://tests/record_theatre_battle.gd','--','--mobile-ui','--mobile-density','2','--output',str(QA/'native-play'),'--profile-path',str(QA/'native-play/isolated-profile.json')],['--rendering-method','gl_compatibility','--resolution','1280x720'])]
    for name,args,engine_flags in runs:
        folder=QA/name;folder.mkdir(parents=True,exist_ok=True);(folder/'report.json').unlink(missing_ok=True)
        run=subprocess.run([str(ENGINE),'--path',str(ROOT/'game'),*engine_flags,*args],cwd=ROOT,capture_output=True,text=True,encoding='utf-8',errors='replace',startupinfo=startup,timeout=240)
        log=run.stdout+'\n'+run.stderr;(folder/'native.log').write_text(log,encoding='utf-8')
        assert run.returncode==0 and (folder/'report.json').exists(),(name,run.returncode,log[-2000:])
        assert not any(line.startswith(('ERROR:','SCRIPT ERROR:')) for line in log.splitlines()),(name,log[-2000:])
        report=json.loads((folder/'report.json').read_text(encoding='utf-8'))
        assert not report.get('failures') and not report.get('capture_errors') and report.get('passed',True)
        print(name+' current native regression passed',flush=True)
    ffmpeg=shutil.which('ffmpeg');assert ffmpeg
    args=[ffmpeg,'-y','-loglevel','error','-framerate','15','-start_number','0','-i',str(QA/'native-play/frames/frame-%04d.png'),'-frames:v','300','-c:v','libx264','-crf','20','-pix_fmt','yuv420p','-movflags','+faststart','-metadata','comment=Silent offline 15fps replay; cut between simulation14-24s and40-50s. Not realtime device performance.',str(QA/'native-play/mobile-play.mp4')]
    run=subprocess.run(args,cwd=ROOT,capture_output=True,text=True,encoding='utf-8',errors='replace',startupinfo=startup,timeout=90)
    (QA/'native-play/encode.log').write_text(run.stdout+'\n'+run.stderr,encoding='utf-8');assert run.returncode==0,run.stderr
    print('Silent offline paid replay encoded: 300 frames / 15fps',flush=True)

if __name__=='__main__':main()
