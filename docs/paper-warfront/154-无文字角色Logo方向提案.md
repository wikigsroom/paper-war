# 《纸上兵戈》无文字角色 Logo 方向提案 · v1

本轮基于当前暖纸、墨线、折叠厚片、朱印与玉青风格，使用 `sub2-image-gen` / `gpt-image-2.5` 生成 5 款不带文字的角色型 Logo。每款都以一个中心形象承担品牌识别，可作为应用图标、启动页主标或菜单角标；目前尚未接入 Godot 正式资源。

## 共同约束

- 图像中禁止中文、英文、数字、符文、伪文字、水印和 UI。
- 角色必须有清楚的外轮廓，在 256px 与 64px 观察尺寸下仍能辨识。
- 统一使用暖白纸 `#F3EBDD`、纸色 `#E8DECA`、墨色 `#343332`、朱印 `#B74532`、玉青 `#377B78` 与少量金 `#B9964F`。
- 使用分层纸片、折痕、纸纤维和克制纸边阴影；不使用金属、霓虹、写实 3D 或复杂场景背景。
- 正式接入前需要从选定候选派生：方形 Icon 裁切、横向主 Logo 构图、浅底/深底变体、单色压印版和 Godot 导入资源。

## 五个方向

| ID | 角色 | 识别特征 | 适合用途 |
| --- | --- | --- | --- |
| `logo.character.seal_marshal` | 纸甲统帅 | 纸甲、朱色披带、折纸剑、玉青盾 | 最稳的主 Icon 与产品主标，军事感直接 |
| `logo.character.kite_scout` | 鸢纸斥候 | 玉青风筝翼、长枪、动态斜向轮廓 | 适合启动页、移动端 Icon、横向动效标志 |
| `logo.character.ink_tiger` | 墨骸纸虎 | 墨色纸虎、玉青鬃、卷尾与大爪 | 最适合作为亲和力强的产品 Mascot |
| `logo.character.bridge_warden` | 纸桥守关 | 城门头盔、拱桥盾、玉青短矛 | 最能表达地图、关隘、道路与防守主题 |
| `logo.character.lantern_strategist` | 提灯策士 | 黑玉纸袍、空白纸扇、折纸提灯 | 最适合单机剧情、章节地图和故事品牌 |

## 本地产物

生成源图、无文字提示词、对比板、256px 图标观察板和哈希清单位于：

`../../output/imagegen/paper-warfront/logo-character-v1/`

- `01-seal-marshal.png`
- `02-kite-scout.png`
- `03-ink-tiger.png`
- `04-bridge-warden.png`
- `05-lantern-strategist.png`
- `logo-character-contact-sheet.png`
- `logo-character-icon-grid.png`
- `logo-character-icon-crops.png`
- `icons/*-icon.png`
- `manifest.json`
- `prompts/*.txt`

对比板的暖纸底只是预览辅助层；正式候选仍以透明 RGBA 源图为准。生成图不能作为运行性能证据，也不会在方向冻结前替换现有 Logo。
