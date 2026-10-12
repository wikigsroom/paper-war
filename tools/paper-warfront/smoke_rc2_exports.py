"""Wait for the actual shipped Windows executable, with isolated QA profiles."""
from pathlib import Path
import hashlib,json,subprocess,time,sys
from PIL import Image

ROOT=Path(__file__).resolve().parents[2]
EXE=ROOT/'release/3.0.0-rc2/windows/PaperWarfront.exe'
QA=ROOT/'output/qa/godot/rc2/export'

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    sys.stdout.reconfigure(encoding='utf-8')
    QA.mkdir(parents=True,exist_ok=True)
    report={'version':'3.0.0-rc2','executable_sha256':sha(EXE),'cases':[],
            'scope':'Actual exported Windows program, isolated profiles, native GPU screenshots. Demo uses a controlled full-technology scenario; normal paid gameplay is recorded separately. Not Android hardware or performance proof.'}
    startup=subprocess.STARTUPINFO();startup.dwFlags|=subprocess.STARTF_USESHOWWINDOW;startup.wShowWindow=0
    for name,engine,extra in [('menu',[],[]),('battle',[],['--demo']),('menu-compatibility',['--rendering-method','gl_compatibility'],[])]:
        picture=QA/(name+'.png');picture.unlink(missing_ok=True)
        args=[str(EXE),*engine,'--',*extra,'--capture',str(picture),'--quit-after-capture','--profile-path',str(QA/(name+'-profile.json'))]
        stamp=time.monotonic()
        p=subprocess.run(args,cwd=ROOT,capture_output=True,text=True,encoding='utf-8',errors='replace',startupinfo=startup,timeout=75)
        log=p.stdout+'\n'+p.stderr;(QA/(name+'.log')).write_text(log,encoding='utf-8')
        assert p.returncode==0 and picture.exists(),(name,p.returncode,log[-1000:])
        assert not any(line.startswith(('ERROR:','SCRIPT ERROR:')) for line in log.splitlines()),name
        im=Image.open(picture);im.verify()
        report['cases'].append({'name':name,'exit_code':p.returncode,'seconds':round(time.monotonic()-stamp,3),'image':picture.relative_to(ROOT).as_posix(),'image_sha256':sha(picture),'passed':True})
        print(name+' actual EXE smoke passed',flush=True)
    report['passed']=True
    (QA/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

if __name__=='__main__':main()
