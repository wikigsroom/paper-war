"""Publish RC33 notes only after actual exported runtime checks have finished."""
from pathlib import Path
import hashlib
import json
import shutil

ROOT = Path(__file__).resolve().parents[2]
QA = ROOT / "output/qa/godot/phase-runtime-rc33"
FINAL = QA / "release-final"
VERSION = "3.0.0-rc33-preview"
RELEASE = ROOT / "release" / VERSION
DOC = ROOT / "docs/paper-warfront/143-行军阻挡与单位绘制调优.md"
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
read = lambda p: json.loads(p.read_text("utf-8"))
assert not DOC.exists() and not (RELEASE / "README.md").exists()
assert read(FINAL / "validation-report.json")["passed"]
manifest = read(RELEASE / "build-manifest.json")
assert manifest["version"] == VERSION and len(manifest["source_inputs"]) == 1194
assert all(sha(ROOT / n) == digest for n, digest in manifest["source_inputs"].items())
for platform in ["windows", "apk"]:
    primary = read(FINAL / (platform + "-logic/report.json"))
    assert primary["passed"] and sum(r["checks"] for r in primary["tests"]) == 187249
    for prefix, count in [("dense", 102920), ("terrain", 5873), ("phase", 461238)]:
        report = read(FINAL / (prefix + "-" + platform + "/report.json"))
        assert report["passed"] and report["checks"] == count
