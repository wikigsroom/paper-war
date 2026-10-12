"""Publish RC35 atlas-cache and non-linear single-player story notes."""
from pathlib import Path
import hashlib, json, shutil

ROOT = Path(__file__).resolve().parents[2]
QA = ROOT / "output/qa/godot/render-runtime-rc35"
FINAL = QA / "release-final"
VERSION = "3.0.0-rc35-preview"
RELEASE = ROOT / "release" / VERSION
DOC = ROOT / "docs/paper-warfront/145-单位图集缓存与非线性剧情地图及rc35预览交付.md"
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
read = lambda p: json.loads(p.read_text("utf-8"))
assert not DOC.exists() and not (RELEASE / "README.md").exists()
validation = read(FINAL / "validation-report.json")
assert validation["passed"] and validation["version"] == VERSION
manifest = read(RELEASE / "build-manifest.json")
assert manifest["version"] == VERSION and len(manifest["source_inputs"]) == 1194
assert all(sha(ROOT / name) == digest for name, digest in manifest["source_inputs"].items())
for platform in ["windows", "apk"]:
    primary = read(FINAL / (platform + "-logic/report.json"))
    assert primary["passed"] and sum(row["checks"] for row in primary["tests"]) == 187249
    for prefix, count in [("dense", 102920), ("terrain", 5873), ("phase", 461238)]:
        report = read(FINAL / (prefix + "-" + platform + "/report.json"))
        assert report["passed"] and report["checks"] == count
pixels = read(FINAL / "atlas-render/report.json")
assert pixels["passed"] and len(pixels["comparisons"]) == 42 and all(row["max_channel_delta"] == 0 for row in pixels["comparisons"])
frames = read(FINAL / "realtime/report.json")
assert frames["passed"] and frames["version"] == VERSION
natural = read(QA / "atlas-cache-natural-observation.json")
assert natural["passed"] and len(natural["cases"]) == 4
base = [row for row in natural["cases"] if row["label"] == "baseline"]
candidate = [row for row in natural["cases"] if row["label"] == "candidate"]
assert max(row["draw_mean_ms"] for row in candidate) < min(row["draw_mean_ms"] for row in base)
assert min(row["fps"] for row in candidate) > max(row["fps"] for row in base) * 1.02
story = read(QA / "authorship.json")
assert story["passed"] and story["authored_maps"] == 200
exe_hash, apk_hash = (row["sha256"] for row in manifest["builds"])
fps_table = "\n".join(f"| {row['case']} | {row['max_units']} | {row['fps_from_mean_interval']:.2f} | {row['p95_frame_ms']:.3f} |" for row in frames["cases"])
candidate_table = "\n".join(f"| {row['order']} | {row['label']} | {row['fps']:.2f} | {row['draw_mean_ms']:.3f} | {row['p95_frame_ms']:.3f} |" for row in natural["cases"])
text = f"""# 单位图集句柄缓存、非线性剧情地图与rc35预览交付

RC35 在战斗视图中按图集路径复用已加载的 Texture2D 句柄，并在重开战斗时清空。它没有缓存帧区域、单位位置、战争迷雾或路线命中结果，因此不改变动作帧、单位大小、迷雾边界和地图交互，只减少密集单位绘制时的重复资源查找。

## 单机地图与剧情

单机地图继续遵守“地图即叙事场所”的合同：十章200张地图逐图绑定战前冲突、地点动机、真实目标、战后结果和证据旗。`campaign.json`负责对战字段，`campaign-flow.json`负责可达路线，`campaign-narrative.json`负责叙事与道路/目标绑定，`story.json`负责展示文本。

路线不被强制成一条直线。地图按冲突选择单路压迫、分岔择一、并行调查后汇流、条件汇合或可回访支线；战役推进图与一场战斗内部的道路图分开。桥口、矿点、道路长度、护送对象和未知区域必须实际改变自动行军、运金风险、视野或目标窗口。剧情文本不越过战争迷雾泄露实时敌情，未走支线不会自动获得其证据；失败不推进，回访保留已取得记录和最高星级。

## RC35 验证

| 项目 | 结果 |
|---|---:|
| 源码回归 | 78 组 / 195435 项，通过 |
| 固定姿态画面对照 | 42 组，像素差 0 |
| 移动端紧凑路线/分岔矩阵 | 通过，战场可视比例 ≥70% |
| Windows/APK 基础逻辑 | 各 36 组 / 187249 项，通过 |
| 密集、地形、阶段编译检查 | 各 102920、5873、461238 项，通过 |
| 单机剧情作者记录 | 200 张地图，通过 |

自然压力窗口（124 个单位、20 秒，仅比较渲染开销）：

| 顺序 | 输入 | 平均 FPS | 绘制 CPU 均值 | P95 帧间隔 |
|---:|---|---:|---:|---:|
{candidate_table}

实际导出程序帧率：

| 场景 | 峰值单位 | 平均 FPS | P95 帧间隔 |
|---|---:|---:|---:|
{fps_table}

持续满员 60FPS、全阵营/全关人工平衡、原作精确迷雾时序、真人完整剧情体验、Android 实体设备和真人联机仍待验证。当前 Android 结果是 Windows 原生 Godot 对 APK 的资源/字节码检查，没有使用模拟器。

## 下载

- [Windows ZIP](../../release/{VERSION}/PaperWarfront-Windows-{VERSION}.zip)
- [Windows EXE](../../release/{VERSION}/windows/PaperWarfront.exe)
- [Android APK](../../release/{VERSION}/android/PaperWarfront-{VERSION}.apk)
- [发布验证](../../release/{VERSION}/preview-verification.json)
- [SHA256 清单](../../release/{VERSION}/SHA256SUMS.txt)

EXE SHA256：`{exe_hash}`  
APK SHA256：`{apk_hash}`
"""
DOC.write_text(text, "utf-8")
(RELEASE / "README.md").write_text(text, "utf-8")
backup = QA / "pre-publication"
assert not backup.exists()
for name in ["README.md", "docs/paper-warfront/README.md"]:
    source = ROOT / name
    destination = backup / name
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    old = source.read_text("utf-8")
    entry = "[145-单位图集缓存、非线性剧情地图与rc35交付](145-单位图集缓存与非线性剧情地图及rc35预览交付.md)：按图集路径复用Texture2D句柄；200张单机地图逐图绑定剧情，支持分岔、并行、汇流和回访。"
    if name == "docs/paper-warfront/README.md":
        lines = old.splitlines()
        source.write_text(lines[0] + "\n\n" + entry + "\n\n" + "\n".join(lines[1:]) + "\n", "utf-8")
    else:
        source.write_text("# 纸上兵戈：十院留名 · rc35-preview\n\n" + entry.replace("](145-", "](docs/paper-warfront/145-") + "\n\n" + old.lstrip("# 纸上兵戈：十院留名 · rc34-preview\n"), "utf-8")
files = [DOC, RELEASE / "README.md", ROOT / "README.md", ROOT / "docs/paper-warfront/README.md"]
(QA / "publication.json").write_text(json.dumps({"passed": True, "version": VERSION, "files": {path.relative_to(ROOT).as_posix(): sha(path) for path in files}, "scope": "Published after RC35 atlas source/pixel/mobile and fresh native package validation. The 200-map single-player story and non-linear route contract remain active."}, ensure_ascii=False, indent=2) + "\n", "utf-8")
print(json.dumps({"passed": True, "doc": DOC.relative_to(ROOT).as_posix(), "exe_sha256": exe_hash, "apk_sha256": apk_hash}))
