"""Build reviewable reports from actual native test/export evidence."""
from pathlib import Path
import json,re,shutil
from PIL import Image,ImageDraw,ImageFont
from write_runtime_docs import table,name,FACTIONS,SPELL_EFFECTS,UNIT_ABILITIES

ROOT=Path(__file__).resolve().parents[2];GAME=ROOT/'game';DOC=ROOT/'docs/paper-warfront';QA=ROOT/'output/qa/godot';RELEASE=ROOT/'release'

def read(path):return json.loads(path.read_text(encoding='utf-8'))
def save(filename,text):
    published = text.strip()
    if filename == '15-运行验收与交付报告.md':
        heading, rest = published.split('\n',1)
        notice = '地图专项复核（2026-10-08）：本报告保留 1.0 的程序与导出验证记录，不构成地图对标通过证据。三场景共用一套机械地图，十五战役关均拆基地；后续方向见 [地图研究](../research/swords-and-soldiers-map/README.md)，新方案尚未实施。'
        published = heading+'\n\n'+notice+'\n'+rest
    (DOC/filename).write_text(published+'\n',encoding='utf-8')

def contact_sheet():
    fonts=GAME/'assets/fonts'
    font=ImageFont.truetype(str(fonts/'NotoSansSC.ttf'),22)
    title=ImageFont.truetype(str(fonts/'NotoSerifSC.ttf'),36)
    ids=list(read(GAME/'data/balance-prototype.json')['spells'])
    out=Image.new('RGB',(1500,1680),'#e8deca');d=ImageDraw.Draw(out)
    d.text((24,15),'纸上兵戈 · 十五法术运行验收',font=title,fill='#b74532')
    for i,asset_id in enumerate(ids):
        path=QA/'ui-export'/('fx-'+asset_id.replace('.','-')+'.png')
        im=Image.open(path).convert('RGB')
        # Native viewport shots are 1280x720 here; crop only the battle, keep the full files.
        im=im.crop((int(im.width*.23),int(im.height*.30),int(im.width*.86),int(im.height*.86)))
        im.thumbnail((478,268),Image.Resampling.LANCZOS)
        x=16+(i%3)*495;y=77+(i//3)*318
        d.rectangle((x,y,x+479,y+300),fill='#f3ebdd',outline='#baa994',width=2)
        out.paste(im,(x+(480-im.width)//2,y+3))
        d.text((x+10,y+269),FACTIONS[asset_id.split('.')[1]]+' · '+name(asset_id),font=font,fill='#343332')
    out.save(QA/'spell-feedback-overview.png')

def main():
    simulation=read(GAME/'tests/simulation-report.json')
    paths=read(GAME/'tests/campaign-path-report.json')
    desktop=read(QA/'ui-export/ui-report.json');mobile=read(QA/'ui-mobile-layout/ui-report.json')
    assets=read(QA/'runtime-assets-report.json');builds=read(RELEASE/'build-manifest.json')
    assert not simulation['failures'] and not paths['failures'] and len(paths['results'])==15
    assert all(c['ok'] for c in desktop['checks']+mobile['checks'])
    assert not desktop.get('capture_errors') and not mobile.get('capture_errors') and not assets['errors']
    for log in ['windows-ui.log','mobile-layout.log','release-import.log','export-windows.log','export-android.log']:
        assert not re.search(r'(?m)^(?:SCRIPT ERROR:|ERROR:)',(QA/log).read_text(encoding='utf-8'))
    contact_sheet()
    source=read(ROOT/'assets/paper-warfront/library-manifest.json')
    records={r['id']:r for r in source['assets']}
    runtime=read(GAME/'data/assets.json')['assets']
    sections=[]
    for category in ['unit','portrait','spell','building','resource','prop','ui','texture','fx','background','audio']:
        rows=[]
        for asset_id,a in runtime.items():
            if a['category']!=category:continue
            purpose=records[asset_id].get('role',records[asset_id].get('usage',category))
            if category=='unit':purpose=UNIT_ABILITIES[asset_id.split('.')[-1]]
            elif category=='spell':purpose=SPELL_EFFECTS[asset_id.split('.')[-1]]
            elif category=='portrait':purpose='战前叙事与菜单统帅，无可操控英雄'
            elif category=='ui':purpose='公共符号库；当前界面主要使用Control文字，仅部分符号常驻'
            elif category=='texture':purpose='纸材风格/运行装饰参考；不代表每张都用于活动角色表面'
            elif category=='fx':purpose='特效母题；部分印/雷/碎屑用Canvas代码替代表达'
            elif category=='audio':purpose='40秒阵营循环' if '.music.' in asset_id else '事件SFX，运行限流/混音'
            elif category=='background':purpose='低对比远景，地图不提供隐含地形伤害'
            elif category=='resource':purpose='经济矿点；采金结果由纸工状态结算'
            elif category=='prop':purpose='纸面装饰/经济表现，无独立碰撞或资源收益'
            else:purpose='有生命/归属的真实基地、纸哨或产法灯'
            relative='../../game/'+a['path'].removeprefix('res://')
            rows.append([asset_id,records[asset_id]['name'],purpose,f'[运行文件]({relative})'])
        sections.append('## '+category+'\n\n'+table(['稳定ID','名称','实际用途与边界','资源'],rows))
    save('13-运行素材与反馈矩阵.md',r'''
# 运行素材与反馈矩阵 · 1.0

116稳定ID、53纸偶分件，实际绑定与文件散列见 [assets.json](../../game/data/assets.json)、[asset-inventory.json](../../game/data/asset-inventory.json) 和 [Godot溯源](../../assets/paper-warfront/godot-integration.json)。下表列出每项素材，明确运行用途与保留参考；并非每个原始图标/纹理都必须常驻同一战场。

![实际导出程序十五法术截图总览](../../output/qa/godot/spell-feedback-overview.png)

## 动作与反馈验收

| 反馈 | 模拟/表现关联 | 证据 |
| --- | --- | --- |
| 行走、前摇、挥击、炮轮 | 固定步长状态→纸偶双腿/身体/轮轴 | 三阵营实际战场截图，Windows原生窗口操作 |
| 受击 | 伤害事件→闪白/55ms局部步态停顿/纸屑/数字 | 战场与法术命中截图；伤害值规则测试 |
| 死亡、纸标、召唤 | 当步死亡→0.44秒折倒；纸标/寿命独立 | 规则消费/寿命测试，祭司/召唤场景 |
| 治疗、护符、强化、控制、毒 | 实际状态与生命变化→局部环/印/恢复数字 | 十五法术独立截图与规则测试 |
| 落印、雷印、火签雨、泼墨 | 延迟/直接/三段→短预告/命中/范围母题 | 延迟/半径/三段伤害测试与实际程序截图 |
| 招募、研究、退款、归仓 | 成功命令/资源事件→卡片/队列/短提示/声音 | Windows UI集成检查 |
| 建筑 | 生命→贴近实际纸图的血条；破坏停止能力 | 灯被拆规则检查与实际看家截图 |
| 声音 | 20语义SFX、三正式循环、运行警报、独立音量 | WAV采样/峰值校验；播放接入；手机听感未实测 |

Windows的视觉捕获使用真实Godot导出程序，法术场景是固定布景，报告不把它们称为真实通关。纸粒上限650、短特效限流、16音源复用；基于预算做保护，不承诺未经测量的手机帧率。具体测试范围和限制见 [15](15-运行验收与交付报告.md)。

'''+ '\n'.join(sections))
    legal_rows=[]
    for r in paths['results']:
        win=next(a for a in r['attempts'] if a['winner']==0)
        legal_rows.append([r['id'],win['variant'],win['seconds'],int(win['base_hp'][0]),win['stats']['recruited'],win['stats']['casts'],'通过'])
    exe=next(b for b in builds['builds'] if b['path'].endswith('.exe'));apk=next(b for b in builds['builds'] if b['path'].endswith('.apk'))
    png_count=len(list((QA/'ui-export').glob('*.png')))
    mobile_size=mobile.get('window_size',[1440,720])
    mobile_dimensions=mobile_size.strip('()').replace(', ', '×') if isinstance(mobile_size,str) else '×'.join(str(v) for v in mobile_size)
    save('15-运行验收与交付报告.md',f'''
# 运行验收与交付报告 · 1.0.0

日期2026-10-08。原生Windows11、NVIDIA RTX3060、Godot4.7.2.stable.official.ed1daf0bf。Windows测试使用Vulkan Mobile；Android导出使用GL Compatibility。未使用Docker、WSL、虚拟化或模拟器。

## 本次结果

| 层级 | 结果 | 可复查证据 |
| --- | --- | --- |
| 机制与对局 | {simulation['passed']}通过、0失败；包含15个双方自动指挥对局 | [规则JSON](../../game/tests/simulation-report.json)、[原始日志](../../output/qa/godot/simulation.log) |
| 合法通关路径 | 15/15关找到胜利；资源/敌AI与正式关卡相同 | [通关JSON](../../game/tests/campaign-path-report.json)、[脚本](../../game/tests/test_campaign_paths.gd) |
| 导出Windows UI | {len(desktop['checks'])}/{len(desktop['checks'])}通过；{png_count}张实际捕获 | [UI报告](../../output/qa/godot/ui-export/ui-report.json)、[日志](../../output/qa/godot/windows-ui.log) |
| 横屏触控布局 | Windows运行移动布局，{len(mobile['checks'])}检查通过，{mobile_dimensions}窗口 | [布局报告](../../output/qa/godot/ui-mobile-layout/ui-report.json)、[移动菜单](../../output/qa/godot/ui-mobile-layout/01-menu.png) |
| 素材绑定 | 116ID、53分件、{assets['files']}目录文件；引用/图像/字库/WAV检查0错误 | [运行校验](../../output/qa/godot/runtime-assets-report.json) |
| Windows文件 | EXE内嵌资源，实际启动/显示/点击战役与招募 | [EXE](../../release/windows/PaperWarfront.exe) |
| Android文件 | 签名v2/v3、ZIP16KB页对齐、ARM64 ELF16KB对齐、双ARM ABI通过 | [签名日志](../../output/qa/godot/apk-signature.log)、[包信息](../../output/qa/godot/apk-badging.log)、[ELF](../../output/qa/godot/apk-elf-report.json) |

Windows原生窗口曾实际进入战役说明和战场、点击招募并看到失败结算；自动集成检查进一步覆盖研究、恢复目标、暂停冻结、遮罩清理、重开、线性解锁、挑战星章与15种法术实际渲染。UI检查里的强制胜负只验证路由，不是通关证据。

## 十五关合法路径

玩家指挥脚本只调用正式side0 request API，每0.5秒决策；无额外金币、直接生成作战兵、删除敌兵或强制杀基地。以下是模拟时间；证明存在可胜策略，不代表真人首次游玩时间或最佳三星攻略。

{table(['关卡ID','策略编号','获胜秒','我城剩余生命','招募','施法','结果'],legal_rows)}

## 两个程序

Windows x86_64 EXE：{exe['bytes']/1024/1024:.1f}MiB；SHA256 `{exe['sha256']}`。

Android APK：{apk['bytes']/1024/1024:.1f}MiB；SHA256 `{apk['sha256']}`。包名org.paperwarfront.game，versionName1.0.0，versionCode10000；原生badging为minSDK24/targetSDK36，ABI armeabi-v7a和arm64-v8a，无互联网权限。

完整包体与散列以 [build-manifest.json](../../release/build-manifest.json) 为准；源码、许可和Windows压缩包见 [交付入口](../../release/README.md)。

## 尚未完成的实测

本次ADB未发现Android真机，因此没有手机安装启动、触控/系统返回、声音延迟、发热/耗电、长时间稳定性或手机FPS实测。Windows上的移动布局检查只验证布局/同一游戏逻辑；不能替代Android设备运行。未开展多GPU/旧驱动兼容与真人十五关完整手动通关；平衡仍可继续按实际玩家体验迭代。

当前交付是完整离线可玩1.0工程与两平台文件，不含线上对战。所有素材生成、静态审核、运行链接、场景验证和设备验证保持不同证据，不把生成图标成实战画面。
''')
    RELEASE.mkdir(exist_ok=True)
    (RELEASE/'README.md').write_text(f'''
# 《纸上兵戈》1.0.0 交付

地图复核（2026-10-08）：此 1.0 交付使用三个场景主题与一套机械地图，不代表原作地图对标已完成。新研究、现版差距和尚未实施的重设计见 [地图专项研究](../docs/research/swords-and-soldiers-map/README.md)。

Godot构建的离线自动军团RTS。三阵营、17单位（含工人与召唤）、15法术、26科技、15线性战役、6挑战、AI遭遇战、完整菜单/HUD/设置/兵书/星章与存档。

## 程序与源码

- [Windows EXE](windows/PaperWarfront.exe)：{exe['bytes']/1024/1024:.1f}MiB，资源内嵌，直接双击。
- [Windows完整ZIP](PaperWarfront-Windows-1.0.0.zip)：含EXE、操作说明与许可。
- [Android APK](android/PaperWarfront-1.0.0.apk)：{apk['bytes']/1024/1024:.1f}MiB，签名release，ARMv7/ARM64，minSDK24、targetSDK36。
- [Godot源码与素材ZIP](PaperWarfront-Source-1.0.0.zip)：可直接导入game/project.godot，含文档、源图/提示词、加工与构建工具、原字体与许可；不含密钥/SDK/引擎缓存。
- [制作文档入口](../docs/paper-warfront/README.md) / [玩家手册](../docs/paper-warfront/16-玩家手册.md) / [验收报告](../docs/paper-warfront/15-运行验收与交付报告.md)。

## 启动与操作

Windows：解压ZIP并双击PaperWarfront.exe，无需安装Godot；建议64位Windows10/11及支持Vulkan的显卡驱动，本机Win11/RTX3060实际运行。Android：把APK复制到手机，文件管理器点开安装；系统询问时允许该安装来源，再启动“纸上兵戈”。手机横屏，按钮招募/施法，拖动战场或战线图。

招募1..5，法术Q/W/E/R/T后点目标，F科技，B建造，P暂停，Home看家，Space追踪交锋，A/D或拖动移动镜头，右键/Esc取消。科技打开时战斗继续；阅读请暂停。先出兵再投资工人；工人归仓才入金。战役胜利自动存进度；Windows存档 `%APPDATA%\\PaperWarfront\\profile.json`。

## 验证范围

{simulation['passed']}规则/对局检查、15关合法指挥通关、Windows导出{len(desktop['checks'])}集成检查、15法术实际捕获、移动布局{len(mobile['checks'])}检查、运行资源校验与APK签名/架构/16KB对齐全部通过。Android尚未真机运行，手机触控、音频及性能未实测。完整记录与SHA256见验收报告和build-manifest.json。

Godot MIT/第三方与Noto OFL许可随包。Android签名私钥只在本机.keys中保留，未来覆盖升级需沿用同一签名；该私钥不放进交付源码。Windows EXE未使用商业代码签名。
'''.strip()+'\n',encoding='utf-8')
    (ROOT/'README.md').write_text('''# 纸上兵戈 / Paper Warfront

Godot 4.7.2制作的纸偶风离线军团实时策略。

[下载与安装](release/README.md) · [完整制作文档](docs/paper-warfront/README.md) · [玩家手册](docs/paper-warfront/16-玩家手册.md) · [Godot工程](game/project.godot) · [源素材库](assets/paper-warfront/gallery.html)

三阵营、17单位、15法术、26科技、15线性关卡与6战术挑战。保留自动行军、金币/法力、局内科技与手动施法核心；2D分层纸偶无需外部建模。

![实际Windows导出画面](output/qa/godot/ui-export/12-battle-deng.png)

程序、源码、原始生成素材、加工工具与验证报告均在本工作区。Android APK已签名导出并完成包校验，尚未连接真机实测；全部实现与限制见验收报告。
''',encoding='utf-8')
    print('Runtime feedback matrix, actual validation report and delivery README written.')

if __name__=='__main__':main()
