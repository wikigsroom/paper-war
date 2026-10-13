"""Author the 2.0 world, 200 spatial maps, 400 combat rosters and linear story.

Templates share a spatial grammar, not geometry or palette-only duplicates.
Definitions are development content until simulation, UI, art and campaign QA pass.
"""
from pathlib import Path
import json, math, copy, hashlib, shutil

ROOT=Path(__file__).resolve().parents[2]
DATA=ROOT/'game/data'
DOC=ROOT/'docs/paper-warfront/world'
BASE=ROOT/'docs/archive/paper-warfront-1.0/data'

FACTIONS=[
 dict(id='yin',name='印甲军',color='b74532',region='朱印疆',hero='赤砚',title='守印将军',
      motif='朱印、方甲、铜签、封缄',mana='upgrade',trait='fortified',
      premise='祖印碎裂后，印甲军封锁运输线。赤砚奉命收回失印，却发现被查封的村落仍在执行伪造王命。',
      stake='守住秩序，还是承认自己保护的印令已经被篡改。',ending='赤砚解除封路，把第一片祖印交给原本被视为敌人的拾纸祭司。',enemy='mo',prefix='朱印'),
 dict(id='mo',name='墨骸社',color='554160',region='旧册泽',hero='墨归',title='拾纸祭司',
      motif='旧纸、骨折、墨斑、尖刃',mana='sacrifice',trait='lifesteal',
      premise='墨归从废纸坑召回被抹去的守城兵，他们共同指认死亡名单先于战斗印好。墨骸社因此追查命令的来源。',
      stake='让亡者作证，还是把他们再次当成可以献弃的兵力。',ending='墨归送回被夺印的活人，留下不能再被复制的原始死亡名单。',enemy='deng',prefix='旧墨'),
 dict(id='deng',name='灯符朝',color='377b78',region='青灯都',hero='灯照',title='校符使',
      motif='青灯、圆符、镜纸、复印纹',mana='facility',trait='ward',
      premise='朝廷同一日发出互相冲突的两份王命。灯照检查纸灯网络，发现真正的王印被无限复印的命令掩盖。',
      stake='维持灯网供给，还是公开会令朝廷崩溃的副本证据。',ending='灯照切断伪令灯阵，保住供民间使用的灯网，并承认没有任何印令可以替代证词。',enemy='ji',prefix='青符'),
 dict(id='ji',name='纸械工坊',color='996a38',region='铜折炉',hero='榫七',title='总装匠',
      motif='铜色纸机、齿轮折线、卷轴车',mana='construction',trait='workshop',
      premise='工坊为十院制造印机，却被告知所有故障都源于工人怠惰。榫七在停转矿炉里发现人为更改的生产顺序。',
      stake='继续交付战争机器，还是让停工的工人掌握自己的运输线。',ending='榫七拆除覆写机的送料结构，将可以修复祖印的榫接图交给鸢纸行会。',enemy='yuan',prefix='铜折'),
 dict(id='yuan',name='鸢纸行会',color='527e9c',region='雁信岭',hero='飞笺',title='领信人',
      motif='蓝羽、折翼、风袋、信筒',mana='junction',trait='junction_haste',
      premise='唯一能串联十院的雁路被相互矛盾的通行符封死。飞笺必须把目击者和榫接图送过被截断的汇流口。',
      stake='快速送信完成契约，还是冒险带上拖慢队伍的人。',ending='飞笺公开雁路时刻表，拒绝再替任何一院秘密封锁消息。',enemy='qi',prefix='雁羽'),
 dict(id='qi',name='金契商盟',color='aa8a32',region='契金埠',hero='契衡',title='行账人',
      motif='金契、票据、秤签、结绳',mana='delivery',trait='bounty',
      premise='商盟掌握矿路与债契，却发现账面上越来越多的金币来自没有运金人的归仓记录。契衡追查被印出来的繁荣。',
      stake='保住账面财富，还是承认财富建立在被注销的名字上。',ending='契衡烧毁强制债契，保留真实货运账，资助难民与活纸种子的运输。',enemy='mu',prefix='金契'),
 dict(id='mu',name='植纤古庭',color='64834a',region='活纤林',hero='纤枝',title='守根人',
      motif='纤维、叶纸、木纹、根脉',mana='growth',trait='regeneration',
      premise='古庭的活纸能保存未经印写的记忆，却正在被新王命的墨液侵蚀。纤枝沿根脉寻找旧约的原始载体。',
      stake='隔绝外界保住古庭，还是让活纸成为所有人的记忆容器。',ending='纤枝将最后一株活纸交给十院共同保管，不再把记忆锁在古庭内部。',enemy='shuang',prefix='活纤'),
 dict(id='shuang',name='霜裁守序',color='6996a7',region='冻页台',hero='霜律',title='解封裁官',
      motif='霜蓝、裁刀、冰页、方框',mana='control',trait='control_reward',
      premise='裁院把争议证词冻结，声称这样便不会再有战争。霜律发现被冻结的不是争议，而是被反复擦除的和平协定。',
      stake='服从永远不变的裁定，还是让矛盾公开并承担判断的责任。',ending='霜律解冻十院旧约，撤销所有以沉默代替证据的裁决。',enemy='jin',prefix='霜裁'),
 dict(id='jin',name='烬纸流亡',color='b9673f',region='余烬渡',hero='烬禾',title='渡纸人',
      motif='炭边、橙火、补丁、残旗',mana='damage',trait='last_stand',
      premise='印院战争后的难民被统一记录为灰烬。烬禾带着幸存者穿过旧战场，把十院收集的证据送到祖印核心。',
      stake='靠愤怒摧毁所有印院，还是让每个幸存者获得自己的名字。',ending='烬禾阻止报复性焚城，带着十院证据和活纸抵达留白庭。',enemy='bai',prefix='余烬'),
 dict(id='bai',name='空白档案',color='817c96',region='留白庭',hero='白匣',title='末任校档官',
      motif='象牙白、灰紫、空框、删改印',mana='research',trait='arcane_resistance',
      premise='白匣发现归零印以消除记忆阻止战争，又以同样的消除制造下一场战争。他必须在自己的档案军追捕下解开覆写程序。',
      stake='接受无争议的空白世界，还是保留真实且不能被统一的记忆。',ending='十院拆解归零印，将祖印改为只能共同见证、不能覆写个人记忆的留名印。战场成为可读的旧页，而不是被抹去的历史。',enemy='yin',prefix='留白'),
]

