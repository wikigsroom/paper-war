# Godot 工程 · 纸上兵戈

当前工程与双平台预览为 3.0.0-rc41-night-lantern-components；本版将“夜战灯笼”方向细化到任务简报、实时战斗、结算页的组件几何与纸材状态，并接入 `background.night-lantern` 夜战底图；品牌 Logo 仍只用于游戏图标与 Android 自适应前景。迷雾失效缓存、单机剧情地图路线、阵营差异、动作帧合同和输出资源排除继续沿用。项目内容、实机 GIF、构建方式和仓库约束见根目录 [README](../README.md)；当前验收范围见[夜战灯笼组件级对标与 rc41 验收](../docs/paper-warfront/162-夜战灯笼组件级对标与rc41验收.md)。

使用 Windows 原生 Godot 4.7.2 打开 project.godot 后运行 main.tscn。项目使用 GDScript 与原生 Control，60Hz 战斗模拟独立于完整姿态图集绘制。现成 PNG 已包含，启动和导出不需要调用图片服务。

[完整设计与约束](../docs/paper-warfront/frame-rebuild/README.md) · [玩家手册](../docs/paper-warfront/16-玩家手册.md) · [地图与剧情路线](../docs/paper-warfront/147-单机地图剧情合同与路线分支验收.md)

72 个单位分别由 unit-frames.json、unit-actions.json、assets.json 和 balance-prototype.json 管理帧、动作语义、资源与规则。UnitFramePlayer 选完整帧，BattleView 只绘制完整姿态；飞弹、命中、持续状态、实际路径、工作 FIFO 和资源由模拟执行。旧关节脚本保留历史，不进入当前导出。

当前 QA：tools/paper-warfront/check_frame_rebuild.py 的 import、contracts、gallery、motion、duels、audio、pan；随后 check_mobile_adaptation.py 和 check_mobile_preserved_systems.py。使用 Windows 原生 Python，不能运行 Docker、WSL 或模拟器。

构建：配置 Godot 4.7.2 原生控制台和官方导出模板、Android SDK 36 与 JDK 21。`build_game.py` 生成 EXE / APK，`smoke_mobile_exports.py` 检查实际程序，`package_release.py` 打包，`capture_gameplay_gif.py` 从 Windows 原生包生成 README GIF；当前预览使用 `audit_preview_build.py` 核验源数据、编译包、UI 和 ZIP 内验证记录。导出预设明确排除 `output/*` QA 生成物。工具使用本地 `.tools/godot` 路径；机器变更时先配置路径，不更改游戏数据。

本地签名凭据位于项目外部的 .keys，禁止提交、复制到公共目录或交付包。素材新增仅通过用户指定 sub2-image-gen / gpt-image-2.5，技能配置和密钥不随工程交付。
