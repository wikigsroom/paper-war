"""Publish RC31 notes only after fresh exports, rendering and natural FPS finish."""
from pathlib import Path
import hashlib
import json
import shutil

ROOT = Path(__file__).resolve().parents[2]
VERSION = "3.0.0-rc31-preview"
QA = ROOT / "output/qa/godot/pressure-runtime-rc31"
FINAL = QA / "release-final"
RELEASE = ROOT / "release" / VERSION
DOC = ROOT / "docs/paper-warfront/140-地形绘制缓存与镜头移动复核.md"
read = lambda p: json.loads(p.read_text("utf-8"))
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert not DOC.exists() and not (RELEASE / "README.md").exists()
validation = read(FINAL / "validation-report.json")
assert validation["passed"] and validation["version"] == VERSION
manifest = read(RELEASE / "build-manifest.json")
assert len(manifest["source_inputs"]) == 1194
assert all(sha(ROOT / n) == d for n, d in manifest["source_inputs"].items())
cpu = read(QA / "terrain-cpu-summary.json")
assert cpu["passed"] and cpu["paired_stable_quartets"] == 75
for platform in ["windows", "apk"]:
    primary = read(FINAL / (platform + "-logic/report.json"))
    dense = read(FINAL / ("dense-" + platform + "/report.json"))
    terrain = read(FINAL / ("terrain-" + platform + "/report.json"))
    assert primary["passed"] and sum(r["checks"] for r in primary["tests"]) == 187249
    assert dense["passed"] and dense["checks"] == 102920
    assert terrain["passed"] and terrain["checks"] == 5873
