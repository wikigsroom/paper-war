"""Publish RC32 only after real artifacts and natural frame checks finish."""
from pathlib import Path
import hashlib
import json
import shutil

ROOT=Path(__file__).resolve().parents[2]
QA=ROOT/"output/qa/godot/contact-runtime-rc32";FINAL=QA/"release-final"
VERSION="3.0.0-rc32-preview";RELEASE=ROOT/"release"/VERSION
DOC=ROOT/"docs/paper-warfront/141-密集寻敌与迷雾查询复核.md"
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text("utf-8"))
assert not DOC.exists() and not (RELEASE/"README.md").exists()
assert read(FINAL/"validation-report.json")["passed"]
manifest=read(RELEASE/"build-manifest.json")
assert manifest["version"]==VERSION and len(manifest["source_inputs"])==1194
assert all(sha(ROOT/n)==d for n,d in manifest["source_inputs"].items())
adoption=read(QA/"adoption.json");assert adoption["passed"]
for platform in ["windows","apk"]:
    primary=read(FINAL/(platform+"-logic/report.json"))
    assert primary["passed"] and sum(r["checks"] for r in primary["tests"])==187249
    for prefix,count in [("dense",102920),("terrain",5873),("answers",640706)]:
        x=read(FINAL/(prefix+"-"+platform+"/report.json"));assert x["passed"] and x["checks"]==count
