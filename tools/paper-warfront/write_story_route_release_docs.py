"""Final, measured rc27 narrative/map release; preserve previous release scope."""
from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parents[2]
VERSION='3.0.0-rc27-preview'
QA=ROOT/'output/qa/godot/capacity-performance-rc27'
FINAL=QA/'release-final'
read=lambda p:json.loads(p.read_text('utf-8'))
def put(p,text):p.write_text(text,'utf-8')
def main():
 reg=read(QA/'formal-reach/regression/report.json');assert reg['passed'] and reg['source_unchanged']
 source_checks=sum(t['checks'] for t in reg['tests'])
 counts={platform:sum(r['checks'] for r in read(FINAL/f'{platform}-logic/report.json')['tests']) for platform in ['apk','windows']}
 assert all(read(FINAL/f'{platform}-logic/report.json')['passed'] for platform in counts)
 real=read(FINAL/'realtime/report.json');assert real['passed']
 ui=read(FINAL/'story-ui-final/report.json');assert ui['passed']
 matrix=read(FINAL/'mobile/mobile-matrix.json')
 assert matrix['passed']
 stage=read(FINAL/'stage-proportions/report.json');assert stage['passed']
 paid=read(QA/'paid-runtime-equivalence.json');assert paid['passed']
 table='| 场景 | 单位峰值 | 稳态FPS | P95帧间隔 | 墙钟/模拟时间 |\n|---|---:|---:|---:|---:|\n'
 for row in real['cases']:
  label={'before-stress':'rc26满员对照','stress':'rc27满员压力','bridge':'rc27正常分岔','long':'rc27正常长图','phone':'rc27手机布局（Windows）'}[row['case']]
  table+=f"| {label} | {row['max_units']} | {row['fps_from_mean_interval']:.2f} | {row['p95_frame_ms']:.2f}ms | {row['wall_seconds']:.2f}/{row['simulation_seconds']:.2f}s |\n"
 doc=ROOT/'docs/paper-warfront/136-单机剧情地图与章内分支.md'
 text=doc.read_text('utf-8');text=text.replace('双平台包、实际编译界面、画面及帧率复测结果在完成后追加。当前不得声称第二至十章已完成同等叙事重写、200关人工平衡、Android真机、满员流畅性能或原作精确时序验收。','')
 text+=f'''\n## rc27交付与最终复核

[Windows程序压缩包](../../release/{VERSION}/PaperWarfront-Windows-{VERSION}.zip) · [Android APK](../../release/{VERSION}/android/PaperWarfront-{VERSION}.apk)。同一签名、Android版本号30026；真机未验证。

| 已测范围 | 最终结果 |
|---|---|
| 正式规则 | {len(reg['tests'])}组、{source_checks:,}项，全过；含路线6,376项和跃进/阻挡1,200项 |
| 实际包字节码 | EXE与APK各33组、{counts['apk']:,}项，在Windows原生引擎加载真实编译资源 |
| 剧情界面 | 两种布局共66项；真实注入鼠标/ScreenTouch，隔离存档，20份胜利/战术简报全显 |
| 正常付费对局 | 印垒/木拓三图镜像六场，{paid['checks']:,}个60Hz步骤与rc26逐步一致 |
| 地图比例 | 200图、22,902项；道路、桥面、厚纸层、单位比例与原约束一致 |
| 移动显示 | 八配置{matrix['checks']:,}项；战斗净画面至少70%，不等于Android实体设备 |
| 编译画面对照 | 两尺寸、三图、两小数镜头位置共12组，全部在预定容差内 |
| 对战/UI | 正常付费行军50项、受控交锋OpenGL64项/default Vulkan32项，菜单、军令、焦点、六EXE场景与38项折纸资源复核 |

旧简报实际包中20份有15份战术段落超过固定高度，已经缩短为一个完整战术问题；相同观察器最终20份全部通过。第一批UI观察错误地哈希Godot逻辑`.gd`资源路径，修为真实`.gdc`文件字节后在同包重验。原失败、首批导出和源码均归档，没有覆盖已完成证据。

{table}

正常样本每场160秒，300金币、科技未解锁、敌方等待4秒；满员样本每侧直接放入60战斗单位，加4纸工，关闭AI并提高生命值维持负载，不能当正常付费玩法。稳态FPS来自真实单调时钟帧间隔，排除开始2秒以及截图回读和其后0.5秒。模拟按自然App处理推进，没有手动加速；测试中窗口可见、音频开启，默认60FPS上限。

本轮桌面有其他项目的原生无界面任务在运行，未干预用户的其他工作。当前帧率是这台机器此时的观察，不能据此宣布性能提升或独占硬件指标。正常55FPS目标=`{str(real['normal_55fps_target_met']).lower()}`；满员60FPS目标=`{str(real['capacity_60fps_target_met']).lower()}`。高密度卡顿仍需继续优化。

所有新剧情与章内解锁均未发放额外金币、法力或科技。单位、动作、粒子、全舞台未知雾幕和厚土层继续使用已核验版本；本轮没有生成新图，复用用户指定sub2-image-gen/gpt-image-2.5的既有折纸UI与图集。字体使用现有OFL源重新覆盖新增文本，检查1192个CJK字符、两字体无缺字。

证据根目录`output/qa/godot/capacity-performance-rc27/`，最终包运行证据在`release-final/`；首批导出在`first-export/`，修改前源码/文档在`pre-story-change/`。发布清单绑定当前全部公开输入。

第二至十章同等叙事改写、200关人工平衡、Android真机、满员流畅性能、原作精确视野/时序与真人互战仍未完成。本交付没有把自动结果转换夹具算作真实关卡胜利。
'''
 put(doc,text)
 p=ROOT/'README.md';s=p.read_text('utf-8');head,tail=s.split('\n',1)
 head=head.replace('rc26-preview','rc27-preview');tail=tail.replace('当前预览为 **rc26**：','rc26阶段记录：',1)
 tail=tail.replace('release/3.0.0-rc26-preview/','release/'+VERSION+'/').replace('PaperWarfront-Windows-3.0.0-rc26-preview.zip','PaperWarfront-Windows-'+VERSION+'.zip').replace('PaperWarfront-3.0.0-rc26-preview.apk','PaperWarfront-'+VERSION+'.apk')
 put(p,head+'\n\n当前预览为 **rc27**：[单机剧情地图与章内分支](docs/paper-warfront/136-单机剧情地图与章内分支.md)。第一章20关逐关叙事与六处可选汇合路线已进入程序；旧存档迁移、实际完成旗、回访、故事菜单和完整简报均已检查。75组95,386项、两包各33组87,200项、原生剧情界面66项通过；六场正常付费对局73,103步与rc26一致。地图比例、厚纸地层、独立道路迷雾和至少70%战斗画面沿用已核验约束。其余180关同等深度叙事、满员性能、整体平衡及Android硬件仍待完成。\n'+tail)
 p=ROOT/'docs/paper-warfront/README.md';s=p.read_text('utf-8');head,tail=s.split('\n',1)
 tail=tail.replace('当前下载以本项为准','本项保留rc26记录，当前下载以上方136为准',1)
 put(p,head.replace('rc26-preview','rc27-preview')+'\n\n[单机剧情地图与章内分支及rc27交付](136-单机剧情地图与章内分支.md)：每图配套剧情，线性或分岔按具体任务选型。第一章20关逐关叙事、六组择一路线与回访；schema3真实完成集合、旧档迁移、75组95,386项、两包各87,200项、编译剧情界面66项、200图与八显示配置通过。当前下载以本项为准；后续180关叙事、密集性能与Android真机待完成。\n'+tail)
 p=ROOT/'docs/paper-warfront/11-Godot架构与数据契约.md'
 put(p,'rc27剧情地图补充：[章内解锁与实际完成ID](136-单机剧情地图与章内分支.md)。`campaign_progress`读取独立故事图，不复用道路图；schema3保存实际完成ID，`unlocked`只为继续推荐页，不再当锁关权威。第一章六组OR前置汇合，未走页不发证据；schema2迁移旧连续历史。地图剧情和任务分别绑定，战斗参数沿用。当前交付以136为准。\n\n'+p.read_text('utf-8'))
 p=ROOT/'docs/paper-warfront/16-玩家手册.md';put(p,p.read_text('utf-8').replace('3.0.0-rc26-preview',VERSION,1))
 p=ROOT/'docs/paper-warfront/world/04-完整故事路线.md';old=p.read_bytes()
 backup=QA/'story-world-doc-before';backup.mkdir(exist_ok=False)
 (backup/p.name).write_bytes(old)
 put(backup/'inputs.json',json.dumps({'path':p.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(old).hexdigest(),'bytes':len(old),'reason':'Preserve the original all-linear outline before aligning it with the reviewed rc27 chapter1 data.'},ensure_ascii=False,indent=2)+'\n')
 s=old.decode('utf-8');start=s.index('## 朱印疆：守住秩序');end=s.index('## 旧册泽：让亡者作证')
 profiles=read(ROOT/'game/data/campaign-narrative.json')['profiles']
 section='## 朱印疆：守住秩序\n\n赤砚从封锁矿村，转向保护被抹名的劳动者与原始证据，最终携伪令母版通过合印门与墨归会盟。以下20页绑定当前运行数据；六组支线可择一推进，汇合页不引用未走支线的独有证词。\n\n'
 for i in range(1,21):
  n=profiles[f'campaign.yin.{i:02d}'];section+=f"{i}. **{n['title']}**（{n['objective']}，`{n['map']}`）：{n['goal']} {n['geography_reason']} 实际完成后保全：{n['evidence_name']}。\n"
 section+='\n本章结果：原物、实际保全的见证与第一片祖印到达会盟处；未走纸页继续可回访，不自动获证。\n\n'
 intro='# 完整故事与战役路线\n\n祖印碎裂，十院相互追索王命。玩家沿十位统帅的行动收集证据，阻止用抹除记忆换取和平的归零印。\n\n**单机每图配套剧情，地图和章节均不强制线性。** 当前20页剧情、六处择一汇合及schema3实际完成解锁，以[单机剧情地图与章内分支](../136-单机剧情地图与章内分支.md)和`campaign-flow.json`为准；道路图独立管理。下方第二至十章180页是保留的既有故事纲要与因果顺序，尚未完成第一章同等深度的地形／剧情核验，不把故事中的道路数量当成已经实现的几何。\n\n'
 put(p,intro+section+s[end:])
 put(ROOT/f'release/{VERSION}/README.md',f'''# 纸上兵戈 · {VERSION}

[Windows压缩包](PaperWarfront-Windows-{VERSION}.zip) · [Android APK](android/PaperWarfront-{VERSION}.apk)

第一章20张地图逐关配套剧情，六处择一推进与汇合；已完成和未走支线可回访。首关后可先查外矿账册，或先保护前哨拓片；胜利后选择下一页。schema3保留真实完成旗、最高星级与旧档历史。

普通兵、长卷地图与厚纸地层继续采用当前比例；桥路和主路独立迷雾，手机战斗保留至少70%净画面。复用38项折纸UI、72套36帧图集。修复跃进单位在同帧友军间距查询中的位置缓存。

75组95,386项规则、两包各33组87,200项、原生剧情UI66项与20份完整简报、六实际EXE场景、200地图比例、八移动显示配置、付款/命中链和ZIP核验。Windows加载APK字节码验证不代表Android硬件运行。

真实帧率与完整范围见[剧情地图与交付记录](../../docs/paper-warfront/136-单机剧情地图与章内分支.md)。高密度性能仍未达标；其他180关同等叙事改写、整体平衡、Android实体设备与原作精确时序仍待完成。生成图不承担运行证据。

首次运行：解压后双击PaperWarfront.exe。Vulkan不兼容时使用同目录OpenGL启动脚本。Android保留原包名/签名，版本号30026。
''')
 print('Final story-route release documentation written')
if __name__=='__main__':main()