# Each row specifies a different tactical role and implemented ability contract.
# Worker and temporary summons are deliberately outside these 40 combat slots.
ROLES=[
 ('vanguard','前阵刀兵',45,160,18,.9,.16,.65,1.10,'melee',{}),
 ('pike','拒骑矛卫',58,125,20,1.05,.19,1.3,1.02,'melee',{'anti_fast_multiplier':1.55}),
 ('guard','护运甲士',70,245,14,1.1,.2,.7,.88,'melee',{'worker_guard_radius':2.8,'worker_guard_reduction':.28}),
 ('cleaver','裂页斧手',78,165,24,1.35,.3,.8,1.02,'melee-area',{'radius':.8}),
 ('duelist','试刃客',72,108,15,.48,.12,.7,1.23,'melee',{'duel_multiplier':1.22}),
 ('lancer','跃折枪兵',76,136,22,.95,.18,.8,1.18,'melee',{'leap_max_distance':2.5,'leap_cooldown':5}),
 ('assassin','越阵短刃',106,105,30,1.15,.18,.75,1.36,'melee',{'crossing_max_distance':3.6,'crossing_cooldown':6,'support_multiplier':1.35}),
 ('shield','叠甲守卫',100,270,18,1.15,.25,.75,.82,'melee',{'physical_damage_multiplier':.70}),
 ('crusher','震纸锤卫',96,238,33,1.75,.4,.85,.87,'melee-area',{'radius':.55,'stun_seconds':.45}),
 ('harrier','缚足钩兵',78,140,15,.95,.18,1.1,1.12,'melee',{'on_hit_slow':1.4}),
 ('banner','行军旗手',88,175,12,1.2,.2,.7,1.0,'melee',{'aura_speed':.18,'aura_radius':3}),
 ('drummer','战鼓签手',98,135,10,1.15,.2,2.1,1.0,'projectile',{'aura_damage':.16,'aura_radius':3.2}),
 ('medic','补页医师',110,112,8,1.5,.2,3.4,.95,'projectile',{'heal_amount':20,'heal_interval':3.2,'heal_radius':3.2}),
 ('engineer','修塔匠',105,148,13,1.3,.22,2.5,.96,'projectile',{'repair_building':22,'repair_interval':3.4,'repair_radius':3.5}),
 ('mirror','返签卫',105,163,18,1.0,.2,.72,1.1,'melee',{'reflection_cooldown':3}),
 ('scribe','禁言符师',122,97,13,1.4,.24,4.0,1.0,'projectile',{'silence_seconds':1.6}),
 ('poisoner','腐墨针手',62,84,9,1.2,.18,4.0,1.1,'projectile',{'poison_damage_per_second':4,'reflectable':True}),
 ('burner','焚边签兵',106,94,16,1.4,.24,3.8,.99,'projectile',{'burn_damage_per_second':6,'radius':.4}),
 ('archer','折弦弓兵',60,76,17,1.0,.17,4.8,1.1,'projectile',{'reflectable':True}),
 ('javelin','投纸矛手',62,83,15,1.05,.18,4.2,1.05,'projectile',{'reflectable':True,'anti_fast_multiplier':1.25}),
 ('sniper','望页弩手',136,82,46,2.2,.45,6.2,.89,'projectile',{'support_priority':True,'reflectable':True}),
 ('repeater','连签火手',104,105,11,1.75,.2,4.2,1.04,'projectile',{'burst_count':3,'reflectable':True}),
 ('artillery','卷轴炮车',152,172,38,2.5,.4,5.1,.54,'projectile-area',{'radius':.6,'building_multiplier':2.5,'reflectable':True}),
 ('siege','撞印车',164,350,40,2.0,.48,1.1,.58,'melee',{'building_multiplier':3.0}),
 ('mortar','抛墨臼',175,130,43,3.1,.65,6.0,.58,'projectile-area',{'radius':1.2,'reflectable':False}),
 ('chain','连墨术士',146,99,22,1.9,.3,4.5,.93,'projectile',{'chain_targets':3,'chain_radius':2.2,'reflectable':False}),
 ('executioner','断页刑兵',118,178,31,1.25,.3,.85,1.04,'melee',{'execute_threshold':.35,'execute_multiplier':1.7}),
 ('leech','夺血纸客',120,146,23,1.1,.23,.75,1.14,'melee',{'lifesteal':.28}),
 ('raider','截金游兵',84,120,17,.8,.16,.7,1.3,'melee',{'worker_multiplier':2.4}),
 ('demolisher','拆灯斧匠',128,220,25,1.4,.28,.9,.97,'melee',{'building_multiplier':2.8,'construction_multiplier':1.5}),
 ('summoner','唤卫符使',172,112,10,1.55,.2,3.5,.92,'projectile',{'auto_guardian_seconds':12,'ability_interval':7}),
 ('necromancer','拾页祭司',158,98,7,1.4,.2,3.8,.95,'projectile',{'corpse_summon':True,'corpse_range':3.6,'summon_interval':3,'max_owned_thralls':4}),
 ('illusionist','复影校书',162,114,13,1.5,.22,3.7,.98,'projectile',{'auto_clone_seconds':8,'ability_interval':9}),
 ('saboteur','熄台潜客',130,127,19,1.15,.2,.8,1.25,'melee',{'disable_facility_seconds':3}),
 ('warden','钉页卫',103,200,17,1.3,.26,1.1,.94,'melee',{'root_seconds':1.1}),
 ('berserker','破缄狂兵',125,218,27,1.15,.2,.8,1.07,'melee',{'enrage_threshold':.35,'enrage_multiplier':1.7}),
 ('colossus','厚页巨像',270,650,67,2.9,.72,1.35,.54,'melee-area',{'radius':1.2,'giant':True}),
 ('caravan','护矿执旗',115,172,14,1.05,.2,2.8,1.07,'projectile',{'delivery_aura':2,'aura_radius':3.2}),
 ('oracle','观墨师',146,104,20,1.7,.25,4.8,.94,'projectile',{'kill_mana':5,'magic_damage':True}),
 ('phoenix','燃尽重卫',165,260,28,1.7,.4,.9,.85,'melee',{'death_burst_damage':45,'death_burst_radius':1.7}),
]

LEGACY={'yin':{'vanguard':'axe','javelin':'spear','crusher':'hammer','artillery':'cannon'},
        'mo':{'lancer':'blade','poisoner':'needle','necromancer':'priest','colossus':'giant'},
        'deng':{'mirror':'mirror','repeater':'fire','assassin':'shadow','shield':'effigy'}}

RECIPES=[
 ('归仓道','经济与增援',0,1,'destroy_base'),('外矿岔','安全矿与外矿',1,2,'deliver_gold'),
 ('前哨坡','施工与保护',0,2,'protect'),('折页口','第一次选路',1,1,'destroy_base'),
 ('金车线','矿位服务与运输',1,3,'deliver_gold'),('证人径','指定对象护送',1,2,'escort'),
 ('灯阵口','争夺设施空间',2,2,'destroy_base'),('长援岭','慢兵与远程增援',0,2,'survive'),
 ('双汇桥','两段分岔的批次时序',2,2,'destroy_base'),('余粮页','有限预算与突破',1,1,'escort'),
 ('三签道','三选一与汇流',1,2,'destroy_base'),('回折坂','绕行与拦截',2,2,'intercept'),
 ('三矿埠','扩张经济与防守',2,3,'deliver_gold'),('截巨线','控制与矿线边界',0,2,'intercept'),
 ('护印台','前置对象与施工',2,2,'protect'),('三路渡','护送的路线承诺',2,2,'escort'),
 ('高折原','地表高度与选取',2,2,'destroy_base'),('围灯阵','多设施与反制',3,3,'protect'),
 ('反攻页','守住后的反扑',2,3,'survive'),('合印门','本章综合战',3,3,'destroy_base'),
]