pixels=read(FINAL/"render-cache/report.json")
assert pixels["passed"] and len(pixels["comparisons"])==12 and all(r["max_channel_delta"]==0 for r in pixels["comparisons"])
frames=read(FINAL/"realtime/report.json");assert frames["passed"] and frames["version"]==VERSION
cpu=read(QA/"cpu-summary.json");assert cpu["passed"] and len(cpu["cases"])==3
cpu_table="\n".join(f"| {r['map']} | {r['original_us']/1000:.3f} ms | {r['candidate_us']/1000:.3f} ms | {r['decrease_percent']:.2f}% |" for r in cpu["cases"])
labels={"before-stress":"rc31满员对照","stress":"rc32满员压力","bridge":"rc32正常分岔","long":"rc32正常长图","phone":"rc32手机布局（Windows）"}
fps_table="\n".join(f"| {labels[r['case']]} | {r['max_units']} | {r['fps_from_mean_interval']:.2f} FPS | {r['p95_frame_ms']:.3f} ms |" for r in frames["cases"])
exe_hash,apk_hash=(r["sha256"] for r in manifest["builds"])
text=f'''# 密集寻敌、迷雾查询复核与rc32预览

本次优化密集部队反复查询最近目标，以及射击短暂暴露／建筑记忆刷新时的演员查找。同进程交替执行原版和候选，三图完整状态逐步一致，模拟耗时降低11.62%–12.61%。该数值来自原生源码CPU对照，实际导出程序帧率单独列出，持续满员60FPS仍按真实结果验收。

## 剧情地图与战役

[200图剧情与十章分支战役](138-二百图剧情与非线性战役.md)继续生效。每张地图有战前冲突、地理动机、实际任务与战后见证；章节允许择一路线、并行调查、齐备汇合和支线回访。战役推进图与局内道路图独立，单路、分岔、汇流按任务选用。道路几何在一场对局内静态，选路改变后续行军选择；换图重新初始化模拟。没有把地图强制改成线性。

本次正式只改battle_sim.gd、battle_visibility.gd和两个导出版本文件；1194输入中的1190份与rc31字节相同。全部200图／剧情／AI／价格／科技／动作／美术／字体／UI和42个其他脚本保持既有内容。38项Sub2折纸UI、72套36格整身动作、单位比例、厚纸地层和全舞台未知区域继续使用原版资源。

## 查询约束

| 情况 | 处理 |
|---|---|
| 不足40单位、建筑阶段或对外调用寻敌 | 执行原查询。缓存只在tick内部的密集同时行军阶段开启。 |
| 可见演员对象、顺序、物理位置、支援分类变化 | 现有精确几何快照失效，清除最近目标答案。道路偏移保持float64，屏幕物理点沿用原生Vector2运算。 |
| 每步的存活／阵营状态变化 | 对可见名单逐项记录当前可攻击状态，清除旧答案；每步只核对一次。 |
| 本步毒伤／寿命到期／死亡连锁 | 真实致死伤害与死亡立即清空答案；命中、反伤和死亡处理仍执行原规则。 |
| 查询者位置、阵营、武器类型、支援优先或范围改变 | 精确比较来源对象和查询参数，当前结果重新计算。 |
| 长对局不断产生UID、开始新对局 | 最多256份来源记录；重开释放记录与诊断计数，阶段外不读取答案。 |
| 射击暴露／记忆刷新含至少四项UID查询 | 本次刷新按单位、建筑、基地原顺序建立第一名存活演员表，只在当前刷新使用。 |
| 重复UID、死演员、非整数UID夹具 | 第一名存活顺序保持；非整数演员UID走原标量查找。死亡射手保留释放位置，改阵营与1.5秒到期继续按原规则清理。 |

先前怀疑的阻挡索引重复重建，经计数确认每步只构建一次，未据此修改阻挡逻辑。第一候选仅优化迷雾UID查找，三图CPU改善1.46%–2.06%；第二候选加入密集寻敌答案，下表为两项组合的实际对照。

## 源码与实际编译逻辑

源码既有78组195435项、新密集阶段21607项、新200图迷雾619103项通过，共836145项断言。另以完整独立冻结的rc31全部44脚本闭包，逐步比较3600满员步与73103正常付款步；演员、事件、金币／法力、状态、弹体、随机流和权威视野一致。完整付费检查包含三图与印垒／木拓镜像，最多240模拟秒，没有把高生命压力夹具当作正常付款。

密集阶段额外覆盖十院全兵种的30组三图原生对照、寿命与致死毒伤、阵营变化、极小位置变化、对象替换／排序、外部实时查询、300来源容量夹具与重开。迷雾额外覆盖所有200图、纸工独立身体锚、死亡／移除、重复与浮点UID、射击到期、关闭迷雾、清场和少量查询门槛。300来源仅验证缓存上限，正式兵员上限没有改变。

EXE和APK各36组187249项基础、两组102920项既有模拟边界、5873项地形、两组640706项新查询边界，共41组936748项。Windows使用实际内嵌GDC；APK提取实际GDC由Windows原生Godot执行，未替换成工作区源码。两包编译脚本绑定一致，版本代码30031、原签名、16KB对齐、22份运行JSON和455项资源核验。

第一次编译观察器直接加载.gdc时触发脚本类型解析错误，已保留失败日志；改走原.gd.remap后错误消失。第二次200图逻辑全通过，但工具仍按44个源码脚本统计，实际导出按原合同排除unit_motion.gd与worker_motion.gd两个旧关节动作助手，只有42份GDC，因此字节发现／不变性检查比源码少4项。第三次使用正确映射和真实42份编译脚本集合，完整检查通过。失败观察器与统计错误没有计入最终通过数，游戏／导出字节未为这些工具修订而更改。

桌面／手机12组编译画面对照逐像素相同；200图比例、八显示配置、474项真实战役UI／选择／存档、军令纸页、迷雾、镜头、正常付款与命中、默认Vulkan和六次EXE启动各自完成。200图原稿与1288个CJK字形覆盖证据明确沿用且绑定到相同数据，不冒充新叙事创作或真机测试。

## 同进程模拟计时

| 地图 | 原版每步均值 | 候选每步均值 | 降低 |
|---|---:|---:|---:|
{cpu_table}

每图1200步，在同一Windows原生进程交替先后执行；JSON状态比较不计入耗时，没有嵌套计时器。124名高生命演员和关闭AI用于持续交战，不能推断整体胜率或实际FPS。早期候选／诊断、所有输入与观察器分别冻结保留。

## 实际导出程序帧率

| 场景 | 单位峰值 | 均值帧率 | P95帧间隔 |
|---|---:|---:|---:|
{fps_table}

压力20秒、正常场景160秒，真实Windows可见窗口、声音开启、自然App处理。自己的导出／复制／哈希和其他QA结束后串行采样；其他用户项目进程未停止。保留原帧CSV与截图，相邻版本观察不能直接当作因果增益。候选源码另记录约31.3→34.4FPS，仅属于该次源码自然窗口观察；正式程序以本表为准。手机布局仍在Windows运行。

普通55FPS目标：{frames['normal_55fps_target_met']}；持续满员60FPS目标：{frames['capacity_60fps_target_met']}。密集性能、全阵营／全关平衡、原作精确视野时序、真人完整剧情、Android实体设备及真人联机仍待完成。没有可用Android手机，未使用模拟器。

## 下载与复核

Windows解压后运行PaperWarfront.exe；兼容渲染可运行Play-OpenGLCompatibility.cmd。Android沿用原签名，可更新同包。

- [WindowsZIP](../../release/{VERSION}/PaperWarfront-Windows-{VERSION}.zip)
- [WindowsEXE](../../release/{VERSION}/windows/PaperWarfront.exe)
- [AndroidAPK](../../release/{VERSION}/android/PaperWarfront-{VERSION}.apk)
- [发布验证](../../release/{VERSION}/preview-verification.json)
- [SHA256清单](../../release/{VERSION}/SHA256SUMS.txt)

EXE SHA256：`{exe_hash}`；APK SHA256：`{apk_hash}`。证据根为output/qa/godot/contact-runtime-rc32/。旧rc31与更早程序、规范、工具及证据保持独立版本记录。
'''
DOC.write_text(text,"utf-8")
(RELEASE/"README.md").write_text(text.replace('](../../release/'+VERSION+'/','](').replace('](138-二百图剧情与非线性战役.md)','](../../docs/paper-warfront/138-二百图剧情与非线性战役.md)'),"utf-8")
entry="[141-密集寻敌与迷雾查询复核及rc32交付](141-密集寻敌与迷雾查询复核.md)：200图剧情与分支继续生效；完整rc31闭包3600满员步和73103付费步一致，三图同进程模拟约降低12%；源码836145项，两包各936748项，实际帧率和待完成项见本项。"
backup=QA/"pre-publication";assert not backup.exists()
for n in ["README.md","docs/paper-warfront/README.md"]:
    p=ROOT/n;dest=backup/n;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest)
    old=p.read_text("utf-8")
    if n=="docs/paper-warfront/README.md":
        lines=old.splitlines();old=old.replace(lines[0],"# 纸上兵戈：十院留名 · rc32-preview",1)
        head,tail=old.split("\n",1)
        old=head+"\n\n"+entry+"\n\n最新下载与验收范围以141为准。以下保留历史阶段记录。\n"+tail
    else:
        if old.startswith("# "):old=old.split("\n",1)[1].lstrip()
        old="# 纸上兵戈：十院留名 · rc32-preview\n\n"+entry.replace('](141-','](docs/paper-warfront/141-')+"\n\n以下保留各历史阶段记录，最新下载与验收范围以141为准。\n\n"+old
    p.write_text(old,"utf-8")
files=[DOC,RELEASE/"README.md",ROOT/"README.md",ROOT/"docs/paper-warfront/README.md"]
(QA/"publication.json").write_text(json.dumps({"passed":True,"version":VERSION,"files":{p.relative_to(ROOT).as_posix():sha(p) for p in files},
    "scope":"Published only after completed actual exports, native compiled state/UI/render and serial natural FPS; current200-map story retained, dense60FPS and hardware/balance/human review remain pending."
},ensure_ascii=False,indent=2)+"\n","utf-8")
print("Published RC32 verified preview notes")
