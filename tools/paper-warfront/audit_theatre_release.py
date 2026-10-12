"""Verify current release evidence and write factual acceptance scope, not HD parity."""
from pathlib import Path
from collections import Counter
from urllib.parse import unquote
import argparse, json, hashlib, re, zipfile, sys
from PIL import Image

ROOT=Path(__file__).resolve().parents[2]
QA=ROOT/'output/qa/godot'
REL=ROOT/'release/3.0.0-rc1'
DOC=ROOT/'docs/paper-warfront/redesign-3.0'
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def write(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def strings(d):
    if isinstance(d,str):yield d
    elif isinstance(d,dict):
        for v in d.values():yield from strings(v)
    elif isinstance(d,list):
        for v in d:yield from strings(v)
def main():
    sys.stdout.reconfigure(encoding='utf-8');p=argparse.ArgumentParser();p.add_argument('--archives',action='store_true');args=p.parse_args()
    checks=[];errors=[]
    def require(name,ok):
        checks.append({'name':name,'passed':bool(ok)})
        if not ok:errors.append(name)
    asset=read(ROOT/'game/data/assets.json')['assets'];pr=read(ROOT/'game/data/theatre-art-provenance.json')['records']
    for path in sorted(set(s for s in strings(asset) if s.startswith('res://'))):require('runtime resource '+path,(ROOT/'game'/path[6:]).is_file())
    for r in pr:
        source=ROOT/r['source'];require('source digest '+r['id'],source.is_file() and sha(source)==r['sha256'])
        if r.get('output_sha256'):require('derived digest '+r['id'],sha(ROOT/'game'/asset[r['id']]['path'][6:])==r['output_sha256'])
        if r.get('portrait_sha256'):require('portrait digest '+r['id'],sha(ROOT/'game'/asset[r['id']]['portrait'][6:])==r['portrait_sha256'])
        if r.get('master_sha256'):
            master=ROOT/r['master_path'] if r.get('master_path') else ROOT/'game'/asset[r['master_id']]['path'][6:]
            require('role master '+r['id'],sha(master)==r['master_sha256'])
    require('clipped original props not published',not any(r['source']=='output/imagegen/paper-warfront/theatre-v3/props-yin.png' for r in pr))
    source_rows=[{'path':s,'sha256':sha(ROOT/s),'review':'visually reviewed source/contact boards; original clipped props-yin replaced by repair'} for s in sorted(set(r['source'] for r in pr))]
    sourcescope={'version':'3.0.0-rc1','accepted_sources':source_rows,'rejected_sources':[{'path':'output/imagegen/paper-warfront/theatre-v3/props-yin.png','reason':'one subject touched cell edge; replaced by repairs/props-yin.png'}],'reviewed_contact_boards':['review-army-0.jpg','review-army-1.jpg','review-army-2.jpg','review-props-0.jpg','review-props-1.jpg','review-props-2.jpg','review-background-0.jpg','review-background-1.jpg','review-background-2.jpg']+['role-variants-'+f+'.jpg' for f in ['yin','mo','deng','ji','yuan','qi','mu','shuang','jin','bai']],'derived_records':len(pr),'native_visual_scope':['ten faction core armies and regional backgrounds in controlled GPU fixtures','six baseline maps, home and decision viewport','seven articulated pose phases with representative extra roles','W01 and W04 full legal budget native replay, with silent captured excerpts','new Windows export menu, battle and compatibility menu'],'limitations':['400 unit recruitment/damage tests are headless, not 400 independent native visual approvals','360 units reuse forty role master silhouettes with faction recoloring; some donor accents and colored skin remain','weapon limbs do not have separate per-unit shoulder/elbow rigs','human tactical/visual acceptance and Android hardware remain unverified']}
    for board in sourcescope['reviewed_contact_boards']:require('review board '+board,(ROOT/'output/imagegen/paper-warfront/theatre-v3'/board).is_file())
    write(ROOT/'assets/paper-warfront/visual-review-v3.json',sourcescope)
    reports=[('Foundation','v3-world-foundation.json'),('400 paid recruits and damage','v3-world-combat.json'),('Transport: 200 maps / 602 infinite mines','v3-map-transport-all.json'),('Map decisions and objective boundaries','v3-map-decisions.json'),('Outer mine: capacity and paid worker investment','v3-theatre-economy.json'),('Simulation rules','v3-simulation-final.json'),('Six challenge settlements','v3-challenges-final.json'),('Desktop native pointers and fixtures','v3-ui-final-desktop/report.json'),('Landscape mobile-layout pointers and fixtures','v3-ui-final-mobile/report.json')]
    rows=[]
    for label,file in reports:
        path=QA/file;r=read(path)
        require(label+' no failures',not r.get('failures') and r.get('passed',True))
        for res,digest in r.get('inputs',{}).items():require(label+' current input '+res,sha(ROOT/'game'/res[6:])==digest)
        n=len(r.get('checks',[])) if isinstance(r.get('checks'),list) else r.get('checks',r.get('passed',0))
        rows.append({'name':label,'path':path.relative_to(ROOT).as_posix(),'sha256':sha(path),'checks':n,'passed':True,'scope':r.get('scope',r.get('not_covered',[]))})
    campaign=read(QA/'v3-campaign-play.json');require('200 authored campaign simulations',len(campaign['results'])==200)
    maps=read(ROOT/'game/data/maps.json')['maps'];geometry=[]
    for m in maps:
        digest=hashlib.sha256(json.dumps({k:m[k] for k in ['length','nodes','edges','mines','build_sites']},sort_keys=True).encode()).hexdigest()
        geometry.append(digest);require('recomputed geometry '+m['id'],digest==m['geometry_sha256'])
    require('200 scenarios with193 geometries',len(maps)==200 and len(set(geometry))==193)
    for c in read(ROOT/'game/data/campaign.json')['levels']:require('small production roster '+c['id'],3<=len(c['default_roster'])+1<=5)
    for res,digest in campaign['inputs'].items():require('campaign current '+res,sha(ROOT/'game'/res[6:])==digest)
    for path in ['v3-campaign-counter-077.json','v3-campaign-counter-137.json']:
        r=read(QA/path);require('alternative counter resolves '+path,not r['unresolved'])
        for res,digest in r['inputs'].items():require('counter current '+res,sha(ROOT/'game'/res[6:])==digest)
    for folder in ['v3-native-play','v3-native-contact']:
        r=read(QA/folder/'report.json');require('full native replay '+folder,r['winner']==0 and r['frames']==300 and not r['capture_errors'])
        require('encoded excerpt '+folder,(QA/folder/'battle-replay.mp4').stat().st_size>100000)
        for res,digest in r['inputs'].items():require(folder+' current '+res,sha(ROOT/'game'/res[6:])==digest)
    overview=Image.open(DOC/'figures/actual-six-maps.png');require('actual six map diagram size',overview.size==(1800,1500))
    for name in ['menu.png','battle.png','menu-compatibility.png']:
        path=QA/'v3/export'/name;im=Image.open(path);require('export capture '+name,im.size==(1280,720) and path.stat().st_size>100000)
    b=read(QA/'v3/browser/interaction-report.json');require('browser faction lists',len(b['factions'])==10 and all(r['entries']==40 for r in b['factions']))
    require('browser gallery details image',(QA/'v3/browser/gallery-dialog.png').stat().st_size>10000)
    require('APK offline and version',"versionCode='30000' versionName='3.0.0-rc1'" in (QA/'v3/build/apk-badging.log').read_text(encoding='utf-8') and 'android.permission.INTERNET' not in (QA/'v3/build/apk-badging.log').read_text(encoding='utf-8'))
    require('arm64 16KB ELF',all(r['arm64_16kb_pass'] for r in read(QA/'v3/build/apk-elf-report.json')))
    manifest=read(REL/'build-manifest.json')
    for row in manifest['builds']+(manifest.get('archives',[]) if args.archives else []):
        path=ROOT/row['path'];require('artifact hash '+row['path'],path.stat().st_size==row['bytes'] and sha(path)==row['sha256'])
    state={'version':'3.0.0-rc1','scope':'Current input SHA checks, runtime file links, generated source/derivative provenance, rule and native fixtures, full legal-budget replays, new EXE captures, Android package checks and optional archive integrity. No human HD parity or Android hardware acceptance.','reports':rows,'campaign':{'results':len(campaign['results']),'victories':campaign['victories'],'defeats':sum(r['winner']==1 for r in campaign['results']),'draws':sum(r['winner']==-1 for r in campaign['results']),'unresolved_default_540s':[r['map'] for r in campaign['unresolved']],'alternative_counter':'both unresolved maps settled as defeats at582.6s/242.0s; not a victory coverage claim'},'sources':{'new_sources':len(source_rows),'new_provenance_records':len(pr),'bespoke_core':40,'role_masters':40,'recolored_variants':360,'summoned_aliases':2}}
    write(QA/'v3/validation-index.json',state)
    lines=['# 实现与验证边界 · 3.0.0-rc1','', '六张基准地图与194关空间简报已接入，所有正式资源按当前源散列可追踪。此版可用于直接试演与继续评审，尚未宣称达到HD完整品质。','', '| 检查 | 当前结果 | 证据 |','| --- | --- | --- |']
    for row in rows:lines.append(f'| {row["name"]} | {row["checks"]}项／无失败 | [报告](../../../{row["path"]}) |')
    lines+=['','[外矿双侧回款](../../../output/qa/godot/v3-theatre-economy.json)验证180秒2／3／4／6工人256／344／408／536金。地图运输包含全部602无限矿的300秒持续往返，有限矿不属于这份持续无限运输检查。','', '200关默认AI互战：136胜、61负、1平、2局540秒未结算（map.04.17、map.07.17）。两局改用counter后分别582.6秒、242.0秒败北，证明策略改变可推进局势；不能据此声称全部默认编组人类可胜。六附加挑战只有三关自动获胜，另三关败北；通过指正常结算。','', '[完整200关结果](../../../output/qa/godot/v3-campaign-play.json) · [长坡077补查](../../../output/qa/godot/v3-campaign-counter-077.json) · [长坡137补查](../../../output/qa/godot/v3-campaign-counter-137.json)','', '[W04原生完整对战记录](../../../output/qa/godot/v3-native-play/report.json)用正式230／260预算、付费阵地与招募，95.717秒获胜，122攻击、261命中事件。 [W01原生完整对战](../../../output/qa/godot/v3-native-contact/report.json)用190／160预算，84.967秒获胜，108攻击、142命中、修复及打断事件。双方为战术AI，不是人工操作录像。','', '[纸桥片段](../../../output/qa/godot/v3-native-play/battle-replay.mp4) · [归金坡交战片段](../../../output/qa/godot/v3-native-contact/battle-replay.mp4)。静音20秒，15fps离线取帧，14–24秒与40–50秒间有剪切；不作实际性能证据。','', '[素材目视及代表覆盖](../../../assets/paper-warfront/visual-review-v3.json)：34个采用的新源、473来源加工记录、40专属核心、40角色母版、360调色变体、2召唤别名。原props-yin裁边源已拒用。原生十院核心和区域背景、六图、七姿态已目视；非核心变体主要以十院联系板审查，并非400张独立原生逐兵验收。','', '[新EXE菜单](../../../output/qa/godot/v3/export/menu.png) · [新EXE战斗](../../../output/qa/godot/v3/export/battle.png) · [OpenGL兼容菜单](../../../output/qa/godot/v3/export/menu-compatibility.png)。APK离线、版本、签名、ARM架构、ZIP与ELF16KB对齐已检查，尚无真机。','', '原作证据与事实边界：本机没有运行原作；PC路标权限、精确坡速、矿服务容量及跨路射程仍待原作实测。桥、容量和数值明确属于本作设计。全200关人工平衡、六图两种人工打法、骚扰收入对比、Android触摸／声音／热量／帧率未完成。','', '[机器证据总索引](../../../output/qa/godot/v3/validation-index.json) · [下载与安装](../../../release/3.0.0-rc1/README.md)']
    (DOC/'03-实现与验证边界.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    release=f'''# 纸上兵戈 · 3.0.0-rc1 地图重做评审版

[Windows ZIP](PaperWarfront-Windows-3.0.0-rc1.zip) · [Windows EXE](windows/PaperWarfront.exe) · [Android APK](android/PaperWarfront-3.0.0-rc1.apk) · [完整源码](PaperWarfront-Source-3.0.0-rc1.zip) · [SHA256](SHA256SUMS.txt)

先试主菜单“地图试演 · 六张基准”，直接选择归金坡、前哨外矿、灯台长坡、纸桥岔口、矿线阻击或守签接力。试演不改战役进度。每局2–4个战斗兵种加工人，合计3–5项生产。

Windows ZIP解压后运行PaperWarfront.exe，资源内嵌，无需Godot；旧显卡可用Launch-Compatibility.cmd。本机Win11／RTX3060检视新包菜单、桥战场与OpenGL路径。Android APK签名安装，离线横屏，arm64-v8a／armeabi-v7a、versionCode30000、org.paperwarfront.game；尚未连接真机。EXE约{manifest['builds'][0]['bytes']/1048576:.1f}MiB，APK约{manifest['builds'][1]['bytes']/1048576:.1f}MiB。

[玩家手册](../../docs/paper-warfront/16-玩家手册.md) · [六图地图规格](../../docs/paper-warfront/redesign-3.0/01-六张基准地图.md) · [验证范围](../../docs/paper-warfront/redesign-3.0/03-实现与验证边界.md) · [素材浏览](../../assets/paper-warfront/theatre-v3-gallery.html)

当前200场景／193几何、十院400全局兵种。200关默认AI互战136胜／61负／1平／2局540秒未结束；两长局counter补查正常败北。尚未完成全关人工平衡、原作HD实机对照和Android真机。本包是可运行评审候选，不能把自动检查当作体验认可。

源包含游戏、文档、生成素材及验证证据，不含.keys签名凭据、网关配置、引擎与缓存。Godot及第三方许可随Windows目录；中文字体采用OFL子集，制作工具保留源字体与许可。旧2.0发布和二次研究历史保留。
'''
    (REL/'README.md').write_text(release,encoding='utf-8')
    # Current docs only: old research/rejected input evidence stays immutable.
    documents=[ROOT/'README.md',ROOT/'docs/README.md',ROOT/'game/README.md',ROOT/'release/README.md',REL/'README.md',ROOT/'assets/paper-warfront/README.md']+list(DOC.glob('*.md'))+list(DOC.glob('redesign-3.0/*.md'))+list(DOC.glob('world/*.md'))+list(DOC.glob('world/maps/*.md'))+list(DOC.glob('world/units/*.md'))
    link_count=0
    for path in documents:
        for match in re.finditer(r'!?\[[^\]]*\]\(([^)]+)\)',path.read_text(encoding='utf-8')):
            target=match.group(1).strip().strip('<>')
            if re.match(r'^[A-Za-z]+://',target) or target.startswith(('#','mailto:')):continue
            target=unquote(target.partition('#')[0])
            if not target:continue
            if not args.archives and ('PaperWarfront-' in target and target.endswith('.zip') or target.endswith('SHA256SUMS.txt')):continue
            link_count+=1;require('document link '+str(path.relative_to(ROOT))+' -> '+target,(path.parent/target).resolve().exists())
    if args.archives:
        for file in REL.glob('*.zip'):
            with zipfile.ZipFile(file) as z:
                require('ZIP CRC '+file.name,z.testzip() is None)
                require('credentials/cache excluded '+file.name,not any(any(part in ['.keys','.tools','.godot','__pycache__'] for part in n.split('/')) or n.endswith(('.keystore','.jks','export_credentials.cfg')) for n in z.namelist()))
                if 'Source' in file.name:
                    for required in ['game/project.godot','game/scripts/battle_sim.gd','game/data/maps.json','docs/paper-warfront/redesign-3.0/README.md','assets/paper-warfront/theatre-v3-gallery.html','output/qa/godot/v3/validation-index.json']:
                        require('source archive '+required,'PaperWarfront-Source/'+required in z.namelist())
    report={'passed':not errors,'checks':len(checks),'document_links':link_count,'archives_checked':args.archives,'errors':errors,'scope':state['scope']}
    write(QA/('v3/release-audit.json' if args.archives else 'v3/pre-package-audit.json'),report)
    print(json.dumps(report,ensure_ascii=False))
    if errors:raise SystemExit(1)

if __name__=='__main__':main()
