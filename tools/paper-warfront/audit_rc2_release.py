"""Audit RC2 inputs, native evidence, asset provenance and shipped archives."""
from pathlib import Path
from collections import Counter
from urllib.parse import unquote
import argparse,hashlib,json,re,sys,zipfile
from PIL import Image

ROOT=Path(__file__).resolve().parents[2]
QA=ROOT/'output/qa/godot/rc2'
REL=ROOT/'release/3.0.0-rc2'

def read(path):return json.loads(path.read_text(encoding='utf-8'))
def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1048576),b''):h.update(block)
    return h.hexdigest()
def strings(value):
    if isinstance(value,str):yield value
    elif isinstance(value,dict):
        for v in value.values():yield from strings(v)
    elif isinstance(value,list):
        for v in value:yield from strings(v)
def write(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def main():
    sys.stdout.reconfigure(encoding='utf-8');parser=argparse.ArgumentParser();parser.add_argument('--archives',action='store_true');args=parser.parse_args()
    checks=[];errors=[];inputs={}
    def require(name,ok):
        checks.append({'name':name,'passed':bool(ok)})
        if not ok:errors.append(name)
    def current(res,digest,label):
        p=ROOT/'game'/res.removeprefix('res://')
        require(label+' input '+res,p.exists() and sha(p)==digest)
        if res in inputs:require('consistent input '+res,inputs[res]==digest)
        inputs[res]=digest
    asset=read(ROOT/'game/data/assets.json')['assets']
    for res in sorted(set(x for x in strings(asset) if x.startswith('res://'))):require('resource '+res,(ROOT/'game'/res[6:]).is_file())
    previous=read(ROOT/'game/data/theatre-art-provenance.json')['records']
    for row in previous:
        source=ROOT/row['source'];require('original source '+row['id'],source.exists() and sha(source)==row['sha256'])
        for field,key in [('path','output_sha256'),('portrait','portrait_sha256')]:
            if row.get(key):require('original derived '+row['id']+' '+field,sha(ROOT/'game'/asset[row['id']][field][6:])==row[key])
        if row.get('master_sha256'):
            master=ROOT/row['master_path'] if row.get('master_path') else ROOT/'game'/asset[row['master_id']]['path'][6:]
            require('original master '+row['id'],sha(master)==row['master_sha256'])
    new=read(ROOT/'game/data/rc2-art-provenance.json')['records']
    require('15 RC2 provenance records',len(new)==15)
    for row in new:
        require('RC2 source '+row['id'],sha(ROOT/row['source'])==row['source_sha256'])
        for derived in row['derived']:require('RC2 derived '+derived['path'],sha(ROOT/derived['path'])==derived['sha256'])
    names=['ownership-after.json','worker-actions.json','foundation.json','combat.json','transport.json','simulation.json','economy.json','decisions.json','ui-desktop/report.json','ui-mobile/report.json']
    rows=[];total=0
    for name in names:
        p=QA/name;r=read(p)
        require('no failures '+name,not r.get('failures') and not r.get('failed') and r.get('passed',True) is not False)
        for res,digest in r.get('inputs',{}).items():current(res,digest,name)
        for key,res in [('simulation_sha256','res://scripts/battle_sim.gd'),('assets_sha256','res://data/assets.json')]:
            if key in r:current(res,r[key],name)
        test='test_combat_ownership.gd' if name.startswith('ownership') else 'test_worker_actions.gd'
        if r.get('test_sha256'):current('res://tests/'+test,r['test_sha256'],name)
        c=r.get('checks',r.get('passed'));n=len(c) if isinstance(c,list) else c;total+=n
        rows.append({'path':p.relative_to(ROOT).as_posix(),'sha256':sha(p),'checks':n,'passed':True})
    require('8720 rule and UI checks',total==8720)
    ownership=read(QA/'ownership-after.json')['evidence']['paid_passage']
    require('paid passage truly overlaps and never friendly-hits',ownership['overlap_ticks']>0 and not ownership['friendly_hits'])
    workers=read(QA/'worker-actions.json')['factions']
    require('ten worker factions and real gold',len(workers)==10 and all(w['gold_deposited']>0 and w['queue_strikes']==0 and w['body_on_road'] for w in workers))
    native=read(QA/'native-final/report.json')
    for key,res in [('simulation_sha256','res://scripts/battle_sim.gd'),('view_sha256','res://scripts/battle_view.gd'),('ground_sha256','res://scripts/theatre_ground.gd')]:current(res,native[key],'native mining')
    captures=[r for r in native['workers'] if 'faction' in r]
    require('ten native work pose sets',len(captures)==10 and all(set(r['captured'])=={'mine-30','mine-56','mine-79','unload'} for r in captures))
    for r in captures:
        for pose in r['captured']:
            picture=QA/'native-final'/(r['faction']+'-'+pose+'.png');Image.open(picture).verify();require('native pose '+picture.name,True)
    battle=read(QA/'native-play/report.json')
    for res,digest in battle['inputs'].items():current(res,digest,'normal paid native battle')
    require('normal paid native battle settles',battle['winner'] in [-1,0,1] and not battle['capture_errors'] and battle['frames']==300 and battle['events']['hit']>0)
    campaign=read(QA/'campaign-play.json');extended=read(QA/'campaign-137-extended.json')
    for r in [campaign,extended]:
        for res,digest in r['inputs'].items():current(res,digest,'campaign')
    require('200 default campaign runs',len(campaign['results'])==200)
    unresolved={r['index'] for r in campaign['unresolved']};follow={r['index'] for r in extended['results'] if r['winner']!=-2}
    require('same default AI extended follow-up settles outstanding run',extended['player_style_override']=='none' and unresolved<=follow)
    summary=dict(Counter(str(r['winner']) for r in campaign['results']))
    require('RC2 project version','config/version="3.0.0-rc2"' in (ROOT/'game/project.godot').read_text(encoding='utf-8'))
    require('Android version code','version/code=30001' in (ROOT/'game/export_presets.cfg').read_text(encoding='utf-8'))
    manifest=read(REL/'build-manifest.json')
    for r in manifest['builds']:require('built executable digest '+r['path'],sha(ROOT/r['path'])==r['sha256'] and (ROOT/r['path']).stat().st_size==r['bytes'])
    smoke=read(QA/'export/report.json')
    require('actual Windows executable matches smoke',smoke['passed'] and smoke['executable_sha256']==manifest['builds'][0]['sha256'] and len(smoke['cases'])==3)
    for case in smoke['cases']:
        require('EXE capture '+case['name'],case['exit_code']==0 and sha(ROOT/case['image'])==case['image_sha256']);Image.open(ROOT/case['image']).verify()
    signature=(QA/'build/apk-signature.log').read_text(encoding='utf-8');badging=(QA/'build/apk-badging.log').read_text(encoding='utf-8')
    require('APK v2/v3 signature','(APK Signature Scheme v2): true' in signature and '(APK Signature Scheme v3): true' in signature)
    require('APK package and version',"name='org.paperwarfront.game' versionCode='30001' versionName='3.0.0-rc2'" in badging)
    require('APK offline','android.permission.INTERNET' not in badging)
    require('APK ARM architectures','arm64-v8a' in badging and 'armeabi-v7a' in badging)
    elf=read(QA/'build/apk-elf-report.json');require('ARM64 ELF 16KB',bool(elf) and all(r['arm64_16kb_pass'] for r in elf))
    with zipfile.ZipFile(ROOT/manifest['builds'][1]['path']) as z:
        require('APK CRC',z.testzip() is None)
        require('APK excludes credentials',not any('.keys' in n or n.endswith(('.keystore','.jks','signing.json','export_credentials.cfg')) for n in z.namelist()))
    state={'version':'3.0.0-rc2','scope':'Current damage/worker/UI rules, native representative visuals, same-rules AI campaign and actual Windows exports. Android APK package checks only; no phone or human balance certification.','checks':total,'reports':rows,'inputs':inputs,'native_renderer':native['native_renderer'],'campaign_540s':summary,'extended_followup':[{'index':r['index'],'time':r['time'],'winner':r['winner']} for r in extended['results']],'assets':{'baseline_records':len(previous),'rc2_records':len(new),'new_generated_masters':2,'worker_rigs':10,'terrain_materials':5},'builds':manifest['builds']}
    write(QA/'validation-index.json',state)
    docs=[ROOT/'README.md',ROOT/'docs/README.md',ROOT/'game/README.md',ROOT/'release/README.md',REL/'README.md',ROOT/'assets/paper-warfront/README.md',*list((ROOT/'docs/paper-warfront').glob('*.md')),*list((ROOT/'docs/paper-warfront/fixes-rc2').glob('*.md'))]
    links=0
    for p in docs:
        for target in re.findall(r'!?\[[^\]]*\]\(([^)]+)\)',p.read_text(encoding='utf-8')):
            target=target.strip().strip('<>')
            if re.match(r'^[A-Za-z]+://',target) or target.startswith(('#','mailto:')):continue
            target=unquote(target.partition('#')[0]);links+=1
            # This file is published after this audit completes; avoid a self-link
            # requiring an earlier (and therefore stale) final audit to exist.
            if (p.parent/target).resolve()==QA/'release-audit.json':continue
            if not args.archives and (target.endswith('SHA256SUMS.txt') or 'PaperWarfront-' in target and target.endswith('.zip')):continue
            require('document link '+p.relative_to(ROOT).as_posix()+' -> '+target,(p.parent/target).resolve().exists())
    gallery=ROOT/'assets/paper-warfront/rc2-review.html'
    for target in set(re.findall(r'(?:src|href)="([^"]+)"',gallery.read_text(encoding='utf-8'))):
        if re.match(r'^[A-Za-z]+://',target):continue
        require('offline gallery resource '+target,(gallery.parent/target).resolve().is_file())
    if args.archives:
        require('two archive manifests',len(manifest.get('archives',[]))==2)
        for row in manifest.get('archives',[]):
            p=ROOT/row['path'];require('archive digest '+p.name,sha(p)==row['sha256'])
            with zipfile.ZipFile(p) as z:
                require('archive CRC '+p.name,z.testzip() is None)
                require('archive excludes credentials and caches '+p.name,not any(any(part in ['.keys','.tools','.godot','__pycache__','frames'] for part in n.split('/')) or n.endswith(('.keystore','.jks','export_credentials.cfg')) for n in z.namelist()))
                if 'Source' in p.name:
                    for path in ['game/project.godot','game/scripts/ui_theme.gd','game/data/rc2-art-provenance.json','docs/paper-warfront/fixes-rc2/README.md','assets/paper-warfront/rc2-review.html','output/qa/godot/rc2/validation-index.json']:
                        require('source entry '+path,'PaperWarfront-Source/'+path in z.namelist())
                    for path in ['game/scripts/battle_sim.gd','game/scripts/battle_view.gd','game/scripts/ui_theme.gd','game/data/assets.json','game/data/rc2-art-provenance.json','assets/paper-warfront/rc2-review.html','output/qa/godot/rc2/before-after.jpg',*['docs/paper-warfront/fixes-rc2/'+name for name in ['01-修复与视觉设计约束.md','02-判定与采矿复查.md','03-素材与地图制作约束.md','04-原生UI规范与状态验收.md','05-验证与交付报告.md']]]:
                        require('archived current code '+path,hashlib.sha256(z.read('PaperWarfront-Source/'+path)).hexdigest()==sha(ROOT/path))
    audit={'version':'3.0.0-rc2','passed':not errors,'checks':len(checks),'gameplay_ui_checks':total,'document_links':links,'archives_checked':args.archives,'errors':errors,'scope':state['scope']}
    write(QA/('release-audit.json' if args.archives else 'pre-package-audit.json'),audit)
    print(json.dumps(audit,ensure_ascii=False))
    if errors:raise SystemExit(1)

if __name__=='__main__':main()
