"""Describe the final measurements without promoting integrity into FPS claims."""
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[2]
QA=ROOT/'output/qa/godot/realtime-performance-rc26'
VERSION='3.0.0-rc26-preview'
read=lambda p:json.loads(p.read_text('utf-8'))
real=read(QA/'release/realtime/report.json')
assert real['passed'] and real['version']==VERSION
rows={r['case']:r for r in real['cases']}
reg=read(QA/'formal-reach/regression/report.json')
assert reg['passed'] and reg['source_unchanged']
paid=read(QA/'paid-runtime-equivalence.json');assert paid['passed']
for platform in ['apk','windows']:assert read(QA/f'release/{platform}-logic/report.json')['passed']
table='| 场景 | 实际单位峰值 | 稳态 FPS | P95 帧间隔 | 墙钟 / 模拟时间 |\n|---|---:|---:|---:|---:|\n'
for name,label in [('before-stress','rc25 满员压力'),('stress','rc26 满员压力'),('bridge','rc26 正常分岔图'),('long','rc26 正常长图'),('phone','rc26 手机布局正常分岔图')]:
 r=rows[name];table+=f"| {label} | {r['max_units']} | {r['fps_from_mean_interval']:.2f} | {r['p95_frame_ms']:.2f} ms | {r['wall_seconds']:.2f} / {r['simulation_seconds']:.2f} s |\n"
