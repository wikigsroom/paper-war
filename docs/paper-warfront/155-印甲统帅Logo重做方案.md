# 《纸上兵戈》印甲统帅 Logo 重做方案 · v2

上一轮角色 Logo 过于接近精细角色设定图，和当前运行中的平面纸偶美术不够贴合。本轮固定 **印甲统帅** 为唯一核心角色，只改变 Logo 的图形表现语言，重新生成 5 个可用于 Icon 与产品主 Logo 的无文字候选。

## 统一角色锚点

- 方形朱红头盔与方肩甲。
- 空白朱红矩形盾牌，不放文字、徽记或伪文字。
- 短折纸剑、短披带、墨色内甲和少量金色连接件。
- 角色比例、轮廓和色块参考当前运行中的 `unit.yin.axe` / `portrait.yin.commander`，不引入新阵营形象。

## 五种表现风格

| ID | 风格 | 重点 | 适用场景 |
| --- | --- | --- | --- |
| `logo.yin_marshal.flat_cutout` | 平面纸偶 | 8–12 个大色块、粗墨线、直接复用当前 Sprite 语言 | 最稳妥的产品 Icon 与主 Logo |
| `logo.yin_marshal.woodblock_ink` | 木刻墨印 | 墨黑/朱红双色、粗糙版画边缘、强剪影 | 战斗加载、章节印章、深色背景 |
| `logo.yin_marshal.stage_shadow` | 纸剧场 | 角色、朱甲、墨色舞台影三层套印 | 主菜单、纸片舞台品牌标记 |
| `logo.yin_marshal.geometric_origami` | 几何折纸 | 低多边形折面、头盔与盾牌作为识别锚点 | 移动端 Icon、启动页、缩小图标 |
| `logo.yin_marshal.chibi_mascot` | Q 版纸偶 | 更大头部、更短身体、亲和表情 | 产品 Mascot、商店图标、宣传物料 |

## 本地产物

源图、逐款提示词、对比板、小尺寸检查和哈希登记位于：

`../../output/imagegen/paper-warfront/logo-character-v2/`

- `01-flat-paper-puppet.png`
- `02-woodblock-ink-warrior.png`
- `03-stage-shadow-warden.png`
- `04-geometric-origami-marshal.png`
- `05-chibi-paper-marshal.png`
- `logo-character-v2-contact-sheet.png`
- `logo-character-v2-64px-check.png`
- `manifest.json`
- `prompts/*.txt`

五张源图请求尺寸为 1024×1024，服务实际返回 1254×1254 透明 RGBA PNG；均明确禁止文字、字母、数字、符文和水印。对比板标签只用于评审，不属于正式 Logo 资源。

本轮仍是候选方案，未替换 Godot 中的正式 Logo；方向冻结后再制作浅底、深底、单色压印和最终导入规格。
