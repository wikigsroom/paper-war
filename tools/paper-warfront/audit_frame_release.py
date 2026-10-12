"""Audit current asymmetric frame gameplay, native evidence and shipped archives."""
from pathlib import Path
from urllib.parse import unquote
import argparse,hashlib,json,re,sys,zipfile
from PIL import Image
from fontTools.ttLib import TTFont
from audit_rc2_release import read,sha,strings,write
ROOT=Path(__file__).resolve().parents[2];QA=ROOT/'output/qa/godot/frame-rebuild';MOBILE=QA/'mobile';REL=ROOT/'release/3.0.0-rc5'
def main():
 sys.stdout.reconfigure(encoding='utf-8');p=argparse.ArgumentParser();p.add_argument('--archives',action='store_true');args=p.parse_args();checks=[];errors=[];inputs={};reports=[];logic_total=0
 def require(label,ok):
  checks.append({'name':label,'passed':bool(ok)})
  if not ok:errors.append(label)
 def current(res,digest,label):
  path=ROOT/'game'/res.removeprefix('res://');require(label+' current '+res,path.is_file() and sha(path)==digest)
  if res in inputs:require('consistent '+res,inputs[res]==digest)
  inputs[res]=digest
 def evidence(path,label):
  nonlocal logic_total
  r=read(path);require(label+' passed',r.get('passed',True) and not r.get('failures') and not r.get('failed') and not r.get('capture_errors'))
  for res,digest in r.get('inputs',{}).items():current(res,digest,label)
  n=r.get('checks',0);n=len(n) if isinstance(n,list) else int(n);logic_total+=n
  reports.append({'path':path.relative_to(ROOT).as_posix(),'sha256':sha(path),'checks':n});return r
 def picture(path,label):
  with Image.open(path) as im:size=im.size;im.verify()
  require(label+' readable PNG',True);return size
 balance=read(ROOT/'game/data/balance-prototype.json')['units'];assets=read(ROOT/'game/data/assets.json')['assets'];briefs=read(ROOT/'assets/paper-warfront/frame-rebuild/unit-briefs.json')['units'];provenance=read(ROOT/'game/data/unit-frames.json');profiles=provenance['profiles']
 require('72 complete distinct actors',len(balance)==len(briefs)==len(profiles)==72 and set(balance)==set(profiles)=={r['id'] for r in briefs})
 require('60 combat / 10 workers / 2 summons',sum(not d.get('economy') and not d.get('summoned') for d in balance.values())==60 and sum(bool(d.get('economy')) for d in balance.values())==10 and sum(bool(d.get('summoned')) for d in balance.values())==2)
 aliases=read(ROOT/'game/data/unit-id-migration.json')['aliases'];require('340 retired stable IDs migrate',len(aliases)==340 and all(old not in balance and new in balance for old,new in aliases.items()))
 require('legacy data retained',len(read(ROOT/'assets/paper-warfront/frame-rebuild/legacy/balance-prototype.json')['units'])==412)
 require('current frame processor',sha(ROOT/provenance['processor'])==provenance['processor_sha256'])
 for path,digest in provenance['processor_inputs'].items():require('processor dependency '+path,sha(ROOT/path)==digest)
 require('authoring provenance copy current',provenance==read(ROOT/'assets/paper-warfront/frame-rebuild/frame-provenance.json'))
 for row in briefs:
  uid=row['id'];rec=profiles[uid]
  require('new identity '+uid,row['identity_version']==2 and balance[uid]['identity_version']==2 and rec['source']==row['source'] and rec['raw']==row['raw'] and '/v2/' in rec['source'])
  require('whole drawing and fixed contract '+uid,rec['frame_count']==36 and rec['frame_size']==[192,192] and rec['anchor']==[96,180] and rec['normalization']['one_scale_for_all_36_frames'] and rec['normalization']['fixed_anchor'])
  require('model '+uid,rec['model']=='gpt-image-2.5')
  for path,digest in rec['generation_reference_inputs'].items():require('generation reference '+uid+' '+path,sha(ROOT/path)==digest)
  for field,key in [('source','source_sha256'),('prompt','prompt_sha256'),('raw','raw_sha256'),('atlas','atlas_sha256'),('idle','idle_sha256'),('portrait','portrait_sha256'),('preview','preview_sha256')]:
   path=ROOT/'game'/rec[field][6:] if rec[field].startswith('res://') else ROOT/rec[field];require('frame input '+uid+' '+field,path.is_file() and sha(path)==rec[key])
  require('bound atlas '+uid,assets[uid]['path']==rec['idle'] and assets[uid]['portrait']==rec['portrait'] and assets[uid]['animation']['atlas']==rec['atlas'])
  require('atlas dimensions '+uid,picture(ROOT/'game'/rec['atlas'][6:],uid)==(1152,1152))
 for res in set(s for s in strings(assets) if s.startswith('res://')):require('asset resource '+res,(ROOT/'game'/res[6:]).is_file())
 code=(ROOT/'game/scripts/battle_view.gd').read_text(encoding='utf-8');require('whole-frame only renderer',all(s not in code for s in ['draw_action_puppet','draw_worker_puppet','UnitMotion.pose','draw_part(']) and 'draw_frame_unit(u,pos,meta,modulation)' in code)
 for name,test in [('factions','test_distinct_factions.gd'),('frames','test_frame_contracts.gd'),('ownership','test_combat_ownership.gd'),('workers','test_worker_actions.gd'),('foundation','test_world_foundation.gd')]:
  r=evidence(QA/(name+'-report.json'),name)
  for field,res in [('simulation_sha256','res://scripts/battle_sim.gd'),('assets_sha256','res://data/assets.json'),('test_sha256','res://tests/'+test)]:
   if r.get(field):current(res,r[field],name)
 workers=read(QA/'workers-report.json');require('ten workers physically mine and deposit',len(workers['factions'])==10 and all(w['gold_deposited']>0 and w['queue_strikes']==0 for w in workers['factions']))
 ownership=read(QA/'ownership-report.json');require('friendly paid passage safe',ownership['evidence']['paid_passage']['overlap_ticks']>0 and not ownership['evidence']['paid_passage']['friendly_hits'])
 gallery=evidence(QA/'native-frames/report.json','native whole-frame gallery');require('all 72 native sheets',gallery['units']==72 and gallery['frames_per_unit']==36)
 for name in gallery['captures']:require('native sheet '+name,picture(QA/'native-frames'/name,name)==(1320,1080))
 visual=read(QA/'visual-review.json');require('all current unit identities visually reviewed',visual['passed'] and set(visual['reviewed_ids'])==set(balance) and visual['gallery_sha256']==sha(QA/'native-frames/report.json') and visual['frame_provenance_sha256']==sha(ROOT/'game/data/unit-frames.json'))
 for row in visual['captures']:require('reviewed visual '+row['path'],sha(ROOT/row['path'])==row['sha256'])
 motion=evidence(QA/'motion/report.json','continuous pose review');require('native 12 actor continuous review',len(motion['units'])==12 and motion['frames']==120 and (QA/'motion/unit-frames.mp4').stat().st_size>10000)
 duels=evidence(QA/'duels/report.json','real attacks');require('14 actual release / flight / damage fixtures',len(duels['duels'])==14 and all(d['passed'] for d in duels['duels']))
 for name in duels['captures']:picture(QA/'duels'/name,'real attack '+name)
 evidence(QA/'audio/report.json','actual equipment sound routing')
 pan=evidence(QA/'pan/report.json','camera and five-row menu');require('200 maps fixed geometry',pan['maps']==200 and pan['max_vertex_residual_px']<.001)
 pixels=read(QA/'pan/pixel-report.json');require('48 native pan frames stable',pixels['passed'] and pixels['pairs']==47)
 paths=sorted((QA/'pan/frames').glob('frame-*.png'));require('current pan screenshots',len(paths)==48 and [sha(path) for path in paths]==pixels['frame_sha256'])
 matrix=read(MOBILE/'mobile-matrix.json');require('all eight mobile layouts',matrix['passed'] and len(matrix['cases'])==8)
 mobile_count=0
 for case in matrix['cases']:
  r=evidence(MOBILE/case['name']/'report.json',case['name']);mobile_count+=len(r['checks']);require('matrix result '+case['name'],case['passed'] and case['exit_code']==0 and case['checks']==len(r['checks']))
  size=tuple(map(int,case['physical_resolution'].split('x')))
  if case['name']=='portrait-recovery':picture(MOBILE/case['name']/'00-portrait-guard.png','portrait recovery');size=(max(size),min(size))
  require('physical metrics '+case['name'],tuple(map(float,re.findall(r'[-\d.]+',r['metrics']['pixels'])))==size and float(r['metrics']['density'])==float(case['density']))
  require('native mobile menu '+case['name'],picture(MOBILE/case['name']/'01-menu.png','mobile menu')==size)
 require('matrix check total',matrix['checks']==mobile_count)
 evidence(MOBILE/'desktop/report.json','desktop pointer UI')
 play=evidence(MOBILE/'native-play/report.json','ordinary paid AI battle');require('ordinary paid battle settled and visible',play['winner']!=-2 and play['frames']==300 and all(play['events'][k]>0 for k in ['attack','hit','gold','mine_strike','cast']))
 require('ordinary paid replay encoded',(MOBILE/'native-play/mobile-play.mp4').stat().st_size>10000)
 required={ch for file in [*sorted((ROOT/'game/scripts').glob('*.gd')),*sorted((ROOT/'game/data').glob('*.json'))] for ch in file.read_text(encoding='utf-8') if 0x3400<=ord(ch)<=0x9fff}
 fonts=read(QA/'font-coverage.json');require('current bundled fonts',fonts==read(ROOT/'game/data/mobile-font-provenance.json') and fonts['passed'] and fonts['required_cjk']==len(required))
 for row in fonts['records']:
  require('font inputs '+row['id'],sha(ROOT/row['source'])==row['source_sha256'] and sha(ROOT/row['path'])==row['sha256'] and (ROOT/row['license']).is_file());cmap=TTFont(ROOT/row['path']).getBestCmap();require('font current CJK '+row['id'],all(ord(ch) in cmap for ch in required))
 project=(ROOT/'game/project.godot').read_text(encoding='utf-8');preset=(ROOT/'game/export_presets.cfg').read_text(encoding='utf-8')
 require('version and landscape','config/version="3.0.0-rc5"' in project and 'window/handheld/orientation=4' in project and 'version/code=30004' in preset)
 manifest=read(REL/'build-manifest.json');require('export inputs recorded',bool(manifest['source_inputs']))
 for path,digest in manifest['source_inputs'].items():require('current export '+path,sha(ROOT/path)==digest)
 for row in manifest['builds']:require('current binary '+row['path'],sha(ROOT/row['path'])==row['sha256'] and (ROOT/row['path']).stat().st_size==row['bytes'])
 smoke=read(MOBILE/'export/report.json');require('actual final EXE six configurations',smoke['passed'] and len(smoke['cases'])==6 and smoke['executable_sha256']==manifest['builds'][0]['sha256'])
 for row in smoke['cases']:require('current EXE screenshot '+row['name'],row['exit_code']==0 and sha(ROOT/row['image'])==row['image_sha256']);picture(ROOT/row['image'],'EXE screenshot')
 signature=(QA/'build/apk-signature.log').read_text(encoding='utf-8');old=(ROOT/'output/qa/godot/rc2/build/apk-signature.log').read_text(encoding='utf-8');certs=re.findall(r'certificate SHA-256 digest: (\w+)',signature)
 require('same Android signer',bool(certs) and certs==re.findall(r'certificate SHA-256 digest: (\w+)',old));require('APK v2/v3 signatures',all(f'(APK Signature Scheme {v}): true' in signature for v in ['v2','v3']))
 badging=(QA/'build/apk-badging.log').read_text(encoding='utf-8');require('APK package and version',"name='org.paperwarfront.game' versionCode='30004' versionName='3.0.0-rc5'" in badging);require('offline ARM64/ARMv7','android.permission.INTERNET' not in badging and 'arm64-v8a' in badging and 'armeabi-v7a' in badging)
 require('APK user landscape',bool(re.search(r'android:screenOrientation[^\n]*0xb',(QA/'build/apk-manifest.log').read_text(encoding='utf-8'))));require('ARM64 16KB ELF',all(row['arm64_16kb_pass'] for row in read(QA/'build/apk-elf-report.json')))
 with zipfile.ZipFile(ROOT/manifest['builds'][1]['path']) as z:
  names=z.namelist();require('APK CRC',z.testzip() is None);require('APK secret exclusion',not any(n.endswith(('.keystore','.jks','signing.json','export_credentials.cfg')) for n in names));require('unused rig textures excluded',not any('/actions-rc4/' in n or '/characters/cutouts/' in n for n in names))
 docs=[ROOT/'README.md',ROOT/'docs/README.md',ROOT/'game/README.md',ROOT/'release/README.md',REL/'README.md',ROOT/'assets/paper-warfront/README.md',ROOT/'docs/paper-warfront/README.md',*sorted((ROOT/'docs/paper-warfront/frame-rebuild').glob('*.md'))];links=0
 for file in docs:
  for target in re.findall(r'!?\[[^\]]*\]\(([^)]+)\)',file.read_text(encoding='utf-8')):
   target=target.strip().strip('<>')
   if re.match(r'^[A-Za-z]+://',target) or target.startswith(('#','mailto:')):continue
   resolved=(file.parent/unquote(target.partition('#')[0])).resolve();links+=1
   if resolved==QA/'release-audit.json':continue
   if not args.archives and (resolved.name=='SHA256SUMS.txt' or resolved.suffix=='.zip' and resolved.parent==REL):continue
   require('document link '+file.name+' '+target,resolved.exists())
 review=ROOT/'assets/paper-warfront/frame-rebuild-review.html'
 for target in set(re.findall(r'(?:src|href)="([^"]+)"',review.read_text(encoding='utf-8'))):require('offline review '+target,(review.parent/unquote(target)).resolve().is_file())
 if args.archives:
  require('two release archives',len(manifest['archives'])==2)
  for row in manifest['archives']:
   path=ROOT/row['path'];require('archive digest '+path.name,sha(path)==row['sha256'])
   with zipfile.ZipFile(path) as z:
    require('archive CRC '+path.name,z.testzip() is None);require('archive secrets/cache excluded',not any(any(part in ['.keys','.tools','.godot','__pycache__','frames','rejected'] for part in name.split('/')) or name.endswith(('.keystore','.jks','export_credentials.cfg')) for name in z.namelist()))
    if 'Source' in path.name:
     paths=[*manifest['source_inputs'],*[str(p.relative_to(ROOT)).replace('\\','/') for p in (ROOT/'docs/paper-warfront/frame-rebuild').glob('*.md')],'assets/paper-warfront/frame-rebuild-review.html','output/qa/godot/frame-rebuild/visual-review.json','output/qa/godot/frame-rebuild/mobile/mobile-matrix.json']
     for public in paths:require('archived current '+public,hashlib.sha256(z.read('PaperWarfront-Source/'+public)).hexdigest()==sha(ROOT/public))
    else:require('archived current EXE',hashlib.sha256(z.read('PaperWarfront/PaperWarfront.exe')).hexdigest()==manifest['builds'][0]['sha256'])
  for line in (REL/'SHA256SUMS.txt').read_text(encoding='utf-8').splitlines():digest,name=line.split('  ',1);require('published checksum '+name,sha(REL/name)==digest)
 audit={'version':'3.0.0-rc5','passed':not errors,'artifact_checks':len(checks),'gameplay_ui_checks':logic_total,'document_links':links,'archives_checked':args.archives,'errors':errors,'reports':reports,'inputs':inputs,'scope':'72 native whole-frame actors / 60 asymmetric combat kits, native Windows Godot GPU and injected mobile metrics, actual paid AI play, real EXE and signed APK structure. No human campaign balance or Android hardware/performance acceptance.'}
 write(QA/('release-audit.json' if args.archives else 'pre-package-audit.json'),audit);print(json.dumps({k:v for k,v in audit.items() if k not in ['reports','inputs']},ensure_ascii=False))
 if errors:raise SystemExit(1)
if __name__=='__main__':main()