# The entries are chronological facts/scenes, not randomly assembled plot fragments.
BEATS={
'yin':[
'赤砚护送第一批运金工回城，发现查封令盖着尚未制作的日期。','被封外矿仍养着村民，赤砚允许工人重开运输。','前哨匠指出两枚王印边角不同，需要保住施工塔留下实物。','追捕队从上路逼近，赤砚改路救下携带旧印的信人。','账册显示供军金币来自被宣布废弃的矿场。','信人带来一名墨骸俘虏，他能说出尚未发生的伤亡名单。','灯符守卫奉另一份王命拆塔，赤砚拒绝交出证据。','增援迟到，印甲军第一次必须靠自己守住矿线。','赤砚让两批兵在双汇口会合，避免把工人当成断后队伍。','有限军粮只能保护一队证人穿过封路军。','三处路标被盖成同一方向，赤砚亲自恢复分流。','伪令使巨像沿矿道推进，必须在运输线前截住。','三矿劳工提交同一份被抹名的薪册。','第二具巨像携带覆写印记，赤砚拦下它以免矿册被毁。','原印被送上护印台，施工塔必须撑到鉴印结束。','证人经三路渡返回，印甲追捕队开始质疑自己的命令。','高度错落的纸坡暴露出伪令队藏着的印机。','赤砚守住检验灯阵，确认王命出自同一台复制机。','印甲旧部反扑索印，赤砚让工人先撤再守住城门。','赤砚解除矿路封锁，带着第一片祖印与墨归结盟。'],
'mo':[
'墨归召回废纸坑的守城兵，确认他们的名字先于死亡被注销。','拾金纸工在外矿找到未烧完的伤亡底稿。','祭司护住记名塔，让亡者说出当时的守城顺序。','追捕者沿主路来袭，墨归分流护送活着的家属。','运回的不是祭品，而是可证明薪资仍被领取的旧契。','一名归来的纸骨兵执意送回自己的姓名牌。','灯网把证词复制成互相矛盾的版本，祭司逼近校符台。','墨归拒绝无限献弃亡者，守住最后一批尚能作证的纸页。','两支追捕队在汇流口交错，墨归利用停顿清出证人道路。','残页不足以再召军，有限部队护送名单原件。','三路中的一条通向焚册炉，路标必须让后来者避开。','夺印巨兵带走活人，墨归在矿线前解救被俘工人。','多个矿点都藏着同一种提前印好的死亡章。','巨像企图踩碎旧册仓，控制窗口决定原件能否保存。','墨归保护记名台，给被误认为复制体的证人确认身份。','家属随证人穿过三路渡，召回的军队自愿留下断后。','高折纸层里找到没有经过灯网的原始命令。','记名灯阵保留每一个不同版本，不能让追捕队逐个熄灭。','祭司面对索祭的旧部，守住活人而非继续扩充亡军。','墨归归还被夺印的人，携原始名单进入青灯都。'],
'deng':[
'灯照检查归仓灯，发现同一金币记录被点亮了两次。','外矿信灯收到两份互斥王命，必须保持真实货运。','校符塔施工时遭到纸械试机队压制。','灯照切路分开两批副本，避免相同命令互相覆盖。','运输纸签的编号证明复制早于原印签发。','一名不肯被复印的校书生带原版进入灯都。','灯照夺回校符台，查明伪令来自覆写机。','关闭总灯会让居民失去照明，他选择守住分支灯。','不同批次火签兵在双汇桥清出通往民灯的路径。','预算只够护送一份原稿，灯照拒绝用副本替代。','三签道呈现三种王令，必须按证人给出的次序分流。','覆写机的试验巨兵要撞毁原版库存。','三矿票签都被灌入相同回法印记。','灯照在金线前截住试机兵，留下可检查的驱动纸。','鉴令台将证明原印已经破碎，所有校符塔必须存活。','原版经三路渡分送十院，灯照不再独占解释权。','高折原的镜纸反射暴露工坊藏着的第二套驱动板。','灯照保护民灯并逐座关闭伪令设施。','朝廷副本军反扑，分灯网络撑住居民撤离。','灯照保留民灯、切断伪令，将驱动板交给榫七。'],
'ji':[
'榫七恢复停转归仓机，工人交来的第一趟金币没有账面副本。','外矿送料线被刻意延长，工坊必须保障实际货运。','新前哨要在试验车冲到之前完成。','榫七更改分流签，让工人和试机军走不同批次。','金车记录指向一台从未停机的秘密印炉。','一名领班带着原始排产单逃出车间。','工坊保住校机台，发现故障命令来自覆写程序。','远方慢车来不及支援，榫七用前线修塔撑住炉口。','双汇桥让修塔匠与攻城车同步抵达。','有限燃料只够把领班送出烧炉区。','三签道对应三个送料口，选路影响车队能否合流。','自动巨车被错误指令锁死，必须在矿线前拆掉。','三矿实际出料与账面产量不符，工人取回底账。','另一台巨车带着原印榫件，不能让它抵达碎纸槽。','总装台必须保持完整，榫七在此完成祖印修复方案。','携图匠人穿过三路渡，鸢纸信队前来接应。','高折传动页揭示机器从来无法自行决定王命。','工坊护住校准灯阵，使每个驱动错误都能被看见。','封工军反扑，榫七守住工人撤离的最后一班车。','榫七拆开覆写机送料部，把榫接图交给飞笺。'],
'yuan':[
'飞笺重新打通归仓雁路，信人第一次收到真实运输时刻。','外矿运金与信队争路，需要用批次避免相互耽搁。','临时信塔在契军到来前必须完成。','一封假通行符改变路标，飞笺按证人的指示恢复方向。','回仓纸袋带着被商盟扣下的送信凭据。','飞笺护送慢行的目击者，放弃最快的独行路线。','信队保住分发台，让十院同时看到同一份榫图。','契军围堵长岭，飞笺靠短路补给撑到见证者到达。','两批信队在双汇桥交接，快慢路径承担不同责任。','余粮只够一趟送信，必须带上不能复印的原件。','三路通行签中的封路权限被查出属于同一账房。','拦截巨兵沿雁路靠近，不能让它踩碎矿工回程。','三矿信笺揭露运输延误被反复算成欠债。','飞笺截住缴债巨车，救下被当成抵押品的信人。','共阅信台必须存活，不能让公开消息再次变成秘密。','见证者经三路渡抵达契金埠，路线选择关乎护卫到达。','高折风袋中藏着历年被退回的和平信。','飞笺守住公开灯阵，令每个印院都能确认收信时刻。','独占雁路的旧行首反扑，信队守住最后一班民信。','飞笺公布雁路时刻表，与契衡清算被篡改的货运账。'],
'qi':[
'契衡核实第一趟归仓，账面多出的金币没有对应运金人。','外矿断货仍被计成盈利，他命令恢复可见运输。','审账塔施工中遭到拒交底账的私兵攻击。','两条路线分别运送证人和假账，契衡先保护原始记录。','金车交付证明工人薪资被改成了债务。','一个被注销的账房带着签名逃向公审台。','商盟保住核契灯，把副本收入从真实货物中分离。','没有纸面利润可买增援，契衡必须守住实物矿仓。','双汇口同时收到雁路信与矿场底账，账目第一次能相互校验。','有限预算只够护送账房，不能再靠征债扩大军队。','三路债签把同一个人分成三个欠款人。','征债巨车要夺走外矿，契衡在矿线前拦下。','三矿的名单拼出被抹去的活纸种子运输。','印金巨像带着没有归仓记录的空币，必须留下证据。','公审台存活期间，强制债契才能被逐份撤销。','账房与活纸种子经三路渡去往古庭。','高折契页中藏着商盟与留白庭签下的秘密回收协议。','契衡守住结算灯阵，让所有债人看到撤销结果。','旧账房私军反扑，商盟守住难民的最后一批货。','契衡烧毁强制债契，资助纤枝保存活纸记忆。'],
'mu':[
'纤枝保护运金工，确认新墨病会先侵蚀反复改写的纸。','外矿运输带来受病叶纸，古庭不能靠封路避开现实。','守根塔要在裁院的封存兵到来前完成。','不同纸层的根脉分岔，让护卫避开最脆弱的活纸。','归仓种子保存着一个与王命不同的旧日期。','最后一名植纸人携活根逃向共育台。','古庭守住净墨设施，让原始纤维抵住副本墨液。','霜裁要求冻结所有病页，纤枝守住仍能自愈的根脉。','两批护根兵在双汇口接上，防止慢行医师孤立。','只余一株活根，有限军粮必须把它送出林缘。','三签道连接三处记忆叶，任何一处被抹去都会留下空缺。','封存巨兵将踩断运输根线，必须提前截住。','三矿底纸保存着旧约各院的原始签名。','巨像携着冻页框，纤枝在矿线前救出封存纸。','共育台存活到根脉稳定，原始旧约才可显现。','活纸经三路渡送往冻页台，护送对象不能被复印替代。','高折原的旧根显出第一次归零以前的和平约定。','纤枝守住净墨灯阵，使冻结记录保留清晰边缘。','封林军反扑，古庭让难民带走种子再守住林口。','纤枝将活纸交给十院共同保管，要求霜律解封旧约。'],
'shuang':[
'霜律检查冻仓，发现金币记录冻结以后仍在被修改。','外矿冻结令让工人失去回程，他恢复可验证的运输。','解封塔施工中遭到旧裁官干预。','霜律分路引开封存兵，让原始证词沿安全路径前进。','归仓冰签显示每次战争前都有同一份撤证裁定。','一名被冻住身份的书记走向共审台。','裁院保护解冻设施，不能让证据在展示前被焚毁。','烬军要求立即破冰，霜律守住仍有活人的冻页层。','两批部队在双汇口协调，避免解冻队遭到误伤。','有限热纸只够解封一队书记，必须把他们送出冰库。','三签道分别通向封存、复审与删除，路标决定后来者去向。','删除巨兵要抵达矿仓，霜律以控制争取取证时间。','三矿旧册拼出留白庭历次归零的年份。','巨像带着最后一份归零名单，必须在金线前留下。','共审台必须完整，冻结的旧约才能公开展示。','书记经三路渡把解封记录交给难民。','高折冰页下的裂痕证明记忆抹除从未阻止战争。','霜律守住解封灯阵，使不同证词同时可读。','旧裁官军反扑，裁院守住带证词撤离的民众。','霜律撤销沉默裁定，把归零记录交给烬禾。'],
'jin':[
'烬禾让幸存者完成第一趟归仓，证明他们并不是账上的灰烬。','外矿残旗记录失踪的人，他带工人重新取回姓名牌。','临时护名塔在档案追兵抵达前必须完成。','烬禾改变后续部队的路线，把慢行难民留在护卫之后。','归仓补丁上写着被十院反复注销的同一家人。','一队难民带着十院证物向祖印门前进。','流亡军护住合页设施，避免不同证据再次被副本覆盖。','档案兵围堵余烬渡，烬禾守住正在登车的人。','两批护卫在双汇桥替换，受伤前排不再被当作燃料。','有限余粮只能送走最后一队见证者。','三路渡中最快的路有追兵，烬禾选择能让护卫接上的路线。','归零巨兵朝矿线推进，流亡军必须在断粮前拦住。','三矿残页说明留白庭正在准备新的记忆清空。','第二具巨像携删除印，烬禾拒绝让它烧尽姓名仓。','共名台保持完整，流亡者可以在此恢复记录。','证物与难民穿过三路渡，白匣秘密打开档案外门。','高折旧战场展示上一次归零后同样的战火。','烬禾守住留名灯阵，阻止己方愤怒的焚城队。','报复军反扑，流亡军先保护民众再守住渡口。','烬禾带着完整证物抵达留白庭，要求白匣停止归零。'],
'bai':[
'白匣核对原始归仓记录，发现覆写程序连自己的记忆也在修改。','他开放外矿给追来的难民，让纸城不再靠注销人名维持。','留名塔施工中遭到档案旧军追捕。','白匣更改路标，让后来者绕过被设为删除口的路径。','真实货运账与伪造收入一起送到公共档台。','最后一名校档官携归零程序的原件前来作证。','十院部队保护合印设施，白匣逐段拆开覆写命令。','档案军封锁长岭，见证者必须活到共同印台开放。','双汇口让不同阵营在同一时刻到达，祖印第一次由多方持有。','有限纸页只够保存一份程序，白匣选择原件而非可重写副本。','三签道分别指向独占、删除与共阅，后续军队被引向共阅。','归零巨兵试图踩碎证物矿仓，白匣在边界前拆下它的印头。','三矿账、旧约与姓名牌共同证明十院可以共享真实记录。','最后的覆写巨像逼近合印门，所有证据必须保留下来。','十院保护留名台直到共同校印完成，任何一院都不能独占。','见证者穿过三路渡，汇聚到不可再被复制替代的原始签名处。','高折档页中显出归零的最初恐惧，白匣承认它已经制造新的战争。','共阅灯阵照亮所有不同证词，删除命令逐一失效。','旧档军发动最后反扑，十院守住每个已经恢复的名字。','十院拆解归零印，建立只能共同见证的留名印；飞笺送出第一封不再被覆写的和平信。'],
}

