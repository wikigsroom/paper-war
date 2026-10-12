"""Document the current roster/frame revision, with release claims gated on evidence."""
from pathlib import Path
import argparse,json,csv,hashlib,shutil,html
ROOT=Path(__file__).resolve().parents[2];DOC=ROOT/'docs/paper-warfront';FOLDER=DOC/'frame-rebuild';QA=ROOT/'output/qa/godot/frame-rebuild';VERSION='3.0.0-rc5'
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def write(p,t):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(t.strip()+'\n',encoding='utf-8')
def main():
 p=argparse.ArgumentParser();p.add_argument('--release',action='store_true');args=p.parse_args()
 briefs=read(ROOT/'assets/paper-warfront/frame-rebuild/unit-briefs.json')['units'];balance=read(ROOT/'game/data/balance-prototype.json')['units'];factions=read(ROOT/'game/data/factions.json')['factions'];frames=read(ROOT/'game/data/unit-frames.json')['profiles']
 if args.release:
  for name in ['factions-report.json','frames-report.json','ownership-report.json','workers-report.json','foundation-report.json','visual-review.json','native-frames/report.json','mobile/mobile-matrix.json','mobile/export/report.json']:
   r=read(QA/name);assert r.get('passed',True) and not r.get('failures'),name
  assert len(frames)==72 and all(frames[r['id']]['source']==r['source'] for r in briefs)
  assert (ROOT/f'release/{VERSION}/windows/PaperWarfront.exe').is_file()
 archive=ROOT/'docs/archive/paper-warfront-before-frame-rebuild'
 if not archive.exists():
  archive.mkdir(parents=True)
  for file in DOC.glob('*.md'):shutil.copy2(file,archive/file.name)
 stage='已完成当前原生检查与双平台构建；验收范围见报告。' if args.release else '正在接入和检查。候选帧、开发绑定及未复核文件不作为成品。'
 write(FOLDER/'README.md',f'''# 十院独特兵种与整身动作帧 · {VERSION}

{stage}

本次按用户选型，十院各六种可招募作战单位，共 60 种；另有十个阵营纸工和两类召唤物，共 72 个运行定义。每局仍选择 2–4 个作战位加纸工。旧 400 个作战模板存入历史，340 个退役 ID 迁移到相同工作方向的新兵种。地图、任务和故事链保持 200 关的实际空间结构。

- [阵营与兵种设计](01-阵营与兵种设计.md)：装备、轮廓、执行机制、组合和反制。
- [整身动作帧契约](02-整身动作帧契约.md)：参考图的制作思路、六行动作、脚点、释放时刻。
- [素材生产与接入](03-素材生产与接入.md)：新原型、提示词、原图、加工、来源与移动内存。
- [检查与交付范围](04-检查与交付范围.md)：当前证据、可视检查、移动矩阵、双平台包。
- [逐兵种资产与机制表](../../../assets/paper-warfront/frame-rebuild/roster.csv)。
- [离线素材查看页](../../../assets/paper-warfront/frame-rebuild-review.html)。

[项目入口](../README.md) · [地图研究与六图基准](../redesign-3.0/README.md)
''')
 rows=[]
 for f in factions:
  rows.append('## '+f['name']+' · '+f.get('motif',''))
  rows.append('| 兵种 / 稳定 ID | 装备与身体轮廓 | 实际规则与反制 |\n| --- | --- | --- |')
  for row in briefs:
   if row['faction']==f['id'] and not balance[row['id']].get('economy') and not balance[row['id']].get('summoned'):
    rows.append('| '+row['name']+' / '+row['id']+' | '+row['design']+' | '+row['hint']+' |')
 write(FOLDER/'01-阵营与兵种设计.md','''# 阵营与兵种设计

六兵种是六个可辨认的战场职责与装备体系。跨阵营不共享整身单位贴图，不以统一头盔、统一刀盾再改颜色扩充数量。允许纸纤维、描边和世界光线共享，让它们属于同一纸片舞台。

兵种机制在 BattleSim 和 UnitAbilities 内执行，动画只表现状态。实际距离、阵营归属、生命、冷却、弹丸与资源决定结果。颜色不决定敌我；己方工人与战斗单位可以交错通过，不触发伤害。夺印后依新归属重新验证伤害和持续状态。

金币由真实运输归仓产生，法力、科技、手动施法、自动行军、分岔选路和横向导航构成决策骨架。玩家应能从低密度的六种兵里组织护矿、压线、后排突击、阵地修理、范围控制或攻城组合。召唤、反射、偷血、赏金都必须有来源和边界。

'''+'\n\n'.join(rows)+'''

## 编组、科技和旧存档

每局 2–4 个战斗位，工人独立。前两种基础兵开局可用，其余按当前编组的科技解锁。军库展示每院 6 种作战兵、1 工人和 5 法术。200 关 available_roster、default_roster、enemy_roster 均引用当前 ID，早期关卡可用量小，后期展开六兵种选择。只允许当前编组招募，完整科技也不越过编组限制。

退役 ID 的原定义保存在 assets/paper-warfront/frame-rebuild/legacy；迁移表在 game/data/unit-id-migration.json。旧存档选择会归一化到合法单位。原稳定 ID 被沿用时，其新身份版本为 2；旧外观不能由同名 ID 自动视为合格。

未声称 200 关已经由人逐关完成平衡评价。阵容反制和数值手感仍应结合实际游玩评价，不能靠自动胜率或目录数量证明。
''')
 write(FOLDER/'02-整身动作帧契约.md','''# 整身动作帧契约

用户提供的六列帧表用于参考制作方法：在固定画布里重新绘制动作的身体、握持、武器和倒地过程。美术沿用原创纸雕角色。禁止将固定身体、固定手臂围绕关节转动，或只移动、缩放一个静态人物来冒充攻击和死亡。

每个单位六列六行、36 张完整姿态。运行帧为 192×192，图集 1152×1152，固定脚点 (96,180)。同一单位的所有帧使用一个共同缩放值；攻击高举武器时身体不会单独缩小，倒地姿态不会被放大到站立高度。左右朝向仅镜像整帧。地形、命中坐标与镜头不会选择动作帧。

| 行 / 索引 | 任务 | 接入规则 |
| --- | --- | --- |
| 待机 / 0–5 | 呼吸、装备稳定、完整循环 | 模拟 age 驱动，暂停停止 |
| 行走 / 6–11 | 跨步、脚掌、装备惯性；车轮或四足按体型绘制 | 真实 walk 距离驱动，原地等待不播走路；游弓后撤倒放步态 |
| 攻击 / 12–17 | 12–14 蓄势；15 释放；16 跟随；17 回收 | 前摇由实际 windup 驱动；模拟出手时切到 15，随后用 recovery |
| 受击 / 18–23 | 可见重心变化、屈膝、防御、恢复 | 真实 hurt 状态；白闪与短暂停顿独立，不制造第二次伤害 |
| 死亡 / 24–29 | 支撑失效、下跪或翻倒、伏地，最后静止 | 0.65 秒过程，再保留伏地和短淡出；车械留下塌落残骸 |
| 特殊 / 30–35 | 重装填、治疗、折符、仪式；纸工卸货 | 由真实特殊事件、装填剩余或工作进度驱动。被动效果不强迫循环此行 |

## 武器释放与握持

刀、锤、镰、藤臂必须改变躯干、肘部和握持，并完成明显的蓄势、挥击、回收。投矛、霜楔和金签释放后第 15、16 帧手里不保留原投掷物，第 17 帧准备下一枚。弓前手握弓、后手拉弦到脸颊；第 15 帧释放并清空搭箭，第 16 帧后手回弹。弩车与钉枪有机械扣机、空轨和真正的装填窗口。古树、叶蛾和四足折兽使用自身结构，不套人形斩击。

飞行物由真实弹丸独立绘制，起点按释放帧的武器位置校准。图片中不画飞出的弹丸，否则会出现重复箭或一直握着已投出的长矛。受击、闪光、粒子和声音来自实际战斗事件，友军接触不发命中反馈。

## 纸工动作

矿口 FIFO 服务中的工人站定后举工具、提到高处、落镐、回收；0.95 秒循环的实际 mine_strike 对应释放姿态。排队者维持等待，不能空挥工具。装载后走负重回程；在基地使用独立六帧卸货，卸货完成才入账。十个工人各有阵营装备、容器与身体，不共享一个采矿者调色。

## 验收

原图检查、归一化图检查、原生 36 帧截图、连续播放、真实出手截图、普通付费对战分别保存。固定脚点只能证明接入约束，不能证明艺术动作正确。完整帧表还必须人工查看装备连续性、清空投掷物、动作幅度、真实倒地、比例和小尺寸可读性。
''')
 write(FOLDER/'03-素材生产与接入.md','''# 素材生产与接入

只通过用户指定 sub2-image-gen 调用 gpt-image-2.5。密钥由技能本地配置管理，不进入提示词、加工工具、文档、报告或源码包。使用 Windows 原生 Python、Pillow、SciPy、Godot 与 Android SDK；不调用 Docker、WSL、模拟器或虚拟机。

## 目录与生产顺序

1. assets/paper-warfront/frame-rebuild/unit-briefs.json 定义 72 个稳定 ID、造型、装备、动作和真实机制。
2. output/imagegen/paper-warfront/frame-rebuild/v2 保存十院新原型板及提示词。先检查新种族、体型、装备、角色关系；不把旧人物截图作为新身份参照。
3. prepare_distinct_frame_seeds.py 从已查看的原型板按格提取种子，去除生成网格线并登记原图 SHA256。种子保持完整形体。
4. generate_frame_sheets.py 对每个新种子生成完整 36 帧，同时提供用户的排帧方法参考图。每次尝试有记录，限流或超时重试不覆盖旧记录。
5. normalize_frame_sheets.py 清除小型孤立透明噪点与边缘色污染，所有 36 帧共用尺度，固定脚点；输出 atlas、idle、portrait 和预览。
6. publish_distinct_rosters.py 校验全部新身份和当前来源，再绑定 game/data/assets.json、unit-actions.json、unit-frames.json。开发模式不等于发布验收。
7. 原生截图与真实对战通过后，记录 visual-review.json 和最终验收索引，再构建 EXE / APK。

生成尺寸请求为 1536×1536。服务返回的 PNG 尺寸可能不同，按实际像素切格，并在 provenance 同时记请求和实际尺寸；不虚报原生分辨率。最终运行格与图集尺寸固定。

## 来源与版本

unit-frames.json / frame-provenance.json 保存种子、提示词、原始帧图、加工工具、图集、头像与预览哈希。身份版本 2 对应新原型。首轮编辑旧角色的候选图无法满足独特轮廓，保留为未采用历史，不能作为通过样本。旧调色素材和骨骼尝试保存为历史，不进入当前单位渲染链。

资产 CSV 列出每个单位的装备、机制、提示词、源图、运行图集与状态。地图、远景、建筑和法术图沿用已记录的来源；本次角色更新不替换它们的证据。

## Godot、移动内存和导出

UnitFramePlayer 仅选择完整帧；BattleView 以固定脚点绘制区域，模拟负责命中与资源。图集按需加载，缓存最多 18 张单位图集，换战场与回主菜单释放，头像和场景贴图独立。单图集未压缩 RGBA 约 5.1 MiB，此数为像素预算估算，不是手机实测峰值。

Windows 主资源内嵌 EXE。Android 使用原生 Control、安全区和密度，动作图集同时支持 ARM64 / ARMv7 APK。最终导出排除旧单位切片、骨骼图集和测试源码；完整历史仍可在工程素材库中追溯。无需外部三维建模。
''')
 checks=[]
 for name in ['factions','frames','ownership','workers','foundation']:
  file=QA/(name+'-report.json')
  if file.exists():
   r=read(file);n=r.get('checks',0);n=len(n) if isinstance(n,list) else n
   checks.append('| '+name+' | '+str(n)+' | '+('通过' if r.get('passed',True) and not r.get('failures') else '待修复')+' |')
 write(FOLDER/'04-检查与交付范围.md',f'''# 检查与交付范围 · {VERSION}

{stage}

当前所有证据保存在 output/qa/godot/frame-rebuild。历史 rc2 / rc3 / actions-rc4 的结果只代表当时输入；本次不可用旧 412 个单位的检查数量为新版本背书。新范围是 60 个作战兵、10 个纸工、2 个召唤物和 72 套整身动作。

| 检查 | 当前数量 | 记录状态 |
| --- | ---: | --- |
'''+'\n'.join(checks)+'''

最终必须核对报告中的代码和数据哈希与导出输入一致。生成图片只证明素材生成，不能证明游戏运行、伤害、碰撞或性能。 native-frames 是真实 Godot 绘制截图；motion 为受控姿态离线播放；duels 为真实模拟攻击；mobile/native-play 为普通资源付费和敌方 AI 对战。它们分别覆盖不同事实。

移动矩阵覆盖八种屏幕、密度、缺口、安全区和旋转恢复；输入使用原生触摸事件。Windows 导出程序另跑六种菜单和战斗配置。APK 检查签名、相同包名、双 ARM、无网络权限、传感横屏和 16KB ELF / ZIP 对齐。没有 Android 真机，不声称已验证触屏硬件、温升、帧率或蓝牙音频。

地图平移检查覆盖 200 张地图的固定几何、鼠标和触屏捕获、取消、跨 HUD 释放、镜头震动抑制，以及 48 帧平移截图的像素一致性。主菜单检查严格保留五行；新战役子菜单只有线性战役和遭遇战。

日常检查：运行 check_frame_rebuild.py 的 import、contracts、gallery、motion、duels、pan、audio，然后运行 check_mobile_adaptation.py 和 check_mobile_preserved_systems.py。字体从当前运行文本重建。build_game.py、smoke_mobile_exports.py、package_release.py、audit_frame_release.py 完成双平台发布。

人工游玩平衡和 Android 真机测试仍是后续评价；已检查范围和限制必须一同交付。
''')
 csvfile=ROOT/'assets/paper-warfront/frame-rebuild/roster.csv'
 with csvfile.open('w',encoding='utf-8-sig',newline='') as stream:
  writer=csv.DictWriter(stream,fieldnames=['id','faction','name','kind','gesture','design','rule','mechanics','identity_version','source','prompt','raw','atlas','status']);writer.writeheader()
  for row in briefs:
   d=balance[row['id']];rec=frames.get(row['id'],{})
   writer.writerow({'id':row['id'],'faction':row['faction'],'name':row['name'],'kind':'worker' if d.get('economy') else 'summon' if d.get('summoned') else 'combat','gesture':row['gesture'],'design':row['design'],'rule':row['hint'],'mechanics':json.dumps(row['mechanics'],ensure_ascii=False),'identity_version':row.get('identity_version',1),'source':row['source'],'prompt':row['prompt'],'raw':row['raw'],'atlas':rec.get('atlas',''),'status':'native-reviewed' if args.release else 'candidate-needs-complete-review'})
 parts=['<!doctype html><html lang="zh"><meta charset="utf-8"><title>十院整身动作素材</title><style>body{background:#f4ead3;color:#283633;font:16px system-ui;margin:30px}h1{font-size:30px}section{margin:26px 0}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(330px,1fr));gap:18px}article{background:#fff8e9;border:1px solid #c7b795;padding:15px}img{width:100%;height:auto}a{color:#26736e}small{display:block;overflow-wrap:anywhere}</style><h1>十院独特兵种 · 完整绘制动作</h1><p>'+stage+' 原生截图、受控动作与普通对战在各自记录中，不混为性能证据。</p><a href="../../docs/paper-warfront/frame-rebuild/README.md">方案与契约</a>']
 for f in factions:
  parts.append('<section><h2>'+html.escape(f['name'])+'</h2><div class="grid">')
  for row in briefs:
   if row['faction']!=f['id']:continue
   uid=row['id'];picture=QA/'native-frames'/(uid.replace('.','-')+'.png')
   src='../../'+picture.relative_to(ROOT).as_posix()
   parts.append('<article><h3>'+html.escape(row['name'])+'</h3><small>'+uid+'</small><p>'+html.escape(row['hint'])+'</p>'+('<a href="'+src+'"><img loading="lazy" src="'+src+'" alt="完整36帧原生截图"></a>' if picture.exists() else '<p>尚无当前完整截图。</p>')+'</article>')
  parts.append('</div></section>')
 parts.append('</html>');write(ROOT/'assets/paper-warfront/frame-rebuild-review.html',''.join(parts))
 # Current technical pages supersede the archived palette/joint specifications.
 for filename,title,text in [
  ('06-Godot纸偶与动画规范.md','Godot整身动作帧','完整姿态图集替代关节转动。36帧、共同缩放、固定脚点、攻击释放同步、采矿与卸货、独立弹丸详见整身动作帧契约。'),
  ('17-规模扩展与实施进度.md','当前内容规模','十院各6种可招募作战兵、10个工人、2种召唤物，共72个运行定义。340个退役ID迁移，旧400作战模板归档。200关、50法术与六挑战保留。'),
  ('21-十院素材与动画规范.md','十院素材与动画','每个阵营由新原型板建立自身身体、装备和单位组合；72套实际整身帧表。不得以旧40角色家族调色覆盖当前兵种。'),
  ('19-战前编组与科技规范.md','战前编组与科技','军库60兵种，每局2–4作战位加纸工。招募/研究限制当前编组；开局基础两种，其余科技真实完成才解锁。旧存档经迁移表归一化。')]:
  write(DOC/filename,'# '+title+' · '+VERSION+'\n\n'+text+'\n\n[当前完整规范](frame-rebuild/README.md) · [项目入口](README.md)')
 for filename,title,text in [
  ('02-玩法与十阵营规则.md','玩法与十阵营规则','金币等工人归仓才入账，法力用于手动法术。招募、研究与设施共享金币；施工不攻击、不产法，科技真实完成才解锁。十院法力来源保留升级、献纸、灯设施、施工、路口、归仓、生长、控制、受击和研究，各兵种装备与具体能力按当前六兵种设计执行。'),
  ('03-美术风格圣经.md','美术风格圣经','暖纸、墨线、纤维与折叠纸厚片统一舞台。十院共享材质语言，身体种类与装备必须不同；不要求树、虫、四足兽、机器、人形都用相同头身比例。印甲方形、墨骸破口、灯符中空、工坊齿轮、鸢纸羽翼、金契票币、植纤根叶、霜裁规尺、烬纸陶灰、空白镂孔组成不同轮廓。背景不生成假道路，装饰避开互动节点，实际路缘和桥梁遵从地图几何。'),
  ('04-素材库与命名规范.md','素材库与命名规范','权威绑定为game/data/assets.json，稳定ID区分unit、spell、building、background、prop、resource。当前72个单位各有1152×1152图集、192×192待机与144×144头像，资产表在assets/paper-warfront/frame-rebuild/roster.csv。源板、种子、提示词、生成帧图、共同尺度和输出哈希分别记录。旧调色资源保留历史，不能被当作当前身份。'),
  ('05-素材生成与加工指导.md','素材生成与加工指导','用户指定sub2-image-gen / gpt-image-2.5。先生成、查看新阵营原型，再提取完整种子，生成36帧，统一尺度与脚点，最后原生查看和真实对战。源与提示词在output/imagegen/paper-warfront/frame-rebuild/v2，处理工具在tools/paper-warfront，定义和来源在assets/paper-warfront/frame-rebuild。完整生产、透明边缘与跨格杂片处理详见当前素材指导。'),
  ('13-运行素材与反馈矩阵.md','运行素材与反馈矩阵','军队采用完整绘制姿态；独立弹丸、实际受击短暂停顿、白闪、伤害数字与纸屑由真实事件驱动。工人采矿落镐、装载、卸货与归仓各对应实际作业；等待不落镐。建筑施工、完成、停机、攻击、摧毁；路线标牌、矿点、桥梁、任务生命和接力点均对应实际实体。音频使用原生缓存样本与16声部池，弓、钉枪和绞盘弩按装备分声，装填有低强度扣机反馈；录像是静音离线播放，不声明设备帧率。')]:
  write(DOC/filename,'# '+title+' · '+VERSION+'\n\n'+text+'\n\n[当前完整约束与素材](frame-rebuild/README.md) · [项目入口](README.md)')
 write(DOC/'07-交互与UI规范.md','''# 交互与 UI · 3.0.0-rc5

主菜单从上到下固定为：继续战役、新战役、成就挑战、兵书、设置。新战役只有线性战役和遭遇战。地图试演、操作帮助、鸣谢和退出在设置中。兵书展示每院六兵种与真实机制，编组可带2–4种作战兵。

游玩 UI 保留金币、法力、任务、生产、研究、设施和手动施法。兵种卡使用新头像和可读短名，详情显示全名和规则。非法目标不收费，取消和返回遵照当前模态层级。鼠标/首指拖动捕获镜头，8dp拖动阈值防止误选，越过HUD释放可结束，取消/后台/旋转清除捕获。

移动界面使用原生 Control、实际密度、安全区、48dp行动目标、可滚动详情及横屏恢复。军阵/法术两组保护战场视野；返回先退出选择，再关闭面板或暂停。切后台停止声音与模拟，回来手动继续。

[当前方案与检查](frame-rebuild/README.md) · [移动基本契约](mobile-rc3/README.md)
''')
 write(DOC/'16-玩家手册.md','''# 玩家手册 · 3.0.0-rc5

从“继续战役”进入已解锁的关卡，或“新战役”选择线性战役 / 遭遇战。设置内的“地图试演”可直接尝试六张空间基准图。兵书可查看每院六种独特作战兵与反制，战前带2–4种兵加一个纸工。

军队自动行军交战，你负责金币与法力的取舍。纸工在矿口站定采金、装载并归城卸货，金币在实际归仓时入账。先招前排与远程护住经济；研究解锁本局重兵和法术。设施选卡后提交合法建造位才收费，施工中的阵地需要保护。

路标切换后续军队的道路，已上路的军队继续走当前路线。纸桥较长，能绕开近战阵地，但真实射程内仍可能被敌人攻击。远矿增收需要较长归仓时间和护卫。护送、截击、守护按任务锚点实际执行。

法术选卡后点对象 / 地面；非法目标不会扣法力。右键、取消或返回退出选择。拖动战场或点小地图导航；A/D或方向键移动，Home回城，Space跟前线，1–5招募，Q/W/E/R/T选法术，F研究，B建造，Esc暂停。手机长按行动卡看完整机制，军令内管理科技、施工与生产队列。

钉枪和重弩有装填停火窗口；游弓射后后撤；钩线能拉动实际站位；腐墨叠层，花冠师能净化；霜楔配合压雪车打被控目标；留白消矢师可删飞弹但怕沉默。用兵书中的真实机制组织组合。

胜利解锁故事下一关并保存进度，试演不改变战役解锁。设置可调音量、减少动态和省电。后台回来需手动继续。

[方案与验收](frame-rebuild/README.md) · [项目入口](README.md)
''')
 write(DOC/'README.md',f'''# 纸上兵戈：十院留名 · {VERSION}

{stage}

[当前阵营、动作与素材体系](frame-rebuild/README.md) · [玩家手册](16-玩家手册.md) · [离线素材查看](../../assets/paper-warfront/frame-rebuild-review.html)

十院各六个独特作战兵，保留自动行军、金币/法力、科技、手动施法、非对称军阵与横向导航。每局2–4作战位加纸工，200关的经济道路、分岔、阵地与任务继续由实际地图执行。当前角色使用完整绘制的36帧图集。

| 体系 | 入口 |
| --- | --- |
| 章程与原创规则 | [项目章程](01-项目章程与硬约束.md) |
| 当前兵种、动作和素材 | [当前完整规范](frame-rebuild/README.md) |
| UI与编组 | [UI](07-交互与UI规范.md) · [编组](19-战前编组与科技规范.md) |
| 地图与运输 | [地图研究](../research/swords-and-soldiers-map/recheck-20261008/README.md) · [六图与200关](redesign-3.0/README.md) · [实际路径](18-路径与经济执行规范.md) |
| 模拟、AI与故事 | [架构](11-Godot架构与数据契约.md) · [AI](12-AI与关卡导演规范.md) · [任务](20-战役与任务执行规范.md) |
| 检查和双平台交付 | [当前验收范围](frame-rebuild/04-检查与交付范围.md) |

旧调色和关节规范保存于 [重做前文档](../archive/paper-warfront-before-frame-rebuild/README.md)，旧发布与报告保留历史事实。生成图不能作为运行和手机性能证据。
''')
 print('Current frame documentation written. Release=',args.release)
if __name__=='__main__':main()
