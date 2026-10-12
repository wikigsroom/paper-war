"""Verify current mobile evidence, public build inputs and release archives."""
from pathlib import Path
from urllib.parse import unquote
import argparse,hashlib,json,re,sys,zipfile
from PIL import Image
from fontTools.ttLib import TTFont
from audit_rc2_release import read,sha,strings,write

ROOT=Path(__file__).resolve().parents[2]
QA=ROOT/'output/qa/godot/mobile-rc3'
REL=ROOT/'release/3.0.0-rc3'

def main():
    sys.stdout.reconfigure(encoding='utf-8')
    parser=argparse.ArgumentParser();parser.add_argument('--archives',action='store_true');args=parser.parse_args()
    checks=[];errors=[];inputs={};reports=[]
    def require(name,condition):
        checks.append({'name':name,'passed':bool(condition)})
        if not condition:errors.append(name)
    def current(res,digest,label):
        path=ROOT/'game'/res.removeprefix('res://')
        require(label+' current '+res,path.exists() and sha(path)==digest)
        if res in inputs:require('consistent '+res,inputs[res]==digest)
        inputs[res]=digest
    def evidence(path,label):
        r=read(path)
        require(label+' passed',not r.get('failures') and not r.get('failed') and r.get('passed',True) is not False and not r.get('capture_errors'))
        for res,digest in r.get('inputs',{}).items():current(res,digest,label)
        count=r.get('checks',0);count=len(count) if isinstance(count,list) else count
        reports.append({'path':path.relative_to(ROOT).as_posix(),'sha256':sha(path),'checks':count})
        return r
    def picture(path,label):
        with Image.open(path) as im:size=im.size;im.verify()
        require(label,True);return size

    matrix=read(QA/'mobile-matrix.json');require('all eight screen configurations',matrix['passed'] and len(matrix['cases'])==8)
    mobile_count=0
    for case in matrix['cases']:
        r=evidence(QA/case['name']/'report.json',case['name'])
        mobile_count+=len(r['checks'])
        require('matrix case count '+case['name'],case['checks']==len(r['checks']) and case['exit_code']==0)
        size=tuple(map(int,case['physical_resolution'].split('x')))
        if case['name']=='portrait-recovery':
            require('portrait guard captured',picture(QA/case['name']/'00-portrait-guard.png','portrait guard PNG')==size)
            size=(max(size),min(size))
        measured=tuple(map(float,re.findall(r'[-\d.]+',r['metrics']['pixels'])))
        require('actual physical size '+case['name'],measured==size)
        require('actual density '+case['name'],float(r['metrics']['density'])==float(case['density']))
        require('actual menu capture size '+case['name'],picture(QA/case['name']/'01-menu.png',case['name']+' menu PNG')==size)
        log=(QA/case['name']/'native.log').read_text(encoding='utf-8')
        require('clean native log '+case['name'],not any(line.startswith(('ERROR:','SCRIPT ERROR:')) for line in log.splitlines()))
    require('matrix count matches reports',matrix['checks']==mobile_count)
    desktop=evidence(QA/'desktop/report.json','desktop')
    require('desktop pointer regression',desktop['passed'] and len(desktop['checks'])==197)
    core=read(QA/'rules/index.json');rule_count=0
    for row,test in zip(core,['test_combat_ownership.gd','test_worker_actions.gd','test_world_foundation.gd']):
        r=evidence(QA/'rules'/f"{row['name']}.json",row['name']);rule_count+=row['checks']
        require('core run '+row['name'],row['exit_code']==0 and row['checks']==r['checks'])
        if r.get('simulation_sha256'):current('res://scripts/battle_sim.gd',r['simulation_sha256'],row['name'])
        if r.get('assets_sha256'):current('res://data/assets.json',r['assets_sha256'],row['name'])
        if r.get('test_sha256'):current('res://tests/'+test,r['test_sha256'],row['name'])
    require('4904 core checks',rule_count==4904)
    require('paid friendly passage preserved',read(QA/'rules/ownership.json')['evidence']['paid_passage']['overlap_ticks']>0 and not read(QA/'rules/ownership.json')['evidence']['paid_passage']['friendly_hits'])
    require('all ten workers mine and deposit',len(read(QA/'rules/workers.json')['factions'])==10 and all(w['gold_deposited']>0 and w['queue_strikes']==0 for w in read(QA/'rules/workers.json')['factions']))
    play=evidence(QA/'native-play/report.json','ordinary paid mobile battle')
    require('paid battle settled with visible gameplay',play['winner']!=-2 and play['frames']==300 and all(play['events'][k]>0 for k in ['attack','hit','gold','mine_strike','cast']))
    require('paid replay artifact',(QA/'native-play/mobile-play.mp4').stat().st_size>10000)

    assets=read(ROOT/'game/data/assets.json')['assets']
    for res in sorted(set(x for x in strings(assets) if x.startswith('res://'))):require('asset binding '+res,(ROOT/'game'/res[6:]).is_file())
    for row in read(ROOT/'game/data/theatre-art-provenance.json')['records']:
        require('original art source '+row['id'],sha(ROOT/row['source'])==row['sha256'])
        for field,key in [('path','output_sha256'),('portrait','portrait_sha256')]:
            if row.get(key):require('original derived art '+row['id']+' '+field,sha(ROOT/'game'/assets[row['id']][field][6:])==row[key])
    for row in read(ROOT/'game/data/rc2-art-provenance.json')['records']:
        require('rc2 art source '+row['id'],sha(ROOT/row['source'])==row['source_sha256'])
        for derived in row['derived']:require('rc2 art derivative '+derived['path'],sha(ROOT/derived['path'])==derived['sha256'])
    required={ch for path in [*sorted((ROOT/'game/scripts').glob('*.gd')),*sorted((ROOT/'game/data').glob('*.json'))] for ch in path.read_text(encoding='utf-8') if 0x3400<=ord(ch)<=0x9fff}
    font_report=read(QA/'font-coverage.json');require('bundled fonts covered',font_report['passed'] and len(font_report['records'])==2)
    require('font provenance matches coverage',font_report==read(ROOT/'game/data/mobile-font-provenance.json') and font_report['required_cjk']==len(required))
    for row in font_report['records']:
        require('licensed full font '+row['id'],sha(ROOT/row['source'])==row['source_sha256'] and (ROOT/row['license']).is_file())
        require('current font subset '+row['id'],sha(ROOT/row['path'])==row['sha256'])
        cmap=TTFont(ROOT/row['path']).getBestCmap();require('font has all current CJK '+row['id'],all(ord(ch) in cmap for ch in required))
    baseline=read(ROOT/'output/qa/godot/rc2/validation-index.json')['inputs']
    for res in ['res://scripts/battle_sim.gd','res://data/maps.json','res://data/campaign.json','res://data/assets.json','res://data/balance-prototype.json']:current(res,baseline[res],'rc2 rule/asset baseline preserved')
    require('current game version','config/version="3.0.0-rc3"' in (ROOT/'game/project.godot').read_text(encoding='utf-8'))
    require('sensor landscape configured','window/handheld/orientation=4' in (ROOT/'game/project.godot').read_text(encoding='utf-8'))
    require('APK version code configured','version/code=30002' in (ROOT/'game/export_presets.cfg').read_text(encoding='utf-8'))
    manifest=read(REL/'build-manifest.json')
    require('public export inputs recorded',bool(manifest.get('source_inputs')))
    for path,digest in manifest.get('source_inputs',{}).items():require('export current '+path,sha(ROOT/path)==digest)
    for row in manifest['builds']:require('binary digest '+row['path'],sha(ROOT/row['path'])==row['sha256'] and (ROOT/row['path']).stat().st_size==row['bytes'])
    smoke=read(QA/'export/report.json')
    require('actual final EXE smoke',smoke['passed'] and len(smoke['cases'])==6 and smoke['executable_sha256']==manifest['builds'][0]['sha256'])
    for row in smoke['cases']:
        require('EXE smoke '+row['name'],row['exit_code']==0 and sha(ROOT/row['image'])==row['image_sha256']);picture(ROOT/row['image'],'EXE PNG '+row['name'])
    signature=(QA/'build/apk-signature.log').read_text(encoding='utf-8')
    old_signature=(ROOT/'output/qa/godot/rc2/build/apk-signature.log').read_text(encoding='utf-8')
    certificates=re.findall(r'certificate SHA-256 digest: (\w+)',signature)
    require('same Android signer',bool(certificates) and certificates==re.findall(r'certificate SHA-256 digest: (\w+)',old_signature))
    require('APK v2/v3 signatures',all(f'(APK Signature Scheme {v}): true' in signature for v in ['v2','v3']))
    badging=(QA/'build/apk-badging.log').read_text(encoding='utf-8')
    require('APK identity/version',"name='org.paperwarfront.game' versionCode='30002' versionName='3.0.0-rc3'" in badging)
    require('offline dual ARM APK','android.permission.INTERNET' not in badging and 'arm64-v8a' in badging and 'armeabi-v7a' in badging)
    # Godot 4.7.2 exports SCREEN_SENSOR_LANDSCAPE as Android userLandscape=11.
    require('APK user landscape',bool(re.search(r'android:screenOrientation[^\n]*0xb', (QA/'build/apk-manifest.log').read_text(encoding='utf-8'))))
    require('ARM64 16KB ELF alignment',all(row['arm64_16kb_pass'] for row in read(QA/'build/apk-elf-report.json')))
    with zipfile.ZipFile(ROOT/manifest['builds'][1]['path']) as z:
        require('APK CRC',z.testzip() is None)
        require('APK excludes secrets',not any(n.endswith(('.keystore','.jks','signing.json','export_credentials.cfg')) or '.keys/' in n for n in z.namelist()))

    docs=[ROOT/'README.md',ROOT/'docs/README.md',ROOT/'game/README.md',ROOT/'release/README.md',REL/'README.md',ROOT/'assets/paper-warfront/README.md',ROOT/'docs/paper-warfront/README.md',*list((ROOT/'docs/paper-warfront/mobile-rc3').glob('*.md'))]
    links=0
    for path in docs:
        for target in re.findall(r'!?\[[^\]]*\]\(([^)]+)\)',path.read_text(encoding='utf-8')):
            target=target.strip().strip('<>')
            if re.match(r'^[A-Za-z]+://',target) or target.startswith(('#','mailto:')):continue
            resolved=(path.parent/unquote(target.partition('#')[0])).resolve();links+=1
            if resolved==QA/'release-audit.json':continue
            if not args.archives and (resolved.name=='SHA256SUMS.txt' or resolved.suffix=='.zip' and resolved.parent==REL):continue
            require('document link '+path.name+' -> '+target,resolved.exists())
    gallery=ROOT/'assets/paper-warfront/mobile-rc3-review.html'
    for target in set(re.findall(r'(?:src|href)="([^"]+)"',gallery.read_text(encoding='utf-8'))):
        if re.match(r'^[A-Za-z]+://',target) or target.startswith('#'):continue
        require('offline review resource '+target,(gallery.parent/unquote(target)).resolve().is_file())
    if args.archives:
        require('two archives',len(manifest.get('archives',[]))==2)
        for row in manifest['archives']:
            path=ROOT/row['path'];require('archive digest '+path.name,sha(path)==row['sha256'])
            with zipfile.ZipFile(path) as z:
                require('archive CRC '+path.name,z.testzip() is None)
                require('archive excludes secrets/cache/frames',not any(any(p in ['.keys','.tools','.godot','__pycache__','frames'] for p in n.split('/')) or n.endswith(('.keystore','.jks','export_credentials.cfg')) for n in z.namelist()))
                if 'Source' in path.name:
                    paths=[*manifest['source_inputs'],*['docs/paper-warfront/mobile-rc3/'+p.name for p in (ROOT/'docs/paper-warfront/mobile-rc3').glob('*.md')],'game/tests/mobile_ui_qa.gd','assets/paper-warfront/mobile-rc3-review.html','output/qa/godot/mobile-rc3/mobile-matrix.json','output/qa/godot/mobile-rc3/verification-index.json']
                    for public in paths:require('archived current '+public,hashlib.sha256(z.read('PaperWarfront-Source/'+public)).hexdigest()==sha(ROOT/public))
                else:require('archived final EXE',hashlib.sha256(z.read('PaperWarfront/PaperWarfront.exe')).hexdigest()==manifest['builds'][0]['sha256'])
        for line in (REL/'SHA256SUMS.txt').read_text(encoding='utf-8').splitlines():
            digest,name=line.split('  ',1);require('published checksum '+name,sha(REL/name)==digest)
    total=mobile_count+len(desktop['checks'])+rule_count
    audit={'version':'3.0.0-rc3','passed':not errors,'artifact_checks':len(checks),'gameplay_ui_checks':total,'document_links':links,'archives_checked':args.archives,'errors':errors,'reports':reports,'inputs':inputs,'scope':'Native Windows Godot GPU and ScreenTouch/ScreenDrag with injected mobile density/safe-area metrics; current shared rules, ordinary paid AI replay, actual Windows exports and signed APK package checks. No Android device, human play or realtime device-performance certification.'}
    write(QA/('release-audit.json' if args.archives else 'pre-package-audit.json'),audit)
    print(json.dumps({k:v for k,v in audit.items() if k not in ['reports','inputs']},ensure_ascii=False))
    if errors:raise SystemExit(1)

if __name__=='__main__':main()