pixels = read(FINAL / "render-cache/report.json")
assert pixels["passed"] and len(pixels["comparisons"]) == 12
assert all(r["max_channel_delta"] == 0 for r in pixels["comparisons"])
frames = read(FINAL / "realtime/report.json")
assert frames["passed"] and frames["version"] == VERSION
labels = {"before-stress": "rc30满员对照", "stress": "rc31满员压力", "bridge": "rc31正常分岔", "long": "rc31正常长图", "phone": "rc31手机布局（Windows）"}
table = "\n".join(f"| {labels[r['case']]} | {r['max_units']} | {r['fps_from_mean_interval']:.2f} FPS | {r['p95_frame_ms']:.3f} ms |" for r in frames["cases"])
for name in ["README.md", "docs/paper-warfront/README.md"]:
    dest = QA / "pre-publication" / name
    assert not dest.exists()
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / name, dest)
exe_hash, apk_hash = (r["sha256"] for r in manifest["builds"])
text = f"""# 地形绘制缓存、镜头移动复核与rc31预览

本次减少纸片地层与场景装饰的重复绘制准备。镜头移动时走原绘制，布局与镜头完全停稳后才记录并复用一份命令；75组同进程交替样本中，包含背景的地形绘制层平均耗时从{cpu['original_layer_us']/1000:.3f}毫秒降至{cpu['optimized_layer_us']/1000:.3f}毫秒，降低{cpu['decrease_percent']:.2f}%。这是Windows原生源码试验的绘制层计时，实际编译包帧率另表记录。

## 单机剧情与地图

[200图剧情与十章分支战役](138-二百图剧情与非线性战役.md)继续生效。每图的战前冲突、地理动机、真实任务、战后见证与完成集合保持现有设计；章节允许择一、并行调查、齐备汇合和未选支线回访。战役推进图与局内道路图独立，单路、分岔和汇流按剧情目标选用，不强制线性。

## 缓存的行为约束

| 触发 | 当前处理 |
|---|---|
| 镜头移动／回弹、窗口／战场比例变化 | 参数逐项精确比较。移动帧直接执行旧地形绘制，避免每帧记录失效计划；相同参数重复出现后记录当前计划。 |
| 道路、地面曲线、节点、矿点、基地或选路变化 | 地理快照不相等即失效，当前原绘制生成实际图形。 |
| 增删素材、修改纸边参数或替换贴图 | 元数据和原生贴图身份／尺寸变化即失效；缺失素材也被记录，随后补入能立即生效。 |
| 贴图被移出缓存／再次加载失败 | 走原加载和绘制，保留实际加载结果；加载失败不能沿用旧地形。 |
| 新关卡、地图／视图／数据对象替换、网格池重置 | 失效重建；只弱引用视图、地图和数据库，清场释放计划引用。 |
| 攻受击震动、迷雾、兵体动作、工人采矿和粒子 | 地形命令仍继承当前绘制变换；这些动态效果继续执行每帧原逻辑。 |

正式只更新battle_view.gd、theatre_ground_cache.gd及两个导出版本文件；1194输入中1190份与rc30字节相同。42个其余脚本、全部剧情／地图／AI／价格／科技、60Hz模拟、单位比例、厚纸土层、38项折纸UI和72套36格整身动作按原版本保留。没有生成或替换位图。

## 原生绘制与编译验证

源码基础78组195435项和新地形检查5873项通过，共201308项。新检查用独立冻结的rc30地形／网格助手，逐一比对200图、桌面／手机两布局、两个小数镜头下的原生绘制顺序、参数和真实网格数组；2521次绘制比对还覆盖失效、加载失败／恢复、替换对象、清场及弱引用释放。合成贴图用于隔离绘制参数，真实素材的像素对照单独完成。

实际EXE与APK各36组187249项基础逻辑、两组102920项原模拟边界和一组5873项地形检查，共296042项。Windows加载真实内嵌GDC，APK提取真实GDC后由Windows原生Godot执行；两包字节绑定一致。APK版本代码30030、原签名、16KB对齐、22份运行JSON与455项资源核验。

编译包桌面／手机12组画面对照逐像素相同。200图比例、八显示配置、战役UI474项及真实选择／存档、纸页／军令／迷雾／镜头、正常付款命中、默认Vulkan和六次EXE启动分别完成。全部关卡剧情与1288个CJK字形的既有证据绑定到相同输入；rc30的3600满员步和73103正常付费步原版闭包对照明确沿用，没有声称重新执行。

候选R1逐帧记录在移动镜头中产生额外开销，R2加入移动绕过。独立检查随后发现R2贴图移出后加载失败仍复用旧画面；R3修正为保守失效。早期观察器类型错误、对照夹具的视图参数不一致、源检查缺少测试文件和校验目录已有UID侧文件的准备失败均保留记录，修正后用独立目录验证；这些失败没有计为通过。

首轮长图自然采样在进程退出后只留下第一张截图，没有完整帧报告；确认工具句柄及对应OS进程均不存在后，将中断目录独立保留，完成长图和手机两场。已完成的前三场通过原收据／帧文件哈希沿用，中断截图未计作成功采样。

## 实际编译包帧率

| 场景 | 单位峰值 | 均值帧率 | P95帧间隔 |
|---|---:|---:|---:|
{table}

压力各20秒，正常场景各160秒。可见Windows原生窗口、声音开启、自然App处理；压力夹具124名高生命演员、AI关闭，正常场景为300金币与原AI。自己的导出／复制／哈希及其他QA均结束后串行采样，保留原帧CSV和截图；其他项目的用户进程未被停止，相邻版本FPS差值不能直接当作缓存增益。上述37.45%仅来自同进程停稳镜头绘制层，不能换算成整体FPS。手机布局仍在Windows运行。

普通55FPS目标：{frames['normal_55fps_target_met']}；持续满员60FPS目标：{frames['capacity_60fps_target_met']}。密集性能、全阵营／全关平衡、原作精确视野时序、真人完整剧情、Android实体设备与真人联机仍待完成；没有可用手机，未使用模拟器。

## 使用与下载

Windows解压后运行PaperWarfront.exe；需要兼容渲染时使用Play-OpenGLCompatibility.cmd。Android沿用原签名，可更新同包。单机战役纸页选择可行动剧情图，关后保留真实见证，未选支线可回访。

- [WindowsZIP](../../release/{VERSION}/PaperWarfront-Windows-{VERSION}.zip)
- [WindowsEXE](../../release/{VERSION}/windows/PaperWarfront.exe)
- [AndroidAPK](../../release/{VERSION}/android/PaperWarfront-{VERSION}.apk)
- [发布验证](../../release/{VERSION}/preview-verification.json)
- [SHA256清单](../../release/{VERSION}/SHA256SUMS.txt)

EXE SHA256：`{exe_hash}`；APK SHA256：`{apk_hash}`。证据根为output/qa/godot/pressure-runtime-rc31/；源码试验、失败候选、编译验证和自然运行按各自报告范围保存。旧rc30与更早版本的文档／工具／程序保持独立版本记录。
"""
DOC.write_text(text, "utf-8")
(RELEASE / "README.md").write_text(text.replace("../../release/" + VERSION + "/", "").replace("(138-二百图剧情与非线性战役.md)", "(../../docs/paper-warfront/138-二百图剧情与非线性战役.md)"), "utf-8")
root_readme = (ROOT / "README.md").read_text("utf-8")
body = root_readme[root_readme.index("Godot4.7.2") :]
body = body.replace("源码基础78组195435项与额外两组102920项，编译包各基础36组187249项与额外两组102920项通过；", "源码基础78组195435项和地形5873项通过；编译包各基础36组187249项、原模拟边界102920项和地形5873项通过；")
(ROOT / "README.md").write_text(f"# 纸上兵戈：十院留名 / Paper Warfront · rc31-preview\n\n当前预览为**rc31**：[地形绘制与镜头移动复核](docs/paper-warfront/{DOC.name})。镜头移动时原绘制、停稳后精确复用；75组同进程原生样本的背景／地形层耗时降低约37%，实际编译帧率和未完成目标单列。\n\n[Windows下载](release/{VERSION}/PaperWarfront-Windows-{VERSION}.zip) · [AndroidAPK](release/{VERSION}/android/PaperWarfront-{VERSION}.apk) · [发布验证](release/{VERSION}/preview-verification.json) · [版本说明](release/{VERSION}/README.md)\n\n" + body, "utf-8")
index = ROOT / "docs/paper-warfront/README.md"
old = index.read_text("utf-8")
index.write_text("# 纸上兵戈：十院留名 · rc31-preview\n\n[140-地形绘制与镜头移动复核及rc31交付](" + DOC.name + ")：200图、5873项新地形约束和2521次原生绘制比对，12组编译像素一致；源码201308项，两包各296042项。剧情、分支、迷雾和单位比例继续生效，实际FPS及待完成项见本项。\n\n最新下载与验收范围以140为准。下方保留历史版本记录；其旧“当前”表述仅适用于对应版本。\n\n" + old[old.index("[139-"):], "utf-8")
(QA / "publication.json").write_text(json.dumps({"passed": True, "version": VERSION,
    "files": {p.relative_to(ROOT).as_posix(): sha(p) for p in [DOC, RELEASE / "README.md", ROOT / "README.md", index]},
    "generator_sha256": sha(Path(__file__)), "validation_sha256": sha(FINAL / "validation-report.json"),
    "scope": "Notes derive from completed native source/compiled/raster/FPS observations; simulation/story/font evidence retention explicitly distinguished. Package bundling/final audit remain."
}, ensure_ascii=False, indent=2) + "\n", "utf-8")
print("Published reviewed RC31 documentation; final package audit remains")
