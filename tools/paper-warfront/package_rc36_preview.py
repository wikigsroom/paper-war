"""Package reviewed preview binaries and licenses without source credentials."""
from pathlib import Path
import hashlib,json,shutil,zipfile,os
ROOT=Path(__file__).resolve().parents[2]
VERSION=os.environ.get('PAPER_RELEASE_VERSION','3.0.0-rc9-preview')
RELEASE=ROOT/'release'/VERSION
WIN=RELEASE/'windows'
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
manifest=json.loads((RELEASE/'build-manifest.json').read_text(encoding='utf-8'))
for row in manifest['builds']:
    assert sha(ROOT/row['path'])==row['sha256'],row['path']
(WIN/'licenses').mkdir(exist_ok=True)
for source in [*(ROOT/'game/licenses').glob('*.txt'),*(ROOT/'game/assets/fonts').glob('OFL-*.txt')]:
    shutil.copy2(source,WIN/'licenses'/source.name)
assert VERSION=='3.0.0-rc36-preview'
(WIN/'README.md').write_text('# 纸上兵戈：十院留名 · '+VERSION+'\n\n解压整个目录后运行 PaperWarfront.exe。若默认渲染无法启动，运行 Play-OpenGLCompatibility.cmd。\n\n单机十章200图带逐图剧情、并行任务和择一路线；可回访。战斗保持自动行军、金币/法力、科技和手动施法。\n\n本版复用纸屑网格，保持动作和粒子数量；本地实际检查范围见 [发布验证](preview-verification.json)。\n\n持续满员60FPS、全关平衡、真人剧情/联机与Android硬件仍待验证。Android安装包单独提供。\n\n许可证见 licenses/。\n',encoding='utf-8')
if (RELEASE/'preview-verification.json').exists():shutil.copy2(RELEASE/'preview-verification.json',WIN/'preview-verification.json')
(WIN/'Play-OpenGLCompatibility.cmd').write_text('@echo off\r\ncd /d "%~dp0"\r\nstart "" "PaperWarfront.exe" --rendering-method gl_compatibility\r\n',encoding='ascii',newline='')
archive=RELEASE/f'PaperWarfront-Windows-{VERSION}.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=1) as bundle:
    for path in WIN.rglob('*'):
        if path.is_file() and path.suffix not in ['.tmp','.log']:bundle.write(path,'PaperWarfront/'+path.relative_to(WIN).as_posix())
with zipfile.ZipFile(archive) as bundle:
    assert bundle.testzip() is None
    assert not any('.keys' in name or 'signing.json' in name for name in bundle.namelist())
manifest['archives']=[{'path':archive.relative_to(ROOT).as_posix(),'bytes':archive.stat().st_size,'sha256':sha(archive)}]
(RELEASE/'build-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
(RELEASE/'SHA256SUMS.txt').write_text('\n'.join(row['sha256']+'  '+row['path'].removeprefix(f'release/{VERSION}/') for row in manifest['builds']+manifest['archives'])+'\n',encoding='utf-8')
print(json.dumps(manifest['archives']))
