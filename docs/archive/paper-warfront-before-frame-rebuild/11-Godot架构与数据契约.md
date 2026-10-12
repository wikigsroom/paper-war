<!-- rc2-current-note -->

> 当前移动适配为 3.0.0-rc3：[实现与验证](../../paper-warfront/mobile-rc3/README.md) · [双平台下载](../../../release/3.0.0-rc3/README.md)。下文保留原系统规则；移动界面以新文档为准。
**当前3.0.0-rc2补充：** damage是统一敌友保护边界；attack/launch、前摇、飞行和状态脉冲重查side与source_uid。physical_anchor/physical_point区分矿服务锚点和实际身体站位，同时供战斗及渲染使用。ui_theme和paper_panel管理原生主题。

[本次完整约束与证据](../../paper-warfront/fixes-rc2/README.md)。以下rc1正文保留其地图重做基线含义。
<!-- /rc2-current-note -->

# Godot架构与数据契约 · 3.0.0-rc1

当前为 **3.0.0-rc1 地图重做评审版**。自动规则与原生代表画面已有证据；原作 HD 未在本机运行，200 关人工平衡和 Android 真机尚未验收。参数以 `game/data` 为准。

data_store读取maps／campaign／factions／balance／technology／assets；main管理Control菜单、模态、指针输入与原子存档；battle_sim独立60Hz，map_runtime管理节点、边、真实坐标与路径提交；unit_abilities管理能力；tactical_ai仅发公共命令。battle_view／theatre_ground／theatre_hud消费状态和事件；audio_controller消费同一反馈事件。

地图必须包含nodes、edges、bases、mines、build_sites、presentation、design_card；地表边单独标明，ground_y_at在实际请求x插值。工人目标路径不能立即重入当前位置同一边；岔路选择在到节点后承诺，已进入边的单位不瞬移。

命令带序号防重复支付。先校验阵营、编组、科技、资源、目标和位置，再修改。事件附位置y及命中进攻方；渲染不能回写战斗。存档schema2，通过.tmp原子替换；QA以--profile-path隔离用户档。

[制作入口](README.md) · [地图重做与证据](../../paper-warfront/redesign-3.0/README.md)
