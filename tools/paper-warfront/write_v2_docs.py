"""Publish current specifications and indexes, preserving the superseded 1.0 documents."""
from pathlib import Path
from collections import Counter
import json,re,os,shutil
ROOT=Path(__file__).resolve().parents[2];DOC=ROOT/'docs/paper-warfront'
def read(name):return json.loads((ROOT/'game/data'/name).read_text(encoding='utf-8'))
def write(path,text):path.parent.mkdir(parents=True,exist_ok=True);path.write_text(text.strip()+'\n',encoding='utf-8')
def archive():
    destination=ROOT/'docs/archive/paper-warfront-1.0/docs'
    candidates=[p for p in DOC.glob('*.md') if re.match(r'^(0[1-9]|1[0-5])-',p.name)]
    for source in candidates:
        target=destination/source.name
        if target.exists():continue
        text=source.read_text(encoding='utf-8')
        def link(match):
            value=match.group(2)
            if value.startswith(('http:','https:','#')):return match.group(0)
            value,sep,fragment=value.partition('#');old=(source.parent/value).resolve()
            if old in candidates:new=destination/old.name
            elif old.parent==ROOT/'game/data' and (destination.parent/'data'/old.name).exists():new=destination.parent/'data'/old.name
            else:new=old
            relative=os.path.relpath(new,target.parent).replace('\\','/')
            return match.group(1)+'('+relative+(sep+fragment if sep else '')+')'
        text=re.sub(r'(!?\[[^\]]*\])\(([^)]+)\)',link,text)
        write(target,'> 1.0 历史快照。当前版本请读 [2.0 制作入口](../../../paper-warfront/README.md)。\n\n'+text)

