"""Publish measured rc28 documentation after package and native checks."""
from pathlib import Path
import hashlib
import json
import statistics

ROOT = Path(__file__).resolve().parents[2]
QA = ROOT / 'output/qa/godot/packed-query-rc28'
FINAL = QA / 'release-final'
VERSION = '3.0.0-rc28-preview'
RELEASE = ROOT / 'release' / VERSION
DOC = '137-密集交战查询与运行资源绑定.md'
read = lambda p: json.loads(p.read_text('utf-8'))
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
target = ROOT / 'docs/paper-warfront' / DOC
assert not target.exists(), 'Do not overwrite published revision documentation'
reg = read(QA / 'formal-reach/regression/report.json')
assert reg['passed'] and reg['source_unchanged']
assert len(reg['tests']) == 77 and sum(t['checks'] for t in reg['tests']) == 96606
for platform in ('apk', 'windows'):
    result = read(FINAL / f'{platform}-logic/report.json')
    assert result['passed'] and len(result['tests']) == 35
    assert sum(t['checks'] for t in result['tests']) == 88420
manifest = read(RELEASE / 'build-manifest.json')
proof = read(RELEASE / 'preview-verification.json')
assert proof['source_inputs_verified'] and proof['packed_query_equivalence_verified']
assert all(sha(ROOT / name) == digest for name, digest in manifest['source_inputs'].items())
real = read(FINAL / 'realtime/report.json')
assert real['passed'] and real['version'] == VERSION
capacity = read(QA / 'capacity-axis-original-closure.json')
paid = read(QA / 'paid-axis-original-closure.json')
assert capacity['passed'] and capacity['loaded_source_matches'] and capacity['source_unchanged']
assert paid['passed'] and paid['checks'] == 73103
cpu = '| 地图 | 原版模拟均值 | rc28模拟均值 | 同进程减少 |\n|---|---:|---:|---:|\n'
for map_id in sorted({r['map'] for r in capacity['paired_cpu']}):
    rows = [r for r in capacity['paired_cpu'] if r['map'] == map_id]
    before = statistics.mean(r['baseline_us'] for r in rows) / 1000
    after = statistics.mean(r['candidate_us'] for r in rows) / 1000
    cpu += f'| {map_id} | {before:.3f}ms | {after:.3f}ms | {(before-after)/before*100:.2f}% |\n'
fps = '| 场景 | 单位峰值 | 稳态FPS | P95帧间隔 | 墙钟/模拟时间 |\n|---|---:|---:|---:|---:|\n'
for row in real['cases']:
    label = {'before-stress': 'rc27满员对照', 'stress': 'rc28满员压力',
             'bridge': 'rc28正常分岔', 'long': 'rc28正常长图', 'phone': 'rc28手机布局（Windows）'}[row['case']]
    fps += f"| {label} | {row['max_units']} | {row['fps_from_mean_interval']:.2f} | {row['p95_frame_ms']:.2f}ms | {row['wall_seconds']:.2f}/{row['simulation_seconds']:.2f}s |\n"
