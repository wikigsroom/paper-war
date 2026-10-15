# 纸上兵戈素材库 · 3.0.0-rc5

## 已冻结品牌资产 · Branding 1.0.0

当前产品 Logo 组合已经确定：

- 图形 Logo：`brand.logo.character.yin_marshal.woodblock_ink`，即 **02 木刻墨印·印甲统帅**。
- 文字 Logo：`brand.logo.wordmark.battle_seal`，即 **朱印战印** 方案中的“纸上兵戈”字标。
- 主横向锁定组合：`brand.lockup.primary`，文字 Logo 在左、印甲统帅在右。

完整登记见 [branding.json](branding/branding.json)，素材加工记录见 [processing-record.json](branding/processing-record.json)。Banner 位于 `branding/banners/`，源背景位于 `branding/backgrounds/`。Banner 已按桌面、移动端、章节地图和商店/社交卡片分别输出，但不接入 Godot 菜单；本轮仅将图形 Logo 派生为游戏图标与 Android 自适应前景。

### 统一木刻 Banner 候选 · Branding 1.1.0 candidate

上一版 Banner 的背景与 Logo 质感不够统一，本轮候选使用同一套木刻 / 凹版纸剧场 Key Art，再以冻结的 02 木刻墨印·印甲统帅、朱印战印和本地字体完成精确排字。候选清单、配文、尺寸与 SHA-256 见 [branding-v2/branding.json](branding/v2/branding.json)；生成提示词、无文字背景和合成总览保留在 `output/imagegen/paper-warfront/branding-v2/`。候选 Banner 不替换现有菜单内容；选定图形 Logo 仅用于图标运行时资源。

运行时接入清单见 [game/data/branding-runtime.json](../../game/data/branding-runtime.json)，安装工具为 `tools/paper-warfront/install_branding_runtime.py`。游戏图标与 Android 自适应前景现已从选定图形 Logo 派生，菜单继续使用原有内容。

[原生 72 套完整动作查看](frame-rebuild-review.html) · [72 单位资产索引](frame-rebuild/roster.csv) · [角色定义](frame-rebuild/unit-briefs.json) · [帧加工来源](frame-rebuild/frame-provenance.json) · [手工校准与透明清理](frame-rebuild/frame-adjustments.json)

[完整方案与风格约束](../../docs/paper-warfront/frame-rebuild/README.md) · [阵营轮廓与真实参数](../../docs/paper-warfront/frame-rebuild/05-阵营轮廓与执行参数.md) · [最终视觉复核](../../output/qa/godot/frame-rebuild/visual-review.json)

十院各六种作战兵，十纸工、两召唤物，共 72 套、2592 个整身动作格。每个单位有独立身体和装备原型。先检查新原型、再生成整张帧表，不能用统一身体改色替代阵营。原图、种子、提示词与尝试记录位于 output/imagegen/paper-warfront/frame-rebuild/v2；运行图集位于 game/assets/animation/frames-v1。

正式运行绑定以 game/data 为准；最终视觉接受以相同输入的 visual-review.json 为准。加工阶段 candidate 标签与历史资源状态不构成最终接收。CSV 登记当前已复核版本。失败遮挡与缺格尝试在工作区历史中保存，未进入公开源码 ZIP 或运行包。

旧 400 作战模板数据保存于 frame-rebuild/legacy，340 个退役 ID 经游戏迁移表兼容。旧调色家族和关节切片不参与当前角色绘制。