before=rows['before-stress']['fps_from_mean_interval'];after=rows['stress']['fps_from_mean_interval']
doc=f'''# 单位与地图比例、运行缓存与 rc26 交付

当前双平台预览为 **{VERSION}**。单位/地图比例、厚纸地层和完整舞台迷雾继续使用已核验的 rc21 呈现；rc26 减少密集队伍的目标查询、友军间距和重复绘制开销。正常付费对局的战斗与视野权威逐步一致。满员压力帧率从本轮相邻复测的 {before:.2f} 提升至 {after:.2f} FPS，**仍未达到流畅目标**。

[Windows 压缩包](../../release/{VERSION}/PaperWarfront-Windows-{VERSION}.zip) · [Android APK](../../release/{VERSION}/android/PaperWarfront-{VERSION}.apk)。Android 真机和整体平衡仍未验收。

## 单位、地图和画面占比

| 项目 | 调整后的实际约束 |
|---|---|
| 横向投影 | 每世界单位 112 逻辑像素；42 单位短图约 2.94 个标准视窗，旧比例约 2.05 |
| 普通兵体型 | 高度 1.42 的兵约 124.05 逻辑像素，在1280宽桌面约99.24像素，较旧比例缩小约17% |
| 厚地层 | 地表以下150.8逻辑像素，1280宽桌面约121像素；分层土纸、根系、石块与纸边阴影 |
| 手机辨识 | 普通兵至少60dp、纸工52dp；巨型兵保留约40.8%的高度差 |
| 战场占比 | 桌面83.78%；八显示配置与实际编译UI均保持至少70%，移动配置约70.62%–80.95% |
| 规则尺度 | 实际道路长度、速度、射程、视野、金币、法力、生产和研究时间保持原定义 |

比例和规则分开管理。横向导航仍覆盖完整道路，桥路、坡道、矿路和分岔仍使用同一地图锚点；完整舞台未知雾幕、各路当前视野和历史探索继续区分。地图比例检查覆盖200张地图，共22,902项；八种显示配置26,779项通过。

## 本次采用的实现

1. 近战候选按道路弧长索引。查询只在同步单位阶段使用固定的移动前几何；阵亡和转属仍读取实际对象。路口附近的浮点等距候选先宽松收集，再用原有精确距离及视野列表次序决胜。异常弧长回到原扫描。
2. 同路友军按弧长查询最近的合法阻挡者。纸工穿越己方军队、前排间距、长射程后排通行、巨型兵间距和阶段中新生单位规则保留。道路分组在阶段/转属/出生时失效；异常弧长使用原扫描。
3. 远程查询复用本阶段可见敌军的物理坐标，保留原顺序、真实欧氏距离和支援优先级。视野刷新、施法和新阶段重新建立记录；渲染坐标和屏幕横坐标不能充当判定坐标。
4. 静态地层填充复用三角网格；地图、逻辑尺寸、地表基线或投影变化重新建立。摄像机只更新变换，土纹UV沿用世界坐标。雾幕、可见敌军和动态动作独立更新。
5. 阴影、保护和寒冷状态椭圆复用24点网格。全身动作读取已检查的36帧图集，直接传入前摇时间，减少每帧配置复制。

没有采用演员编号索引、静态绘制命令回放或远程空间树：当前样本未带来明确收益。早期近战索引在路口浮点舍入的同距排序上存在反例，已保留负例并由最终精确次序修复。所有已完成报告和关键阶段源文件快照保留，rc25资产与发布记录保持原版本。

## 实际原生帧率

{table}

上述为相邻串行 Windows 原生观察，i5-12400F / RTX3060；桌面默认 Vulkan Forward Mobile，手机布局为 Windows OpenGL 注入显示配置。正常场景各观察160秒，300金币、未解锁科技、敌方4秒开局等待，西侧明确作为AI自动操作。窗口可见、声音开启，真实 App._process 推进60Hz模拟；没有手动加速推进。

满员压力为直接放入每侧60名作战单位，保留4名纸工、关闭AI并给予100000生命值，以维持负载，**不能当作正常付款玩法或平衡证据**。稳态FPS来自单调时钟帧间隔，排除开始2秒以及PNG回读与其后0.5秒；墙钟和模拟时间保留截图停顿。观察器和每秒记录仍有开销，当前桌面环境并非独占硬件实验室。

正常55FPS目标：`{str(real['normal_55fps_target_met']).lower()}`；满员60FPS目标：`{str(real['capacity_60fps_target_met']).lower()}`。捕获和哈希校验成功与帧率达标分别报告。纹理分配峰值由运行监测记录；压力样本约{rows['stress']['max_texture_bytes']/1048576:.2f}MiB，不等于整个进程内存或显存总占用。

Godot4.7的TIME_PROCESS是上一统计区间的峰值，约每秒更新，不能当作逐帧App CPU时间。本轮使用继承实际App/View方法的包装计时；绘制计时仅表示CPU提交命令。早期报告解释更正单独追加，未覆盖原始证据。[Godot官方主循环源码](https://github.com/godotengine/godot/blob/4.7/main/main.cpp) / [Performance文档](https://docs.godotengine.org/en/stable/classes/class_performance.html)。

## 行为和画面验收

| 范围 | 结果 |
|---|---|
| 正式机制 | 73组、87,810项；道路目标58,576项，同路间距13,600项均含200图双侧边界 |
| 逐步完整战斗 | 十院、三种图、混编7200步；最终候选状态与旧线性算法一致 |
| 正常付费AI | 三图、印垒/木拓镜像六场，{paid['checks']:,}步；经济、科技、事件、视野和随机数逐步一致 |
| 实际编译包 | Windows与APK各31组79,624项，在Windows原生引擎加载实际包中字节码 |
| 前后画面 | 两尺寸、三图、两处含小数的镜头位置，12组通过；11组最大单通道差1，手机桥图一组仅2个像素差超过2 |
| 行军与反制 | 正常付费镜像50项；OpenGL桌面/手机64项；默认Vulkan32项，实际订单/出仓/命中通过 |
| UI和素材 | 实际编译军令、纸页、焦点、触控、六EXE场景通过；38项折纸UI与APK纹理一致，72套全身动作3263项通过 |

两处验收工具问题也已归档：动作帧测试的空失败输出格式误判；编译UI观察提前于APK依赖报告启动。修正格式识别和依赖顺序后，保留同一包的通过记录，只重跑受影响检查。原始失败报告及完成补充报告并存。

本轮复用用户指定sub2-image-gen / gpt-image-2.5已检查的图集和折纸素材，没有生成新图。源图、稳定ID和生成版本保留；运行优化登记为独立系统修订。生成图不承担运行证据。

## 证据与未完成范围

证据位于 `output/qa/godot/realtime-performance-rc26/`；发布清单为 `release/{VERSION}/build-manifest.json`。`release/realtime/report.json`绑定真实帧CSV与截图；`release/render-cache/report.json`绑定旧/新实际编译包的像素对照；`paid-runtime-equivalence.json`记录正常付款逐步对照。

后续重点仍是高密度模拟和绘制预算、实际Android硬件帧率与触控、完整阵营平衡，以及原作精确视野/时序的继续对照。当前未声称这些项目已经完成，也没有减少模拟频率、隐藏单位数量或降低原图帧数来替代优化。
'''
path=ROOT/'docs/paper-warfront/135-单位地图比例与原生运行性能复核.md';path.write_text(doc,'utf-8')
p=ROOT/'README.md';s=p.read_text('utf-8');s=s.replace('· rc25-preview','· rc26-preview',1).replace('当前双平台预览为rc25：','rc25阶段记录：',1)
s=s.replace('release/3.0.0-rc25-preview','release/3.0.0-rc26-preview').replace('PaperWarfront-Windows-3.0.0-rc25-preview.zip','PaperWarfront-Windows-3.0.0-rc26-preview.zip').replace('PaperWarfront-3.0.0-rc25-preview.apk','PaperWarfront-3.0.0-rc26-preview.apk')
title,tail=s.split('\n',1)
intro=f'\n当前预览为 **rc26**：[单位/地图比例与原生运行性能复核](docs/paper-warfront/135-单位地图比例与原生运行性能复核.md)。加厚地层、缩小普通兵和扩展横向画面的比例继续落实；静态纸层/阴影与战斗查询减少重复开销，六场正常AI {paid["checks"]:,}步逐步一致，两包各79,624项。相邻编译包满员压力 {before:.2f}→{after:.2f}FPS，仍待优化；正常场景与手机布局实测见135。Android真机和整体平衡仍未完成。\n'
p.write_text(title+'\n'+intro+tail,'utf-8')
p=ROOT/'docs/paper-warfront/README.md';s=p.read_text('utf-8').replace('· rc25-preview','· rc26-preview',1)
s=s.replace('当前下载以本项为准','本项保留rc25记录，当前下载以上方135为准',1)
title,tail=s.split('\n',1);p.write_text(title+'\n\n[单位地图比例与原生运行性能复核及rc26交付](135-单位地图比例与原生运行性能复核.md)：73组87,810项，两包各31组79,624项；六场正常付费逐步一致，200图和八显示配置通过，12组实际编译包画面对照通过。原生帧CSV分开记录正常对局与满员压力，后者仍未达到流畅目标；当前下载以本项为准。\n'+tail,'utf-8')
p=ROOT/'docs/paper-warfront/11-Godot架构与数据契约.md';s=p.read_text('utf-8');p.write_text('rc26运行补充：[规则不变的道路查询与纸层缓存](135-单位地图比例与原生运行性能复核.md)。近战弧长候选和同路阻挡索引限定于同步单位阶段，原精确距离/次序、转属/阵亡过滤与异常回退保留；远程缓存保持当前可见对象原顺序，刷新视野和新阶段重建。`theatre_ground_cache`仅缓存静态填充网格，地图/投影/布局变化失效；阴影网格与全身动作计时复用，雾幕独立更新。325项发布源输入、两包编译逻辑和真实墙钟帧分别绑定。正常AI逐步一致，满员FPS与Android硬件仍未达成完整验收；当前交付以135为准。\n\n'+s,'utf-8')
p=ROOT/'docs/paper-warfront/16-玩家手册.md';s=p.read_text('utf-8').replace('3.0.0-rc25-preview','3.0.0-rc26-preview',1);title,tail=s.split('\n',1);p.write_text(title+'\n\n普通兵与长卷地图采用更舒展的比例，厚土纸层帮助辨识地表、桥面和上下路。未知区域覆盖整个舞台；拖动镜头只改变观看位置，部队侦察才会展开地图。手机仍保留可辨识的兵体与至少70%的战场区域。满员密集场景帧率仍在优化，Android真机性能尚未验证。\n'+tail,'utf-8')
release=ROOT/f'release/{VERSION}'
(release/'README.md').write_text(f'# 纸上兵戈 · {VERSION}\n\n[Windows压缩包](PaperWarfront-Windows-{VERSION}.zip) · [Android APK](android/PaperWarfront-{VERSION}.apk) · [详细实现与验证](../../docs/paper-warfront/135-单位地图比例与原生运行性能复核.md)\n\n单位/地图比例、厚纸地层与全舞台迷雾继续落实；战斗查询与静态绘制减少重复开销。规则、实际金币与60Hz模拟保持原定义。73组87,810项；两包各31组79,624项；200图/八显示配置、12组画面对照与实际付费命中通过。\n\n'+table+'\nWindows原生RTX3060测量；手机行是Windows注入布局，不是Android真机。满员为AI关闭、双方各60作战兵及4纸工、高生命维持负载的压力夹具，仍未达到流畅目标。Android硬件、整体平衡与原作精确视野时序待进一步验收。\n\n实际包启动、签名、16KB对齐、编译逻辑和SHA清单随发布记录提供；资料和原始失败样本保留在工作区。\n','utf-8')
print('rc26 docs updated from final receipts')
