"""Write reviewed rc30 release notes from completed native observations."""
from pathlib import Path
import hashlib
import json
import shutil
import statistics

ROOT = Path(__file__).resolve().parents[2]
VERSION = "3.0.0-rc30-preview"
QA = ROOT / "output/qa/godot/dense-runtime-rc30"
FINAL = QA / "release-final"
RELEASE = ROOT / "release" / VERSION
DOC = ROOT / "docs/paper-warfront/139-密集交战缓存与运行复核.md"
read = lambda p: json.loads(p.read_text(encoding="utf-8"))
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert not DOC.exists() and not (RELEASE / "README.md").exists()
for name in ["runner-report.json", "extras-runner-report.json", "realtime/report.json"]:
    proof = read(FINAL / name)
    assert proof["passed"] and proof["version"] == VERSION, name
capacity = read(QA / "phase-reuse-r2-capacity.json")
paid = read(QA / "phase-reuse-r2-paid-r3.json")
frames = read(FINAL / "realtime/report.json")
manifest = read(RELEASE / "build-manifest.json")
assert capacity["passed"] and capacity["checks"] == 3600
assert paid["passed"] and paid["checks"] == 73103
assert manifest["version"] == VERSION and len(manifest["source_inputs"]) == 1194
for platform in ["windows", "apk"]:
    primary = read(FINAL / (platform + "-logic/report.json"))
    extra = read(FINAL / ("dense-" + platform + "/report.json"))
    assert primary["passed"] and sum(r["checks"] for r in primary["tests"]) == 187249
    assert extra["passed"] and extra["checks"] == 102920
for name in ["README.md", "docs/paper-warfront/README.md"]:
    dst = QA / "pre-publication" / name
    assert not dst.exists()
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / name, dst)

cpu_rows = []
for map_id, label in [("map.01.01", "短主路"), ("map.01.04", "分岔与汇流"), ("map.01.11", "长接援")]:
    rows = [r for r in capacity["paired_cpu"] if r["map"] == map_id]
    before = statistics.mean(r["baseline_us"] for r in rows) / 1000
    after = statistics.mean(r["candidate_us"] for r in rows) / 1000
    cpu_rows.append(f"| {map_id} · {label} | {len(rows)} | {before:.3f} ms | {after:.3f} ms | {(1-after/before)*100:.2f}% |")
labels = {"before-stress": "rc29持续满员对照", "stress": "rc30持续满员压力", "bridge": "rc30正常分岔",
          "long": "rc30正常长图", "phone": "rc30手机布局（Windows）"}
frame_rows = [f"| {labels[r['case']]} | {r['max_units']} | {r['fps_from_mean_interval']:.2f} FPS | {r['p95_frame_ms']:.3f} ms |"
              for r in frames["cases"]]
