# 《纸上兵戈》统一木刻 Banner 与配文方案 · 1.1.0 candidate

## 本轮修订目的

1.0 的 Banner 使用了不同质感的场景背景，再把 Logo 贴到场景上，导致角色、纸张、色彩和文案像来自不同套视觉系统。本轮以已经选定的 **02 木刻墨印·印甲统帅** 与 **朱印战印** 为两个固定锚点，重新用 Sub2API / `gpt-image-2.5` 生成无文字的共同纸剧场 Key Art，再由本地字体完成精确排字。

这样处理后，配图负责氛围、角色和地图语义；Logo 与配文负责品牌识别和可读性。模型生成图不承载任何正式文字，避免错字、伪文字和不同 Banner 间字形漂移。

## 冻结的品牌输入

| 输入 | 稳定 ID / 标签 | 源文件 |
| --- | --- | --- |
| 图形 Logo | `brand.logo.character.yin_marshal.woodblock_ink` / 02 木刻墨印·印甲统帅 | `output/imagegen/paper-warfront/logo-character-v2/02-woodblock-ink-warrior.png` |
| 文字 Logo | `brand.logo.wordmark.battle_seal` / 朱印战印 | `output/imagegen/paper-warfront/logo-directions-v1/01-battle-seal.png` |
| 产品显示名 | 纸上兵戈 | 文字 Logo 源图中的可见字标 |

文字 Logo 的选择名是“朱印战印”，源图里的可见字标是“纸上兵戈”。两者是同一项已选择的品牌资产，不应在文案中混写成两个产品名。

## 统一视觉参数

- **媒介隐喻**：木刻印版 + 纸剧场 + 少量套色错位。角色、城墙、道路、云和地图节点都必须像同一张纸上印出的层片。
- **主色**：墨黑 `#343332`、朱砂 `#B74532`、象牙 `#F3EBDD`、旧纸 `#E8DECA`。
- **功能色**：玉青 `#377B78` 仅用于章节节点或次级行动色；旧金 `#B9964F` 仅用于铆钉、印章圆心和少量强调。
- **禁止项**：渐变、霓虹、玻璃、发光、写实 3D、风景油画感、黑色暗角、生成式文字、符文、水印、额外可读标记。
- **角色锚点**：朱砂方盔、宽方甲、象牙色空白矩形盾、短折剑、撕裂朱砂披带。Banner 背景里的角色必须与该轮廓一致；不能把角色换成通用骑士或真人。
- **留白锚点**：主横幅左侧、移动端上方、章节卷轴左半必须保留连续的象牙纸面，给字标和排字使用。

## Banner 与配文清单

| 稳定 ID | 输出尺寸 | 配图结构 | 精确配文 | 使用位置 |
| --- | ---: | --- | --- | --- |
| `brand.banner.main.v2` | 1920×800 | 右侧印甲统帅走过折纸桥，远处墨色关城与朱砂日盘，左侧整块留白 | `一纸成阵，横行破局`；`自动行军 · 金币与法力 · 雾中决策`；`把每一次推进，都变成可读的战局。`；`展开战局`；底部签名 `PAPER WARFRONT  ·  纸上兵戈` | Windows 主菜单、桌面落地页 |
| `brand.banner.mobile_splash.v2` | 1080×1440 | 下半部角色站在折纸道路，左下朱砂关门、右下墨色桥堡，上方留白 | `纸上起兵，所见即战局`；`自动行军 · 金币与法力 · 雾中决策`；`展开战局` | Android 竖版启动、商店宣传 |
| `brand.banner.chapter_map.v2` | 1600×900 | 左侧卷轴留白，右侧分岔路线、三色节点、桥标和印甲统帅 | `每一次分岔，都是一场战役`；`路线未定，战局先行。`；`进入章节` | 单机章节地图、路线选择 |
| `brand.banner.social.v2` | 1200×630 | 主横幅 Key Art 的社交裁切，左侧小型纸牌排字 | `布阵 · 推进 · 破城`；`一纸成阵，横行破局`；`自动行军 · 雾中决策`；`纸上兵戈` | 商店图、发行说明、社交卡片 |
| `brand.lockup.primary.v2` | 1440×520 | 一张连续象牙纸板，左字标、中央朱砂线、右印甲统帅 | 无新增文案；只使用已选字标 | 无背景 UI、加载页、合作物料 |

文件对应 `output/imagegen/paper-warfront/branding-v2/final/`，正式候选副本对应 `assets/paper-warfront/branding/v2/`。

## 生成与排字流程

1. 在 `output/imagegen/paper-warfront/branding-v2/prompts/` 固定三张无文字 Key Art 提示词，模型统一使用 `gpt-image-2.5`，并记录实际输出尺寸和 SHA-256。
2. 对生成图做人工图像检查：角色轮廓、留白区、地图节点、纸张层次、禁用文字与水印均通过后才进入合成。
3. 使用 `tools/paper-warfront/compose_branding_v2.py`，从冻结的 Logo 源图取透明内容；用 `game/assets/fonts/NotoSerifSC.ttf` 与 `game/assets/fonts/NotoSansSC.ttf` 渲染文案。
4. 合成结果经过尺寸、色彩、可读字形、Alpha 和接缝检查；任何 Banner 的字标或配文都不得重新交给图像模型绘制。

配文使用“雾中决策”和“所见即战局”是字体覆盖范围内的稳定写法，避免当前随包 Noto 子集缺少“迷”“皆”时出现方框字。后续若扩充字体子集，应先更新字体资产和检查记录，再讨论是否恢复旧措辞。

## 安全区与裁切约束

- 桌面横幅四周至少保留 7.5% 安全边距；左侧纸板不进入角色、城墙和桥梁的关键轮廓。
- 移动端上方排字区不得超过画面高度 50%；底部保留系统手势条、刘海和状态栏安全区。
- 章节卷轴内的 Logo 与配文只占卷轴可读面，不覆盖路线节点；节点和角色保持完整。
- 社交卡片缩小到 600px 宽仍必须能读出字标、主标题和三个玩法关键词。
- 正式 UI 接入前，还需使用实际 Godot 启动场景、章节页和 Android 安全区做运行时采样；生成图本身不构成运行性能证据。

## 文件与检查记录

- 生成提示词：`output/imagegen/paper-warfront/branding-v2/prompts/`
- 无文字背景：`output/imagegen/paper-warfront/branding-v2/backgrounds/`
- 候选成品：`output/imagegen/paper-warfront/branding-v2/final/`
- 候选清单与哈希：`output/imagegen/paper-warfront/branding-v2/branding-v2-manifest.json`
- 可复用加工脚本：`tools/paper-warfront/compose_branding_v2.py`
- 预览总览：`output/imagegen/paper-warfront/branding-v2/branding-v2-banner-contact-sheet.png`

本轮候选 Banner 与 `branding-v2` 目录已完成静态尺寸、字体方框和人工视觉检查，但暂不替换 Branding 1.0.0 的历史文件，也暂不宣称已经接入 Godot 运行时。
