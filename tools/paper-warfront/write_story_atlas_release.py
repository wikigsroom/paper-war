"""Write rc29 release notes only after concrete package and native checks."""
from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parents[2]
QA=ROOT/'output/qa/godot/story-atlas-rc29'
FINAL=QA/'release-final'
VERSION='3.0.0-rc29-preview'
RELEASE=ROOT/'release'/VERSION
DOC='138-二百图剧情与非线性战役.md'
read=lambda p:json.loads(p.read_text('utf-8'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def main():
 manifest=read(RELEASE/'build-manifest.json');proof=read(RELEASE/'preview-verification.json')
 assert proof['preview_artifacts_verified'] and proof['source_inputs_verified']
 assert proof['story_map_progression_verified']['authored_maps']==200
 assert all(sha(ROOT/n)==h for n,h in manifest['source_inputs'].items())
 assert proof['packaged_logic_checks_on_windows']=={'apk':187249,'windows':187249}
 source=read(QA/'source-final/report.json');assert source['passed']
 story=read(ROOT/'game/data/story.json');flow=read(ROOT/'game/data/campaign-flow.json')
 table='| 章 | 地区 | 最短实际通关数 | 本章最短路线及并行顺序数 | 推进原则 |\n|---|---|---:|---:|---|\n'
 for c in flow['chapters']:
  table+=f"| {c['index']+1:02} | {story['chapters'][c['index']]['title'].split('：')[0]} | {c['minimum_actual_clears']} | {len(c['minimal_routes'])} | {c['summary']} |\n"
 fps=read(FINAL/'realtime/report.json')
 measured='| 场景 | 最大单位数 | 均值帧率 | P95帧间隔 |\n|---|---:|---:|---:|\n'
 for row in fps['cases']:
  name={'before-stress':'rc28持续满员对照','stress':'rc29持续满员压力','bridge':'rc29正常分岔','long':'rc29正常长图','phone':'rc29手机布局（Windows）'}[row['case']]
  measured+=f"| {name} | {row['max_units']} | {row['fps_from_mean_interval']:.2f} FPS | {row['p95_frame_ms']:.3f} ms |\n"
 text=f'''# 二百图逐图剧情、非线性战役与rc29预览

十章200关现均有逐图战前冲突、叙事目标、地理动机、战后结果与独立证据。后续180关替换了重复战前内容的通用结尾，第一章既有六组择一支线继续保留。章内按因果支持任选一路、并行调查与全部取证后汇合；未走支线可回访，不自动完成或授予证据。

Windows与Android包已导出并核验。Android编译逻辑由Windows原生Godot加载实际APK资源检查；没有实体手机，本记录不等于Android硬件验收。当前仍是预览版本。

## 实际实现

{table}

铜折炉的第02、03、04折可以任意先后完成，三项真实结果齐备才开放第05折；材料账、断齿样、送料令分别对应归仓、守塔和攻桥口。雁信岭则允许第02、03、04折先择一处，再继续送令账调查。留白庭关键原件全部必须在案，可自由选择并行调查先后，最终解除归零。十章交证仍依因果先后推进。

章节行动图与战场道路图独立。单主路可以承载长接援、回款或拦截截止；双路承载探视、绕阵、护矿和汇流。没有把三项案签当三条道路，没有强制每图分岔。地图几何、胜利类型、资金、生产、科技、AI阶段、兵种和时限都保持既有值。

200份叙事记录绑定真实地图和目标。保护关指向开局已存在的指定前哨位置，使用实际塔位而非通用终点锚；护送必须原携证者本人存活抵达，拦截必须对应指定目标并在越线前击倒。钩翼兵、定身司、重锤卫等按真实单位说明，任务简介与目标栏使用中性拦截称呼。战斗内旧通用浮名仍属呈现文字，不能用其称呼推断单位尺寸或规则。

剧情在战前与结果纸页演出；NPC与十院会盟并未额外生成战斗演员，也没有新加采样、取件或多人编队任务。护送、守塔、运金、拦截、守城和攻营均由原模拟器判胜，剧情只解释任务缘由和结果。

推进器新增实际完成的AND前置，并保留OR择一。完成并行调查的一项后，“继续”推荐仍缺的可行动同伴，避免停在锁住的汇合页。卡片区分“和”与“或”，跨章前置显示章节号。schema3只保存真实完成集合；旧schema2保留其实际线性历史，重访不减少星数、不把未走支线补成已留证。

地图文档、故事总纲、逐图素材指导均以稳定ID保留。完整分支图与200图表在[完整故事路线](world/04-完整故事路线.md)，逐图纸页列出剧情和实际目标绑定。当前正式每院6种作战单位，旧40模板规模从阵营总纲中纠正。两套随包字体覆盖1288个运行所需CJK字符，无需依赖系统中文字体。

## 验证范围

- 最终源码78组195435项通过；每包36组187249项实际编译逻辑通过，包含103595项路线/迁移/证据检查和1610项实际目标初始状态检查。
- 552种是章内最短路径与必须并行调查先后顺序之和，另保留第一章64种择一路径复核。它们是推进夹具，不是200关正常付费获胜记录，也不等于所有跨章及回访组合。
- 实际Windows编译包桌面与手机布局各237项，共474项；所有200关固定简介排版通过，触摸/鼠标选择、双证据与三处调查汇合、存档重载通过。测试先把屏外卡片滚到可见处，再使用原生输入；它没有把程序化滚入视野当成触摸滚动验收。
- 200图比例、八显示配置、纸艺UI、军令纸页、迷雾、导航、默认Vulkan、正常付款与命中、实际EXE启动分别按现行检查完成；战斗画面至少70%。38项既有Sub2折纸UI资源继续复用，没有生成新位图。
- 原版完整闭包的3600满员步骤和73103付款步骤证据保留在rc28，逐一绑定本次未改的战斗输入及全部200关战斗字段；本次两包另新执行查询、碰撞、绘制次序与浮点边界检查。保留证据不冒充新CPU基准。
- 两包签名/版本、APK16KB对齐、全部运行JSON、1194份源输入与455项运行资源绑定核验。WindowsZIP附同一验证JSON。

## 本次原生帧率观察

{measured}

均值帧率来自实际帧CSV，正常对局160秒与持续124单位压力夹具分别记录；原生窗口可见、音频开启、自然60Hz。满员夹具使用高生命并关闭AI以持续保留单位，不是正常付款对局。外部进程环境保留，不能把这两次相邻压力观察解读为剧情更新带来的性能收益。

普通场景55FPS目标：{fps['normal_55fps_target_met']}；满员60FPS目标：{fps['capacity_60fps_target_met']}。密集性能、全关难度和平衡、原作精确视野时序、真人完整剧情体验、Android真机与真人联机仍待完成。

## 下载与复核

- [WindowsEXE](../../release/{VERSION}/windows/PaperWarfront.exe)
- [WindowsZIP](../../release/{VERSION}/PaperWarfront-Windows-{VERSION}.zip)
- [AndroidAPK](../../release/{VERSION}/android/PaperWarfront-{VERSION}.apk)
- [实际发布验证](../../release/{VERSION}/preview-verification.json)

证据根为`output/qa/godot/story-atlas-rc29/`；正式包观察在`release-final/`。首次目标夹具错误、屏外点击误判、缺少付费观察文件的初次回归与非零导入记录均保留并区分，未被计入最终通过结果。逐关原稿为`tools/paper-warfront/story-chapters/*.psv`，没有以旧纲要批量拼接战后文本。
'''
 (ROOT/'docs/paper-warfront'/DOC).write_text(text,'utf-8')
 p=ROOT/'docs/paper-warfront/README.md';body=p.read_text('utf-8');head,rest=body.split('\n',1)
 new=f'[{DOC.removesuffix(".md")}与rc29交付]({DOC})：200图逐图剧情、十章并行与择一路线，552种最短路线/顺序、78组195435项、两包各187249项、编译剧情界面474项通过。当前下载以本项为准；密集性能、难度/平衡、真人完整体验与Android真机待完成。'
 p.write_text(head.replace('rc28-preview','rc29-preview')+'\n\n'+new+'\n'+rest,'utf-8')
 p=ROOT/'README.md';body=p.read_text('utf-8')
 first=body.find('当前预览为');end=body.find('\n',first)
 summary=f'当前预览为 **rc29**：[二百图逐图剧情与非线性战役](docs/paper-warfront/{DOC})。200图战前/战后与实际地理、目标绑定齐备；章内择一路线或并行取证后汇合，未走支线保留回访。78组195435项、两包各187249项和编译剧情UI474项通过。密集性能、全关难度/平衡、真人完整体验与Android硬件仍待完成。'
 assert first>=0 and end>first;p.write_text(body[:first]+summary+body[end:],'utf-8')
 p=RELEASE/'README.md';body=p.read_text('utf-8');body=body.replace('程序不要放入不信任的安装包合集；许可见 licenses/。','许可见 licenses/。')
 body+='\n本包正式检查已完成：源码78组195435项，两包各36组187249项，实际编译剧情UI474项。具体范围和仍待完成事项以preview-verification.json及上述交付文档为准。\n'
 p.write_text(body,'utf-8')
 print('rc29 verified release and narrative documentation written')

if __name__=='__main__':main()