text = f'''# 密集交战查询、运行资源绑定与rc28预览

当前双平台预览为 **{VERSION}**。密集交战改用类型明确的查询记录，减少字典读取、重复坐标计算和无效能力查询；三图满员样本在同进程交替计时中减少约8%–10%的模拟CPU耗时。真实帧率单独记录，满员流畅性仍以其实际结果为准。

[Windows压缩包](../../release/{VERSION}/PaperWarfront-Windows-{VERSION}.zip) · [Android APK](../../release/{VERSION}/android/PaperWarfront-{VERSION}.apk)。Android版本号30027、沿用原签名；实体设备尚未验证。

## 剧情地图与玩法约束

[单机剧情地图](136-单机剧情地图与章内分支.md)继续生效：每图的剧情冲突绑定实际道路、任务和完成见证；第一章20关、六组可选路线及汇合、回访、schema3真实完成集合保持原规则。战役解锁图与局内道路图独立，地图和章节均不强求线性。其余180关仍需同等深度叙事扩写，本次没有把它们写成已经完成。

金币/法力、手动施法、实际前摇/命中、生产研究、自动行军和不对称阵营继续由原模拟规则决定。人口上限、60Hz步骤、地图长度、单位比例、采矿动作、粒子、攻受击反馈、完整舞台未知雾幕及70%以上战斗画面没有被降低以换取指标。38项折纸UI与72套36帧全身动作复用已检查的sub2-image-gen/gpt-image-2.5资源，没有新生成位图或变更素材ID。

## 采用的运行实现

| 实现 | 原行为的保留边界 |
|---|---|
| 近战道路记录 | 活对象、float64弧长、原视野次序；路口仍以原精确距离决胜，保留1e-9候选容差 |
| 行军阻挡记录 | 同路前方合法兵体，排除纸工；保留射程/支援规则、转属和阶段出生失效、跃进前锚点 |
| 远程横坐标索引 | 先找原始最近对象，再独立查射程内支援权重；最终仍用原Vector2欧氏距离和原次序 |
| 浮点边界 | 剪枝下界使用原生Vector2长度；禁止用float64绝对横距排除float32等距目标；非有限坐标退回原扫描 |
| 单位步骤 | 类型明确的定义和状态引用；范围按本次调用缓存，状态仍为实时共享字典，结算次序保留 |
| 自动能力 | 无自动生成守卫/分身的定义不再为这两个能力遍历人口；生成者、上限、冷却与随机流保持 |
| 绘制顺序 | 每兵实际高度只算一次；沿用原0.05阈值和uid余数次序，包括阈值附近的非传递比较结果；不改模拟数组 |

远程筛选保留10000初始距离、支援0.35权重、死亡/转属过滤以及矿工body_anchor。超出10000的原始距离仍可能因合法支援权重入选，不能提前全局截断。新增20项刻意边界与1200项绘制排序检查进入源码和两包编译逻辑检查。

## 同进程完整逻辑对照

{cpu}

每图1200个60Hz步骤、124演员，按步骤交替执行原版和候选，独立计时tick调用；不嵌套性能包装器。完整原版44份脚本冻结在`oracle-runtime/`，只重写内部资源引用到独立绝对路径，能力、地图和视野也使用原版闭包；共享数据与冻结基线逐字节相同。完整演员/状态/事件/经济/投射物/视野/探索/随机流共3600步一致。加载后的脚本文本及结束后的输入哈希也通过。

正常付款另做印垒/木拓镜像、短/分岔/长图六场、300金币、科技未解锁、敌方4秒等待；73103个步骤与完整原版闭包一致。该对照证明行为保持，不证明全部阵营已平衡，也不是渲染FPS。

## 实际原生帧率

{fps}

正常样本各160秒，真实App自然推进、窗口可见、音频开启、60FPS上限；桌面默认Vulkan，手机布局为Windows OpenGL注入显示信息。满员夹具每侧直接放入60兵与共4纸工，关闭AI、提高生命值维持负载，不能作为正常付费玩法。稳态排除开始2秒、截图回读及其后0.5秒，CSV、墙钟和模拟时间分别保留。

正常55FPS目标=`{str(real['normal_55fps_target_met']).lower()}`；满员60FPS目标=`{str(real['capacity_60fps_target_met']).lower()}`。本机还有用户其他项目的原生任务，未干预这些进程；不同进程之间的相邻FPS不能据此宣布稳定性能增益。上方同进程CPU对照也不能替代此表的真实帧结果。

## 运行资源与发布输入

构建清单补全运行数据/脚本实际引用的背景、地表、图标、纹样、音乐和导入设置，并绑定场景、UID、字体许可等输入。旧清单只显式列出328项选定文件，实际旧包中的资源仍存在；本次修复的是源输入绑定遗漏，不把旧资源误称缺失。新清单绑定{len(manifest['source_inputs'])}份输入，解析到{proof['runtime_asset_bindings_verified']['resolved_assets']}项运行资源。解析器遵守导出排除规则，未使用的动作源帧不纳入运行引用。

孤立候选曾因复用旧选定清单漏拷贝背景/音乐而产生资源加载错误，该次观察没有合法receipt，已排除性能证据。完整资源候选与旧包12张固定画面对照逐像素一致，正式两包再做12张编译画面对照。早期同进程观察共享候选的能力脚本，最终证据改为完整原版44脚本闭包。曾提前启动的源状态观察、解析失败和采用工具字段校验失败均保存；新采用记录仅引用输入绑定与原版完整闭包通过的证据。

首批导出还暴露了新增边界观察器依赖路径问题：游戏包按规定排除测试脚本，外部观察器需要从自身所在目录加载独立原扫描参考。只修正该preload路径，原失败包/报告保留，20项源码检查重验；76组游戏输入与观察器均未变化的已过记录按哈希保留，最终两包35组分别重新执行。随后将配置中的应用图标也纳入资源解析，正式导出绑定455项实际资源。

## 最终检查与未完成范围

| 范围 | 结果 |
|---|---|
| 源码机制 | 77组96606项，全过 |
| 实际包字节码 | EXE、APK各35组88420项；Windows原生引擎加载真实编译资源 |
| 地图/显示 | 200图22902项，八配置{proof['mobile_checks']}项；至少70%净战场 |
| 原生故事UI | 两布局66项，20份完整简报、分支解锁/回访/保存转换检查 |
| 实际交锋/UI | 研究到首次付款/出仓/命中、前排反制、法术、采矿、军令、焦点、38项折纸UI与六EXE场景检查 |
| APK静态交付 | 签名、包名、版本号、64位资源与16KB对齐通过；不等于Android硬件运行 |

证据根为`output/qa/godot/packed-query-rc28/`，正式包观察在`release-final/`；`pre-adoption/`、冻结候选与原始失败保持可追溯。独立系统修订登记正式资源引用及检查文件哈希。Windows ZIP随附与发布目录相同的验证JSON。

其余180关深度剧情、200关人工平衡、满员稳定流畅、Android实体设备、原作精确视野/时序及真人互战仍未完成。
'''
target.write_text(text, 'utf-8')
summary = f'当前预览为 **rc28**：[密集交战查询与运行资源绑定](docs/paper-warfront/{DOC})。三图同进程模拟耗时减少约8%–10%，3600满员步骤与73103正常付款步骤同原版完整逻辑一致；77组96606项、两包各35组88420项通过。第一章剧情地图与六组分支、单位地图比例、完整舞台迷雾和至少70%战斗画面继续生效。满员真实FPS、后续180关剧情、整体平衡和Android硬件仍待完成。'
p = ROOT / 'README.md'
content = p.read_text('utf-8')
content = content.replace('rc27-preview', 'rc28-preview', 1)
content = content.replace('当前预览为 **rc27**：', 'rc27阶段记录：', 1)
content = content.replace('release/3.0.0-rc27-preview/', f'release/{VERSION}/').replace('PaperWarfront-Windows-3.0.0-rc27-preview.zip', f'PaperWarfront-Windows-{VERSION}.zip').replace('PaperWarfront-3.0.0-rc27-preview.apk', f'PaperWarfront-{VERSION}.apk')
head, rest = content.split('\n', 1)
p.write_text(head + '\n\n' + summary + '\n' + rest, 'utf-8')
p = ROOT / 'docs/paper-warfront/README.md'
head, rest = p.read_text('utf-8').split('\n', 1)
p.write_text(head.replace('rc27-preview', 'rc28-preview') + f'\n\n[密集交战查询与运行资源绑定及rc28交付]({DOC})：77组96606项、两包各88420项，完整原版闭包逐步一致，实测FPS单列。单机剧情地图与分支继续生效，当前下载以本项为准；后续180关剧情、密集性能与Android真机待完成。\n' + rest, 'utf-8')
p = ROOT / 'docs/paper-warfront/11-Godot架构与数据契约.md'
p.write_text(f'rc28运行补充：[密集查询与资源绑定]({DOC})。类型明确的活对象/float64道路记录，原生Vector2筛选及独立支援索引保留精确同距和10000距离边界；渲染缓存高度但不改模拟数组。能力人口查询只为定义中存在的自动生成能力执行。原版完整44脚本闭包与全步骤对照、实际编译包分别记录，模拟CPU与FPS不得混用。\n\n' + p.read_text('utf-8'), 'utf-8')
p = ROOT / 'docs/paper-warfront/16-玩家手册.md'
p.write_text(p.read_text('utf-8').replace('3.0.0-rc27-preview', VERSION, 1), 'utf-8')
(RELEASE / 'README.md').write_text(f'# 纸上兵戈 {VERSION}\n\n[Windows压缩包](PaperWarfront-Windows-{VERSION}.zip) · [Android APK](android/PaperWarfront-{VERSION}.apk)。\n\n'+summary.replace(f'(docs/paper-warfront/{DOC})', f'(../../docs/paper-warfront/{DOC})')+'\n\n源输入、实际运行结果和未完成范围见[检查记录](preview-verification.json)。APK版本号30027，沿用原签名；尚未做实体设备验证。\n', 'utf-8')
print('Final rc28 documentation written')
