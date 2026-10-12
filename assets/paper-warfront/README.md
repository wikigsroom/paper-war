# 纸上兵戈素材库 · 3.0.0-rc5

[原生 72 套完整动作查看](frame-rebuild-review.html) · [72 单位资产索引](frame-rebuild/roster.csv) · [角色定义](frame-rebuild/unit-briefs.json) · [帧加工来源](frame-rebuild/frame-provenance.json) · [手工校准与透明清理](frame-rebuild/frame-adjustments.json)

[完整方案与风格约束](../../docs/paper-warfront/frame-rebuild/README.md) · [阵营轮廓与真实参数](../../docs/paper-warfront/frame-rebuild/05-阵营轮廓与执行参数.md) · [最终视觉复核](../../output/qa/godot/frame-rebuild/visual-review.json)

十院各六种作战兵，十纸工、两召唤物，共 72 套、2592 个整身动作格。每个单位有独立身体和装备原型。先检查新原型、再生成整张帧表，不能用统一身体改色替代阵营。原图、种子、提示词与尝试记录位于 output/imagegen/paper-warfront/frame-rebuild/v2；运行图集位于 game/assets/animation/frames-v1。

正式运行绑定以 game/data 为准；最终视觉接受以相同输入的 visual-review.json 为准。加工阶段 candidate 标签与历史资源状态不构成最终接收。CSV 登记当前已复核版本。失败遮挡与缺格尝试在工作区历史中保存，未进入公开源码 ZIP 或运行包。

旧 400 作战模板数据保存于 frame-rebuild/legacy，340 个退役 ID 经游戏迁移表兼容。旧调色家族和关节切片不参与当前角色绘制。
