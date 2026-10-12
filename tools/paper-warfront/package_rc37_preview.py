"""Package the RC37 visibility-cache preview without touching older releases."""
from pathlib import Path
import hashlib
import json
import shutil
import zipfile

ROOT=Path(__file__).resolve().parents[2]
VERSION="3.0.0-rc37-preview"
RELEASE=ROOT/"release"/VERSION
WIN=RELEASE/"windows"

def sha(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda:stream.read(1024*1024),b""):
            h.update(block)
    return h.hexdigest()

manifest=json.loads((RELEASE/"build-manifest.json").read_text("utf-8"))
assert manifest["version"]==VERSION
for row in manifest["builds"]:
    path=ROOT/row["path"]
    assert path.is_file() and sha(path)==row["sha256"], path
for name,digest in manifest["source_inputs"].items():
    assert sha(ROOT/name)==digest, name

(WIN/"licenses").mkdir(exist_ok=True)
for source in [*(ROOT/"game/licenses").glob("*.txt"),*(ROOT/"game/assets/fonts").glob("OFL-*.txt")]:
    shutil.copy2(source,WIN/"licenses"/source.name)
(WIN/"README.md").write_text(
    f"""# 纸上兵戈：十院留名 · {VERSION}

解压整个目录后运行 `PaperWarfront.exe`。若默认渲染无法启动，运行 `Play-OpenGLCompatibility.cmd`。

本版采用战争迷雾失效缓存：只有单位/建筑/路线/法术视野或开火揭示真正变化时才重建权威视野；强制刷新、手动施法和剧情路线语义保持不变。单机地图为十章 200 张剧情地图，支持分岔、并行调查、条件汇流与回访。

密集 124 单位压力窗口仍低于稳定 60FPS 目标；普通移动窗口已通过原生验证。Android 安装包单独提供，当前没有 Android 实体设备验证。

许可证见 `licenses/`。
""",encoding="utf-8")
(WIN/"Play-OpenGLCompatibility.cmd").write_text(
    '@echo off\r\ncd /d "%~dp0"\r\nstart "" "PaperWarfront.exe" --rendering-method gl_compatibility\r\n',
    encoding="ascii",newline="")
archive=RELEASE/f"PaperWarfront-Windows-{VERSION}.zip"
with zipfile.ZipFile(archive,"w",zipfile.ZIP_DEFLATED,compresslevel=1) as bundle:
    for path in WIN.rglob("*"):
        if path.is_file() and path.suffix not in [".tmp",".log"]:
            bundle.write(path,"PaperWarfront/"+path.relative_to(WIN).as_posix())
with zipfile.ZipFile(archive) as bundle:
    assert bundle.testzip() is None
    assert not any(".keys" in name or "signing.json" in name for name in bundle.namelist())
manifest["archives"]=[{"path":archive.relative_to(ROOT).as_posix(),"bytes":archive.stat().st_size,"sha256":sha(archive)}]
(RELEASE/"build-manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
(RELEASE/"SHA256SUMS.txt").write_text(
    "\n".join(row["sha256"]+"  "+row["path"].removeprefix(f"release/{VERSION}/") for row in manifest["builds"]+manifest["archives"])+"\n",
    encoding="utf-8")
print(json.dumps({"passed":True,"version":VERSION,"archive":manifest["archives"][0]},ensure_ascii=False))
