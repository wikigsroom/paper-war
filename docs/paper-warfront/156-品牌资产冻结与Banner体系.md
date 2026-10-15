# 《纸上兵戈》品牌资产冻结与 Banner 体系 · 1.0.0

## 选择结果

本轮正式记录用户选择：

| 资产类型 | 选择 | 稳定 ID |
| --- | --- | --- |
| 图形 Logo / Icon | 02 木刻墨印·印甲统帅 | `brand.logo.character.yin_marshal.woodblock_ink` |
| 文字 Logo | 朱印战印方案中的“纸上兵戈”字标 | `brand.logo.wordmark.battle_seal` |
| 主锁定组合 | 文字 Logo 左、印甲统帅右 | `brand.lockup.primary` |

两项 Logo 均来自已检查的透明源图。图形 Logo 不包含文字、字母、数字、符文或水印；文字 Logo 只在已选中的字标源图中出现“纸上兵戈”。Banner 的背景没有重新生成文字，均通过已选 Logo 进行合成。

## Banner 输出

| 稳定 ID | 文件 | 尺寸 | 用途 |
| --- | --- | --- | --- |
| `brand.banner.main` | `banner-main-1920x800.png` | 1920×800 | Windows 主菜单、桌面落地页 |
| `brand.banner.mobile_splash` | `banner-mobile-1080x1440.png` | 1080×1440 | Android 竖版启动/宣传画面 |
| `brand.banner.chapter_map` | `banner-chapter-map-1600x900.png` | 1600×900 | 单机章节地图、路线选择 |
| `brand.banner.social` | `banner-social-1200x630.png` | 1200×630 | 商店、发行说明、社交分享卡片 |
| `brand.lockup.primary` | `brand-lockup-transparent.png` | 1600×620 | 无背景 UI、加载页、合作物料 |

源背景保存在 `assets/paper-warfront/branding/backgrounds/`，正式合成结果保存在 `assets/paper-warfront/branding/banners/`。透明 Logo 的原始生成图仍保留在 `output/imagegen/paper-warfront/`，提示词与处理哈希见 `branding/processing-record.json` 和 `branding/branding.json`。

## 使用约束

- 横向 Banner 四周保持至少 7.5% 安全边距；不把字标压到地平线、桥梁或城门关键轮廓上。
- 移动端 Logo 组放在画面上 62% 区域内，底部预留手势条和系统安全区。
- 角色 Logo 必须保留完整头盔、披带、盾牌与双脚，不做会破坏识别的裁切。
- 文字 Logo 不在运行时重新由图片模型绘制；需要新尺寸时从已选源图缩放或按既定处理工具加工。
- 这些 Banner 已作为品牌素材交付，但尚未替换 Godot 工程的 `config/icon`、启动画面或主菜单控件；接入需单独进行运行包与移动端安全区验收。