cpu_table = "\n".join(cpu_rows)
frame_table = "\n".join(frame_rows)
exe_hash, apk_hash = (r["sha256"] for r in manifest["builds"])
doc = f"""# 密集交战缓存、独立边界复核与rc30预览

本次减少密集交战中重复的寻敌索引、停驻坐标投影和视野所有者读取。三个124单位场景的同进程交替模拟计时降低9.40%–10.36%；自然运行的画面帧率另表实测，不用CPU检查替代FPS。

十章200关的逐图剧情、地理动机、真实任务目标和独立证据，以及章内择一、并行取证、汇合与回访，沿用[138的已实现设计](138-二百图剧情与非线性战役.md)。章节推进图与战场道路图独立；单主路、双路、汇流仍按任务设计使用，不强制线性，也不强制分岔。

## 实现边界

| 改动 | 复用条件与失效条件 | 保留的游戏行为 |
|---|---|---|
| 寻敌几何记录 | 同一演员引用、原顺序、道路、float64弧长、原生坐标与支援分类完全一致才复用。几何或分类变化重建。 | 当前生命和阵营仍实时筛选；死亡、换阵营、同UID换演员不沿用旧判定；同距离优先顺序、工人实际身体锚点不变。 |
| 停驻道路投影 | 仅有限的零／负行进且有合法UID；先执行原投影作归一化。演员、归一化状态、长度、节点和累计长度逐一相等才复用，最多256条。 | 正向行军与过路口继续执行原逻辑；每次返回独立的空越线事件；保留双精度边界。 |
| 视野所有者读取 | 每次方法调用内只读取一次弱引用所有者，方法外仍为弱引用。 | 视野半径、更新时序、当前／已探索／记忆、开火揭示、AI及施法可见性规则一致。 |

正式只更新三个脚本及导出版本。1194份运行输入中1189份保持rc29字节内容；全部关卡、兵种、科技、AI预算、价格、生产、60Hz规则、粒子、动作、38项Sub2折纸UI与72套36格整身动作均保留。缓存计数只用于诊断，不参与战斗统计或胜利条件。

## 同进程模拟计时

| 场景 | 比对步骤 | 原rc29完整闭包 | 优化后 | 平均耗时下降 |
|---|---:|---:|---:|---:|
{cpu_table}

每图1200步，双方同一Windows原生进程执行，奇偶步交替先后，计时不含状态序列化。每步随后比对全部模拟状态与事件。原版44个辅助脚本完整冻结，只改内部引用位置，没有把优化助手混进旧基线。CPU表来自3600个实际记录，不是渲染帧率。机器仍有其他原生项目任务，未停止用户进程，不能视作独占硬件基准。

六场正常300金币、科技锁定、印垒／木拓镜像、三图、敌方4秒暖机的240秒内对照完成73103步，全状态、金币／法力、研究／订单、命中／死亡、随机流、双方当前及已探索视野、记忆、告警、开火揭示与结果均一致。正常对照范围限于这六场，不是全阵营或200关平衡证明。

## 实际原生画面帧率

| 场景 | 最大单位数 | 均值帧率 | P95帧间隔 |
|---|---:|---:|---:|
{frame_table}

两次压力各20秒，正常场景各160秒；实际Windows编译包、可见窗口、音频开启、自然App60Hz。124演员夹具高生命、AI关闭以持续交锋，独立于真实付费对局。所有本任务的其他导出、复制、哈希与QA完成后串行运行；原始帧CSV、进程环境和截图保留。相邻rc29／rc30压力帧率也受外部负载影响，不将其差值直接归因于本次缓存。手机布局使用Windows渲染，不代表Android手机性能。

普通场景55FPS目标：{frames['normal_55fps_target_met']}；持续满员60FPS目标：{frames['capacity_60fps_target_met']}。本次记录不掩盖未达成目标。

## 验证与素材记录

- 基础源码机制78组195435项在冻结的最终候选中完成，采用后逐项核对运行输入完全一致并保留原报告，未算作第二次执行。另两组独立原版参考完成102920项，合计298355项。
- 实际EXE与APK各36组187249项基础编译逻辑，另各2组102920项新边界检查；每包合计290169项。新检查覆盖全部200图与道路、两侧、实际缓存命中、死亡／改阵营、替换演员、小数精度、路径几何编辑、清场及256条上限。
- APK检查运行Windows原生Godot加载实际提取的GDC；EXE检查读取实际内嵌包。两者字节匹配，未以源码通过替代编译包。Android签名、版本代码30029、16KB对齐、全部22份运行JSON、455项运行资源及1194输入核验。
- 桌面与手机布局12组实际编译包画面对照逐像素一致。战役界面474项、200份固定简介、真实分支选择／重载、八显示配置、200图比例、纸页／军令／迷雾／导航、真实付款命中与默认Vulkan均完成。触摸手势与真人操作范围仍按各报告说明。
- 未生成或替换位图；38项UI沿用用户指定sub2-image-gen／gpt-image-2.5生成版本。剧情与两套字体的1288个CJK字符覆盖按相同输入保留，未声称重新生成或重新测量字体。
- 首次观察器类型推断失败和一场未完成的付款观察超时独立保留；修正工具后使用新目录完成检查。失败／未完成记录未算为通过，也未覆盖成成功。

## 使用与待完成内容

运行WindowsZIP内的PaperWarfront.exe；显卡兼容问题可运行Play-OpenGLCompatibility.cmd。AndroidAPK沿用既有签名，新版可更新同包。单机从战役纸页选择可行动关卡；完成页留下真实证据，未选支线可回访，多证据关按“和”前置解锁。

密集性能、全阵营与全关难度／平衡、原作精确视野时序、真人完整剧情体验、Android真机及真人联机仍待完成；没有可用实体手机，未使用模拟器。当前是预览交付，不标为最终验收。

- [WindowsZIP](../../release/{VERSION}/PaperWarfront-Windows-{VERSION}.zip)
- [WindowsEXE](../../release/{VERSION}/windows/PaperWarfront.exe)
- [AndroidAPK](../../release/{VERSION}/android/PaperWarfront-{VERSION}.apk)
- [发布验证](../../release/{VERSION}/preview-verification.json)
- [SHA256清单](../../release/{VERSION}/SHA256SUMS.txt)

EXE SHA256：`{exe_hash}`；APK SHA256：`{apk_hash}`。证据根为`output/qa/godot/dense-runtime-rc30/`，包级观察位于`release-final/`，原帧率位于`release-final/realtime/`。新修订索引保留稳定ID及全部输入／加工／验证引用；旧rc29与更早交付继续保存其独立版本范围。
"""
DOC.write_text(doc, encoding="utf-8")
note = f"""# 纸上兵戈：十院留名 · {VERSION}

Windows：运行windows/PaperWarfront.exe；显卡兼容问题可使用Play-OpenGLCompatibility.cmd。
Android：安装android/PaperWarfront-{VERSION}.apk；沿用相同签名，版本代码30029。

十章200关配有逐图剧情与真实目标。章内支持择一路线、并行取证、汇合和回访；已完成与未走支线独立保存。战场道路按任务采用单主路、双路或汇流。

本次减少密集交战中的重复寻敌与停驻投影。三个满员场景的同进程模拟耗时降低约9%–10%，六场正常付费对局73103步与完整rc29原版闭包逐步一致。两包各完成基础187249项及新边界102920项，共290169项实际编译逻辑检查。38项折纸UI与72套整身动作沿用已检查素材。

实际Windows原生帧率及完整范围见随包preview-verification.json与项目docs/paper-warfront/139-密集交战缓存与运行复核.md；CPU计时不等于画面FPS。普通场景55FPS目标为{frames['normal_55fps_target_met']}，124单位压力60FPS目标为{frames['capacity_60fps_target_met']}。

当前为预览版。密集性能、全关难度／平衡、真人完整剧情、Android真机与真人互战仍待完成。APK编译逻辑在Windows检查，不是Android硬件验收。许可见licenses/。
"""
(RELEASE / "README.md").write_text(note, encoding="utf-8")
root_note = f"""# 纸上兵戈：十院留名 / Paper Warfront · rc30-preview

当前预览为**rc30**：[密集交战缓存与原生运行复核](docs/paper-warfront/139-密集交战缓存与运行复核.md)。减少重复寻敌、停驻投影与视野读取，三个满员场景同进程模拟耗时降低约9%–10%；六场正常付费对局73103步与完整原版闭包逐步一致。实际帧率与未达成目标在交付记录中单列。

[Windows下载](release/{VERSION}/PaperWarfront-Windows-{VERSION}.zip) · [AndroidAPK](release/{VERSION}/android/PaperWarfront-{VERSION}.apk) · [发布验证](release/{VERSION}/preview-verification.json) · [版本使用说明](release/{VERSION}/README.md)

Godot4.7.2、GDScript、原生ControlUI构建纸片即时策略；保留自动行军、金币／法力、局内科技、手动法术、阵营不对称与横向导航。十院各六种独特作战兵，共60作战兵、10纸工和2召唤物；72个角色均使用36格整身动作。

单机十章200关配有逐图战前冲突、地理动机、真实目标、战后结果与独立证据。章内允许择一、并行调查和齐备后汇合；未走支线保留回访。章内推进图与战场道路独立，不强制全部线性或全部分岔。完整规则及十章路线见[剧情与非线性战役](docs/paper-warfront/138-二百图剧情与非线性战役.md)和[完整故事路线](docs/paper-warfront/world/04-完整故事路线.md)。

普通对战局内可研究本院全部六兵与纸工；战前2–4兵为快速栏选择，明确限制阵容的任务另行显示。战争迷雾统一约束战场、小地图、AI和施法；镜头移动不揭示敌人，上下道路分别侦察。厚纸地层、横向地图比例及各兵体型差继续执行。

菜单、设置、弹窗、军令与兵卡使用用户指定sub2-image-gen／gpt-image-2.5生成并加工的38项折纸资源。战斗时桌面可见战场约83.78%，已测移动配置至少70%；军令纸页按需展开。[素材定义](assets/paper-warfront/ui/paper-ui.json) · [配套UI素材包](release/3.0.0-rc16-preview/PaperWarfront-UIAssets-rc16.zip) · [动作与兵种规范](docs/paper-warfront/frame-rebuild/README.md)。

源码基础78组195435项与额外两组102920项，编译包各基础36组187249项与额外两组102920项通过；实际战役UI474项、八显示配置、200图比例、迷雾／镜头／军令、付款命中、默认Vulkan、六EXE启动及签名／对齐／ZIP记录分别核验。检查数量不代表全关平衡、真人操作或Android性能。

仍待完成：密集性能、全阵营与全关难度／平衡、原作精确视野时序、真人完整剧情体验、Android真机及真人联机。无可用实体手机，不使用模拟器。预算AI实验保持关闭，正式长镰与重锤触及修复继续生效。

[当前文档体系](docs/paper-warfront/README.md) · [Godot工程](game/project.godot) · [素材查看](assets/paper-warfront/frame-rebuild-review.html) · [原作地图研究](docs/research/swords-and-soldiers-map/recheck-20261008/README.md)

历史阶段保留：[rc29剧情与分支](docs/paper-warfront/138-二百图剧情与非线性战役.md) · [rc28查询与资产绑定](docs/paper-warfront/137-密集交战查询与运行资源绑定.md) · [rc27章内分支](docs/paper-warfront/136-单机剧情地图与章内分支.md) · [rc26地图比例与性能](docs/paper-warfront/135-单位地图比例与原生运行性能复核.md) · [rc25前排反制](docs/paper-warfront/134-受控前排反制与科技收益复核.md) · [rc16折纸UI](docs/paper-warfront/122-折纸UI素材与rc16风格调优.md)。旧程序、素材与报告仅证明各自版本。
"""
(ROOT / "README.md").write_text(root_note, encoding="utf-8")
index_path = ROOT / "docs/paper-warfront/README.md"
old_index = index_path.read_text(encoding="utf-8")
old_body = old_index.split("\n", 1)[1].lstrip("\n")
intro = "# 纸上兵戈：十院留名 · rc30-preview\n\n[139-密集交战缓存与运行复核及rc30交付](139-密集交战缓存与运行复核.md)：完整rc29闭包3600满员步与73103正常付费步一致；同进程模拟耗时降低约9%–10%，两包各基础187249项及新边界102920项通过。原生FPS另表记录，剧情与非线性战役继续生效。\n\n最新下载与验收范围以上方139为准。下方均为历史阶段记录，其旧“当前”表述仅适用于对应版本。密集性能、全关平衡／真人体验与Android硬件仍待完成。\n\n"
index_path.write_text(intro + old_body, encoding="utf-8")
(QA / "publication-inputs.json").write_text(json.dumps({"version": VERSION,
    "files": {p.relative_to(ROOT).as_posix(): sha(p) for p in [DOC, RELEASE / "README.md", ROOT / "README.md", index_path]},
    "observations": {n: sha(FINAL / n) for n in ["runner-report.json", "extras-runner-report.json", "realtime/report.json"]},
    "scope": "Local publication text written from completed concrete observations; final artifact audit still performed separately."}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print("Published rc30 notes from completed native observations")
