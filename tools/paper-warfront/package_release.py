"""Archive only the deliverable source, assets and evidence; never credentials."""
from pathlib import Path
import zipfile,json,hashlib,shutil,sys,os,subprocess,argparse,re
from runtime_asset_inputs import runtime_asset_inputs

ROOT=Path(__file__).resolve().parents[2];VERSION=os.environ.get('PAPER_RELEASE_VERSION','3.0.0-rc41-night-lantern-components');RELEASE=ROOT/'release'/VERSION

def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1048576),b''):h.update(block)
    return h.hexdigest()
def archive(path,files,prefix=''):
    with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for source,target in files:
            # Raster/media/previous ZIPs are already compressed. Preserve their
            # bytes directly; use fast deflate for large native binaries/audio.
            encoded=source.suffix.lower() in ['.png','.jpg','.jpeg','.webp','.mp4','.ogg','.mp3','.zip']
            method=zipfile.ZIP_STORED if encoded else zipfile.ZIP_DEFLATED
            level=1 if source.suffix.lower() in ['.exe','.wav','.ttf'] else 6
            z.write(source,prefix+target,compress_type=method,compresslevel=None if encoded else level)
    with zipfile.ZipFile(path) as z:
        assert z.testzip() is None
        assert not any(any(part in ['.keys','.tools','.godot','__pycache__','.git'] for part in n.split('/')) or n.endswith(('.keystore','.jks','export_credentials.cfg','/.env')) for n in z.namelist())