pixels = read(FINAL / "ownership-render/report.json")
assert pixels["passed"] and len(pixels["comparisons"]) == 24 and all(r["max_channel_delta"] == 0 for r in pixels["comparisons"])
frames = read(FINAL / "realtime/report.json")
assert frames["passed"] and frames["version"] == VERSION
cpu = read(QA / "cpu-summary.json")
cpu_table = "\n".join(f"| {r['map']} | {r['original_us']/1000:.3f} ms | {r['candidate_us']/1000:.3f} ms | {r['decrease_percent']:.2f}% |" for r in cpu["cases"])
source_frames = read(QA / "ownership-r1-natural-observation.json")
source_table = "\n".join(f"| {r['order']} | {'RC32基线' if r['label']=='baseline' else '组合候选'} | {r['fps']:.2f} | {r['draw_mean_ms']:.3f} ms | {r['p95_frame_ms']:.3f} ms |" for r in source_frames["cases"])
labels = {"before-stress": "rc32满员对照", "stress": "rc33满员压力", "bridge": "rc33正常分岔", "long": "rc33正常长图", "phone": "rc33手机布局（Windows）"}
fps_table = "\n".join(f"| {labels[r['case']]} | {r['max_units']} | {r['fps_from_mean_interval']:.2f} FPS | {r['p95_frame_ms']:.3f} ms |" for r in frames["cases"])
minimum = min(r["decrease_percent"] for r in cpu["cases"])
maximum = max(r["decrease_percent"] for r in cpu["cases"])
exe_hash, apk_hash = (r["sha256"] for r in manifest["builds"])
text = f'''# 行军阻挡、单位绘制调优与rc33预览

本次减少密集交战时重复阻挡查询与单位脚下归属纸片的几何重建。三图同进程完整状态逐步一致，模拟每步耗时降低{minimum:.2f}%–{maximum:.2f}%；源码自然窗口组合候选约36FPS，实际导出程序另表记录。持续满员60FPS仍按实测结果验收。

## 剧情和地图

[十章200图剧情与非线性战役](138-二百图剧情与非线性战役.md)继续生效。每图有战前冲突、地理动机、实际任务和战后见证；章节支持择一、并行调查、齐备汇合和未走支线回访。章内推进图与局内道路图独立，单路、分岔和汇流由具体任务决定。

正式只改battle_sim.gd、battle_view.gd及两个版本文件，1194份运行输入中1190份与RC32字节相同。全部200图／剧情／AI／价格／科技／动作／美术／字体／UI和42个其他源码脚本保留。整身动作、纸工采矿／卸货、单位地图比例、厚纸地层与全舞台未知区域保持原有呈现；38项Sub2折纸UI继续复用，没有生成新位图。

## 行军约束和绘制

| 情况 | 当前处理 |
|---|---|
| 不足40单位、非同时行军阶段或外部调用 | 原阻挡查询；本次答案缓存只在tick内部的密集同时行军阶段开启。 |
| 所有活作战阻挡者的对象、顺序、UID、阵营、道路、float64偏移、射程和支援分类相同 | 复用已证明的阻挡结果及按原规则排序的道路索引；经济单位仍参与旧索引的非有限偏移有效性检查。 |
| 来自不同查询者、方向或不同列阵条件 | 精确比较来源参数；无敌／有敌、重型间距等仍依原规则。 |
| 请求步长变化 | 已证明限距时返回当前请求与限距的较小者；先前未限距时只在新请求不大于旧请求时复用。 |
| 本步真实致死伤害、寿命到期、出仓、位置／身份／阵营改变、显式dirty请求 | 清除或重新核验；不让旧阻挡结果继续引用失效前排。 |
| NaN／无穷请求或非常规方向 | 调用真实RC32索引／标量回退。NaN的原索引行为与较早标量参考不同，已分别保留其正确对照。 |
| 长对局或重开 | 最多256个查询来源；重开释放答案、快照和计数。300来源只验证上限，不改变正式人口。 |
| 脚下归属纸片 | 两个方向各保留原六顶点网格，含向内缺口；每个单位的坐标、观察方颜色、阵营转换与绘制顺序仍实时更新。 |

原生绘制诊断中，单位排序约0.25ms，归属标记约0.93ms，整身帧约1.11ms、血条／状态约1.19ms，迷雾约0.04ms。它们是带计时器的分项诊断或约1Hz快照，不能直接相加成真实GPU耗时。Godot已经缓存文字排版，没有另外建立重复文字缓存，也没有削减动作、状态或粒子数量。

早期行军候选把纸工位置纳入作战阻挡快照，精确状态通过但CPU变慢约10%–11%，已弃用并保留记录。第二版只核对作战阻挡者；第三版在精确匹配时同时保留已排序索引，为本次正式采用的模拟候选。

## 检查和失败记录

78组195435项既有源码回归、432427项200图阻挡边界、28811项十院混合兵种／纸工阶段检查，共656673项断言通过。另以完整独立冻结的RC32全部44脚本闭包，逐步比较3600满员步和73103正常付款步，完整演员、事件、金币／法力、弹体、随机流、视野和记忆一致。正常付款涵盖三图与印垒／木拓镜像，最多240模拟秒；压力夹具不作为胜率证据。

第一次观察器从仅含作战兵的接口寻找纸工，尾部脚本错误，已保留失败并停止其自有进程。第二次432416项仅NaN参考不符：实际RC32原索引与旧标量扫描不同；新观察器保留所有有限值独立标量检查，另以实际完整RC32闭包核对12项非有限请求。游戏候选字节没有因此更改。

首次完整回归的简化项目缺少字体／图集，四组资源检查失败；其逻辑边界、混合阶段和付款三项已完成。之后从冻结RC32复制全部1194份运行输入、455项导入资源和两份仅源码QA使用的旧助手，完整78组全部通过。失败日志与部分失败回执仍保留，不计为全部成功。

EXE与APK各36组187249项基础、两组102920项既有模拟边界、5873项地形、两组461238项本次行军边界，共41组757280项实际编译检查。包内按既有合同仅42份GDC；两份旧关节助手排除。本次新观察器没有按源码脚本数增减检查项，只把报告里的模拟脚本后缀切换为.gdc，故新断言数与源码相同。

桌面／手机24组实际编译画面对照逐像素相同，含缓存热用后阵营转换、观察方切换、受击、分身、毒／控制状态和镜头震动；另12组既有地形／整身姿态对照通过。200图比例、八显示配置、战役UI474项、军令纸页、迷雾、导航、正常付费命中、默认Vulkan和六次实际EXE启动分别通过。战场画面继续至少70%。原200图写作与1288个CJK字形证据按相同数据哈希沿用。

APK版本代码30032、原签名、16KB对齐、22份运行JSON和455项运行资源核验。APK真实编译逻辑由Windows原生Godot加载包内GDC完成；没有可用实体Android手机，没有使用模拟器。

## 同进程模拟计时

| 地图 | RC32每步均值 | 行军候选每步均值 | 降低 |
|---|---:|---:|---:|
{cpu_table}

每图1200步，在同一个Windows原生进程交替先后执行，JSON状态比较不计入tick耗时。124名高生命演员、AI关闭用于持续交战；这不是渲染FPS或普通对局平衡。归属网格不会在该无画面计时中执行。

## 源码自然窗口采样

| 先后 | 输入 | 平均FPS | 绘制CPU均值 | P95帧间隔 |
|---|---|---:|---:|---:|
{source_table}

此前仅行军候选的两次采样是34.26→34.24FPS，没有帧率改善；保留该反例后再拆查绘制。上表是增加归属网格后新做的ABBA四次串行20秒满员观察，绘制CPU约8.8→7.7ms。相邻运行仍含环境波动，不能保证所有设备按同样比例改善，也不作为编译包FPS。

## 实际导出程序帧率

| 场景 | 单位峰值 | 平均FPS | P95帧间隔 |
|---|---:|---:|---:|
{fps_table}

压力20秒，正常场景160秒；Windows可见窗口、声音开启、自然App处理。自己的导出／复制／哈希和其他QA完成后串行运行；其他用户进程保留。原始帧CSV、截图与模拟进度分别记录。手机布局是在Windows GPU运行。

普通55FPS目标：{frames['normal_55fps_target_met']}；持续满员60FPS目标：{frames['capacity_60fps_target_met']}。密集性能、全阵营／全关平衡、原作精确迷雾时序、真人完整剧情、Android硬件及真人联机仍待完成。

## 下载和复核

Windows解压后运行PaperWarfront.exe；兼容渲染可运行Play-OpenGLCompatibility.cmd。Android沿用原签名，可覆盖更新同包。

- [WindowsZIP](../../release/{VERSION}/PaperWarfront-Windows-{VERSION}.zip)
- [WindowsEXE](../../release/{VERSION}/windows/PaperWarfront.exe)
- [AndroidAPK](../../release/{VERSION}/android/PaperWarfront-{VERSION}.apk)
- [发布验证](../../release/{VERSION}/preview-verification.json)
- [SHA256清单](../../release/{VERSION}/SHA256SUMS.txt)

EXE SHA256：`{exe_hash}`；APK SHA256：`{apk_hash}`。证据根为output/qa/godot/phase-runtime-rc33/。既有版本程序、诊断、失败记录与规范保持独立版本。
'''
DOC.write_text(text, "utf-8")
(RELEASE / "README.md").write_text(text.replace("](../../release/" + VERSION + "/", "](").replace("](138-二百图剧情与非线性战役.md)", "](../../docs/paper-warfront/138-二百图剧情与非线性战役.md)"), "utf-8")
entry = "[143-行军阻挡与单位绘制调优及rc33交付](143-行军阻挡与单位绘制调优.md)：200图剧情与分支继续生效；完整RC32闭包3600满员步和73103付款步一致，源码656673项、两包各757280项、24组编译画面逐像素一致，实际帧率与待完成项见本项。"
backup = QA / "pre-publication"
assert not backup.exists()
for name in ["README.md", "docs/paper-warfront/README.md"]:
    path = ROOT / name
    dest = backup / name
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, dest)
    old = path.read_text("utf-8")
    if name == "docs/paper-warfront/README.md":
        old = old.replace(old.splitlines()[0], "# 纸上兵戈：十院留名 · rc33-preview", 1)
        head, tail = old.split("\n", 1)
        old = head + "\n\n" + entry + "\n\n最新下载与验收范围以143为准。以下保留历史阶段记录。\n" + tail
    else:
        if old.startswith("# "):
            old = old.split("\n", 1)[1].lstrip()
        old = "# 纸上兵戈：十院留名 · rc33-preview\n\n" + entry.replace("](143-", "](docs/paper-warfront/143-") + "\n\n最新下载与验收范围以143为准。以下保留各历史阶段记录。\n\n" + old
    path.write_text(old, "utf-8")
files = [DOC, RELEASE / "README.md", ROOT / "README.md", ROOT / "docs/paper-warfront/README.md"]
(QA / "publication.json").write_text(json.dumps({
    "passed": True, "version": VERSION, "files": {p.relative_to(ROOT).as_posix(): sha(p) for p in files},
    "scope": "Published after actual native exports, full compiled/UI/story/map/pixel and natural FPS checks. Existing200-map branching plot retained. Pending dense60FPS, full balance, original exact fog, human story/network and physical Android."
}, ensure_ascii=False, indent=2) + "\n", "utf-8")
print("Published RC33 verified preview notes", flush=True)
