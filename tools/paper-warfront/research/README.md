# 地图研究与现版审计工具

当前结果入口：[2026-10-08 二次研究](../../../docs/research/swords-and-soldiers-map/recheck-20261008/README.md)。原作事实依赖其中的外部资料；这些工具只测量当前本作模拟、登记代码位置并绘制明确标识的示意图，不测量原作。

## 当前工具与复现

- `recheck_map_design.py`：只读 200 份地图、战役、规则和源码；统计拓扑、锚定模板与理论时间/收入。默认输出当前研究目录，复跑请用 `--output` 保留原基线。
- `probe_map_decisions.gd`：本机原生 Godot、60 Hz、种子 137、关闭双方 AI，共 49 组经济/路线/接战夹具。直接建立测量对象，不包含生产排队/扣款，不写存档；输出结束状态与下一步路由。
- `collect_primary_map_sources.py`：公开网页只读元数据收集，失败项照实记录。它不代替 web 正文重读，也不意味着所有图像/页面可访问。
- `render_map_recheck.py`：Pillow 与本项目许可字体；从已有测量、原创白盒规格与本地原始截图绘制三张研究图。不下载远程媒体，不生成生产游戏素材。
- `verify_map_recheck.py`：检查研究链接、输入散列、测量数量、白盒约束与 PNG 文件，写证据清单；通过只代表研究材料一致。

在工作区根目录运行 PowerShell：

```powershell
& 'C:/Python313/python.exe' 'tools/paper-warfront/research/recheck_map_design.py' --output 'docs/research/swords-and-soldiers-map/recheck-20261008/current-map-audit-rerun.json'

$mapProbeScript = (Resolve-Path -LiteralPath 'tools/paper-warfront/research/probe_map_decisions.gd').Path
$mapProbeDirectory = (Resolve-Path -LiteralPath 'docs/research/swords-and-soldiers-map/recheck-20261008').Path
$mapProbeResult = Join-Path $mapProbeDirectory 'native-probes-rerun.json'
& '.tools/godot/Godot_v4.7.2-stable_win64_console.exe' --headless --path 'game' --script $mapProbeScript -- $mapProbeResult

& 'C:/Python313/python.exe' 'tools/paper-warfront/research/render_map_recheck.py'
& 'C:/Python313/python.exe' 'tools/paper-warfront/research/verify_map_recheck.py'
```

复跑输出是复跑当时的规则结果；若已修复运输或调地图，差异应保留，而非覆盖旧结果后声称旧版已通过。报告中的 2026-10-08 和固定夹具参数说明研究批次，输入散列说明具体版本。

图像工具默认使用原始 `current-map-audit.json` / `native-probes.json`，以保持报告基线。更换测量批次需新建报告目录并调整工具输出入口，不把新旧版本合并。

## 历史 1.0 工具

`probe_map_equivalence.gd` 与 `build_map_audit.py` 对应 [历史 1.0 审计](../../../docs/research/swords-and-soldiers-map/03-当前版本差距审计.md)。它们的三个旧 map ID、旧输入/API 和输出不能直接用于当前 3.0。不要复跑后覆盖历史文件，再把旧结论误用于新版本。

全部使用 Windows 原生工具，没有 Docker、WSL、虚拟机、模拟器或外部 3D 建模依赖。白盒属于文档提案；探针退出码正常或图片成功生成，都不证明地图已经可玩或通过验收。
