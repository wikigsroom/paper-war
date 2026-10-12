"""Smoke the actual exported executable, using native GPU and isolated saves."""
from pathlib import Path
import hashlib,json,subprocess,time,sys,os
from PIL import Image

ROOT=Path(__file__).resolve().parents[2]
VERSION=os.environ.get('PAPER_RELEASE_VERSION','3.0.0-rc5')
EXE=ROOT/f'release/{VERSION}/windows/PaperWarfront.exe'
QA=ROOT/os.environ.get('PAPER_QA_DIR','output/qa/godot/frame-rebuild')/'mobile/export'

def sha(path):
    digest=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1048576),b''):digest.update(block)
    return digest.hexdigest()

def main():
    sys.stdout.reconfigure(encoding='utf-8');QA.mkdir(parents=True,exist_ok=True)
    report={'version':VERSION,'executable_sha256':sha(EXE),'cases':[],
            'scope':'Actual exported Windows executable, isolated saves, native GPU. Mobile metrics injected; not Android hardware. --demo uses a controlled full-technology scenario; ordinary paid gameplay has its own report.'}
    startup=subprocess.STARTUPINFO();startup.dwFlags=1;startup.wShowWindow=0
    cases=[('desktop-menu',[],[],(1280,720)),('desktop-battle',[],['--demo'],(1280,720)),
           ('mobile-phone',['--rendering-method','gl_compatibility'],['--mobile-ui','--mobile-density','2','--demo'],(1280,720)),
           ('mobile-compact',['--rendering-method','gl_compatibility','--resolution','1136x640'],['--mobile-ui','--mobile-density','2','--demo'],(1136,640)),
           ('mobile-notch',['--rendering-method','gl_compatibility','--resolution','2340x1080'],['--mobile-ui','--mobile-density','3','--mobile-insets','72,0,24,18','--demo'],(2340,1080)),
           ('mobile-tablet',['--rendering-method','gl_compatibility','--resolution','1600x1200'],['--mobile-ui','--mobile-density','2','--mobile-insets','0,24,0,24'],(1600,1200))]
    (QA/'report.json').unlink(missing_ok=True)
    for name,engine,extra,size in cases:
        picture=QA/(name+'.png');picture.unlink(missing_ok=True);stamp=time.monotonic()
        args=[str(EXE),*engine,'--',*extra,'--capture',str(picture),'--quit-after-capture','--profile-path',str(QA/(name+'-profile.json'))]
        run=subprocess.run(args,cwd=ROOT,capture_output=True,text=True,encoding='utf-8',errors='replace',startupinfo=startup,timeout=90)
        log=run.stdout+'\n'+run.stderr;(QA/(name+'.log')).write_text(log,encoding='utf-8')
        assert run.returncode==0 and picture.exists(),(name,run.returncode,log[-1500:])
        assert not any(line.startswith(('ERROR:','SCRIPT ERROR:')) for line in log.splitlines()),name
        with Image.open(picture) as im:
            assert im.size==size,(name,im.size,size);im.verify()
        report['cases'].append({'name':name,'passed':True,'exit_code':0,'physical_size':size,'seconds':round(time.monotonic()-stamp,3),'image':picture.relative_to(ROOT).as_posix(),'image_sha256':sha(picture)})
        print(name+' actual EXE passed',flush=True)
    report['passed']=True
    (QA/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

if __name__=='__main__':main()
