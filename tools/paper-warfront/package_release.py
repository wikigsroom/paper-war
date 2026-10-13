"""Archive only the deliverable source, assets and evidence; never credentials."""
from pathlib import Path
import zipfile,json,hashlib,shutil,sys,os

ROOT=Path(__file__).resolve().parents[2];VERSION=os.environ.get('PAPER_RELEASE_VERSION','3.0.0-rc5');RELEASE=ROOT/'release'/VERSION

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
        assert not any(any(part in ['.keys','.tools','.godot','__pycache__'] for part in n.split('/')) or n.endswith(('.keystore','.jks')) for n in z.namelist())

def main():
    sys.stdout.reconfigure(encoding='utf-8')
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

## 玩家手册

{manual}
''',encoding='utf-8')
    exe=win/'PaperWarfront.exe';apk=RELEASE/f'android/PaperWarfront-{VERSION}.apk'
    assert exe.exists() and apk.exists()
    # The source archive carries executable hashes; archive hashes are written only
    # to the external manifest afterward, so an old self-hash is never shipped.
    manifest=json.loads((RELEASE/'build-manifest.json').read_text(encoding='utf-8'))
    manifest.pop('archives',None)
    (RELEASE/'build-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    files=[(p,p.relative_to(win).as_posix()) for p in win.rglob('*') if p.is_file() and p.suffix not in ['.tmp','.log']]
    if '--source-only' not in sys.argv:
        archive(RELEASE/f'PaperWarfront-Windows-{VERSION}.zip',files,'PaperWarfront/')
    if '--windows-only' in sys.argv:
        path=RELEASE/f'PaperWarfront-Windows-{VERSION}.zip'
        manifest['archives']=[{'path':path.relative_to(ROOT).as_posix(),'bytes':path.stat().st_size,'sha256':sha(path)}]
        (RELEASE/'build-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
        (RELEASE/'SHA256SUMS.txt').write_text('\n'.join(row['sha256']+'  '+row['path'].removeprefix(f'release/{VERSION}/') for row in manifest['builds']+manifest['archives'])+'\n',encoding='utf-8')
        print(json.dumps(manifest['archives'],indent=2));return
    sources=[]
    for root in ['game','docs','assets/paper-warfront','tools/paper-warfront','output/imagegen','output/qa/godot']:
        for p in (ROOT/root).rglob('*'):
            if not p.is_file():continue
            relative=p.relative_to(ROOT)
            if any(s in ['.godot','.keys','.tools','__pycache__','rejected'] for s in relative.parts):continue
            if p.suffix in ['.pyc','.keystore','.jks'] or p.name=='export_credentials.cfg':continue
            # Keep rendered evidence and reports; frame sequences and the pre-edit
            # backup remain in the workspace instead of duplicating them in source.
            if root=='output/qa/godot' and ('frames' in relative.parts or (p.name.startswith('before-') and p.suffix=='.zip')):continue
            # The final archive audit is external: including its own source-ZIP
            # hash would create a circular checksum dependency.
            if relative.as_posix()=='output/qa/godot/frame-rebuild/release-audit.json':continue
            sources.append((p,relative.as_posix()))
    # The approved direction remains available for the references in the art documents.
    for relative in ['README.md','AGENTS.md','.gitignore',f'release/{VERSION}/README.md',f'release/{VERSION}/build-manifest.json']:
        p=ROOT/relative
        if p.exists():sources.append((p,relative))
    archive(RELEASE/f'PaperWarfront-Source-{VERSION}.zip',sources,'PaperWarfront-Source/')
    manifest['archives']=[]
    for filename in [f'PaperWarfront-Windows-{VERSION}.zip',f'PaperWarfront-Source-{VERSION}.zip']:
        p=RELEASE/filename;manifest['archives'].append({'path':p.relative_to(ROOT).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)})
    (RELEASE/'build-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    (RELEASE/'SHA256SUMS.txt').write_text('\n'.join(row['sha256']+'  '+row['path'].removeprefix(f'release/{VERSION}/') for row in manifest['builds']+manifest['archives'])+'\n',encoding='utf-8')
    print(json.dumps(manifest['archives'],indent=2))

if __name__=='__main__':main()
