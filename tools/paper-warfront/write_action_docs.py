"""Publish rc4 documentation from current passing native evidence."""
from pathlib import Path
import json,csv,hashlib,html
ROOT=Path(__file__).resolve().parents[2]
DOC=ROOT/'docs/paper-warfront';QA=ROOT/'output/qa/godot/actions-rc4';REL=ROOT/'release/3.0.0-rc4'
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def write(p,s):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(s.strip()+'\n',encoding='utf-8')
def main():
    actions=read(QA/'actions-report.json');matrix=read(QA/'mobile/mobile-matrix.json');pan=read(QA/'pan/report.json');pixels=read(QA/'pan/pixel-report.json');gallery=read(QA/'gallery/gallery-report.json');visual=read(QA/'visual-review.json')
    assert actions['passed'] and matrix['passed'] and pan['passed'] and pixels['passed'] and visual['passed']
    units=read(ROOT/'game/data/balance-prototype.json')['units'];profiles=read(ROOT/'game/data/unit-actions.json')['profiles'];assets=read(ROOT/'game/data/assets.json')['assets'];rigs=read(ROOT/'game/data/action-rig-provenance.json')
    ids=list(units);folder=DOC/'actions-rc4'
    write(folder/'README.md','''# 3.0.0-rc4：镜头、单位动作与五项菜单

当前运行版本修复地图拖拽抖动，重做武器独立分件与动作，整理桌面／移动主菜单。继承 rc2 友军判定、真实采矿与 rc3 的安全区、密度、触控、后台暂停。

[设计与实现约束](01-设计与实现约束.md) · [412单位动作登记](02-单位动作登记.md) · [本轮验收](03-验收与限制.md) · [离线原生画面](../../../assets/paper-warfront/actions-rc4-review.html) · [Windows／Android下载](../../../release/3.0.0-rc4/README.md)

运行素材权威为 game/data/assets.json、unit-actions.json、action-rig-provenance.json；每个稳定单位 ID 有登记。412 个绑定由 400 个可招募作战定义、10 个工人和2个召唤别名组成。美术仍为40个专属核心造型与40个角色家族及阵营调色，不能把登记数量当作独立手绘动画数量。

[制作总入口](../README.md) · [移动交互基线](../mobile-rc3/README.md) · [判定与矿口基线](../fixes-rc2/README.md)
''')
    write(folder/'01-设计与实现约束.md','''# 镜头、动作与菜单约束 · rc4

Godot 4.7.2、GDScript 与原生 Control；Windows 原生工具。无 Docker、WSL、虚拟机和模拟器。战斗依旧60Hz，渲染状态和伤害判定分开；关节、武器、飞行轨迹与受击停顿不产生额外碰撞伤害。地图、故事、费用、攻击前摇、间隔与射程沿用正式数据。

## 地图和镜头

旧地面随可见窗口起点重新采样，使同一世界位置的顶点与纹理连接变化；一整个凹多边形随镜头被重新三角化。当前沿0.42世界单位固定格点、所有道路折点和地图端点采样，顶层材质按相邻点固定四边形分段铺设，其他土层保留固定世界顶点的闭合多边形。表层、道路、装饰与单位共享前景变换，远景保留视差。手动拖拽时关闭战斗震动。

鼠标和第一根手指从当前可见镜头位置捕获，超过8dp拖动阈值后直接按位移定位。拖拽期间不平滑追赶目标；松开时已到目标，不产生二次追赶。释放到 HUD、模态、取消、后台和旋转均释放捕获。第二根手指仍能操作 HUD。小地图与追踪前线保留独立的导航语义。

## 纸偶动作和武器

身躯、前后腿／车轮、前臂、上臂、武器独立 PNG。双持、巨像、纸鸟与鼓手增加后侧关节。肩→肘→握点保持原始骨长；斩击、锤击、刺矛和投掷通过双骨 IK 指定蓄力和出手位置。源图中的遮挡部位使用本地纸色补片，不重写源图。

动作只由真实 age、walk、anim_t、job_time、hurt 和事件驱动。待机呼吸、行军、前摇末段出手、释放后回收、受击、束缚、倒地均有状态。原始 windup 决定伤害释放时刻；刀光、炮口、纸屑与声音只响应真实事件。受击停顿冻结完整关节采样，避免腿停而手仍转。

| 动作族 | 出手与反馈 |
| --- | --- |
| 刀、剑、斧、镰 | 先抬臂再向前挥下，刀弧、纸屑、命中闪白；双持前后手交替 |
| 长矛、骑枪、钩兵 | 朝对手刺出、收回；枪缨和枪身同属武器层 |
| 投矛 | 蓄力、伸臂、投射生成时手持矛隐藏，恢复末段补回 |
| 弓 | 真实弓弦拉开、持箭、释放弦振；发射后隐藏持箭 |
| 弩、连弩、针 | 扣机与后坐；弩矢、针和弓箭分别绘制，连弩保留逐发延迟 |
| 炮、臼炮、冲车 | 炮管后坐、轮组独立运动；臼炮较高弧线，冲车前冲回位 |
| 巨像、纸鸟 | 拳臂交替重击；纸鸟双翼动作与轻浮空 |
| 旗、鼓、工匠、法器 | 旗面随旗杆，双鼓槌、扳手、毛笔、叶杖、墨杖、折扇等独立挥动与蓄能 |
| 运金纸工 | 真实矿口举镐40%、落镐至57%、回收；等待和束缚不挥镐。装载姿态保留0.25秒，同时开始回程；负载、卸货和死亡另有动作 |

投射物按角色映射箭、矛、弩矢、针、炮弹、火、链、齿轮、叶、墨、纸、扇、印和声波。发射点在实际释放时拍下武器坐标，后续飞行不会跟随移动中的射手。显示弧线不会改写命中、阵营或弹道时长。反射重置发射显示偏移，归属仍由模拟负责。

`publish_action_rigs.py` 从固定 rc3 分件基线与原始透明角色开始；生成独立运行衍生资源及 SHA256。保护面部，清理分件碎屑，弓弦由运行时重画，旗面和武器附件必须随武器。原 PNG 与生成提示词保留；本轮没有再次调用图像生成服务。

## 菜单和移动端

主菜单仅五行，顺序固定：继续战役、新战役、成就挑战、兵书、设置。新战役下一级只有线性战役、遭遇战两种模式。地图试演、帮助、许可、退出在设置。战前编组由简报进入；战役与遭遇战返回新战役，再返回主菜单。

移动 UI 使用逻辑dp、安全区和48dp最小触控。最小320dp横屏压缩标题为32dp，五项全部可见且一行一项；不以滚动才能找到设置。长内容页保留原生触控滚动，声音与显示保留后台、省电和减少动效。字体按当前真实文案覆盖；本机序列化压缩衬线字体曾崩溃，使用 compress=false 导入后通过，导出登记包含字体和导入设置。

[每单位动作与部件](02-单位动作登记.md) · [验证与边界](03-验收与限制.md)
''')
    table=['# 单位动作登记 · rc4','','所有单位共享游戏规则；下表是运行时动作绑定。40个角色家族分别实现动作曲线，阵营变体复用动作并保留本身美术、参数和能力。PNG分件、肩肘坐标和逐文件散列见 [加工记录](../../../game/data/action-rig-provenance.json)。','','[机器动作表](../../../game/data/unit-actions.json) · [CSV登记](../../../assets/paper-warfront/animation/unit-actions-rc4.csv)','','| 稳定ID | 名称 | 家族 / 动作 | 投射 | 前摇 / 回收秒 | 原生页 |','| --- | --- | --- | --- | --- | --- |']
    rows=[]
    for index,uid in enumerate(ids):
        p=profiles[uid];name=units[uid].get('name',uid);page=index//12
        table.append(f"| {uid} | {name} | {p['role']} / {p['gesture']} | {p['projectile'] or '—'} | {p['windup']} / {p['recovery']} | [P{page:02d}](../../../output/qa/godot/actions-rc4/gallery/page-{page:02d}-attack.png) |")
        rows.append({'id':uid,'name':name,'role':p['role'],'gesture':p['gesture'],'projectile':p['projectile'],'windup':p['windup'],'recovery':p['recovery'],'states':','.join(p['states']),'rig':p.get('rig','rc4-articulated'),'page':page,'source_art':p['source_art']})
    write(folder/'02-单位动作登记.md','\n'.join(table))
    csvpath=ROOT/'assets/paper-warfront/animation/unit-actions-rc4.csv'
    with csvpath.open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    write(folder/'03-验收与限制.md',f'''# 原生验收与限制 · rc4

2026-10-09，Godot 4.7.2 / Windows 原生 GPU。当前结果由报告中的输入 SHA256 与构建清单绑定，保留失败迭代，最终通过报告只适用于其登记的文件。

| 范围 | 当前结果 | 证据 |
| --- | --- | --- |
| 全单位动作和实际攻击 | {len(actions['checks']):,}检查；412绑定、402实际敌方攻击、40角色家族、友军不受伤、关节长度、投矛离手和拉弦 | [动作契约](../../../output/qa/godot/actions-rc4/actions-report.json) |
| 判定、十院工人、世界规则 | 当前正式模拟重新执行；真实举镐、装载、归仓、矿口FIFO、道路站位 | [判定](../../../output/qa/godot/actions-rc4/ownership-report.json) · [工人](../../../output/qa/godot/actions-rc4/workers-report.json) · [规则](../../../output/qa/godot/actions-rc4/foundation-report.json) |
| 地图拖拽 | {pan['maps']}图；顶点位移残差最大{pan['max_vertex_residual_px']:.7f}px；原生48帧、47组对齐后地表差异均值最大{pixels['worst_mean_rgb_error']:.5f}/255 | [镜头报告](../../../output/qa/godot/actions-rc4/pan/report.json) · [逐帧像素](../../../output/qa/godot/actions-rc4/pan/pixel-report.json) · [录像](../../../output/qa/godot/actions-rc4/pan/camera-pan.mp4) |
| 原生分件姿态 | 412单位×8状态，35页；10工人另看等待、卸货、束缚；40家族+10工人慢速检查录像 | [逐页报告](../../../output/qa/godot/actions-rc4/gallery/gallery-report.json) · [检查录像](../../../output/qa/godot/actions-rc4/gallery/unit-actions.mp4) · [目视记录](../../../output/qa/godot/actions-rc4/visual-review.json) |
| 八种移动配置 | {matrix['checks']:,}检查；小横屏、高密度、双向刘海、两类平板、竖屏恢复；48dp、安全区、五项菜单、真实触摸、第二指、法术、后台、旋转 | [设备矩阵](../../../output/qa/godot/actions-rc4/mobile/mobile-matrix.json) |
| 真实攻击显示 | 八个代表单位走真实前摇、释放、投射飞行与伤害 | [原生对照](../../../output/qa/godot/actions-rc4/weapon-duels/report.json) |
| 普通经济对战 | 既定预算、正常招募、双方付费AI，完整结算；录像是15fps离线片段 | [对战](../../../output/qa/godot/actions-rc4/mobile/native-play/report.json) |
| 音效 | 四种短PCM不削波、角色事件路由；沿用声道池、限幅和后台停止 | [声音检查](../../../output/qa/godot/actions-rc4/audio/report.json) · [声音设计](../../../game/SOUND_DESIGN.md) |
| 发布 | 重新导出资源内嵌EXE及签名APK，实际EXE六种烟测、APK双ARM与16KB对齐、散列与包内容 | [当前下载](../../../release/3.0.0-rc4/README.md) |

受控姿态页验证显示，真实攻击夹具验证前摇／弹道／命中，普通付费对战验证系统结合。这些证据不能互相替代。412绑定与{sum(len(r['parts']) for r in rigs['records'])}个衍生分件不能等同于412套独立逐帧手绘；数量以当前加工JSON为准。

没有连接 Android 真机，没有使用模拟器。当前移动证据是 Windows 原生 Godot 注入密度、安全区和实际 ScreenTouch／ScreenDrag；APK签名和结构通过不等同于真机帧率、触感、音响或温度验证。200关仍未完成逐关人工平衡验收。纸偶采用程序关节和有限原图补片，保留纸片转动的风格。

[完整发布审计](../../../output/qa/godot/actions-rc4/release-audit.json) · [返回本轮入口](README.md)
''')
    # Current entrypoints; historical reports remain untouched in their folders.
    rootdoc=DOC/'README.md';s=rootdoc.read_text(encoding='utf-8');s=s.replace('3.0.0-rc3','3.0.0-rc4',1)
    start=s.index('当前为 **');end=s.index('\n\n当前版本',start)
    s=s[:start]+'当前为 **3.0.0-rc4 镜头／动作／菜单与移动修订版**：[本轮入口](actions-rc4/README.md) · [当前下载](../../release/3.0.0-rc4/README.md)。rc2判定／采矿和rc3移动报告保留为历史基线；当前实现和发布以rc4为准。'+s[end:]
    s=s.replace('脚点是移动和命中坐标；纸偶整身围绕固定脚点变换。','肩、肘、武器独立关节；412个稳定动作绑定与真实攻击事件。')
    s=s.replace('入口含线性战役、六图试演、遭遇战、编组、军库、挑战、设置、帮助与鸣谢。','主菜单五行；新战役进入线性战役／遭遇战，辅助入口放在设置。')
    s=s.replace('移动 UI 与发布包以 rc3 为准。','rc3移动契约沿用，当前动作、菜单与发布包以rc4为准。')
    s=s.replace('当前移动报告在 mobile-rc3/03-设备矩阵与验收.md，构建在 release/3.0.0-rc3；rc2 与 rc1 保留为基线。','当前八配置、镜头、动作与发布报告在actions-rc4；rc3、rc2与rc1保留为历史基线。')
    s=s.replace('3.0.0-rc2修复包包含WindowsEXE／ZIP、Android签名APK、源码ZIP与SHA256；日志在output/qa/godot/rc2/build。','当前rc4包含WindowsEXE／ZIP、Android签名APK、源码ZIP与SHA256；日志在output/qa/godot/actions-rc4/build。')
    s=s.replace('建议从“地图试演 · 六张基准”的归金坡开始。','从设置进入地图试演；从新战役选择线性战役或遭遇战。')
    write(rootdoc,s)
    for name in ['06-Godot纸偶与动画规范.md','07-交互与UI规范.md','13-运行素材与反馈矩阵.md','21-十院素材与动画规范.md','15-运行验收与交付报告.md','22-双平台验收与发布.md']:
        p=DOC/name;s=p.read_text(encoding='utf-8');marker='<!-- rc4-current -->'
        if marker not in s:s=marker+'\n**当前rc4规范：** [镜头、全单位动作与菜单](actions-rc4/README.md)。下文含rc1／rc2历史实现，肩肘武器、五项菜单和当前发布以rc4为准。\n\n'+s
        write(p,s)
    manual=(DOC/'16-玩家手册.md').read_text(encoding='utf-8');manual=manual[manual.index('建议从'):]
    manual=manual.replace('建议从“地图试演 · 六张基准”的归金坡开始。','主菜单每行一个入口：继续战役、新战役、成就挑战、兵书、设置。新战役内选择线性战役或遭遇战；战前简报可调整2–4个作战兵种。地图试演、操作帮助、鸣谢与退出在设置内。\n\n建议从“设置 → 地图试演”的归金坡开始。')
    write(DOC/'16-玩家手册.md','# 玩家手册 · 3.0.0-rc4\n\n'+manual)
    write(ROOT/'README.md',f'''# 纸上兵戈：十院留名 / Paper Warfront 3.0.0-rc4

Godot4.7.2原生纸偶即时策略。当前修订地图拖拽、全单位独立武器动作、五项主菜单与手机／平板布局。每局2–4战斗兵种加工人。

[Windows／Android](release/3.0.0-rc4/README.md) · [本轮修订与证据](docs/paper-warfront/actions-rc4/README.md) · [原生画面](assets/paper-warfront/actions-rc4-review.html) · [完整文档](docs/paper-warfront/README.md) · [Godot工程](game/project.godot)

![手机原生运行画面](output/qa/godot/actions-rc4/mobile/phone-16x9/06-HUD-yin.png)

412动作绑定、402真实攻击、200图稳定拖拽与八种屏幕配置已检查。200场景／193几何、十院军库、友军判定与真实归仓保留。Android签名APK重新导出，尚未进行真机测试。

[地图研究](docs/research/swords-and-soldiers-map/recheck-20261008/README.md) · [rc2修复基线](docs/paper-warfront/fixes-rc2/README.md) · [rc3移动基线](docs/paper-warfront/mobile-rc3/README.md)
''')
    write(ROOT/'docs/README.md','# 项目文档入口\n\n[当前镜头／动作／移动修订](paper-warfront/actions-rc4/README.md) · [制作总目录](paper-warfront/README.md) · [Windows／Android](../release/3.0.0-rc4/README.md)\n\n[原作地图研究](research/swords-and-soldiers-map/recheck-20261008/README.md) · [六图重做基线](paper-warfront/redesign-3.0/README.md) · [移动基线](paper-warfront/mobile-rc3/README.md)\n\n历史报告保留当时事实，当前输入与发布核对见rc4报告。')
    write(ROOT/'game/README.md','''# Godot工程 · 3.0.0-rc4

Godot4.7.2导入project.godot，F5运行。main.tscn为入口，battle_sim与map_runtime独立60Hz；UI与渲染消费状态和事件。

[当前规范](../docs/paper-warfront/actions-rc4/README.md) · [下载](../release/3.0.0-rc4/README.md) · [声音设计](SOUND_DESIGN.md)

动作与地图回归：check_action_revision.py import、contracts、gallery、pan。移动回归：check_mobile_adaptation.py；保留系统与普通付费对战：check_mobile_preserved_systems.py；原生代表攻击：record_weapon_duels.gd。检查报告登记当前输入散列。字体compress=false；不要用旧压缩导入缓存覆盖。

导出EXE用 -- --demo --capture <绝对PNG> --quit-after-capture --profile-path <隔离JSON> 烟测；测试脚本从发布程序排除。签名凭据、网关配置与Godot缓存不在源包。Windows注入的移动触摸不是Android真机验收。
''')
    p=ROOT/'assets/paper-warfront/README.md';s=p.read_text(encoding='utf-8');write(p,'**当前rc4动作资源：** [原生逐页检查](actions-rc4-review.html) · [逐单位动作登记](animation/unit-actions-rc4.csv) · [加工规范](../../docs/paper-warfront/actions-rc4/01-设计与实现约束.md)。本轮加工已有源图，独立肩肘、武器和附件；没有新增AI图像。\n\n'+s)
    write(ROOT/'release/README.md','# 本地游戏包\n\n[当前3.0.0-rc4](3.0.0-rc4/README.md) · [rc3移动基线](3.0.0-rc3/README.md) · [rc2判定／采矿基线](3.0.0-rc2/README.md) · [rc1地图基线](3.0.0-rc1/README.md)\n\n每版以自己的构建清单和报告为准。Android尚未连接真机。')
    write(REL/'README.md','''# 纸上兵戈：十院留名 · 3.0.0-rc4

本轮修复拖拽地形抖动、独立武器动作与投射反馈，主菜单整理成五行，并回归手机和平板的48dp、安全区、触屏和后台行为。

| 下载 | 使用 |
| --- | --- |
| [Windows ZIP](PaperWarfront-Windows-3.0.0-rc4.zip) | 解压后双击PaperWarfront.exe |
| [Windows EXE](windows/PaperWarfront.exe) | 资源内嵌，64位Windows10／11 |
| [Android APK](android/PaperWarfront-3.0.0-rc4.apk) | 横屏、ARM64／ARMv7、离线；在设备上允许此来源后安装 |
| [Godot源码与素材](PaperWarfront-Source-3.0.0-rc4.zip) | Godot4.7.2导入game/project.godot |
| [SHA256](SHA256SUMS.txt) | 对照文件散列 |

使用上一版本相同 Android 包名与签名，配置 userLandscape；系统安装是否保留数据以设备行为为准。Windows存档沿用本机user目录。GL兼容启动命令包含在Windows ZIP。

[本轮文档](../../docs/paper-warfront/actions-rc4/README.md) · [原生画面](../../assets/paper-warfront/actions-rc4-review.html) · [构建清单](build-manifest.json) · [发布核对](../../output/qa/godot/actions-rc4/release-audit.json)

Windows原生GPU、实际EXE及APK签名／架构／16KB对齐已核对；移动布局用Windows原生触摸和注入屏幕指标检查。Android真机帧率、触感、温度与声音尚未验收，200关尚未逐关人工平衡验收。
''')
    # Single offline page, no external web resources or browser tabs required.
    options=''.join(f'<option value="{i:02d}">P{i:02d}: {html.escape(units[ids[i*12]].get("name",ids[i*12]))}</option>' for i in range(35))
    write(ROOT/'assets/paper-warfront/actions-rc4-review.html',f'''<!doctype html><html lang="zh"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>纸上兵戈 · rc4原生检查</title><style>body{{margin:0;background:#f4ead3;color:#25343a;font:18px system-ui}}main{{max-width:1500px;margin:auto;padding:20px}}select,button{{font:inherit;margin:6px;padding:12px;background:#fff8e8;border:1px solid #99886b;border-radius:6px}}img,video{{max-width:100%;display:block;margin:12px 0}}a{{color:#31777c}}</style><main><h1>纸上兵戈 · rc4原生画面</h1><p>以下均来自Godot原生GPU。姿态页是受控夹具；普通对战和移动检查单独展示。</p><p><a href="../../docs/paper-warfront/actions-rc4/README.md">设计与证据</a> · <a href="animation/unit-actions-rc4.csv">412单位登记</a></p><select id="page">{options}</select><select id="phase">{''.join('<option>'+s+'</option>' for s in ['idle','walk','windup','attack','hurt','left','special','death'])}</select><img id="pose" alt="实际Godot动作姿态页"><h2>40动作家族与十院纸工</h2><video controls preload="none" src="../../output/qa/godot/actions-rc4/gallery/unit-actions.mp4"></video><h2>地图拖拽</h2><video controls preload="none" src="../../output/qa/godot/actions-rc4/pan/camera-pan.mp4"></video><h2>小屏幕五项菜单</h2><img loading="lazy" src="../../output/qa/godot/actions-rc4/mobile/compact-16x9/01-menu.png" alt="1136×640，密度2的小横屏主菜单"><h2>普通付费AI对战</h2><video controls preload="none" src="../../output/qa/godot/actions-rc4/mobile/native-play/mobile-play.mp4"></video><p>录像离线编码，不代表实时设备性能。Android真机未测。</p></main><script>const p=document.querySelector('#page'),s=document.querySelector('#phase'),im=document.querySelector('#pose');function show(){{im.src='../../output/qa/godot/actions-rc4/gallery/page-'+p.value+'-'+s.value+'.png'}}p.onchange=s.onchange=show;show();</script></html>''')
    print('rc4 documents and per-unit registry published from passing evidence')
if __name__=='__main__':main()