def main():
    archive();factions=read('factions.json');maps=read('maps.json')['maps'];balance=read('balance-prototype.json');assets=read('assets.json')['assets']
    docs={
'01-项目章程与硬约束.md':'''# 项目章程与硬约束 · 2.0

《纸上兵戈：十院留名》 / Paper Warfront。Godot 4.7.2、GDScript、原生 Control 和分层 2D 纸偶。玩家投资经济、招募、科技与设施，选择后续军团路径，并在真实二维位置手动施法。部队自主行军与交战，统帅是叙事人物。

正式内容为200张机械地图、十个阵营、每院40个可招募作战兵、10名工人及另计的2种临时实体、50项法术、十章200关线性故事、6道保留挑战和任意地图遭遇战。所有地图均保存独立路径、矿位、容量、施工位和任务锚点；不把背景换色当成新机械地图。

硬约束：金币和法力只有两类主资源；不能免费出兵、窥探敌方钱包或无冷却施法；旧兵不因后来改路而瞬移；矿金真实归仓；施工期不提供完工收益；范围和远程用二维位置，近战用道路连接；任务对象的唯一证据不能献弃、夺印或复印。

原创纸雕造型、纸纹、折痕和墨符服务可读性。无需外部3D建模、蒙皮、动作捕捉或物理刚体战斗。图片使用指定 sub2-image-gen / gpt-image-2.5，密钥由技能管理。原生 Windows 构建；禁止 Docker、WSL、虚拟机、容器和模拟器。使用浏览器后关闭本次不用的标签。

本版本离线单人，不含网络对战或账号服务。Windows单文件EXE、Android签名APK和可编辑源码分别交付。功能、素材、UI、合法对局与实际程序分别验证；APK校验不冒充真机测试，自动玩家胜利不冒充人工平衡验收。详见 [22发布验收](22-双平台验收与发布.md)。''',
'02-玩法与十阵营规则.md':'''# 玩法与十阵营规则 · 2.0

核心循环是运输归仓→选择投资→串行生产与研究→自主进军→路标分流及汇流→玩家施法改变交换→任务结算与保存。金币同时支付工人、兵力、科技和设施；法力支持即时治疗、保护、控制、打击和临时召唤。

四项互相牵制的投入：扩工能提高后续回款，但容量、排队和路程会压低收益；出兵可保护矿线并抢施工窗口，但会延后科技；研究提高编组兵的能力层级，但研究期间的军团仍需顶住压力；前位设施更接近战斗和运输，却有4/5秒施工风险。兵力部署决定本局能用的4–8个作战角色，工人另占一栏。

招募2.4秒一个、队列上限6、军团上限60、工人通常上限10；取消验证索引与单位ID，成功才退款。研究同时一项，四阶公共兵法开放编组内高阶研究；编组外招募与研究拒绝。初始军库和科技由战役定义，遭遇战可选完整科技。

阵营机制见 [十院设定](world/02-十阵营设定.md)。印甲重甲与永久回法、墨骸吸血与献纸、灯符设施供法与灯旁法术抵抗、纸械施工回法与设施旁输出、鸢纸节点回法与加速、金契归仓回法与真实击杀赏金、植纤修复回法且怕腐蚀、霜裁成功控制回法、烬纸受敌伤回法与残血奋战、空白研究回法与法术抵抗。触发和上限由模拟实现，克隆或临时实体不能制造无限循环。

同院40个职责包括前排、突击、反突击、护运、远程、攻城、控制、治疗、光环、召回、复制、禁言和施工破坏。职责体系共享以便读懂反制；各院的经济、抗性、速度、回法与材料轮廓让同一职责形成不同阵容。每兵完整参数和能力见 [单位分院目录](world/README.md)。

主任务为拆城、真实归仓、守城、保前哨、护送和矿线前截巨。护送必须走到交接点；不能拆掉敌城后跳过护送。所有任务先检查我方基地，指定前哨或携证者死亡立即失败。范围伤害与远程可在射程内跨路，近战不能隔支路砍人。参见 [核心博弈](world/01-核心博弈.md)、[路径经济](18-路径与经济执行规范.md)、[任务规范](20-战役与任务执行规范.md)。''',
'03-美术风格圣经.md':'''# 美术风格圣经 · 十院纸雕

主材是象牙色纤维纸、浅褐纸板与克制的炭黑轮廓。清晰切边、折叠层次和少量侧面厚度形成低面数纸雕观感；战斗使用2D纸偶，背景用低对比远景和安静纸面。人物大头、短躯干、明确武器职责，允许诙谐和有辨识度的夸张。

十院材质和色彩按 [阵营设定](world/02-十阵营设定.md) 冻结：朱印赤甲、旧册墨骨、青灯符纸、铜折齿轮、雁信翼羽、契金封契、活纤叶脉、冻页几何霜裁、余烬焦边、留白负形。颜色之外还用头饰、甲片、武器和装置剪影区分。归属通过蓝/赤脚线与生命条表达，不把原始阵营画风等同当前阵营归属。

浅纸背景、深墨正文、金色金币和蓝色法力贯穿菜单与HUD。字体为Noto Sans SC正文、Noto Serif SC标题；费用、冷却、星章、状态和剧情均由代码排版，不生成到图片里。界面采用纸板边线和稳固按钮，按下反馈不改变布局。

禁止真实金属PBR、塑料亮面、霓虹科幻、写实肌肤、照片式角色、满屏高对比纹理和与道路混淆的装饰。地图背景仅描述地方；真实路段、矿位、路标、任务线和施工位由同一运行数据绘制。战斗前景保留足够空白，普通发射闪光短小，重击才使用更强的纸屑、停顿与震动。

源图、加工切图和游戏内画面是不同检查层次。十院400兵审图板、辅助素材板与背景板保存在 output/imagegen/paper-warfront/world-v2 和 world-support；实际游戏截图在 output/qa/godot/v2。''',
'04-素材库与命名规范.md':'''# 素材库与命名规范 · 2.0

稳定ID使用unit.院.职责、spell.院.法术、building.院.设施、portrait.院.commander、prop.院.用途及background.地区。200地图ID为map.01.01至map.10.20。旧作战ID保留，名称和职责以当前平衡JSON为准。

权威运行绑定为 [assets.json](../../game/data/assets.json)，引用文件的尺寸/字节与SHA256登记在 [asset-inventory.json](../../game/data/asset-inventory.json)。400作战兵及87辅助/背景素材有独立生成溯源：world-art-provenance.json与world-support-provenance.json。绑定路径、头像和动作分件分开登记；技术核验、源图审图与运行视觉验收各有证据。

新增全库见 [离线素材与地图库](../../assets/paper-warfront/world-v2-gallery.html)。源图/提示词保留在output/imagegen；运行PNG在game/assets。单位512×512、头像192×192，落脚基线476；实际横向脚点与分腿切线按alpha分布测量。部件仍是512×512，保证关节转换使用统一画布。背景1536×1024，在运行时低对比铺设。

runtime-linked-reviewed表示已完成切图、来源和源板检查；不能据此单独宣称动作、平衡或Android真机质量。发布不允许开发占位图静默替代单位。50法术沿用三类能力家族的15个符号，其共享关系在shared_art_from中明示，不能计作50种独立画稿。

旧assets/paper-warfront/library-manifest.json与gallery.html是1.0原型素材登记，保留作历史来源。当前400兵和十院辅助素材应使用上述运行绑定及新版浏览页。''',
'05-素材生成与加工指导.md':'''# 素材生成与加工指导 · 2.0

只调用用户指定的sub2-image-gen技能CLI，模型gpt-image-2.5、high质量、PNG；单位及辅助物必须显式请求transparent背景，地区背景opaque。项目不读取、打印或复制技能网关密钥，也不切换供应商补图。

400作战兵按50张4列2行源板生成；每院另外一张8物件辅助源板，包含统帅、工人、基地、塔、纸灯、树/植物、旗和货箱；七个新增地区各生成一张低对比全景。提示词约束完整脚、武器和轮廓、无文字、无格线、透明间隔和纸材风格。三处边界裁切用独立1024×1024安全边距图修复，来源散列保持独立。

加工顺序：验证原生alpha→全图连通轮廓定位→检查重复轮廓与画布边界→完整对象归一化→头像→纸偶分件→脚部权重与枢轴→清单及来源→源板审图→Godot导入→运行视觉复核。网格是排版参考，不能直接按格切断长矛、旗帜或头饰。

工具为generate_world_art.py、repair_world_art.py、publish_world_art.py、generate_support_art.py、publish_support_art.py、rebuild_puppet_anchors.py、validate_world_assets.py与build_world_gallery.py。已随源码交付全部成品，导入Godot即可玩，不需要重付生成费用。重新生成或修改世界数据后要重验状态、锚点、清单和实际画面。

非透明或裁切失败的图片不能进入运行清单。历史拒绝图在工作区rejected记录中，源码交付包排除拒绝图。配乐与声效采用原创程序合成，设计见 [SOUND_DESIGN](../../game/SOUND_DESIGN.md)。''',
'06-Godot纸偶与动画规范.md':'''# Godot纸偶与动作反馈 · 2.0

人偶为body、leg-back、leg-front，车辆为body和两个wheel；世界尺寸分别按普通兵、炮车、巨像登记。固定画布512、纵向脚底476；横向落脚点来自实际底部alpha权重，腿的分界和枢轴来自真实脚部，不按画布中心猜测。武器、旗和背负物可能导致整体剪影偏心。

battle_view.gd按相同世界锚点绘制待机、行走、蓄力、攻击、受击与死亡。双腿交替、躯干轻摆、轮子转动；前摇后倾、释放前倾；受击短暂停步与亮色闪白；死亡纸偶倾倒、褪色和飞屑。同一落脚锚点用于生前和死亡，渲染不能改写真实移动和命中。

攻击区分短促发射闪光、弧线挥砍、飞弹、反弹、范围爆发与落印延迟。普通攻击不连续播放大法术图案。伤害、治疗、金币和打断文本读取事件；纸屑上限650、瞬时效果约160，声音池16。施工有进度条和完工反馈；禁言、腐墨、束缚、加速、保护、封禁与克隆有独立读法。

X/Y锚点贯穿单位、命中、死亡、粒子、范围预览和小地图。两条支路上的效果不能回落到同一条假想地面。地图全部道路的屏幕范围经检查位于战斗区域内；背景装饰不决定碰撞。

七种代表纸偶的步态、蓄力、攻击和受击帧在原生引擎内截图，包含旗手、复制兵、拆灯兵、狂兵、巨像、炮车与工人；见output/qa/godot/v2/ui-mobile/pose-00.png至pose-06.png。400兵和10工的1230部件另有非空、alpha和锚点检查。''',
'07-交互与UI规范.md':'''# 交互与UI · 2.0

页面包含主菜单、十章关卡、战前剧情和地图、遭遇配置、战术挑战、十院兵书、4–8兵部署、声音显示、许可、游玩HUD、科技、建造、队列、暂停、结果和终章。胜利保存当前星章、证据和下一关；败局可重开或回菜单。

桌面HUD显示最多8兵+工人及5法术，1–9招募、Q/W/E/R/T选择法术、F科技、B建造、P暂停；右键/Esc取消，A/D/方向键移动，Home看家，Space跟随交锋。拖动战场或点小地图是同等导航入口。

移动布局以1600×900逻辑画布的横屏显示：4兵+工人分两组，第三组5法术；主招募、法术与操作按钮128高，矿/路标点击半径60，小地图和看家/交锋按钮放大。关卡每页9项，兵书每页8项，部署每页10兵，科技每页4项；队列每页最多6项，提供取消及退款。桌面分别每章20关、兵书12、部署20、科技8。

故事、兵种说明和部署清单用可滚动文字，不因定高裁掉正文；滚动子标签必须有实际自动高度，不能启用导致最小高度归零的clip_text。固定单行HUD标签可裁切边界。科技页优先展示兵法门槛，明确费用、时间、前置和完成状态。

技术/建造/队列面板保持战斗推进；暂停冻结模拟、粒子和步态，设置返回仍停在暂停。Android返回键关闭当前面板或打开暂停，后台切换自动暂停。只有合法确认招募、研究、施工或施法才付款；错误提示和取消入口明确。

触屏布局已在原生Windows兼容渲染器以1280×720窗口验证；这并非Android硬件、DPI、刘海、系统文本缩放或耗电验证。本版本横屏，不宣称完成竖屏或屏幕阅读器适配。''',
'08-关卡与内容规划.md':'''# 地图、故事与关卡体系 · 2.0

200张地图由20种战术题型在十个不同地区展开，拓扑、路线坐标、容量、矿位、设施位、预算、对手部署、任务和剧情一起定义。实际几何散列200个不重复；34张单线入门/矿线题与166张分岔地图。不能把同一题型展开误称200种互不相干的机制。

空间设计把经济和作战连接：近矿保证回款底线；外矿有不同容量、采矿时间和载荷，但护卫与回程距离会吃掉收益。分岔隔离近战接敌并改变跨路射程覆盖；汇流使援军到达顺序产生价值。固定施工位提供安全后位和风险前位；建造期间仍可被拆除。

有些支路几乎等长，重点是接敌隔离与火力覆盖；其他地图有可测量的增援时间差。不能将所有分岔一概描述为明显长绕行。按当前200图，分岔地图的全线最长/最短差约0.04–7.65世界距离，均值约1.52；速度不同会放大或缩短等待差。

每图的完整简报包括故事任务、前后关、路段长度、双方矿点与容量、无排队回款估计、施工锚点、 alternative投入、几何散列和验收项。见 [200地图目录](world/03-200地图目录.md) 与 [离线地图浏览](../../assets/paper-warfront/world-v2-gallery.html)。

十章故事连续接力：伪令、死亡名单、复制王命、生产篡改、消息封锁、货账伪造、记忆侵蚀、冻结协定、幸存者注销、归零印。结局以十位统帅共同建立留名印收束。详见 [完整故事](world/04-完整故事路线.md)。六道既有挑战保留为附加内容，遭遇战开放任意阵营与地图。''',
'09-验收与制作计划.md':'''# 验收、维护与验证层次 · 2.0

证据依次为配置/来源、空间与经济、实际招募/能力、完整合法对局、原生界面与动作、导出程序、Android包和真机。每层注明覆盖范围；规模数量、PNG存在、强制结果截图或签名成功不代替其他层。

基础测试覆盖200图连接、双方工人归仓、编组角色、选路承诺、二维命中和设施施工。战斗测试对400兵逐个实际请求招募、扣费、等待生产与造成伤害，另查代表能力和十院回法/抗性。UI测试通过按钮与战场入口执行招募退款、研究、施工、路标、矿点、50法术、部署保存应用、暂停、滚动文本高度及终章保存重读。

完整战役测试双方使用同一命令、金币/法力、队列、施工与射程。200关均有实际结算记录；多个策略取得的胜利按具体记录计，不将AI失败关直接改成免费取胜。人工操作、长期难度曲线与真实Android设备性能仍是独立检查。

修改路线须重算长度、经济周期、锚点与散列并重验可达性、命中和完整对局；修改单位或技能须检查费用、科技、AI、编组、素材和相应能力；修改UI须检视原生截图，不只看页面函数是否运行。通过适当回归后再更新版本、库存散列和发布包。

具体结果见 [实施与证据](17-规模扩展与实施进度.md)、[双平台发布](22-双平台验收与发布.md)。旧1.0证据在docs/archive/paper-warfront-1.0中，不能拿旧程序证明新体系。''',
'10-变更与决策记录.md':'''# 系统更新的决策记录

早期Three.js低面数方案保留在0.1归档。用户后续明确Godot和Windows/Android交付，当前采用原生2D纸偶以避免外部建模。

地图专项研究确认旧1.0三个场景共用机械地图，十五关全拆城，不能体现原作地图空间和任务节奏。研究的原作案例、版本差异与事实边界保留在 [专项研究](../research/swords-and-soldiers-map/README.md)。本次将地图独立成图模块，单位保存路段锚点，近战/远程/范围采用相应真实距离；工人容量、施工位、节点选择和任务线进入同一模拟。

用户扩展规模后，世界采用十院40职责库和战前4–8兵编组；保留有限HUD与局内投资压力。200图以20题型、十地区、逐关事件展开，明确共享题型而保留独立坐标与规则差异。十种阵营机制在实际经济、抗性或触发收益中兑现；不靠换名和换色计数。

原作未直接验证的PC路标权限、精确射程和高地倍率不当成事实。本作双方独立路标是公开原创规则，高差只有位置与距离作用。原作成就与主任务区分；本作六种任务是经过原作节奏研究后的原创设计。

素材生产拒绝非透明源板和武器边界裁切；三兵重新生成。动作核验修复按画布中线导致旗手缺腿的问题，改用真实脚部权重。原生截图修复正文自动高度归零、过大的普通发射FX与移动控件密度；所有重大修正有相应回归和截图。''',
'11-Godot架构与数据契约.md':'''# Godot架构与数据契约 · 2.0

[project.godot](../../game/project.godot)→main.tscn→main.gd。JSON定义世界、单位、科技、地图、剧情和运行资产；模拟不依赖Control、纹理、窗口或音频。

map_runtime.gd保存DAG路段、折线累积距离、节点邻接、双方路标选择、最短路、投影和edge/s/x/y锚点。battle_sim.gd处理付款、招募、研究、施工、工人任务、状态、投射物、死亡、任务与统计。unit_abilities.gd定义职责和阵营能力；tactical_ai.gd通过公共请求执行对手策略。

main.gd处理原生页面、鼠标键盘/触控、暂停、存档和指令桥接；battle_view.gd只读模拟，负责实际路网、脚点纸偶、相机、预览和反馈；map_preview.gd读取同一地图画战前简图。data_store.gd加载与校验运行绑定，纹理缓存最多140条。audio_controller.gd分发声音，audio_synth.gd提供PCM基础。

固定60Hz；真实delta积累单帧限0.15秒。request生成单侧递增序号，command校验侧别、重复序号、胜败、对象和资源后执行recruit/cancel_queue/research/build/cast/route/mine_priority。拒绝无扣费但消耗序号。队列取消同时验证索引与预期单位ID。

单位保存真实edge/s/x/y、归属、生命、冷却、状态、步态、寿命和任务标记。渲染的排次与脚线不改变战斗距离。事件带kind/time及必要的X/Y、来源、目标、单位ID、数量和半径；drain_events一次消费。近战用道路距离，远程/区域用二维欧氏距离；真实受击时再检查抗性、保护、反弹与状态。

schema2存档：unlocked(0..199)、stars、challenge_stars、loadouts、story_flags、settings和可选legacy_campaign。临时文件替换profile.json；旧十五关记录单独保存，设置/挑战保留。场景重开不保留战斗实体、队列、状态或残余FX。自动UI检查备份并恢复原档。

Windows默认Vulkan/Mobile渲染，兼容入口OpenGL；AndroidGL兼容。逻辑1600×900、横屏等比留边，移动端页数与按钮独立调整。原生APK模板导出，不使用Gradle容器或模拟器。''',
'12-AI与关卡导演规范.md':'''# AI与战役导演 · 2.0

AI和玩家经过同一request/command、费用、上限、冷却、生产、施工、射程与合法目标校验。读取自己的资源/队列、公开军团和地图，不读取敌方钱包或队列；不开隐藏收入。关卡预置军团和对象明示在配置中，不以导演名义循环免费刷兵。

每次决策考虑工人数与矿点容量、运输风险、前方压力、分岔出口与设施覆盖、当前前排/远程/辅助比例、科技门槛、基础血量和任务对象。研究只选编组内兵种与公共门槛；纸械和灯符为设施保留真实预算，施工未完成不兑现收益。

前期压制偏重当前出兵，经济攀升偏重工人与可保护设施，空间反制结合公开兵种和路径压力。入门/标准/强敌改变决策节奏。区域法术选真实二维聚集，护送注意携证者，截巨优先关键敌兵；唯一证据对象不能献弃、夺印或复印。

线性战役逐关配置预算、已开放军库、初始科技、敌方8兵以内编组、预置对象、胜败锚点、AI倾向和剧情。敌编组保留开局合法兵，并随着章节内推进引入不同职责；双方经济仍真实运输。道路长度、容量和设施位置对AI与玩家相同。

200关完整60Hz自动对战用于诊断死局和难度；多种玩家投资策略的获胜记录见output/qa/godot/v2。它们不是人工通关，也不保证所有阵容均可取胜。发布说明明确自动未取胜的关卡与后续人工难度工作。''',
'13-运行素材与反馈矩阵.md':'''# 运行素材与反馈矩阵 · 2.0

400作战兵各有完整切图、192头像和三件纸偶动画；10运金工同样分件；2种临时实体另计。十院各有统帅、基地、哨塔、纸灯、树/植物、旗与货箱；十地区有独立背景。全库数量与技术结果见 [素材报告](../../output/qa/godot/v2/world-assets-report.json)，浏览见 [新版库](../../assets/paper-warfront/world-v2-gallery.html)。

| 行为 | 画面 | 声音与规则来源 |
| --- | --- | --- |
| 自主进军 | 交替腿、轻摆躯干、车轮与归属脚线 | 纸步限流；真实锚点推进 |
| 近战/远程 | 前摇、挥砍/短闪、实际二维飞弹 | 挥击/投射/炮车音；伤害由模拟 |
| 受击与死亡 | 闪白、约55ms停顿、数字、纸屑、倾倒 | 按伤害选择轻重音；重击小震屏 |
| 治疗/控制/复制 | 回血数字、束缚圈、状态字、克隆着色 | 法术家族音与实际状态事件 |
| 归仓/研究 | 收金与科技通知，实际计数刷新 | 独立界面音；完成后才触发收益 |
| 施工/完工/封禁 | 施工条、完工碎屑、熄台标记 | 上行/下行PCM状态音 |
| 路标/矿优先 | 当前方向箭头、提示、真实小地图 | 短状态音；仅影响合法后续行为 |
| 胜败/终章 | 统计、星章、剧情和角色归宿 | 原创胜败音、当前院配乐 |

20种基础SFX、十首40秒原创循环及四个运行时PCM信号。16声效音源池、音乐独立、Master限幅；可独立调音乐/声效及减弱震动。纹理按需加载，缓存140项；粒子/瞬时FX有上限，不预装全400兵。

稀疏战斗、十院环境、法术压力画面与代表动作均有原生截图。尚无Android真机帧率、耗电、长时运行及主观音响验收，不能从Windows截图推断这些结果。''',
'14-双平台构建与安装.md':'''# 双平台构建与安装 · 2.0

当前包入口 [release/2.0.0](../../release/2.0.0/README.md)。Windows x86_64 EXE内嵌资源，可直接运行；Windows ZIP带操作说明与许可。默认Vulkan，旧显卡可用兼容启动入口。Android提供org.paperwarfront.game、versionCode20000、versionName2.0.0的签名APK，ARMv7与ARM64。

源码用Godot4.7.2导入game/project.godot即可运行；图片、字体、音效和音乐均随源包提供，不需重新生成。导出需同版Godot模板、原生Android SDK及JDK。导出预设在game/export_presets.cfg；build_game.py执行导入、两平台导出、APK签名/对齐/ELF检查及SHA256。

Android签名私钥保存在工作区.keys，技能网关由本机技能管理；两者均不随源码或运行包交付。重新签名的APK不能覆盖原签名同包名安装；需要自己的签名进行后续发行。当前APK可升级本工作区同签名1.0版本，设置及旧战役记录按schema2迁移。

Windows解压后双击PaperWarfront.exe；Android把APK复制到设备，在系统提示下允许当前文件来源并安装，完成后横屏游玩。没有联网、登录或下载素材步骤。卸载可能删除本地档案，应自行保留需要的profile.json。

Android验证包括签名、包名/版本/ABI、16KB ZIP对齐与ARM64 ELF段对齐。未连接Android真机，设备触控、刘海、音响和性能待测；禁止使用模拟器代替。详见 [22发布结果](22-双平台验收与发布.md)。'''
}
    for name,text in docs.items():write(DOC/name,text)
    write(DOC/'02-玩法与三阵营规则.md','''# 历史入口

当前规则已扩展为十院，请读 [2.0玩法与十阵营规则](02-玩法与十阵营规则.md)。原三院版本保留在 [1.0快照](../archive/paper-warfront-1.0/docs/02-玩法与三阵营规则.md)。''')
    unit_links='\n'.join(f'- [{f["name"]} · 40兵规格](units/{f["id"]}.md)' for f in factions['factions'])
    write(DOC/'world/README.md',f'''# 十院留名 · 世界、地图与军库

十院40作战兵、200地图和200关故事对应当前Godot配置。定义、素材、界面、完整自动对局与发布证据见 [实施报告](../17-规模扩展与实施进度.md)；自动结果不代替人工平衡和真机验收。

- [核心博弈](01-核心博弈.md)
- [十阵营设定](02-十阵营设定.md)
- [200地图与逐图空间设计](03-200地图目录.md)
- [完整故事路线](04-完整故事路线.md)
- [素材与实际地图库](../../../assets/paper-warfront/world-v2-gallery.html)

{unit_links}''')
    rows=['# 200地图目录 · 当前运行数据','','20种战术题型在十地区展开；共有200份独立几何和完整空间简报。路线、容量、矿位、施工位与任务锚点均实际运行。共享题型不等于共享同一机械地图。','','| 关序 | 地区地图 | 任务 | 分岔数 | 路线最短/最长 | 逐图设计 |','| --- | --- | --- | ---: | --- | --- |']
    names={'destroy_base':'拆城','deliver_gold':'归仓','survive':'守城','protect':'保前哨','escort':'护送','intercept':'截巨'}
    for i,m in enumerate(maps):
        counts=Counter(e['from'] for e in m['edges']);forks=sum(v>1 for v in counts.values())
        rows.append(f'| {i+1:03} | {m["name"]} | {names[m["objective_type"]]} | {forks} | {m["route_lengths"]["shortest"]:.2f} / {m["route_lengths"]["longest"]:.2f} | [空间简报](maps/{m["id"]}.md) |')
    write(DOC/'world/03-200地图目录.md','\n'.join(rows))
    write(DOC/'README.md','''# 纸上兵戈：十院留名 · 2.0 制作入口

Godot原生纸偶策略：200张机械地图、十院各40作战兵、200关连续剧情、50法术及6附加挑战。新版把分岔、汇流、矿点容量、真实运输、施工位、二维命中和任务对象接入模拟与UI。

[双平台下载](../../release/2.0.0/README.md) · [玩家手册](16-玩家手册.md) · [核心博弈](world/01-核心博弈.md) · [200图设计](world/03-200地图目录.md) · [十院军库与故事](world/README.md) · [完整素材与地图浏览](../../assets/paper-warfront/world-v2-gallery.html)

| 文档 | 内容 |
| --- | --- |
| [01章程](01-项目章程与硬约束.md) | 规模、核心契约与原生环境约束 |
| [02规则](02-玩法与十阵营规则.md) | 投资、编组、经济、能力与胜败 |
| [03风格](03-美术风格圣经.md) | 十院纸雕材质、剪影、色彩与阅读 |
| [04素材规范](04-素材库与命名规范.md) | ID、成熟度、尺寸、绑定与来源 |
| [05加工](05-素材生成与加工指导.md) | 指定模型、alpha、整轮廓、修复与分件 |
| [06动作](06-Godot纸偶与动画规范.md) | 实际脚点、步态、攻击、受击与反馈 |
| [07交互](07-交互与UI规范.md) | 原生页面、HUD、触屏分页与滚动文字 |
| [08地图内容](08-关卡与内容规划.md) | 200图题型、经济/路径/设施决策与连续故事 |
| [09验收](09-验收与制作计划.md) | 验证层次与变更回归 |
| [10决策](10-变更与决策记录.md) | 对地图旧问题的修正及原创边界 |
| [11架构](11-Godot架构与数据契约.md) | 模拟、图模块、事件、存档和平台 |
| [12AI](12-AI与关卡导演规范.md) | 公共资源规则、路径反制与逐关配置 |
| [13反馈矩阵](13-运行素材与反馈矩阵.md) | 素材用途、动作、声音和预算 |
| [14安装构建](14-双平台构建与安装.md) | EXE/APK、源码、签名和许可 |
| [15交付入口](15-运行验收与交付报告.md) | 当前验收报告及历史区别 |
| [17实施证据](17-规模扩展与实施进度.md) | 各项实际证据和剩余限制 |
| [18路径经济](18-路径与经济执行规范.md) | 锚点、路标、矿容量与真实二维射程 |
| [19编组科技](19-战前编组与科技规范.md) | 4–8兵、门槛、队列与对象限制 |
| [20故事任务](20-战役与任务执行规范.md) | 十章因果、六任务、线性保存及终章 |
| [21美术动作](21-十院素材与动画规范.md) | 十院源图、动作切图和运行审查 |
| [22发布验收](22-双平台验收与发布.md) | 新包、签名/对齐、截图及实测边界 |

权威参数在game/data；来源与ID不能由旧原型库替代。地图研究事实与版本边界见 [原作专项研究](../research/swords-and-soldiers-map/README.md)，旧1.0文档和数据保留在docs/archive/paper-warfront-1.0。原作数值、PC路标权限和高地倍率未直接测量的部分不冒称已验证。

未连接Android真机；自动玩家获胜不等于全战役人工平衡完成。所有数量与证据范围以当前实施/发布报告为准。''')
    write(DOC/'15-运行验收与交付报告.md','''# 当前运行验收入口 · 2.0

当前完整证据请读 [22双平台验收与发布](22-双平台验收与发布.md) 和 [17实施进度](17-规模扩展与实施进度.md)。1.0的十五关、三背景和三军程序不是当前二百图/十院的证据，旧报告保留在 [历史快照](../archive/paper-warfront-1.0/docs/15-运行验收与交付报告.md)。''')
    write(ROOT/'docs/README.md','''# 项目文档入口

- [纸上兵戈2.0制作文档](paper-warfront/README.md)：十院40兵、200地图、原生Godot系统和当前发布。
- [地图专项研究](research/swords-and-soldiers-map/README.md)：原作版本差异、关卡案例、旧1.0差距与重设计依据。
- [200图完整空间设计](paper-warfront/world/03-200地图目录.md)。
- [世界、阵营、军库与完整故事](paper-warfront/world/README.md)。
- [原作核心体验拆解](剑与勇士-HD-核心体验拆解.md)。

旧1.0共用机械地图的问题属于历史审计，新版图模块和200图已经接入当前工程。具体运行、发布与未实测项以2.0报告为准。''')
    write(ROOT/'game/README.md','''# 纸上兵戈：十院留名 · Godot 2.0

Godot4.7.2导入project.godot，F5运行。所有成品资产随源码提供，无需重新生成或外部建模。[制作文档](../docs/paper-warfront/README.md) · [发布包](../release/2.0.0/README.md)。

入口main.tscn；main.gd负责界面，battle_sim.gd负责60Hz模拟，map_runtime.gd负责真实图，unit_abilities.gd负责兵种/阵营能力，tactical_ai.gd负责公共规则AI，battle_view.gd负责纸偶画面，audio_controller.gd负责声音。

```powershell
godot --headless --path game --script res://tests/test_world_foundation.gd
godot --headless --path game --script res://tests/test_world_combat.gd
godot --headless --path game --script res://tests/test_campaign_play.gd -- --range 0 200
godot --path game -- --qa-world "E:/path/to/desktop-qa"
godot --path game --rendering-method gl_compatibility -- --mobile-ui --qa-world "E:/path/to/mobile-qa"
```

UI QA仅在源码项目中运行并恢复原档。已导出EXE可用`-- --demo --capture <绝对PNG路径> --quit-after-capture`进行实际画面烟测。自动结果不是人工通关证据，移动布局不是Android真机证据。

图像来源与加工在output/imagegen及tools/paper-warfront；签名私钥和网关密钥不在源包。Godot/第三方许可在licenses；字体OFL在assets/fonts。''')
    write(ROOT/'tools/paper-warfront/README.md','''# 纸上兵戈 · 原生制作工具

已交付的game可以直接导入Godot。以下工具用于修改和重建，需要Python、Pillow、NumPy、fontTools及Godot4.7.2；不调用Docker、WSL、容器或模拟器。

| 工具 | 用途 |
| --- | --- |
| expand_world.py | 世界/200地图/400兵/科技/故事设计生成；会重写数据，修改后必须重验 |
| write_world_docs.py / write_v2_docs.py | 200空间简报与当前文档/历史快照 |
| generate_world_art.py / generate_support_art.py | 指定Sub2模型生成兵种、辅助物与七背景 |
| repair_world_art.py | 三处画布边界修复 |
| publish_world_art.py / publish_support_art.py | 完整轮廓、头像、分件、清单与溯源 |
| rebuild_puppet_anchors.py | 实际脚部alpha切线、枢轴与分件 |
| validate_world_assets.py | 当前文件、来源、alpha、脚点、科技、背景与配乐 |
| build_world_gallery.py | 487项新增素材/200图离线浏览与引用文件散列 |
| optimize_fonts.py / master_music.py | 中文子集及十院原创循环 |
| build_game.py | Windows/Android原生导出、签名、对齐与包验证 |
| package_release.py | 两平台交付、源码ZIP与SHA256；排除私钥/缓存/拒绝图 |

生成时调用本机sub2-image-gen技能CLI，由技能管理网关配置，项目工具不复制密钥。源码已经包含全部成品，不需要重新生成。先修改数据与素材，完成对应测试和原生截图复核，最后导出并打包；不能运行旧write_delivery_report.py或write_runtime_docs.py替代2.0报告。

旧1.0源库校验与研究审计工具保留作历史复现，不能拿旧规模或旧程序验证2.0。''')
    print('Current specifications, 200-map index and preserved 1.0 documents written.')
if __name__=='__main__':main()
