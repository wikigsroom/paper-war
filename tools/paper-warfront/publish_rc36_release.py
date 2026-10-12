"""Publish the RC36 simulation-buffer preview and its single-player story notes."""
from pathlib import Path
import hashlib
import json
import shutil

ROOT = Path(__file__).resolve().parents[2]
QA = ROOT / "output/qa/godot/render-runtime-rc36"
FINAL = QA / "release-final"
VERSION = "3.0.0-rc36-preview"
RELEASE = ROOT / "release" / VERSION
DOC = ROOT / "docs/paper-warfront/146-战斗模拟快照缓冲与rc36预览交付.md"


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def read(path: Path):
    return json.loads(path.read_text("utf-8"))


validation = read(FINAL / "validation-report.json")
assert validation["passed"] and validation["version"] == VERSION
manifest = read(RELEASE / "build-manifest.json")
assert manifest["version"] == VERSION
assert all(sha(ROOT / name) == digest for name, digest in manifest["source_inputs"].items())
pixels = read(FINAL / "atlas-render/report.json")
assert pixels["passed"] and len(pixels["comparisons"]) == 42
assert all(row["max_channel_delta"] == 0 for row in pixels["comparisons"])
realtime = read(FINAL / "realtime/report.json")
assert realtime["passed"] and realtime["version"] == VERSION
story = read(QA / "authorship.json")
assert story["passed"] and story["authored_maps"] == 200
source = read(QA / "source-final/report.json")
assert source["passed"] and sum(row["checks"] for row in source["tests"]) == 195435

exe_hash, apk_hash = (row["sha256"] for row in manifest["builds"])
doc_text = f"""# 战斗模拟快照缓冲、非线性剧情地图与 rc36 预览交付

RC36 继续沿用《纸上兵戈》的单机地图叙事合同：200 张地图属于十章战役，每一张都绑定战前冲突、地点动机、真实目标、战后结果与可追溯证据。战役路线支持分岔、并行调查、条件汇流和回访；地图内部的桥口、矿点、道路长度、护送对象与战争迷雾仍然决定自动行军风险、金币循环、视野和目标窗口。

本版本的工程改动集中在 [battle_sim.gd](../../game/scripts/battle_sim.gd)：复用单位、投射物、延迟法术、尸体的 tick 快照，以及单位/建筑存活缓冲。它保留原有的快照边界、字典引用、伤害/碰撞/战争迷雾/动作帧顺序，只减少每帧临时 Array 分配。战斗视图、单位图集、地图几何、剧情数据和 UI 没有被这个版本改写。

## RC36 验证

| 项目 | 结果 |
|---|---:|
| 源码机制回归 | 78 组 / 195435 项，通过 |
| 固定姿态桌面/手机像素对照 | 42 组，像素差 0 |
| 单机地图作者记录 | 200 张 / 10 章，通过 |
| Windows 与 APK 编译逻辑 | 由发布验证重新执行，通过 |
| 移动端矩阵、迷雾、地图阶段、剧情 UI | 由发布验证重新执行，通过 |
| Android 实体设备 | 当前未验证（用户暂无设备） |

密集压力窗口仍以实际原生 GPU/CPU 观察为准；本版没有把“满员 60FPS”写成已完成承诺。全阵营/全关人工平衡、原作精确战争迷雾时序、真人完整剧情体验与真人联机仍是后续验收项。

## 下载

- [Windows ZIP](../../release/{VERSION}/PaperWarfront-Windows-{VERSION}.zip)
- [Windows EXE](../../release/{VERSION}/windows/PaperWarfront.exe)
- [Android APK](../../release/{VERSION}/android/PaperWarfront-{VERSION}.apk)
- [发布验证](../../release/{VERSION}/preview-verification.json)
- [SHA256 清单](../../release/{VERSION}/SHA256SUMS.txt)

EXE SHA256：`{exe_hash}`  
APK SHA256：`{apk_hash}`
"""
DOC.write_text(doc_text, "utf-8")
(RELEASE / "README.md").write_text(doc_text, "utf-8")

for name in ["README.md", "docs/paper-warfront/README.md"]:
    source_path = ROOT / name
    backup = QA / "pre-publication" / name
    backup.parent.mkdir(parents=True, exist_ok=True)
    if not backup.exists():
        shutil.copy2(source_path, backup)
    old = source_path.read_text("utf-8")
    if name == "README.md":
        source_path.write_text(
            "# 纸上兵戈：十院留名 · rc36-preview\n\n"
            "[146-战斗模拟快照缓冲与 rc36 交付](docs/paper-warfront/146-战斗模拟快照缓冲与rc36预览交付.md)：复用战斗 tick 快照与存活缓冲，保留 200 张非线性剧情地图与战争迷雾合同。\n\n"
            + old.lstrip("# 纸上兵戈：十院留名 · rc35-preview\n"),
            "utf-8",
        )
    else:
        lines = old.splitlines()
        source_path.write_text(
            lines[0] + "\n\n"
            "[146-战斗模拟快照缓冲与 rc36 交付](146-战斗模拟快照缓冲与rc36预览交付.md)：复用战斗 tick 快照与存活缓冲，地图/剧情/迷雾规则保持绑定。\n\n"
            + "\n".join(lines[1:]) + "\n",
            "utf-8",
        )

files = [DOC, RELEASE / "README.md", ROOT / "README.md", ROOT / "docs/paper-warfront/README.md"]
(QA / "publication.json").write_text(json.dumps({
    "passed": True,
    "version": VERSION,
    "files": {path.relative_to(ROOT).as_posix(): sha(path) for path in files},
    "scope": "Published after fresh RC36 source, pixel, native package, map/story, fog and mobile validation.",
}, ensure_ascii=False, indent=2) + "\n", "utf-8")
print(json.dumps({"passed": True, "version": VERSION, "doc": DOC.relative_to(ROOT).as_posix(), "exe_sha256": exe_hash, "apk_sha256": apk_hash}, ensure_ascii=False))
