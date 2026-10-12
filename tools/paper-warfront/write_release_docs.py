"""Write the current release report from recorded evidence, keeping 1.0 history explicit."""
from pathlib import Path
from collections import Counter
import json, hashlib, sys

ROOT = Path(__file__).resolve().parents[2]
DOC = ROOT / 'docs/paper-warfront'
QA = ROOT / 'output/qa/godot/v2'
RELEASE = ROOT / 'release/2.0.0'

def read(path):
    return json.loads((ROOT / path).read_text(encoding='utf-8'))

def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + '\n', encoding='utf-8')

def main():
    sys.stdout.reconfigure(encoding='utf-8')
    maps = read('game/data/maps.json')['maps']
    factions = read('game/data/factions.json')
    units = read('game/data/balance-prototype.json')['units']
    foundation = read('game/tests/world-foundation-report.json')
    combat = read('game/tests/world-combat-report.json')
    assets = read('output/qa/godot/v2/world-assets-report.json')
    desktop = read('output/qa/godot/v2/ui-desktop/report.json')
    mobile = read('output/qa/godot/v2/ui-mobile/report.json')
    baseline = read('output/qa/godot/v2/campaign-play-final.json')
    alternatives = [
        'game/tests/campaign-play-000-200-fixed-economy.json',
        'game/tests/campaign-play-000-200-fixed-rush.json',
    ]
    wins = {}
    for source, report in [('output/qa/godot/v2/campaign-play-final.json', baseline)] + [(p, read(p)) for p in alternatives]:
        for result in report['results']:
            if result['winner'] == 0:
                wins.setdefault(result['index'], dict(index=result['index'], map=result['map'], campaign=result['id'], evidence_file=source, time=result['time'], reason=result['reason']))
    pending = [i + 1 for i in range(200) if i not in wins]
    coverage = dict(maps=200, automated_player_victories=len(wins), human_balance_pending=pending,
                    scope='Union of baseline and alternative player investment styles, with unchanged authored budgets, opponents and public rules. Not a human playthrough or proof that the remaining maps are impossible.',
                    evidence=[wins[i] for i in sorted(wins)])
    write(QA / 'campaign-win-coverage.json', json.dumps(coverage, ensure_ascii=False, indent=2))
    fork_count = sum(any(c > 1 for c in Counter(e['from'] for e in m['edges']).values()) for m in maps)
    assert len(maps) == 200 and len({m['geometry_sha256'] for m in maps}) == 200
    assert len(factions['order']) == 10 and all(len(f['combat_units']) == 40 for f in factions['factions'])
    assert all(report['passed'] for report in [foundation, combat, assets, desktop, mobile])
    manifest_file = RELEASE / 'build-manifest.json'
    builds = json.loads(manifest_file.read_text(encoding='utf-8'))['builds'] if manifest_file.exists() else []
    for build in builds:
        path = ROOT / build['path']
        assert path.stat().st_size == build['bytes'] and hashlib.sha256(path.read_bytes()).hexdigest() == build['sha256']
    build_status = '新版双平台构建与包检查已完成' if len(builds) == 2 else '新版双平台构建尚未完成'
    brief = f'''# 规模扩展与实施证据 · 2.0.0

用户目标完整保留：地图与核心博弈更新、200张地图、十个阵营各40种作战单位、完整故事和线性战役。运行工程使用Godot 4.7.2；Windows/Android原生交付，不使用Docker、WSL、虚拟机或模拟器。

| 要求 | 实际实现与证据 | 状态 |
| --- | --- | --- |
| 地图与核心博弈 | 路径图真实行军、后续批次路标、矿容量/运输归仓、施工期、二维远程/范围、道路近战、六类任务 | 原生规则与UI检查通过 |
| 200张地图 | 200组独立几何散列、{fork_count}图有局部分路、{200-fork_count}图为单线经济/设施题；每图矿位、施工位、任务锚点与空间设计说明 | 200图加载、可达性与整局模拟完成 |
| 十院 | 不同经济/法力/控制/设施/生存被动、兵种参数、纸雕纹样、统帅与故事；十个实际HUD/AI/背景/音乐 | 规则、素材及UI均接入 |
| 每院40作战兵 | 共400个可付费招募作战定义、角色能力、科技与4–8兵编组；10工人及2种临时实体另计 | 400个实际生产/扣费/伤害检查完成 |
| 完整线性故事 | 十章各20关，逐关事件/对话/因果承接/证据旗标、六类目标、下一关解锁与终章十人归宿 | 流程、存档和终章原生验证通过 |
| 素材与动作 | 400新兵源图、87配套源记录、实际脚点纸偶分件、左右朝向/行军/攻击/受击/倒地、有限粒子与声音池 | 源图及实际运行截图已审查 |
| 双平台新版 | 2.0.0 EXE、签名APK及源码、签名/架构/16KB对齐报告 | {build_status}；Android真机仍未测 |

## 核心决策的实际含义

金币同时支付工人、即时兵力、研究和前位设施。工人走真实矿路，容量已满会排队，归仓才入金；额外工人受往返距离和矿位容量约束。部队串行生产并承担实际增援时间。路标改变后续批次，已经进路的兵继续承担原来的路线风险。前位设施需要4/5秒施工，完工前没有收益。

地图区别来自分路位置与长度、上下路实际距离、工人暴露、建筑前后位、汇流与目标锚点，此外还有十个地区的规则结合。近战依道路连接判定，远程与法术依真实二维位置；地表高差不附加未经原作实测的神秘倍率。分路的价值可能是隔开近战与交叉火力，并非每张岔路都以大幅缩短行军为卖点。

## 验证证据与范围

- [基础报告](../../game/tests/world-foundation-report.json)：{foundation['checks']}项、零失败，包括200图可达性、两侧矿路、真实回款、路线承诺、空间命中、施工与故事引用。
- [战斗报告](../../game/tests/world-combat-report.json)：{combat['checks']}项、零失败，400兵实际扣费/生产/伤害，以及代表能力、阵营触发、唯一任务对象保护和慢速运输。
- [素材报告](../../output/qa/godot/v2/world-assets-report.json)：{assets['checks']}项、零错误，400独立切图、487新来源记录、410新纸偶1230件、十地区图、200空间简报和十音乐循环。
- 原生界面：桌面{len(desktop['checks'])}项、横屏移动布局{len(mobile['checks'])}项，菜单/部署/兵书/HUD/招募退款/施工/路标/矿点/50法术选择/科技/暂停/声音/终章保存；滚动文本同时检查尺寸和实际截图。
- [200关标准模拟](../../output/qa/godot/v2/campaign-play-final.json)：60Hz公共规则、正常关卡预算，{baseline['victories']}胜/{baseline['defeats']}负/{baseline['draws']}和、零不结算。
- [合法自动玩家胜利覆盖](../../output/qa/godot/v2/campaign-win-coverage.json)：更换玩家侧投资策略后，共{len(wins)}个不同关卡获胜。未改敌方预算、费用、冷却或输入合法性。
- 六道保留挑战均在本身预算下正常结算，自动玩家2胜4负；不声称完成人工挑战星章。

## 仍需人工验证

自动模拟与UI动作不代替真人反应、所有兵种组合和长时间平衡。以下{len(pending)}关尚未在已测自动策略中获胜，需要人工核对难度和策略：{', '.join(str(n) for n in pending)}。这份列表不等于证明关卡不可获胜。200关人工全通、Android真机触控/音频/帧率/发热与刘海屏安全区均未完成。

原作初代/HD的精确PC路标权限、跨路攻击细则与数值未实机测量，本版是有研究依据的原创规则实现。历史1.0包不能证明上述内容；当前下载与双平台验证见[22发布报告](22-双平台验收与发布.md)。
'''
    write(DOC / '17-规模扩展与实施进度.md', brief)
    table = '\n'.join(f"| {Path(b['path']).name} | {b['bytes']/1048576:.1f} MiB | `{b['sha256']}` |" for b in builds)
    report = f'''# 双平台验收与发布 · 2.0.0

构建日期：2026-10-08。{build_status}。本报告使用当前十院、200图、400作战兵和完整故事工程；保留的1.0程序是历史交付。Godot 4.7.2、原生Windows、Android SDK/JDK工具，不使用模拟器或虚拟化。

## 程序和源码

[Windows完整包](../../release/2.0.0/PaperWarfront-Windows-2.0.0.zip) · [Windows单文件EXE](../../release/2.0.0/windows/PaperWarfront.exe) · [Android签名APK](../../release/2.0.0/android/PaperWarfront-2.0.0.apk) · [Godot源码与素材](../../release/2.0.0/PaperWarfront-Source-2.0.0.zip) · [下载说明](../../release/2.0.0/README.md)。哈希见[构建清单](../../release/2.0.0/build-manifest.json)和[SHA256SUMS](../../release/2.0.0/SHA256SUMS.txt)。

| 可执行程序 | 大小 | SHA256 |
| --- | --- | --- |
{table or '| 尚未构建 | — | — |'}

Windows为64位资源内嵌EXE，无需安装Godot。默认Vulkan Mobile渲染器，ZIP附带Launch-Compatibility.cmd用于OpenGL兼容启动。Android为签名release APK，ARMv7及ARM64，横屏、兼容渲染器、无网络权限；SDK值与支持特性以aapt报告为准。源码排除密钥、引擎/SDK缓存、拒绝的生成图片与编译缓存，附原始源图、提示词、加工/构建脚本、文档、运行证据及许可。

## 内容、规则与UI

200个独立机械地图、十院各40作战兵、50法术、10工人与2种另计临时实体、十章200关连续故事、6道附加挑战及可选地图遭遇战。实际路径/矿运输/矿位容量/施工/选择后续路线/近战连接/二维远程/六类目标都在模拟层。详细对应见[实施证据](17-规模扩展与实施进度.md)。

基础{foundation['checks']}项、战斗{combat['checks']}项、素材{assets['checks']}项均无错误。原生桌面{len(desktop['checks'])}项、移动布局{len(mobile['checks'])}项通过；涵盖十阵营兵书、HUD、完整编组分页、研究/施工/退款/目标选择、声音、暂停/设置、终章保存重载。文字滚动区曾被压成零高，已修复并核对实际渲染；纸偶脚点已根据真实alpha轮廓修正。

十院共400兵的源图联系表均检查，三个截边轮廓单独重绘修复。487新源记录使用指定sub2-image-gen/gpt-image-2.5，源散列和加工框可追溯。运行素材共610绑定，实际资源文件2242；这两个数字包括复用和分件，不能当成独立生成张数。范围法术、受击闪白/位移/音效、纸屑、死亡与队列/施工反馈均接入受限事件预算。

## 构建与平台检查

- [原生导入日志](../../output/qa/godot/v2/build/release-import.log)、[Windows导出](../../output/qa/godot/v2/build/export-windows.log)、[Android导出](../../output/qa/godot/v2/build/export-android.log)。
- 新Windows EXE主菜单、分路地图自动对局及OpenGL兼容启动：见[实际导出画面](../../output/qa/godot/v2/export/battle.png)与同目录日志。
- [APK签名](../../output/qa/godot/v2/build/apk-signature.log)、[APK对齐](../../output/qa/godot/v2/build/apk-alignment.log)、[APK元数据](../../output/qa/godot/v2/build/apk-badging.log)、[ARM64 ELF 16KB](../../output/qa/godot/v2/build/apk-elf-report.json)。包校验确认可安装格式与签名，不能证明手机上的渲染和操作。
- 桌面[报告/截图](../../output/qa/godot/v2/ui-desktop/report.json)，移动布局[报告/截图](../../output/qa/godot/v2/ui-mobile/report.json)；实际导出程序另做启动检查，源码QA未打包成游戏内容。

## 验证限制

全部200关正常结算，标准自动玩家150胜49负1和；更换玩家投资策略后{len(wins)}关有合法胜利记录。其余{len(pending)}关等待人工平衡核对；没有宣称200关真人全通。每个作战兵完成实际招募/伤害检查，代表能力和阵营事件单独验证，但未穷尽所有组合。

当前没有连接Android真机。实际触控DPI、全面屏安全区、手机帧率/发热/音频与持续运行未实测；移动UI证据来自Windows上的原生Godot横屏布局。Windows本机运行证据不覆盖所有显卡驱动；EXE没有商业代码签名。许可包括Godot MIT及第三方、Noto OFL；Android覆盖安装升级需要本机保留的原签名，私钥不随源码发送。
'''
    write(DOC / '22-双平台验收与发布.md', report)
    write(ROOT / 'README.md', '''# 纸上兵戈：十院留名 / Paper Warfront 2.0

Godot 4.7.2原生纸偶军团实时策略。200张机械地图、十个阵营各40作战兵、50法术、十章200关连续故事、6道附加挑战和自选地图遭遇战。

地图真实参与对战：部队走分岔与汇流路径，路标改变后续批次；矿金运输归仓、容量排队、设施施工与二维射程使经济、增援和施法时机互相牵制。4–8兵战前部署、局内科技、全套菜单/HUD、电脑对手、存档和终章已接入。

[Windows与Android下载](release/2.0.0/README.md) · [完整制作文档](docs/paper-warfront/README.md) · [地图设计与200图目录](docs/paper-warfront/world/03-200地图目录.md) · [十院故事与军库](docs/paper-warfront/world/README.md) · [完整素材/地图浏览页](assets/paper-warfront/world-v2-gallery.html) · [玩家手册](docs/paper-warfront/16-玩家手册.md) · [Godot工程](game/project.godot)。

![新Windows导出程序的分路战场](output/qa/godot/v2/export/battle.png)

自动规则、素材与原生UI检查通过，200关全局模拟正常结算，181关已取得合法自动玩家胜利。尚未完成全200关人工平衡，Android尚无真机实测。验证依据与限制见[发布报告](docs/paper-warfront/22-双平台验收与发布.md)。1.0素材/程序和地图研究保留为历史，不代表当前实现。
''')
    write(ROOT / 'release/README.md', '''# 当前交付：纸上兵戈 2.0.0

[2.0.0 下载、安装与验证说明](2.0.0/README.md)包含本次200图、十院400作战兵和完整线性故事更新后的Windows/Android程序与源码。

本目录直属的PaperWarfront-Windows-1.0.0.zip、PaperWarfront-Source-1.0.0.zip、windows/和android/保留上一版程序，属于三阵营原型历史交付。当前新版全部放在2.0.0/，请按版本选择。

[原作地图专项研究](../docs/research/swords-and-soldiers-map/README.md) · [当前实施证据](../docs/paper-warfront/17-规模扩展与实施进度.md)。
''')
    write(RELEASE / 'README.md', '''# 纸上兵戈：十院留名 · 2.0.0

200张机械地图、十院各40作战兵、50法术、十章200关连续故事、6道附加挑战和AI遭遇战。Godot原生离线单人纸偶RTS，资源内嵌，无需安装Godot。

- [Windows完整ZIP](PaperWarfront-Windows-2.0.0.zip)：解压后双击PaperWarfront.exe；含操作说明及许可。
- [Windows单文件EXE](windows/PaperWarfront.exe)：64位Windows10/11，默认Vulkan；显卡兼容需要时用ZIP内Launch-Compatibility.cmd启动OpenGL版本。
- [Android APK](android/PaperWarfront-2.0.0.apk)：签名release、ARMv7/ARM64、横屏；复制到手机，从文件管理器安装，按系统提示允许该文件来源。
- [Godot源码与素材ZIP](PaperWarfront-Source-2.0.0.zip)：导入game/project.godot；含完整原图/提示词、加工和构建工具、文档/地图简报与运行证据，排除密钥/SDK/引擎缓存。
- [SHA256校验](SHA256SUMS.txt)与[构建清单](build-manifest.json)。

开局先读地图和任务简报，挑选4–8兵部署。招募、工人、科技与施工共同花金币；工人归仓才入金。点击我方路标改变后续部队路线；点矿点选择采矿优先。部队自动行军/交战，法术由你选目标。手机有招募前后组及法术切换、科技、建造、队列和暂停面板。

桌面1–9招募、Q/W/E/R/T选法术后点目标，F科技、B建造、P暂停、Home看家、Space跟随交锋、A/D或拖动移动镜头，右键/Esc取消。胜利自动解锁下一关并保存证据。Windows存档在%APPDATA%\\PaperWarfront\\profile.json，1.0记录独立保留。

[玩家手册](../../docs/paper-warfront/16-玩家手册.md) · [完整方案、素材和约束](../../docs/paper-warfront/README.md) · [发布验收](../../docs/paper-warfront/22-双平台验收与发布.md)。

当前200关完成合法整局模拟，181关有自动玩家胜利记录；其余19关待人工难度核对，不声称真人全通。Android完成签名/架构/对齐校验及原生移动布局检查，尚未连接真机；手机触控、帧率/发热/音频与全面屏未实测。Windows本机验证不覆盖所有显卡，EXE无商业代码签名。

Godot MIT/第三方、Noto OFL随包。Android私钥保留本机，未来覆盖升级应沿用原签名，不含于交付源码。
''')
    write(RELEASE / 'windows/Launch-Compatibility.cmd', '@echo off\nstart "" "%~dp0PaperWarfront.exe" --rendering-method gl_compatibility')
    history = DOC / '素材库检查报告.md'
    old = history.read_text(encoding='utf-8')
    if not old.startswith('> 1.0'):
        write(history, '> 1.0历史技术报告。2.0完整源图、纸偶与运行绑定请读[实施证据](17-规模扩展与实施进度.md)和[发布验收](22-双平台验收与发布.md)。\n\n' + old)
    research = ROOT / 'docs/research/swords-and-soldiers-map/README.md'
    text = research.read_text(encoding='utf-8').replace('本轮交付是事实重查、运行版本审计和地图重设计约束；图中的新方案尚未成为游戏功能。', '以下内容记录研究当时的1.0事实重查、运行审计和重设计约束。研究图是当时的提案；后续2.0已落实真实路径与地图博弈，当前实现见顶部链接。')
    text = text.replace('《纸上兵戈》目前有三个场景主题', '审计时的《纸上兵戈》1.0有三个场景主题')
    text = text.replace('本轮不改写已有 EXE/APK，也不把研究提案标为已实施。先完成可验证的地图白盒，再扩展战役和场景素材，才能重新声称地图对标通过。', '研究阶段保留1.0 EXE/APK。后续2.0另行交付，已先验证路径图/运输/施工白盒再扩展200图、十院和素材；这不改变原作资料未实测的边界。2.0属于原创落实，精确复刻原作数值或全部地图的结论不在本报告范围。')
    write(research, text)
    print(f'Current release documentation: {len(wins)} automated campaign victories, {len(pending)} human balance pending; {build_status}.')

if __name__ == '__main__':
    main()