def main():
    sys.stdout.reconfigure(encoding='utf-8')
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--from-build',help='Existing internal build to package without recompiling or changing its version')
    parser.add_argument('--source-only',action='store_true')
    parser.add_argument('--windows-only',action='store_true')
    args=parser.parse_args()
    for name in [VERSION,args.from_build] if args.from_build else [VERSION]:
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]*',name):raise SystemExit('Invalid release/build directory name')
    if args.from_build:
        source=ROOT/'release'/args.from_build
        original=json.loads((source/'build-manifest.json').read_text(encoding='utf-8'))
        # Refuse to label stale binaries as the current source. Import sidecars
        # are generated on each machine; raw runtime inputs must still match.
        mismatches=[name for name,digest in original['source_inputs'].items()
                    if not name.endswith('.import') and (not (ROOT/name).is_file() or sha(ROOT/name)!=digest)]
        if mismatches:raise SystemExit('Build/source mismatch: '+', '.join(mismatches[:12]))
        targets=[(source/'windows/PaperWarfront.exe',RELEASE/'windows/PaperWarfront.exe'),
                 (source/f'android/PaperWarfront-{args.from_build}.apk',RELEASE/f'android/PaperWarfront-{VERSION}.apk')]
        rows={row['path']:row for row in original['builds']}
        for src,dst in targets:
            expected=rows[src.relative_to(ROOT).as_posix()]
            if sha(src)!=expected['sha256']:raise SystemExit('Compiled binary checksum mismatch: '+str(src))
            dst.parent.mkdir(parents=True,exist_ok=True)
            if src!=dst:shutil.copy2(src,dst)
        manifest={k:v for k,v in original.items() if k not in ['archives','builds']}
        manifest.update({'release_version':VERSION,'internal_build_version':original['version'],
                         'source_build_manifest_sha256':sha(source/'build-manifest.json'),
                         'builds':[{'path':dst.relative_to(ROOT).as_posix(),'bytes':dst.stat().st_size,'sha256':sha(dst)} for _,dst in targets]})
        (RELEASE/'build-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    manifest=json.loads((RELEASE/'build-manifest.json').read_text(encoding='utf-8'))
    notes=ROOT/f'docs/releases/v{VERSION}.md'
    if notes.exists():shutil.copy2(notes,RELEASE/'README.md')
    win=RELEASE/'windows'
    (win/'licenses').mkdir(exist_ok=True)
    (win/'Play-OpenGLCompatibility.cmd').write_text('@echo off\r\ncd /d "%~dp0"\r\nstart "" "PaperWarfront.exe" --rendering-method gl_compatibility\r\n',encoding='ascii',newline='')
    for p in (ROOT/'game/licenses').glob('*.txt'):shutil.copy2(p,win/'licenses'/p.name)
    for p in (ROOT/'game/assets/fonts').glob('OFL-*.txt'):shutil.copy2(p,win/'licenses'/p.name)
    # Keep exactly one current, UTF-8 README in the Windows archive. Older
    # packages left a short README.md beside a newly generated README.txt,
    # which made the ZIP silently ship stale release notes.
    for stale in [win/'README.txt',win/'README.md']:
        stale.unlink(missing_ok=True)
    manual=(ROOT/'docs/paper-warfront/16-玩家手册.md').read_text(encoding='utf-8')
    (win/'README.md').write_text(f'''# 纸上兵戈 · {VERSION}

解压整个目录后运行 `PaperWarfront.exe`。若默认渲染无法启动，运行 `Play-OpenGLCompatibility.cmd`。资源已内嵌，不需要安装 Godot。

本版包含战争迷雾失效缓存、200 张单机剧情地图、分支/汇流/回访路线、十院差异化兵种、原生 6×6 动作帧和移动端安全区适配。完整验证见源码仓库的 `docs/paper-warfront/README.md`，以及发行目录中的 `build-manifest.json` 与 `SHA256SUMS.txt`。

密集 124 单位压力窗口仍未宣称稳定 60FPS；Android APK 当前没有实体设备验证。许可证见 `licenses/`。

内部编译版本：`{manifest.get('internal_build_version',manifest.get('version',VERSION))}`。这是首发预览；综合模拟测试仍有 7 项历史 fixture 失败，不声明全部机制测试通过。完整已知问题见发行说明。

## English quick start

Extract the whole ZIP and run `PaperWarfront.exe`. If the default renderer cannot start, use `Play-OpenGLCompatibility.cmd`. All runtime assets are embedded; Godot is not required. The in-game UI/story is primarily Simplified Chinese.

Recruit with 1–7, select spells with Q/W/E/R/T, click a legal target, and right-click to cancel. F opens research, B opens building, A/D or arrow keys pan, Home returns home, Space follows the friendly front, and P pauses. Escape cancels targeting, closes the active sheet, or pauses.

This preview contains ten factions, 200 story maps, branching campaign routes, mining/return logistics, three-state fog, and the Night Lantern UI. Seven legacy simulation fixtures remain unresolved. Android has no physical-device validation, and dense stress samples are not a stable-60-FPS guarantee. Third-party notices are in `licenses/`.

## 玩家手册

{manual}
''',encoding='utf-8')
    exe=win/'PaperWarfront.exe';apk=RELEASE/f'android/PaperWarfront-{VERSION}.apk'
    assert exe.exists() and apk.exists()
    # The source archive carries executable hashes; archive hashes are written only
    # to the external manifest afterward, so an old self-hash is never shipped.
    manifest.pop('archives',None)
    manifest.pop('download_assets',None)
    manifest['source_commit']=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    manifest['source_dirty']=bool(subprocess.check_output(['git','status','--porcelain','--untracked-files=no'],cwd=ROOT,text=True).strip())
    validation=ROOT/f'docs/releases/{VERSION}/validation-summary.json'
    if validation.exists():manifest['validation']=json.loads(validation.read_text(encoding='utf-8'))
    (RELEASE/'build-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    files=[(p,p.relative_to(win).as_posix()) for p in win.rglob('*') if p.is_file() and p.suffix not in ['.tmp','.log']]
    if not args.source_only:
        archive(RELEASE/f'PaperWarfront-Windows-{VERSION}.zip',files,'PaperWarfront/')
    if args.windows_only:
        path=RELEASE/f'PaperWarfront-Windows-{VERSION}.zip'
        manifest['archives']=[{'path':path.relative_to(ROOT).as_posix(),'bytes':path.stat().st_size,'sha256':sha(path)}]
        (RELEASE/'build-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
        (RELEASE/'SHA256SUMS.txt').write_text('\n'.join(row['sha256']+'  '+row['path'].removeprefix(f'release/{VERSION}/') for row in manifest['builds']+manifest['archives'])+'\n',encoding='utf-8')
        print(json.dumps(manifest['archives'],indent=2));return
    # Use the Git inventory, including complete runtime PNG/audio/font assets.
    # Ignored old art, QA frame trees and import caches never enter the ZIP.
    # A Git checkout is required for packaging; the resulting source ZIP can
    # be imported and exported in Godot without Git or an image service.
    tracked=subprocess.check_output(['git','ls-files','-z'],cwd=ROOT).decode('utf-8').split('\0')
    sources=[]
    for relative in sorted(set(tracked)):
        p=ROOT/relative
        if not relative or not p.is_file():continue
        if any(part in {'.git','.keys','.tools','.godot','__pycache__','output'} or part.endswith('-frames') for part in Path(relative).parts):continue
        if p.suffix.lower() in ['.keystore','.jks','.pyc'] or p.name in ['export_credentials.cfg','.env','.env.local']:continue
        sources.append((p,relative))
    included={relative for _,relative in sources}
    missing=[p.relative_to(ROOT).as_posix() for p in runtime_asset_inputs(ROOT/'game') if p.relative_to(ROOT).as_posix() not in included]
    if missing:raise SystemExit('Runtime assets missing from Git/source archive: '+', '.join(missing))
    for relative in [f'release/{VERSION}/README.md',f'release/{VERSION}/build-manifest.json']:
        p=ROOT/relative
        if p.exists():sources.append((p,relative))
    print('Archiving',len(sources),'tracked source files, including',len(runtime_asset_inputs(ROOT/'game')),'runtime assets',flush=True)
    archive(RELEASE/f'PaperWarfront-Source-{VERSION}.zip',sources,'PaperWarfront-Source/')
    manifest['archives']=[]
    for filename in [f'PaperWarfront-Windows-{VERSION}.zip',f'PaperWarfront-Source-{VERSION}.zip']:
        p=RELEASE/filename;manifest['archives'].append({'path':p.relative_to(ROOT).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)})
    download_apk=RELEASE/apk.name
    shutil.copy2(apk,download_apk)
    manifest['download_assets']=[{'file':Path(row['path']).name,'bytes':row['bytes'],'sha256':row['sha256']} for row in manifest['archives']]
    manifest['download_assets'].append({'file':download_apk.name,'bytes':download_apk.stat().st_size,'sha256':sha(download_apk)})
    manifest_path=RELEASE/'build-manifest.json'
    manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    checks=[row['sha256']+'  '+row['file'] for row in manifest['download_assets']]
    checks.append(sha(manifest_path)+'  build-manifest.json')
    if (RELEASE/'README.md').exists():checks.append(sha(RELEASE/'README.md')+'  README.md')
    (RELEASE/'SHA256SUMS.txt').write_text('\n'.join(checks)+'\n',encoding='utf-8')
    print(json.dumps(manifest['archives'],indent=2))

if __name__=='__main__':main()
