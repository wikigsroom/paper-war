"""Write current mobile contracts and verified release notes from native reports."""
from pathlib import Path
import json

ROOT=Path(__file__).resolve().parents[2];QA=ROOT/'output/qa/godot/mobile-rc3'
DOC=ROOT/'docs/paper-warfront/mobile-rc3';REL=ROOT/'release/3.0.0-rc3'

def put(path,text):
    path.parent.mkdir(parents=True,exist_ok=True);path.write_text(text.strip()+'\n',encoding='utf-8')

def main():
    matrix=json.loads((QA/'mobile-matrix.json').read_text(encoding='utf-8'))
    assert matrix['passed'],'Only write acceptance claims from a passing matrix'
    rules=json.loads((QA/'rules/index.json').read_text(encoding='utf-8'))
    desktop=json.loads((QA/'desktop/report.json').read_text(encoding='utf-8'))
    assert desktop['passed'] and all(r['exit_code']==0 and not r['failures'] for r in rules)
    rule_count=sum(r['checks'] for r in rules);desktop_count=len(desktop['checks']);total=matrix['checks']+rule_count+desktop_count
    links='[检查与修复](01-检查与修复清单.md) · [实现约束](02-移动端实现约束.md) · [验证与交付](03-设备矩阵与验收.md)'
    put(DOC/'README.md',f'''# 移动端适配 · 3.0.0-rc3

Android 改为按屏幕密度布局的横屏游戏界面。已实现安全区、48dp 控件、手机与平板布局、独立触摸、原生滚动和滑杆、长按资料、返回层级、后台暂停和省电档位。

{links}

[下载新包](../../../release/3.0.0-rc3/README.md) · [原生画面](../../../assets/paper-warfront/mobile-rc3-review.html) · [完整文档](../README.md) · [rc2 判定与采矿基线](../fixes-rc2/README.md)

八组原生窗口检查 {matrix['checks']:,} 项，桌面 {desktop_count} 项，判定／工人／地图基础 {rule_count:,} 项，共 {total:,} 项通过。屏幕密度和安全区在 Windows 原生 Godot 中注入，输入使用 ScreenTouch／ScreenDrag。未连接 Android 手机，不能据此声称真机帧率、温度或手指舒适度已验收。
''')
    put(DOC/'01-检查与修复清单.md','''# 移动端检查与修复清单

| 问题 | 修复 | 验证 |
| --- | --- | --- |
| 1600×900 桌面画布直接缩放 | Android dpi/160 映射 UI 逻辑单位，窗口变化重新布局 | 八组屏幕：物理像素、逻辑尺寸和密度核对 |
| 手机上的暂停／辅助按钮过小 | 可操作控件至少 48×48dp，间隔 8dp；五张行动卡保持直接操作 | 原生矩阵逐项检查尺寸、可见边界和重叠 |
| 刘海、挖孔和手势区被忽略 | DisplayServer 安全区转为窗口逻辑坐标，再加 8／16dp 内边距 | 左挖孔、右挖孔、底部手势区与平板上下系统栏 |
| 地图被较大的手机 HUD 挤压 | 镜头按实际道路高差、纸城和纸偶高度装入可玩区域 | 八组配置均核对 200 张图的矿、建造位和我方路标 |
| 固定菜单、资料和结算页越界 | 原生容器、自适应列数、垂直滚动，弹窗固定标题和底部主动作 | 所有页面、首尾内容、部署与失败重试 |
| 用模拟鼠标解释触屏 | 关闭触摸到鼠标模拟；原生按钮接收 ScreenTouch，战场独立捕获手指 | 十院付费招募／退款和五十法术实际触摸注入 |
| 原生滑杆不响应纯触摸 | HSlider 保留 Range、键盘和鼠标行为，补充触摸拖动 | 音乐滑杆实际触摸改变数值与存档 |
| 4.7.2 滚动仍依赖模拟鼠标 | ScrollContainer 增加原生触摸捕获、惯性、滚动提示；滑动取消子按钮 | 从按钮上开始滑动，不选择地图条目 |
| 原字体子集缺少移动 UI 用字 | 从已授权完整字体重建正文／标题子集，补齐当前脚本和数据中的汉字 | 直接核对字体 cmap，不依赖系统字体；记录源字体与加工散列 |
| 拖动回到起点会误当点击 | 8dp 门槛，超过门槛后锁定为拖动直到抬手 | 往返拖动不施法；取消触摸不施法 |
| 手指跨到 HUD 会误招募 | 战场从首触点捕获同一 finger index；另指可操作 HUD | 双指招募、越区抬手、模态阻挡 |
| 依赖悬停才能看卡片资料 | 长按 0.55 秒打开完整资料，轻点保持招募／选法术 | 长按不扣费、不招募 |
| 系统返回键可能直接退出 | 关闭 SceneTree 默认 go-back 退出；撤销选择→面板→暂停→主菜单 | 原生通知及部署、简报、设置、退出确认 |
| 后台后错误追赶模拟、音乐继续 | 后台冻结模拟与视觉，重置触摸及积累时间，暂停音乐、停止 SFX | 后台持卡不触发招募，前台必须手动继续 |
| 竖屏期间旧尺寸地形继续绘制 | 保护界面隐藏战场，恢复横屏后重新取景再显示 | 小屏高差地图旋转无地形多边形错误，付费生产队列保留 |
| 手机持续高绘制负载 | 默认上限 60 帧；省电上限 30 帧；有界粒子、特效、飘字和 LRU 纹理缓存 | 档位切换与缓存上限；不作为真机 FPS 证明 |

基线 1600×900 画布在 1280×720、density=2 的窗口中，每逻辑单位只有 0.4dp。64 高的暂停按钮仅约 25.6dp；62 高的辅助动作约 24.8dp。基线截图保存在 output/qa/godot/mobile-rc3/before-hud.png，正式截图与对照均来自原生游戏。

采矿、伤害、金币归仓、地图几何、关卡和 AI 规则沿用 rc2。移动改动在界面、输入、字体覆盖、视觉取景和表现预算；本轮判定与工人回归确认原有修复继续有效。字体是已有 SIL OFL 源字体的重新子集化，路径和字形风格沿用；来源与加工散列在 game/data/mobile-font-provenance.json。
''')
    put(DOC/'02-移动端实现约束.md','''# 移动端实现约束

## 屏幕与坐标

Godot 4.7.2、原生 Control、Android OpenGL compatibility。项目使用 SCREEN_SENSOR_LANDSCAPE（Godot 配置值 4）；4.7.2 导出器映射为 Android USER_LANDSCAPE（11），已从实际 APK 清单核对。允许两侧横屏，并尊重系统旋转设置。竖屏或过小的分屏窗口显示提示并阻挡战场，停止绘制战场，已有战局进入暂停。恢复横屏保留战局与页面，不自动继续。

Android 从 DisplayServer.screen_get_dpi() 取得密度，从 get_display_safe_area() 取得物理安全区。mobile_layout.gd 计算逻辑尺寸，Window.content_scale_size 取整数，再用实际缩放比例换算安全区。Android 的窗口原点先从物理屏幕坐标中扣除。屏幕／安全区变化由 size_changed 和 0.25 秒低频检查处理。

交互层使用密度逻辑单位；战场另行缩放。触摸事件先进入 UI，未被 UI 接收的战场首触由 mobile_input.gd 捕获；view.to_local() 将其转为战场坐标。模拟仍使用原来的世界单位和 60Hz 时钟。矿点、设施、路标、演员身体和法术落点共享原有几何。

推荐横屏至少 568×320dp。安全内容宽小于 488dp、或高小于 240dp 时显示窗口提示，避免压缩 48dp 行动卡。保留 8dp 间隔，平板外边距 16dp；普通正文 16–18dp，次级信息 12–14dp。信息具有文字、价格、锁、冷却／生产进度，不只靠颜色区分。

正文和标题字体的子集均包含当前游戏脚本与数据所用汉字；用 fontTools 直接检查内置字体 cmap，避免 Windows 系统字体补全掩盖 Android 的缺字。已有 SIL OFL 全字体与许可证在 assets/paper-warfront/fonts/source，不重新绘制游戏角色或地形。加工记录在 game/data/mobile-font-provenance.json，检查在 output/qa/godot/mobile-rc3/font-coverage.json。

## 页面与触控

主菜单、战役、六图试演、遭遇战、挑战、兵书与许可使用纵向滚动页面，列数按可用宽度计算。弹窗宽最多 960dp，标题／返回和底部主动作固定，长内容在中间滚动。部署选择、阵营、地图、章节和返回链保留到重布局。

手机 HUD 上方是金币、法力、时间、基地／军阵和暂停；下方直接保留 3–5 生产卡或 5 法术卡、切组、军令／取消及小地图。军令内含科技、建造、队列、纸城、交锋、方向按钮和帮助。小地图及指令提供拖动导航的替代操作。长按卡片查看资料，轻点招募或选法术。

ScreenTouch 和 ScreenDrag 使用同一手指索引。8dp 后锁定拖动，回到起点仍不施法；取消、开面板、换页、改变窗口和进后台均清理触摸。滚动条是无独立点击动作的进度指示，整个内容区用于手指滑动。滑动时发送 SCROLL_BEGIN，取消原生子按钮的点按状态。滑杆保留原生 HSlider 的 value_changed、键盘和鼠标行为。

返回键先取消选中的法术／建造，再按当前页面关闭或返回；设置返回会保存，部署返回执行原返回回调。战场无面板时返回进入暂停；主菜单返回打开退出确认。后台通知冻结模拟、停声音、取消持住的 UI，前台保持暂停。

## 移动表现预算

| 档位 | 帧率上限 | 粒子 | 特效 | 飘字 | 纹理缓存 |
| --- | ---: | ---: | ---: | ---: | ---: |
| 默认 | 60 | 240 | 64 | 80 | 128 |
| 省电 | 30 | 100 | 32 | 48 | 96 |

后台上限为 10，主循环不推进模拟或重绘战场。纹理按最近访问淘汰；动画、采矿挥镐、攻击前摇、受击和命中事件保留。减少动效控制镜头与背景，省电控制表现数量，两者不会改变经济或伤害规则。

## 来源与实现位置

使用本机 Godot GDScript Patterns 与 UI UX Pro Max 技能，UI 约束参考 [UI UX Pro Max](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill)。屏幕 API 见 [Godot DisplayServer](https://docs.godotengine.org/en/stable/classes/class_displayserver.html)。确认使用当前版本源码：[4.7.2 ScrollContainer](https://raw.githubusercontent.com/godotengine/godot/4.7.2-stable/scene/gui/scroll_container.cpp)，其拖动路径依赖鼠标；不把 master 上新增的原生触屏实现当成本机已有功能。

方向映射见 [Godot 4.7.2 Android 导出源码](https://raw.githubusercontent.com/godotengine/godot/4.7.2-stable/platform/android/export/gradle_export_util.cpp)；Android 的数值含义见 [ActivityInfo 官方文档](https://developer.android.com/reference/android/content/pm/ActivityInfo#SCREEN_ORIENTATION_USER_LANDSCAPE)。

代码为 game/scripts/mobile_layout.gd、mobile_input.gd、mobile_ui.gd、mobile_scroll.gd、mobile_slider.gd；main.gd 管理生命周期和适配入口，battle_view.gd 处理取景与触屏可读标记，action_card.gd 处理触控卡与长按，data_store.gd 管理纹理 LRU，audio_controller.gd 管理后台声音。
''')
    rows=[]
    for c in matrix['cases']:
        report=json.loads((QA/c['name']/'report.json').read_text(encoding='utf-8'))
        rows.append(f"| {c['name']} | {c['physical_resolution']} | {c['density']} | {c['safe_insets_px']} | {c['checks']:,} | 通过 |")
    put(DOC/'03-设备矩阵与验收.md',f'''# 移动端验证与交付 · 3.0.0-rc3

八种屏幕配置 {matrix['checks']:,} 项、桌面 {desktop_count} 项、判定／工人／地图基础 {rule_count:,} 项，共 **{total:,} 项通过**。输入散列与当前源码核对，截图为 Windows 原生 Godot GPU 运行结果。Android 真机未连接。

| 配置 | 请求物理像素 | density | 左／上／右／下安全边距 px | 检查 | 结果 |
| --- | --- | ---: | --- | ---: | --- |
{chr(10).join(rows)}

实际 logical viewport 和安全内容边界记录在各 report.json 的 metrics。portrait-recovery 从 960×1280 的真实竖向 Windows 窗口开始，记录竖屏提示，随后转换为 1280×960 横屏继续相同流程。每组在指定横屏尺寸完成菜单、HUD 和 200 图检查后，才测试战局旋转暂停与恢复；recovery_metrics 另记录恢复后的窗口。16:10 平板采用 1920×1200，避免本机 Windows 将 1600 高度限制为 1421 后误标为指定尺寸。驱动脚本会核对实际物理尺寸。安全边距是可控注入值，不是手机硬件截图。

每组覆盖所有菜单类型、部署与返回链、长列表首尾、真实手指滑动、音量滑杆、省电、十阵营招募／退款、五十法术、长按资料、双指、拖动不施法、越 HUD 抬手、地图优先、路标、建造、工人身体范围施法、模态、返回键、后台音频与战局、胜负和退出。每组检查 200 张地图的矿点、建造位与我方路标在可玩区域内。

Windows 桌面完整原生指针检查 {desktop_count} 项通过；已有判定 834、工人 60、地图／关卡基础 4,010 项重新运行。伤害模拟、地图和关卡数据的散列保持 rc2 规则基线。正常预算移动布局对局另见 native-play/report.json；录像是静音离线 15fps 节选，不代表设备实时帧率。

## 证据与重跑

[八屏幕矩阵](../../../output/qa/godot/mobile-rc3/mobile-matrix.json) · [桌面报告](../../../output/qa/godot/mobile-rc3/desktop/report.json) · [规则检查](../../../output/qa/godot/mobile-rc3/rules/index.json) · [正常预算对局](../../../output/qa/godot/mobile-rc3/native-play/report.json) · [对照图](../../../output/qa/godot/mobile-rc3/before-after.jpg) · [设备状态](../../../output/qa/godot/mobile-rc3/android-devices.txt)

使用本机原生 Python 执行 tools/paper-warfront/check_mobile_adaptation.py；--case 可选择一组。主程序开发参数为 --mobile-ui --mobile-density 2 --mobile-insets 72,0,24,18 --qa-mobile <目录> --profile-path <隔离档案>。每个案例独立启动 Godot，并在结束时退出。发布包排除 tests/，上述 QA 脚本从源码运行。

## 发布与尚待硬件验证

新包位于 release/3.0.0-rc3，APK versionCode 为 30002，沿用原签名和 org.paperwarfront.game，支持覆盖安装并保留私有存档。Windows 与 Android 均包含当前共享脚本。APK 签名、CRC、zipalign 16KB、ARM64 ELF 对齐和包信息，以及真实 Windows EXE 启动，由构建／导出报告确认。

[下载与安装](../../../release/3.0.0-rc3/README.md)。最终归档校验与源码散列见 output/qa/godot/mobile-rc3/release-audit.json；归档 SHA256 另在发布目录。最终归档审计在压缩之后生成，以避免把源 ZIP 自身散列递归写入 ZIP。

Android 真机的实际安全区读数、系统手势冲突、音频焦点、30／60fps 能否达到、内存峰值与温度仍待硬件验证。本轮不把 Windows GPU、受控演员、离线录像或 200 图坐标检查当作 Android 人工体验或关卡胜率证据。
''')
    put(REL/'README.md',f'''# 纸上兵戈 · 3.0.0-rc3 移动适配版

[Android APK](android/PaperWarfront-3.0.0-rc3.apk) · [Windows 完整包](PaperWarfront-Windows-3.0.0-rc3.zip) · [Godot 源码](PaperWarfront-Source-3.0.0-rc3.zip) · [SHA256](SHA256SUMS.txt)

Android 横屏，支持两侧旋转。手机和平板按屏幕密度和安全区布局，按钮至少 48dp。直接招募／施法、军令、小地图、原生触摸滚动、滑杆和长按资料已实现。后台后需手动继续，可在设置开启 30 帧上限省电模式。

APK 沿用现有签名，包名 org.paperwarfront.game，versionCode30002；允许覆盖 rc2 保留存档。Windows 解压后运行 PaperWarfront.exe，旧显卡使用 Play-OpenGLCompatibility.cmd。程序包含全部资源，不需要安装 Godot。

[移动端文档与验证](../../docs/paper-warfront/mobile-rc3/README.md) · [原生画面](../../assets/paper-warfront/mobile-rc3-review.html) · [rc2 历史包](../3.0.0-rc2/README.md)

自动检查 {total:,} 项通过，含八组触屏／密度／安全区配置和 200 图可操作位置。Android 包体检查通过，尚未连接真机；不声称实际设备帧率或温度已验收。
''')
    put(ROOT/'README.md',f'''# 纸上兵戈：十院留名 / Paper Warfront 3.0.0-rc3

Godot4.7.2 原生纸偶即时策略。当前为移动适配版：屏幕密度、安全区、48dp 控件、手机与平板 UI、原生触摸、后台暂停与省电。每局 2–4 战斗兵种加工人，3–5 生产选择。

[Windows／Android](release/3.0.0-rc3/README.md) · [移动修复与证据](docs/paper-warfront/mobile-rc3/README.md) · [原生画面](assets/paper-warfront/mobile-rc3-review.html) · [完整文档](docs/paper-warfront/README.md) · [Godot工程](game/project.godot)

![移动端原生运行画面](output/qa/godot/mobile-rc3/after-hud.png)

本轮 {total:,} 项规则与界面检查通过。200 场景／193 几何、十院军库和 rc2 判定／采矿修复保留。Android 已重新导出签名 APK，真机仍待验证。

[原作地图研究](docs/research/swords-and-soldiers-map/recheck-20261008/README.md) · [3.0地图重做基线](docs/paper-warfront/redesign-3.0/README.md) · [rc2修复基线](docs/paper-warfront/fixes-rc2/README.md)
''')
    put(ROOT/'release/README.md','''# 本地游戏包

[当前 3.0.0-rc3 移动适配版](3.0.0-rc3/README.md) · [rc2 判定／采矿／视觉基线](3.0.0-rc2/README.md) · [rc1 地图基线](3.0.0-rc1/README.md) · [2.0 历史包](2.0.0/README.md)

新包以对应构建清单与检查报告为准。Android 尚未连接真机。
''')
    # Keep historical reports intact and add explicit current entry points.
    for name in ['07-交互与UI规范.md','11-Godot架构与数据契约.md','14-双平台构建与安装.md','15-运行验收与交付报告.md','16-玩家手册.md','22-双平台验收与发布.md']:
        p=ROOT/'docs/paper-warfront'/name;t=p.read_text(encoding='utf-8')
        marker='> 当前移动适配为 3.0.0-rc3：'
        if marker not in t:t=t.replace('\n','\n\n'+marker+'[实现与验证](mobile-rc3/README.md) · [双平台下载](../../release/3.0.0-rc3/README.md)。下文保留原系统规则；移动界面以新文档为准。\n',1)
        if name=='16-玩家手册.md' and '长按行动卡' not in t:t+='\n手机：长按行动卡查看资料；军令内研究、建造、队列与导航。返回先取消选择再返回／暂停。声音与显示中可开省电，后台恢复需手动继续。\n'
        put(p,t)
    p=ROOT/'docs/paper-warfront/README.md';t=p.read_text(encoding='utf-8')
    if '移动适配入口' not in t:t=t.replace('\n','\n\n当前为 **3.0.0-rc3 移动适配版**：[移动适配入口](mobile-rc3/README.md) · [当前下载](../../release/3.0.0-rc3/README.md)。rc2 判定／采矿／视觉报告保留为基线，当前移动交互和构建以 rc3 为准。\n',1)
    t=t.replace('当前为 **3.0.0-rc2 修复与视觉版**','**3.0.0-rc2 修复与视觉基线**').replace('本次实现和检查以[rc2文档体系](fixes-rc2/README.md)为准。','该版判定、采矿和素材记录保存在[rc2文档体系](fixes-rc2/README.md)，移动 UI 与发布包以 rc3 为准。')
    t=t.replace('[下载评审版](../../release/3.0.0-rc2/README.md)','[rc2 历史包](../../release/3.0.0-rc2/README.md)').replace('当前报告在fixes-rc2/05-验证与交付报告.md，构建在release/3.0.0-rc2；rc1报告保留为基线。','当前移动报告在 mobile-rc3/03-设备矩阵与验收.md，构建在 release/3.0.0-rc3；rc2 与 rc1 保留为基线。')
    if '| [移动端适配契约]' not in t:t=t.replace('| [交互与UI规范]', '| [移动端适配契约](mobile-rc3/README.md) | 屏幕密度、安全区、48dp、原生触摸、后台、八配置与实际发布验证。 |\n| [交互与UI规范]')
    put(p,t.replace('# 纸上兵戈：十院留名 · 3.0.0-rc2','# 纸上兵戈：十院留名 · 3.0.0-rc3'))
    p=ROOT/'game/README.md';t=p.read_text(encoding='utf-8').replace('工程 · 3.0.0-rc2','工程 · 3.0.0-rc3').replace('release/3.0.0-rc2','release/3.0.0-rc3')
    t=t.replace('；横屏布局增加`--mobile-ui`，并不等于Android真机。','；当前触屏适配使用 mobile_ui_qa.gd，Windows 注入不等于 Android 真机。')
    if '当前移动适配见' not in t:t+='\n当前移动适配见 [rc3 规范](../docs/paper-warfront/mobile-rc3/README.md)。移动回归使用 mobile_ui_qa.gd 与 check_mobile_adaptation.py；旧 theatre_ui_qa 的 mobile 标志属于 rc2 画布布局，不作为 rc3 触屏证据。\n'
    put(p,t)
    p=ROOT/'tools/paper-warfront/README.md';t=p.read_text(encoding='utf-8')
    if 'check_mobile_adaptation.py' not in t:t+='\n当前移动适配：check_mobile_adaptation.py 检查八组原生触屏与屏幕配置；check_mobile_preserved_systems.py 重跑桌面并录制普通预算对局；build_game.py 导出签名双平台；smoke_mobile_exports.py 检查实际 EXE；build_mobile_review.py 组合原生截图；write_mobile_docs.py 写已验证文档；audit_mobile_release.py --archives 核对最终包与当前源码；package_release.py 生成交付 ZIP。按此顺序运行，归档前先运行不带 --archives 的审计。\n'
    if 'prepare_mobile_fonts.py' not in t:t+='\nprepare_mobile_fonts.py 使用已授权完整源字体补齐当前 UI／数据汉字，记录源字体与子集散列；只在界面新增用字时运行，并在重建字体后重新做原生 UI 检查和导出。\n'
    put(p,t)
    put(ROOT/'docs/README.md','''# 项目文档入口

[当前移动端适配](paper-warfront/mobile-rc3/README.md) · [制作文档](paper-warfront/README.md) · [Windows／Android](../release/3.0.0-rc3/README.md)

[原作地图二次研究](research/swords-and-soldiers-map/recheck-20261008/README.md) · [六图重做基线](paper-warfront/redesign-3.0/README.md) · [rc2 判定／采矿／视觉基线](paper-warfront/fixes-rc2/README.md)

历史报告保存当时事实。rc3 的当前输入散列、触屏检查、构建版本和 Android 真机剩余验证独立登记。
''')
    p=ROOT/'assets/paper-warfront/README.md';t=p.read_text(encoding='utf-8')
    if '当前移动适配画面' not in t:t='**当前移动适配画面 · 3.0.0-rc3：** [原生画面与对照](mobile-rc3-review.html) · [移动契约](../../docs/paper-warfront/mobile-rc3/README.md)。本轮调整取景和 UI，不重新生成或替换角色／地形素材；以下保留素材制作基线。\n\n'+t
    put(p,t)
    (QA/'verification-index.json').write_text(json.dumps({'version':'3.0.0-rc3','mobile_checks':matrix['checks'],'desktop_checks':desktop_count,'rule_checks':rule_count,'total':total},indent=2)+'\n',encoding='utf-8')
    print(f'Wrote mobile docs: {total} passing checks')

if __name__=='__main__':main()
