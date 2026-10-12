"""Publish current fix documentation while preserving historical map research."""
from pathlib import Path
from collections import Counter
import json

ROOT=Path(__file__).resolve().parents[2]
DOC=ROOT/'docs/paper-warfront'
FIX=DOC/'fixes-rc2'
QA=ROOT/'output/qa/godot/rc2'
REL=ROOT/'release/3.0.0-rc2'

def read(path):return json.loads(path.read_text(encoding='utf-8'))
def write(path,text):path.parent.mkdir(parents=True,exist_ok=True);path.write_text(text.strip()+'\n',encoding='utf-8')

def main():
    names=[('归属、命中与空间', 'ownership-after.json'),('十院运金状态','worker-actions.json'),('内容及基础规则','foundation.json'),('400兵种付费招募与战斗','combat.json'),('200图／602无限矿运输','transport.json'),('模拟规则','simulation.json'),('真实经济','economy.json'),('地图决策与任务边界','decisions.json'),('桌面原生UI','ui-desktop/report.json'),('横屏移动布局','ui-mobile/report.json')]
    rows=[];total=0
    for label,file in names:
        r=read(QA/file);assert not r.get('failures') and not r.get('failed')
        n=r.get('checks',r.get('passed'));n=len(n) if isinstance(n,list) else n
        total+=n;rows.append(f'| {label} | {n} 项，0 失败 | [报告](../../../output/qa/godot/rc2/{file}) |')
    battle=read(QA/'native-play/report.json');campaign=read(QA/'campaign-play.json');extended=read(QA/'campaign-137-extended.json');counts=Counter(x['winner'] for x in campaign['results'])
    manifest=read(REL/'build-manifest.json');smoke=read(QA/'export/report.json');assert smoke['passed']
    write(FIX/'05-验证与交付报告.md',f'''# 验证与交付报告 · 3.0.0-rc2

四项修复已进入 Godot 工程和新导出程序：最终敌友保护、实际采矿动作及排队、地图舞台材质、统一原生菜单／HUD。所有下表报告记录当前输入散列；最终发布审计重新对照源码、资源与可执行文件散列。

| 检查 | 结果 | 证据 |
| --- | --- | --- |
{chr(10).join(rows)}

上述共 **{total} 项检查、零失败**。400 兵种检查包含付费招募和敌方有效攻击；不是只验证友军被禁伤。空间夹具检查空服务点与实际身体位置的区别。运输报告覆盖无限矿持续往返，有限矿耗尽不纳入无限运输统计。

## 原生画面与正常对战

十院工人逐院检查举镐、落镐、回收与卸货，在各自地区地图截图；六张基准地图检查地面、桥、矿和设施可读性。桌面／横屏 UI 包含指针注入与受控法术、胜负和存档夹具，夹具不算真实获胜。

[正常预算纸桥完整对战](../../../output/qa/godot/rc2/native-play/report.json)使用双方真实招募、研究、施法和服务收入，在 {battle['seconds']:.3f} 秒结束、玩家侧获胜。事件包括 {battle['events']['attack']} 次攻击、{battle['events']['hit']} 次命中、{battle['events']['gold']} 次归仓。双方为同规则战术 AI，另有一次正常玩家桥路选择，不是人工操作录像。

[纸桥对战片段](../../../output/qa/godot/rc2/native-play/battle-replay.mp4)按 15fps 离线取帧，截取 14–24 与 40–50 秒并有明确剪切；[采矿片段](../../../output/qa/godot/rc2/mining-replay.mp4)为 13 秒。两个视频静音，不作为实时性能、音效体验或手机硬件证据。音效接入使用真实 mine_strike/cargo_loaded 事件，原有音频系统沿用。

## 二百关自动对战边界

[200 关默认 AI 互战](../../../output/qa/godot/rc2/campaign-play.json)，60Hz、每关上限 540 秒：{counts[0]} 胜、{counts[1]} 负、{counts[-1]} 平、{counts[-2]} 未结算。第 137 关（map.07.17）保持相同默认 AI 和预算，仅延长观察上限至 900 秒，在 {extended['results'][0]['time']:.1f} 秒正常败北；[单关延长报告](../../../output/qa/godot/rc2/campaign-137-extended.json)。不得把它记作 540 秒内通过或获胜。

默认阵容、默认战术下输掉关卡不是伤害规则失败。这组检查证明实际运行和结算，不能证明二百关均人工可胜、平衡完善或玩家手感认可。长对局和已有角色变体仍需要人工评审。

## 发布与平台

Windows EXE 约 {manifest['builds'][0]['bytes']/1048576:.1f} MiB，APK 约 {manifest['builds'][1]['bytes']/1048576:.1f} MiB。新 EXE 实际启动并退出，验证新菜单、受控 demo 战场和 OpenGL 兼容菜单，使用隔离档案，不改用户进度。[EXE 检查](../../../output/qa/godot/rc2/export/report.json)。

Android 保持 org.paperwarfront.game、原签名关系，versionName 3.0.0-rc2／versionCode 30001，min SDK24、target SDK36、arm64-v8a 和 armeabi-v7a，离线无 INTERNET 权限。已校验签名 v2/v3、zipalign 16KB 与 ARM64 ELF 加载段。[构建日志](../../../output/qa/godot/rc2/build)；[设备查询](../../../output/qa/godot/rc2/android-device-status.txt)为空，没有 Android 真机连接，因此没有手机安装／触控／音频／热量／帧率结论。

Windows、Android 与源码在 [3.0.0-rc2 发布入口](../../../release/3.0.0-rc2/README.md)。旧 3.0.0-rc1 和研究失败证据保持独立。源包保留生成母图、派生资产、工具、文档、截图／录像和报告；不包含凭据、引擎、缓存、原生逐帧序列及修复前备份 ZIP，后两者仍在工作区。

[发布审计](../../../output/qa/godot/rc2/release-audit.json) · [输入及证据索引](../../../output/qa/godot/rc2/validation-index.json) · [可视审阅](../../../assets/paper-warfront/rc2-review.html)
''')
    write(FIX/'README.md','''# 四项修复与视觉重整 · 3.0.0-rc2

[Windows／Android下载](../../../release/3.0.0-rc2/README.md) · [原生画面与动作](../../../assets/paper-warfront/rc2-review.html) · [验证报告](05-验证与交付报告.md)

| 文档 | 内容 |
| --- | --- |
| [修复与视觉设计约束](01-修复与视觉设计约束.md) | 本次范围、空间与敌友契约、纸层舞台、UI取舍 |
| [判定与采矿复查](02-判定与采矿复查.md) | 实际复现、根因、各伤害入口、FIFO与十院动作状态 |
| [素材与地图制作约束](03-素材与地图制作约束.md) | 两张生成母图、五种材质、十套工人镐臂、来源与加工 |
| [原生UI规范与状态验收](04-原生UI规范与状态验收.md) | 开源技能采用范围、主题、全流程状态与移动布局 |
| [验证与交付报告](05-验证与交付报告.md) | 当前输入检查、自动对战、实际EXE、APK及真实边界 |

此前地图研究与3.0.0-rc1审计保留在[六图重做档案](../redesign-3.0/README.md)。当前实现以game/data、Godot代码和rc2输入散列为准。
''')
    write(REL/'README.md','''# 纸上兵戈 · 3.0.0-rc2 修复与视觉版

[Windows ZIP](PaperWarfront-Windows-3.0.0-rc2.zip) · [直接运行EXE](windows/PaperWarfront.exe) · [Android APK](android/PaperWarfront-3.0.0-rc2.apk) · [源码ZIP](PaperWarfront-Source-3.0.0-rc2.zip) · [SHA256](SHA256SUMS.txt)

本次修复友军误伤入口、策反后的旧弹道／状态、采矿排队和动作；重做地面／桥梁材质及原生菜单／HUD。建议从“地图试演 · 六张基准”开始。每局2–4战斗兵种加工人，共3–5生产选择。

Windows ZIP解压后双击PaperWarfront.exe，资源内嵌，无需Godot；旧显卡使用Launch-Compatibility.cmd。新版EXE已在Windows11／RTX3060检查菜单、战场与OpenGL兼容启动。

Android APK为同包名／同签名的离线横屏安装包，versionCode30001，可作为rc1更新保留正常应用私有存档；安装时按Android系统要求允许本地安装。arm64-v8a／armeabi-v7a、最低Android7.0。APK签名与对齐检查通过，未连接真机，因此手机上的安装、手感、声音、发热与帧率仍未验证。

[玩家手册](../../docs/paper-warfront/16-玩家手册.md) · [修复说明](../../docs/paper-warfront/fixes-rc2/README.md) · [原生画面／动作](../../assets/paper-warfront/rc2-review.html) · [详细验证](../../docs/paper-warfront/fixes-rc2/05-验证与交付报告.md)

源码包含Godot工程、运行素材、生成母图和提示词、文档、工具、截图／视频与检查报告，不含.keys签名私钥、网关配置、.tools引擎、.godot缓存、逐帧截图序列或修复前备份。签名升级需维护原私钥；重生成图像需要本机配置的Sub2技能。Godot及字体第三方许可随Windows目录。

二百关自动检查和代表原生画面不等同于全关人工平衡或原作HD品质验收。[3.0.0-rc1历史版](../3.0.0-rc1/README.md)保持独立。
''')
    write(REL/'windows/Launch-Compatibility.cmd','''@echo off
cd /d "%~dp0"
start "" "%~dp0PaperWarfront.exe" --rendering-method gl_compatibility
''')
    # Current entrances point to RC2; immutable map recheck / prior release files stay intact.
    root_readme='''# 纸上兵戈：十院留名 / Paper Warfront 3.0.0-rc2

Godot4.7.2原生纸偶即时策略。本次修复敌友伤害保护、矿口FIFO与十院采矿动作，改进厚纸地形、桥梁和完整菜单／HUD。每局2–4战斗兵种加工人，3–5生产选择。

[Windows／Android](release/3.0.0-rc2/README.md) · [四项修复与证据](docs/paper-warfront/fixes-rc2/README.md) · [原生画面／动作](assets/paper-warfront/rc2-review.html) · [完整文档](docs/paper-warfront/README.md) · [Godot工程](game/project.godot)

![新版原生纸桥](output/qa/godot/rc2/native-play/battle-022.png)

200场景／193几何、十院400全局兵种库；素材采用专属核心和角色母版派生。当前自动规则8720项无失败，200关默认AI上限540秒内有一关未结算，延长同策略至593秒正常结束；不声称全部人工可胜。Android已导出签名APK，真机仍待验证。

[原作地图研究](docs/research/swords-and-soldiers-map/recheck-20261008/README.md) · [3.0地图重做基线](docs/paper-warfront/redesign-3.0/README.md) · [3.0.0-rc1历史包](release/3.0.0-rc1/README.md)
'''
    write(ROOT/'README.md',root_readme)
    write(ROOT/'release/README.md','''# 本地游戏包

[当前3.0.0-rc2修复与视觉版](3.0.0-rc2/README.md) · [3.0.0-rc1地图基线](3.0.0-rc1/README.md) · [2.0历史包](2.0.0/README.md)

新包以当前构建清单、输入散列和原生验证报告为准。Android尚未连接真机。
''')
    write(ROOT/'docs/README.md','''# 项目文档入口

[当前四项修复与视觉重整](paper-warfront/fixes-rc2/README.md) · [制作文档](paper-warfront/README.md) · [Windows／Android](../release/3.0.0-rc2/README.md)

[原作地图二次研究](research/swords-and-soldiers-map/recheck-20261008/README.md) · [六图重做基线](paper-warfront/redesign-3.0/README.md) · [200关空间目录](paper-warfront/redesign-3.0/02-战役空间目录.md)

研究目录和rc1报告保存当时事实。rc2的实现、证据散列、包版本和剩余人工／真机评审范围独立登记。
''')
    text=(DOC/'README.md').read_text(encoding='utf-8')
    text=text.replace('· 3.0.0-rc1','· 3.0.0-rc2',1)
    a=text.index('当前为 **');b=text.index('\n\n',a)
    text=text[:a]+'当前为 **3.0.0-rc2 修复与视觉版**，已修订友军判定、采矿动作与FIFO、地图美术和原生UI。旧地图研究与rc1报告是历史基线；本次实现和检查以[rc2文档体系](fixes-rc2/README.md)为准。'+text[b:]
    text=text.replace('../../release/3.0.0-rc1/README.md','../../release/3.0.0-rc2/README.md')
    text=text.replace('[离线素材与地图浏览](../../assets/paper-warfront/theatre-v3-gallery.html)','[原生画面与素材](../../assets/paper-warfront/rc2-review.html)')
    text=text.replace('当前完整报告在redesign-3.0/03-实现与验证边界.md，构建在release/3.0.0-rc1。','当前报告在fixes-rc2/05-验证与交付报告.md，构建在release/3.0.0-rc2；rc1报告保留为基线。')
    text=text.replace('3.0.0-rc1作为地图重做评审包，WindowsEXE／ZIP、Android签名APK、源码ZIP、SHA256清单及构建日志集中在release/3.0.0-rc1。','3.0.0-rc2修复包包含WindowsEXE／ZIP、Android签名APK、源码ZIP与SHA256；日志在output/qa/godot/rc2/build。')
    if '[rc2修复与视觉约束]' not in text:
        text=text.replace('| [交互与UI规范](07-交互与UI规范.md)','| [rc2修复与视觉约束](fixes-rc2/01-修复与视觉设计约束.md) | 当前空间、采矿、地形与UI契约。 |\n| [rc2判定与采矿复查](fixes-rc2/02-判定与采矿复查.md) | 真实根因、入口保护、矿口FIFO与工人身体站位。 |\n| [交互与UI规范](07-交互与UI规范.md)')
    write(DOC/'README.md',text)
    # Selected current specifications get focused RC2 notes, rather than silently
    # rewriting historical evidence counts in the prior map documents.
    notes={
        '06-Godot纸偶与动画规范.md':'十院工人现在有独立镐臂、躯干和双腿，举镐／落镐／回收按真实job_time驱动，等待者不采矿。矿口身体位置由模拟body_anchor管理；战斗、点击和渲染共享physical_point。其他兵种保留原分层程序纸偶，未宣称完整逐兵手绘动画。',
        '07-交互与UI规范.md':'全流程原生Control采用统一ui_theme与paper_panel，主菜单突出继续战役，军令／科技／编组／暂停／胜负统一纸面层级；常态提示按时隐藏。已完成研究禁用，失败可调整部署再战，模态隔离键盘与战场，卡片提供语义名称。移动布局使用较大按钮与军阵／法术两组。',
        '11-Godot架构与数据契约.md':'damage是统一敌友保护边界；attack/launch、前摇、飞行和状态脉冲重查side与source_uid。physical_anchor/physical_point区分矿服务锚点和实际身体站位，同时供战斗及渲染使用。ui_theme和paper_panel管理原生主题。',
        '03-美术风格圣经.md':'新增纸纤维、草纸／岩纸／林土／霜纸截面、真实桥梁结构；路缘按模拟几何，装饰回避交互节点。十地区材质与工人镐臂见rc2增量来源表。',
        '04-素材库与命名规范.md':'新增material.common.earth及edge.grass/slate/forest/ice五个材质ID；十院worker动画增arm-pick与独立肩枢轴。权威绑定assets.json，增量15条加工来源在rc2-art-provenance.json。',
        '05-素材生成与加工指导.md':'rc2实际通过sub2-image-gen／gpt-image-2.5生成两张地形母图，另由已有工人母图遮罩加工十套手臂。原图、完整提示词、切片坐标和SHA256独立保存，不能把派生文件数当作生成次数。',
        '13-运行素材与反馈矩阵.md':'新增mine_strike与cargo_loaded模拟事件、独立挥镐、矿屑、装货金币和卸货姿态；友方攻击拒绝产生命中副作用。纸工受击／死亡坐标与实际身体站位一致。',
        '21-十院素材与动画规范.md':'本次逐院检查工人举镐、落镐、回收和卸货，发布独立镐臂与去臂躯干；不扩大为400军库单位逐兵新增动画。十地区原生路缘与材质同时检查。',
        '18-路径与经济执行规范.md':'只有实际抵达矿服务锚点的工人加入FIFO，未到达arrival=-1不能抢槽。排队身体站位保存在模拟body_anchor，供命中与显示使用；不改变服务时长、容量和金币归仓规则。',
    }
    marker='<!-- rc2-current-note -->'
    for name,note in notes.items():
        p=DOC/name;old=p.read_text(encoding='utf-8')
        if marker in old:old=old[old.index('<!-- /rc2-current-note -->')+len('<!-- /rc2-current-note -->'):].lstrip('\n')
        write(p,f'{marker}\n**当前3.0.0-rc2补充：** {note}\n\n[本次完整约束与证据](fixes-rc2/README.md)。以下rc1正文保留其地图重做基线含义。\n<!-- /rc2-current-note -->\n\n'+old)
    for name in ['14-双平台构建与安装.md','15-运行验收与交付报告.md','16-玩家手册.md','22-双平台验收与发布.md']:
        p=DOC/name;text=p.read_text(encoding='utf-8').replace('3.0.0-rc1','3.0.0-rc2').replace('versionCode30000','versionCode30001').replace('地图重做评审版','修复与视觉版').replace('地图重做评审包','修复与视觉包').replace('redesign-3.0/03-实现与验证边界.md','fixes-rc2/05-验证与交付报告.md')
        text=text.replace('SHA256清单及构建日志集中在release/3.0.0-rc2。','SHA256清单集中在release/3.0.0-rc2；构建日志在output/qa/godot/rc2/build。')
        if name.startswith('16-') and '举镐' not in text:text=text.replace('近矿排队时', '采矿可见举镐、落镐、回收及矿屑，等待者不挥镐；装袋回程后在城内卸货才到账。近矿排队时')
        write(p,text)
    p=ROOT/'game/README.md';text=p.read_text(encoding='utf-8').replace('3.0.0-rc1','3.0.0-rc2')
    if '[本次判定、采矿与UI]' not in text:text+='\n[本次判定、采矿与UI](../docs/paper-warfront/fixes-rc2/README.md)。新增回归test_combat_ownership.gd、test_worker_actions.gd；原生十院采矿record_rc2_visuals.gd。\n'
    write(p,text)
    p=ROOT/'assets/paper-warfront/README.md';text=p.read_text(encoding='utf-8')
    if not text.startswith('**当前3.0.0-rc2：**'):text='**当前3.0.0-rc2：** [原生画面与动作](rc2-review.html) · [素材增量契约](../../docs/paper-warfront/fixes-rc2/03-素材与地图制作约束.md)。新增两张生成母图、五种地形材质与十院镐臂；来源在game/data/rc2-art-provenance.json。以下为rc1素材基线。\n\n'+text
    write(p,text)

if __name__=='__main__':main()
