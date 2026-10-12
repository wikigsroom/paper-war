# 原生制作工具 · 3.0.0-rc1

当前游戏可直接导入Godot4.7.2，资源已提供。[研究](research/README.md) · [六图与实施](../../docs/paper-warfront/redesign-3.0/README.md)。所有工具使用Windows原生环境，不调用Docker、WSL、虚拟机或模拟器。

| 当前工具 | 用途与边界 |
| --- | --- |
| author_baseline_maps.py | 六张独立基准规格；会覆盖对应当前配置，已有后续调整时先备份 |
| author_campaign_maps.py | 保留六图，对另外194关按20阶段及10地域规划生成；会改写地图和关卡 |
| publish_theatre_assets.py | 新核心／工人／建筑／背景／装饰的整轮廓加工、头像、脚点和分件 |
| publish_theatre_role_library.py | 40角色母版及360个派生变体，来源和复用记录，不是400独立生成 |
| review_theatre_sources.py | 源图联系板，不自动宣称验收；props-yin以repairs修复源为准 |
| write_theatre_docs.py | 首次保存2.0文档历史；--refresh按当前数据更新22规范、200简报、图示及离线素材库 |
| optimize_fonts.py | 读取运行脚本及数据生成OFL中文字体子集；完成后再Godot导入 |
| audit_theatre_release.py | 当前文件／散列／真实几何／原生证据／来源／本地链接；--archives再检ZIP CRC与排除凭据 |
| build_game.py | 原生双平台导出、签名、包架构及16KB对齐 |
| package_release.py | Windows ZIP、源码ZIP、清单；排除签名配置、引擎和缓存 |

验证脚本在game/tests。test_map_transport覆盖200图的602无限矿；test_theatre_decisions覆盖六图路线、援军和任务边界；test_world_combat用公共命令招募并测伤害；theatre_ui_qa原生注入指针；record_theatre_battle记录正常预算下完整GPU对局。所有原生QA应使用--profile-path隔离用户存档。

先完成数据／素材／文档与相应检查，再build_game，再检查新EXE，再audit_theatre_release、package_release、audit_theatre_release --archives。原作研究保留输入和失败，不用当前游戏覆盖历史审计。

expand_world、prepare_theatre_rules、write_v2_docs、旧2.0校验及交付工具仅作历史复现；其中批量生成会恢复旧模板，不能直接覆盖当前六图与194空间简报。test_campaign_paths针对旧编组，不能作为本版通过证据。

源图生成沿用用户指定sub2-image-gen／gpt-image-2.5；项目不复制网关配置和密钥。无需重新生成图片即可运行交付工程。Android包检查不替代真机验收，自动胜利不替代人工平衡。

当前移动适配：check_mobile_adaptation.py 检查八组原生触屏与屏幕配置；check_mobile_preserved_systems.py 重跑桌面并录制普通预算对局；build_game.py 导出签名双平台；smoke_mobile_exports.py 检查实际 EXE；build_mobile_review.py 组合原生截图；write_mobile_docs.py 写已验证文档；audit_mobile_release.py --archives 核对最终包与当前源码；package_release.py 生成交付 ZIP。按此顺序运行，归档前先运行不带 --archives 的审计。

prepare_mobile_fonts.py 使用已授权完整源字体补齐当前 UI／数据汉字，记录源字体与子集散列；只在界面新增用字时运行，并在重建字体后重新做原生 UI 检查和导出。

rc15紧凑HUD检查使用`check_compact_hud.py`：桌面、普通手机、紧凑手机与额外矮屏，验证收起状态≥70%的净可见战场、真实收费／退款、兵卡横向滚动以及同屏／联机控制面板。`capture_packaged_recruitment_ui.py`在同四种配置下读取实际EXE编译资源，并与实际APK字节核对；联机面板的发送回调是测试夹具，不代表TCP传输或真人对战。发布前由`audit_preview_build.py`核对源码、编译逻辑、屏幕矩阵、交付散列与ZIP内同一验证记录。
## rc16 折纸 UI

`prepare_paper_ui.py` 加工用户指定 Sub2API / gpt-image-2.5 的三张源图；保留 Alpha、按经检查的空隙切割，将折角压入固定12像素切片，输出38项资源与哈希记录。不重新生成文字。

`check_paper_ui.py` 检查桌面与手机各21个原生界面／状态及实际付款、禁用与持按。`--pack release/3.0.0-rc16-preview/windows/PaperWarfront.exe --output output/qa/godot/ui-rc16/release/paper-ui` 使用 EXE 内的真实编译应用与外部测试脚手架；不会用源码替代包内逻辑。移动指标注入仍不等于 Android 真机。