def dump(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def save_baseline():
    BASE.mkdir(parents=True,exist_ok=True)
    for name in ['balance-prototype.json','technology.json','campaign.json']:
        if not (BASE/name).exists(): shutil.copy2(DATA/name,BASE/name)

def archetype_note(role,abilities):
    reasons={
      'vanguard':'低费承伤；远程与控制可在其后积累。','pike':'克制快速冲锋；怕范围打击和长射程消耗。',
      'guard':'保护矿工运输；投入护矿会减少前线火力。','cleaver':'处理密集近战；长前摇易被控制。',
      'duelist':'单点快速交换；生命低，怕范围与远程。','lancer':'缩短接敌等待；不能跳到另一条路线。',
      'assassin':'穿过局部前排威胁支援；定身阻止越线。','shield':'物理承伤；直接法术可以绕过纸甲。',
      'crusher':'重击打断；攻击前摇可被敌方打断。','harrier':'延缓敌方接近；远程持续输出仍能反制。',
      'banner':'改善附近部队到达相位；旗手本身输出不足。','drummer':'增幅附近火力；集群站位怕范围法术。',
      'medic':'周期性恢复附近受伤兵；控制/爆发能突破恢复窗口。','engineer':'修复近处设施；离开建筑区能力受限。',
      'mirror':'有冷却的投射物反弹；直接法术与近战仍有效。','scribe':'暂时禁止敌人自动特殊能力；普通攻击不受影响。',
      'poisoner':'持续伤害；清除后排或免伤可阻止累积。','burner':'范围灼烧；低生命与较长周期限制持续火力。',
      'archer':'远距低费输出；需要前排，怕越线。','javelin':'处理较快敌军；反弹和高甲可反制。',
      'sniper':'优先攻击支援；慢射击给救援法术留下窗口。','repeater':'多次投射；单发反弹会打断火力收益。',
      'artillery':'远程攻城；慢走和慢发使增援位置重要。','siege':'高建筑伤害；面对军团时效率低。',
      'mortar':'远距范围弹；长前摇和低耐久可被突袭。','chain':'弹跳处理集群；分开站位降低价值。',
      'executioner':'收割低血单位；满血前排可以拖住。','leech':'近战吸血续航；控制和集中火力压过恢复。',
      'raider':'快速截工；正面耐久不足。','demolisher':'抢拆设施尤其施工目标；怕远程与迟到。',
      'summoner':'周期召临时护卫；有限所有权与寿命避免无限成军。','necromancer':'消费附近纸标复兵；纸标不足或被争夺时无效。',
      'illusionist':'复制附近普通兵；有限寿命，禁复制链与巨人。','saboteur':'短时熄灭设施能力；无法永久免费拆塔。',
      'warden':'命中定身，敌人仍可攻击；长射程可反制。','berserker':'低血爆发；控制后清除而非慢慢消耗。',
      'colossus':'耐久范围重击；昂贵慢走，前摇可打断。','caravan':'提高附近工人的每趟实际交付；依赖同路护运。',
      'oracle':'魔法输出与合法击杀回法；怕突袭，召唤不能刷回法。','phoenix':'死亡时局部爆发；不能伤到远处和另一条分离路线。'}
    return reasons[role]

def rosters(base):
    units={}; technology=[]; initial={}; faction_output=copy.deepcopy(FACTIONS)
    for f in faction_output:
        fid=f['id']; roster=[]
        for index,row in enumerate(ROLES):
            role,label,gold,hp,damage,interval,windup,reach,speed,attack,ability=row
            tail=LEGACY.get(fid,{}).get(role,role)
            uid=f'unit.{fid}.{tail}'
            definition=dict(gold=gold,hp=hp,damage=damage,attack_interval=interval,windup=windup,range=reach,speed=speed,attack=attack,**copy.deepcopy(ability))
            if uid in base['units']:
                definition.update(copy.deepcopy(base['units'][uid]))
            tier=min(4,index//8)
            definition.update(name=f['prefix']+label,faction=fid,role=role,tier=tier,manual_recruit=True,
                              hint=archetype_note(role,ability),faction_trait=f['trait'],art_status='needs-new-art',
                              art_source=f'unit.{"yin" if attack.startswith("melee") else "deng"}.{ "axe" if attack.startswith("melee") else "fire"}')
            if uid in base['units']: definition['art_source']=uid;definition['art_status']='existing-verified'
            if role in ['artillery','mortar','siege']: definition['art_source']='unit.yin.cannon'
            if role=='colossus': definition['art_source']='unit.mo.giant'
            if role=='necromancer':
                definition.update(summons='unit.mo.thrall',summon_interval=3,corpse_range=3.6,max_owned_thralls=4)
            if fid=='yin':definition['physical_damage_multiplier']=round(definition.get('physical_damage_multiplier',1)*.91,3)
            elif fid=='mo':definition['lifesteal']=max(definition.get('lifesteal',0),.10);definition['hp']=round(definition['hp']*.94)
            elif fid=='ji':definition['workshop_bonus']=.22;definition['speed']=round(definition['speed']*.93,3)
            elif fid=='yuan':definition['junction_haste_seconds']=3.5;definition['hp']=round(definition['hp']*.91)
            elif fid=='qi':definition['bounty_gold']=3;definition['gold']=round(definition['gold']*1.08)
            elif fid=='mu':definition['regeneration']=1.5
            elif fid=='shuang':definition['control_mana']=1.5
            elif fid=='jin':definition['enrage_threshold']=max(definition.get('enrage_threshold',0),.3);definition['enrage_multiplier']=max(definition.get('enrage_multiplier',1),1.35)
            elif fid=='bai':definition['magic_damage_multiplier']=.70;definition['physical_damage_multiplier']=1.10
            units[uid]=definition; roster.append(uid)
            technology.append(dict(id=f'tech.{fid}.{tail}',faction=fid,grant=uid,gold=35+tier*35+index%4*5,seconds=3+tier*1.5,
                                   requires=[] if tier==0 else [f'tech.{fid}.doctrine{tier}'],tier=tier))
        for rank in range(1,5):
            technology.append(dict(id=f'tech.{fid}.doctrine{rank}',faction=fid,grant=f'upgrade.{fid}.doctrine{rank}',
                                   gold=45+rank*25,seconds=3+rank,requires=[] if rank==1 else [f'tech.{fid}.doctrine{rank-1}'],tier=rank))
        worker=f'unit.{fid}.worker'
        units[worker]=dict(gold=35,hp=55,damage=0,attack_interval=0,windup=0,range=0,speed=1.25,attack='none',economy=True,
                           name=f['prefix']+'运金工',art_source=f'unit.{fid if fid in ["yin","mo","deng"] else "yin"}.worker',art_status='needs-new-art',faction=fid,cargo=8)
        if fid=='ji': units[worker].update(cargo=10,speed=1.1)
        if fid=='yuan': units[worker].update(cargo=7,speed=1.5)
        introductory = list(LEGACY.get(fid,{}).keys()) + ['vanguard','archer','guard','medic','javelin','crusher','artillery','mirror']
        preferred = []
        for role in introductory:
            uid=f'unit.{fid}.{LEGACY.get(fid,{}).get(role,role)}'
            if uid not in preferred:preferred.append(uid)
        roster = preferred[:8] + [uid for uid in roster if uid not in preferred[:8]]
        f['combat_units']=roster;f['worker']=worker;f['default_roster']=roster[:8];f['mana_base']=.5
        initial[fid]=roster[:2]+[worker,f'building.{fid}.mana']
    for uid in ['unit.mo.thrall','unit.deng.guardian']:
        units[uid]=copy.deepcopy(base['units'][uid]); units[uid]['art_source']=uid
    return units,technology,initial,faction_output

def make_map(region_index,local):
    faction=FACTIONS[region_index]; label,lesson,forks,mine_count,objective=RECIPES[local]
    spatial_rules=[
        '印军后方设施集中，短路适合重甲集合；绕路让突击暴露在更长的增援等待中。',
        '旧册泽的中段汇流偏晚，前线遗纸更远离后方祭司；要决定随军复兵还是回守矿线。',
        '青灯都保留更多后位灯台；中央支路缩短敌军接近外灯的路程，灯网需要分层保护。',
        '铜折炉增加汇流与施工位，工坊增益覆盖前哨但不能同时覆盖所有支路。',
        '雁信岭增加连续路口；轻军可以多次经过节点获得加速，但仍需承担较长的送信距离。',
        '契金埠增加高载荷外矿、收紧近矿容量；护卫与扩工决定回法与金币是否兑现。',
        '活纤林分路更开阔且采矿时间更长；中段行军提供修复时间，也给腐蚀突击留出窗口。',
        '冻页台支路间距更近，远程可以跨路支援，近战仍必须沿路汇流；控制施法价值更高。',
        '余烬渡前后增援区不对称，较近前哨可以及时支援，但暴露给绕行的截击部队。',
        '留白庭设置连续三选口与中段设施，分兵守证据和集中突破不能同时免费实现。']
    if local>=3:
        if region_index in [3,4,9]:forks=min(4,forks+1)
        if region_index in [5,6]:mine_count=min(4,mine_count+1)
    length=46+local%5*5+region_index*1.4+(14 if local in [7,18,19] else 0)
    start=2.0; finish=length-2
    nodes=[];edges=[]
    def height(x):
        return round(math.sin((x-start)/(finish-start)*math.pi*2+region_index*.27)*(.10+.025*region_index+.05*(local%4)),3)
    def node(nid,x):
        y=height(x);nodes.append(dict(id=nid,position=[round(x,3),y]));return y
    node('west',start);node('east',finish)
    if not forks: cuts=[start,finish]
    else:
        cuts=[start]
        entry=.20+([0,.045,-.035,-.025,-.06,0,.025,.03,-.02,-.055][region_index] if local>=3 else 0)
        split_span=[.58,.64,.56,.60,.65,.58,.62,.54,.59,.63][region_index]
        for k in range(forks):cuts.extend([start+(finish-start)*(entry+k*split_span/forks),start+(finish-start)*(entry+(k+.70+(local%3)*.02)*split_span/forks)])
        cuts.append(finish)
    for i,x in enumerate(cuts[1:-1],1):node(f'n{i}',x)
    def nname(i):return 'west' if i==0 else ('east' if i==len(cuts)-1 else f'n{i}')
    for i in range(len(cuts)-1):
        xa,xb=cuts[i],cuts[i+1];a,b=nname(i),nname(i+1)
        is_fork=forks and i%2==1
        ways=3 if is_fork and (local in [10,15] or (region_index in [2,3,9] and (i+local)%3==0)) else (2 if is_fork else 1)
        for way in range(ways):
            if ways==1: offsets=[0,0,0,0]
            elif way==0: offsets=[0,-1.1-.065*(local%4)-(.34 if region_index==6 else 0)+(.35 if region_index==7 else 0),-1.1-.065*(local%4)-(.34 if region_index==6 else 0)+(.35 if region_index==7 else 0),0]
            elif way==1: offsets=[0,1.35+.08*(region_index%4)-(.35 if region_index==7 else 0),1.45+.08*(region_index%4)-(.35 if region_index==7 else 0),0]
            else: offsets=[0,.1,-.1,0]
            xs=[xa,xa+(xb-xa)*.3,xa+(xb-xa)*.7,xb]
            points=[[round(x,3),round(height(x)+off,3)] for x,off in zip(xs,offsets)]
            if ways>1 and way==1:
                midx=(xa+xb)/2
                points.insert(2,[round(midx,3),round(height(midx)+.4,3)])
            edges.append(dict(id=f'e{i}.{way}',**{'from':a,'to':b},points=points,route_role='direct' if way==0 else ('detour' if way==1 else 'central')))
    edge_by_id={e['id']:e for e in edges}
    def placement(e,portion):
        lengths=[math.dist(a,b) for a,b in zip(e['points'],e['points'][1:])];total=sum(lengths);s=total*portion;left=s
        for index,seg in enumerate(lengths):
            if left<=seg:
                t=left/seg;a,b=e['points'][index:index+2];return dict(edge=e['id'],s=round(s,5),x=round(a[0]+(b[0]-a[0])*t,4),y=round(a[1]+(b[1]-a[1])*t,4))
            left-=seg
        raise ValueError('placement outside edge')
    mines=[];sites=[]
    for side in range(2):
        side_edges=edges if side==0 else list(reversed(edges))
        near=side_edges[0]
        for k in range(mine_count):
            if k==0:
                chosen=near
                edge_length=sum(math.dist(a,b) for a,b in zip(chosen['points'],chosen['points'][1:]))
                portion=min(.8,(4+.18*region_index+.12*(local%3))/edge_length)
                fraction=portion if side==0 else 1-portion
            else:
                target=start+(finish-start)*((.20+.12*k) if side==0 else (.80-.12*k))
                chosen=min(edges,key=lambda e:abs((e['points'][0][0]+e['points'][-1][0])/2-target)+(0 if e['route_role']=='detour' else .05))
                xa,xb=chosen['points'][0][0],chosen['points'][-1][0]
                fraction=min(.9,max(.1,(target-xa)/(xb-xa)))
            mines.append(dict(id=f'mine.{side}.{k}',owner=side,capacity=(2 if k else 1) if region_index==5 else (2 if k else 3),cargo_bonus=k+(2 if region_index==5 and k else 0),mine_seconds=1.2+k*.12+(.4 if region_index==6 else 0),resource=-1,**placement(chosen,fraction)))
        for k in range(3 if local in [14,17,19] or region_index in [2,3,9] else 2):
            rear=.055 if region_index==2 else .075
            spread=.075 if region_index==2 else .135 if region_index in [3,9] else .11
            if region_index==8 and side==0:spread=.14
            target=start+(finish-start)*((rear+spread*k) if side==0 else (1-rear-spread*k))
            chosen=min(edges,key=lambda e:min(abs(p[0]-target) for p in e['points']))
            xa,xb=chosen['points'][0][0],chosen['points'][-1][0]
            fraction=min(.90,max(.10,(target-xa)/(xb-xa)))
            sites.append(dict(id=f'site.{side}.{k}',owner=side,types=['tower','mana'],**placement(chosen,fraction)))
    primary=next(e for e in edges if e['from']=='west')
    last=next(e for e in edges if e['to']=='east')
    objective_mark={k:mines[0][k] for k in ['edge','s','x','y']} if objective=='intercept' else placement(last,.8)
    influence={
      'destroy_base':'通过路线与设施组织推进，在对手增援更近的矿区完成突破。',
      'deliver_gold':'近矿保证底线，扩外矿缩短任务时间但暴露工人与护卫。',
      'protect':'保护前置设施存活至目标时间；短线来兵快，后方投资较安全。',
      'escort':'指定对象持续自动前进；提前选路与护卫到达比无目标堆兵更重要。',
      'intercept':'指定敌兵抵达矿线即失败；控制时间与增援路径决定截击窗口。',
      'survive':'先保证矿线与前哨，再决定反击；到时存活或提前拆城均可胜利。'}
    result=dict(id=f'map.{region_index+1:02}.{local+1:02}',name=faction['region']+'·'+label,region=faction['id'],theme={'yin':'stamp-plain','mo':'ink-marsh','deng':'lantern-ridge'}.get(faction['id'],faction['id']),
                length=round(length,3),nodes=nodes,edges=edges,bases=[dict(node='west',owner=0),dict(node='east',owner=1)],mines=mines,build_sites=sites,
                objective_anchor=objective_mark,lesson=lesson,objective_type=objective,decision=influence[objective],
                alternative='稳住近矿与后位再汇兵推进' if local%2==0 else '较早投入护卫夺回外矿/前位，承担更高暴露风险',
                regional_rule=spatial_rules[region_index],balance_focus=['增援等待','回款延迟','分路压制','设施防守'][local%4],schema_version=2)
    short=sum(min(sum(math.dist(a,b) for a,b in zip(e['points'],e['points'][1:])) for e in edges if e['from']==n['id']) for n in nodes if n['id']!='east')
    long=sum(max(sum(math.dist(a,b) for a,b in zip(e['points'],e['points'][1:])) for e in edges if e['from']==n['id']) for n in nodes if n['id']!='east')
    result['route_lengths']={'shortest':round(short,2),'longest':round(long,2)}
    result['decision']+=f' 全线最短 {short:.1f}、绕行 {long:.1f}；以移速1.0的部队计算，绕行增加约 {long-short:.1f} 秒。'+spatial_rules[region_index]
    result['geometry_sha256']=hashlib.sha256(json.dumps({k:result[k] for k in ['length','nodes','edges','mines','build_sites']},sort_keys=True).encode()).hexdigest()
    return result

def author_campaign(factions,maps):
    levels=[];chapters=[]
    for chapter_index,f in enumerate(factions):
        events=BEATS[f['id']]
        assert len(events)==20
        chapter=dict(id=f'chapter.{chapter_index+1:02}',index=chapter_index,faction=f['id'],title=f['region']+'：'+f['stake'].split('，')[0],
                     synopsis=f['premise'],ending=f['ending'],first_level=chapter_index*20,last_level=chapter_index*20+19)
        chapters.append(chapter)
        for local,event in enumerate(events):
            index=chapter_index*20+local; mapdef=maps[index]; win=mapdef['objective_type']
            enemy=FACTIONS[(chapter_index+(2 if local in [8,16,18] else 1))%10]['id']
            roster=f['combat_units'];unlock_count=40 if local==19 else min(40,8+(local//3)*5)
            enemy_faction=next(e for e in factions if e['id']==enemy)
            enemy_roster=enemy_faction['default_roster'][:2]
            # Keep two affordable openers, then expose different counters across the campaign.
            enemy_pool=enemy_faction['combat_units'][2:min(40,8+local*2)]
            offset=(local+chapter_index*3)%max(1,len(enemy_pool))
            for n in range(min(6,len(enemy_pool))):
                uid=enemy_pool[(offset+n)%len(enemy_pool)]
                if uid not in enemy_roster:enemy_roster.append(uid)
            level=dict(index=index,id=f'campaign.{f["id"]}.{local+1:02}',title=mapdef['name'],chapter=f['id'],faction=f['id'],enemy=enemy,map=mapdef['id'],
                       line=event,tip=mapdef['decision'],story_before=[{'speaker':f['hero'],'text':event},{'speaker':'战地纸签','text':mapdef['lesson']+'。'+mapdef['decision']}],
                       story_after=[{'speaker':f['hero'],'text':f['ending'] if local==19 else event+'这一页已经留下可见的证据。'}],
                       next_level=f'campaign.{f["id"]}.{local+2:02}' if local<19 else (f'campaign.{FACTIONS[chapter_index+1]["id"]}.01' if chapter_index<9 else ''),
                       available_roster=roster[:unlock_count],initial_unlocked=roster[:min(8,2+local//2)],enemy_roster=enemy_roster,enemy_unlocked=enemy_roster[:min(8,2+local//3)],
                       tier=min(5,1+local//4),difficulty=0 if local<4 else (1 if local<16 else 2),starting_gold=260+local//5*25,enemy_starting_gold=180+local//5*20,
                       ai_style=['rush','economy','counter'][local%3],ai_warmup=12 if local<4 else 5,ai_army_limit=5 if local<2 else 60,
                       win=win,duration=100+local*2 if win in ['protect','survive'] else 0,goal_gold=120+local*12 if win=='deliver_gold' else 0,
                       star_time=240+local*8,objective_anchor=mapdef['objective_anchor'],protect_slot=1,
                       story_flag=f'evidence.{f["id"]}.{local+1:02}',predecessor=levels[-1]['id'] if levels else '')
            if win=='escort':level.update(escort_id=f'unit.{f["id"]}.guard',escort_hp=650,escort_speed=.55,escort_required=True)
            if win=='intercept':level.update(intercept_id=f'unit.{enemy}.{LEGACY.get(enemy,{}).get("colossus","colossus")}',intercept_hp=420,intercept_speed=.50)
            if local in [9]:level['starting_gold']=420;level['worker_limit']=2
            level['tip']={
                'destroy_base':'摧毁敌方纸城，同时守住我方纸城。',
                'deliver_gold':f'真实归仓金币累计达到 {level["goal_gold"]}；开局金币不计入。',
                'protect':f'守住指定设施 {level["duration"]} 秒；设施毁坏立即失败，提前拆城也可胜利。',
                'survive':f'守住我方纸城 {level["duration"]} 秒，或提前摧毁敌方纸城。',
                'escort':'携证者存活并抵达回印点；其阵亡立即失败，拆城不能替代护送。',
                'intercept':'击倒指定巨像；巨像抵达我方近矿线立即失败。'}[win]
            levels.append(level)
    return levels,dict(schema_version=2,title='纸上兵戈',premise='祖印碎裂，十院相互追索王命。玩家沿十位统帅的连续行动收集证据，阻止用抹除记忆换取和平的归零印。',
                       antagonist='留白庭旧档军与自动覆写程序；不是任意一个可以被简单消灭的阵营。',
                       ending=factions[-1]['ending'],chapters=chapters,linear_route=[level['id'] for level in levels],facts=levels)

def documents(factions,maps,levels,story):
    DOC.mkdir(parents=True,exist_ok=True)
    (DOC/'README.md').write_text('# 十院留名 · 2.0 内容设计\n\n开发中：本目录对应200张地图、10阵营和每阵营40作战兵的正式数据设计。数量登记不等于运行、素材或通关验收完成；总体状态见 [实施进度](../17-规模扩展与实施进度.md)。\n\n- [核心博弈](01-核心博弈.md)\n- [十阵营设定](02-十阵营设定.md)\n- [200地图目录](03-200地图目录.md)\n- [完整故事路线](04-完整故事路线.md)\n- [单位分阵营规格](units/)\n',encoding='utf-8')
    rows=['# 十阵营设定\n','每阵营40个可招募作战兵，工人与临时召唤另计。数值与能力设计属于本作，不声称是原作规则。\n']
    for f in factions:
        rows.extend([f'## {f["name"]} / {f["region"]}\n',f'统帅：{f["hero"]}，{f["title"]}。\n',f['premise']+'\n',
                     '选择冲突：'+f['stake']+'\n',f'经济机制：{f["mana"]}；军团特性：{f["trait"]}。造型：{f["motif"]}。\n',f'本章结局：{f["ending"]}\n'])
    (DOC/'02-十阵营设定.md').write_text('\n'.join(rows),encoding='utf-8')
    catalog=['# 200张地图设计目录\n','每个ID对应独立几何、矿位、设施位、任务锚点和决策说明；不是只换主题。地图族共用路径语法，区域参数改变实际空间和行军时间。\n',
             '| 序号 | 地图 | 核心概念 | 主任务 | 长度 | 分岔/边数 | 每方矿数 | 决策 |','| --- | --- | --- | --- | --- | --- | --- | --- |']
    for i,m in enumerate(maps):catalog.append(f'| {i+1} | {m["id"]} {m["name"]} | {m["lesson"]} | {m["objective_type"]} | {m["length"]} | {len(m["edges"])} | {len(m["mines"])//2} | {m["decision"]} |')
    (DOC/'03-200地图目录.md').write_text('\n'.join(catalog)+'\n',encoding='utf-8')
    narrative=['# 完整故事与线性战役路线\n',story['premise']+'\n','总共10章、200关，单一因果顺序。每关保留前置ID、故事事实、任务类型和后续ID；战役进度不能任意跳过前置。\n']
    for chapter in story['chapters']:
        narrative.extend([f'## {chapter["title"]}\n',chapter['synopsis']+'\n'])
        for level in levels[chapter['first_level']:chapter['last_level']+1]:
            narrative.append(f'{level["index"]+1}. **{level["title"]}**（{level["win"]}）：{level["line"]}')
        narrative.append('\n本章结果：'+chapter['ending']+'\n')
    narrative.append('## 结局\n\n'+story['ending']+'\n')
    (DOC/'04-完整故事路线.md').write_text('\n'.join(narrative),encoding='utf-8')

def main():
    save_baseline()
    base=json.loads((BASE/'balance-prototype.json').read_text(encoding='utf-8'))
    original_tech=json.loads((BASE/'technology.json').read_text(encoding='utf-8'))
    original_campaign=json.loads((BASE/'campaign.json').read_text(encoding='utf-8'))
    units,tech,initial,factions=rosters(base)
    # Resolve all enemy rosters after every faction has been authored.
    for i,f in enumerate(factions):FACTIONS[i].update(combat_units=f['combat_units'])
    maps=[make_map(region,local) for region in range(10) for local in range(20)]
    levels,story=author_campaign(factions,maps)
    balance=copy.deepcopy(base);balance.update(version='2.0.0-dev',stage='world-systems-development',units=units)
    balance['simulation']['max_workers_per_side']=10
    for f in factions:
        for rank in range(1,5):
            balance['upgrades'][f'upgrade.{f["id"]}.doctrine{rank}']=dict(mana_per_second_add=0,name=['初阶兵法','合阵兵法','重装兵法','决胜兵法'][rank-1])
    for f in factions:
        fid=f['id']
        for tail in ['base','tower','mana']:
            bid=f'building.{fid}.{tail}'
            if bid not in balance['buildings']:balance['buildings'][bid]=copy.deepcopy(base['buildings'][f'building.deng.{tail}'])
            balance['buildings'][bid].update(construction_seconds=0 if tail=='base' else (5 if tail=='tower' else 4))
            if tail=='mana':balance['buildings'][bid]['mana_per_second']=1.1 if fid=='deng' else .3
            if tail!='base':initial[fid].append(bid)
        if fid not in ['yin','mo','deng']:
            source='mo' if fid in ['jin','mu'] else 'yin' if fid in ['ji','qi','shuang'] else 'deng'
            for sid,spec in base['spells'].items():
                if sid.split('.')[1]==source:
                    new=f'spell.{fid}.{sid.split(".")[2]}'
                    balance['spells'][new]=copy.deepcopy(spec)
                    initial[fid].append(new)
                    tech.append(dict(id=f'tech.{fid}.spell-{sid.split(".")[2]}',faction=fid,grant=new,gold=65,seconds=4,requires=[]))
        else:
            initial[fid]+=[sid for sid in base['spells'] if sid.split('.')[1]==fid]
    # Keep original non-unit tech IDs valid. Unit grants are covered by the expanded tree.
    tech_ids={n['id'] for n in tech}
    for node in original_tech['nodes']:
        if node['id'] not in tech_ids: tech.append(copy.deepcopy(node))
    dump(DATA/'balance-prototype.json',balance)
    dump(DATA/'factions.json',dict(schema_version=2,order=[f['id'] for f in factions],factions=factions))
    dump(DATA/'maps.json',dict(schema_version=2,maps=maps,aliases={'stamp-plain':maps[0]['id'],'ink-marsh':maps[23]['id'],'lantern-ridge':maps[54]['id']}))
    dump(DATA/'technology.json',dict(schema_version=2,starting_unlocked=initial,nodes=tech))
    dump(DATA/'campaign.json',dict(schema_version=2,levels=levels,challenges=original_campaign['challenges']))
    dump(DATA/'story.json',story)
    documents(factions,maps,levels,story)
    unit_dir=DOC/'units';unit_dir.mkdir(exist_ok=True)
    for f in factions:
        rows=[f'# {f["name"]} · 40种作战单位\n','工人和临时召唤不计入40种。每个定义含费用、前摇、射程、移速、职责与能力；素材生产和对局验证仍在进行。\n',
              '| ID | 名称 | 角色 | 金 | HP | 伤害/间隔 | 射程/速度 | 能力字段 | 职责与反制 |','| --- | --- | --- | --- | --- | --- | --- | --- | --- |']
        for uid in f['combat_units']:
            u=units[uid];mechanical={k:v for k,v in u.items() if k not in ['gold','hp','damage','attack_interval','windup','range','speed','name','faction','role','tier','manual_recruit','hint','art_status','art_source','attack']}
            rows.append(f'| {uid} | {u["name"]} | {u["role"]} | {u["gold"]} | {u["hp"]} | {u["damage"]}/{u["attack_interval"]} | {u["range"]}/{u["speed"]} | {json.dumps(mechanical,ensure_ascii=False)} | {u["hint"]} |')
        (unit_dir/f'{f["id"]}.md').write_text('\n'.join(rows)+'\n',encoding='utf-8')
    print(json.dumps({'maps':len(maps),'unique_geometries':len({m['geometry_sha256'] for m in maps}),'factions':len(factions),'combat_units':[len(f['combat_units']) for f in factions],'campaign':len(levels),'status':'development definitions, not final playable acceptance'},ensure_ascii=False))

if __name__=='__main__':main()
