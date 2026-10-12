"""Current system specifications and one complete spatial brief for each of 200 maps."""
from pathlib import Path
import json,math,heapq
ROOT=Path(__file__).resolve().parents[2]
DOC=ROOT/'docs/paper-warfront';WORLD=DOC/'world'
def read(name):return json.loads((ROOT/'game/data'/name).read_text(encoding='utf-8'))
def write(path,text):path.parent.mkdir(parents=True,exist_ok=True);path.write_text(text+'\n',encoding='utf-8')
def lengths(m):return {e['id']:sum(math.dist(a,b) for a,b in zip(e['points'],e['points'][1:])) for e in m['edges']}
def distances(m,node):
    cost=lengths(m);adj={n['id']:[] for n in m['nodes']}
    for e in m['edges']:
        adj[e['from']].append((e['to'],cost[e['id']]));adj[e['to']].append((e['from'],cost[e['id']]))
    found={node:0};queue=[(0,node)]
    while queue:
        d,n=heapq.heappop(queue)
        if d>found[n]:continue
        for b,c in adj[n]:
            if d+c<found.get(b,float('inf')):found[b]=d+c;heapq.heappush(queue,(d+c,b))
    return found
def main():
    world=read('factions.json');balance=read('balance-prototype.json');maps=read('maps.json')['maps'];campaign=read('campaign.json')['levels']
    lookup={f['id']:f for f in world['factions']}
    for m,level in zip(maps,campaign):
        cost=lengths(m);edges={e['id']:e for e in m['edges']};from_nodes={e['from'] for e in m['edges']}
        rows=[f'# {int(level["index"])+1:03} · {m["name"]}',f'\n地图ID `{m["id"]}`；战役ID `{level["id"]}`。数据来源：game/data/maps.json 与 campaign.json。\n',
              '## 任务与故事',f'\n我方：{lookup[level["faction"]]["name"]}；敌方：{lookup[level["enemy"]]["name"]}。起始金币 {level["starting_gold"]} : {level["enemy_starting_gold"]}，工人上限 {level.get("worker_limit",10)}。',
              f'\n任务：{level["tip"]}',f'\n推进事件：{level["line"]}',f'\n前置关：`{level["predecessor"] or "故事开端"}`；下一关：`{level["next_level"] or "十院留名终章"}`。',
              '\n## 空间判断',f'\n{m["decision"]}',f'\n另一种投入：{m["alternative"]}。应重点观察：{m["balance_focus"]}。',
              f'\n全线最短 {m["route_lengths"]["shortest"]:.2f}，最长 {m["route_lengths"]["longest"]:.2f} 世界距离。世界X/Y参与移动与射程，地表高度不附加伤害加成。',
              '\n## 路段与汇流', '\n| 路段 | 起点→终点 | 实际长度 | 分路性质 |', '| --- | --- | ---: | --- |']
        for e in m['edges']:rows.append(f'| {e["id"]} | {e["from"]}→{e["to"]} | {cost[e["id"]]:.2f} | {e["route_role"]} |')
        rows+=['\n分岔路标在军队进入下一路段时读取；入路的旧兵不会响应后来改路。近战不能只凭X接近穿路攻击，远程读取二维距离。节点前后批次的抵达顺序可以改变汇流处的交换。',
               '\n## 经济与归仓', '\n| 矿点 | 所属 | 世界位置 | 同采容量 | 单程距离 | 载荷 | 无排队估计回款周期 |', '| --- | --- | --- | ---: | ---: | ---: | ---: |']
        for mine in m['mines']:
            side=mine['owner'];edge=edges[mine['edge']];dist=distances(m,'west' if side==0 else 'east')
            d=min(dist[edge['from']]+mine['s'],dist[edge['to']]+cost[edge['id']]-mine['s'])
            f=lookup[level['faction'] if side==0 else level['enemy']];worker=balance['units'][f['worker']]
            cargo=worker.get('cargo',8)+mine['cargo_bonus'];cycle=2*d/worker['speed']+mine['mine_seconds']+1
            rows.append(f'| {mine["id"]} | {"我方" if side==0 else "敌方"} | ({mine["x"]:.2f}, {mine["y"]:.2f}) | {mine["capacity"]} | {d:.2f} | {cargo} | {cycle:.2f} 秒 |')
        rows+=['\n估计周期仅用于比较空间投资，包含采矿和1秒归仓处理，不包含排队、控制、护矿战斗或阵营护运光环。实际金币必须真实运回。点击优先矿点不取消在途运输。',
               '\n## 施工与防守位置', '\n| 施工位 | 所属 | 路段/锚点 | 世界位置 |', '| --- | --- | --- | --- |']
        for site in m['build_sites']:rows.append(f'| {site["id"]} | {"我方" if site["owner"]==0 else "敌方"} | {site["edge"]} / {site["s"]:.2f} | ({site["x"]:.2f}, {site["y"]:.2f}) |')
        rows+=['\n施工位可选哨塔或纸灯；同一位置只能占用一座存活建筑。哨塔5秒、纸灯4秒，未完工不提供火力和持续回法。远程跨路射程可能让看似后位的设施仍受到威胁。',
               '\n## 本关验收', '\n检查两侧矿路可达并真实回款、所有路标出口可走、所选路线箭头与实际后续来兵一致、施工位合法性与施工期收益、任务对象及失败线位置、任务胜败和下一关保存。自动玩家胜败记录用于找问题，不代替人类战术判断。',
               f'\n几何散列：`{m["geometry_sha256"]}`。背景图不会参与上述散列或改写碰撞与路径。']
        write(WORLD/'maps'/f'{m["id"]}.md','\n'.join(rows))
    write(DOC/'18-路径与经济执行规范.md', '''# 路径与经济执行规范 · 2.0

权威实现是 map_runtime.gd、battle_sim.gd。每个节点保存位置，路段保存折线、累积长度、实际长度、正反相邻边；所有部队保存 edge/s/x/y。移动、工人往返、近战距离、远程距离、范围法术和小地图都读取同一数据。

路标为每侧独立的节点选择。修改发生在公共command接口中，只有到节点的新批次读取；旧批次在边上承诺其实际移动。原作的PC路标权限未直接测量，这一权限是本作公开规则。路段高度参与路径与位置，不提供未经验证的高地加成。

工人默认上限10，特殊预算关可降低。每方两名开局工人，矿点容量限定同采人数，按稳定UID排队。工人持有mine、job、cargo、job_time，采金、载货返回、归仓是不同状态；矿路使用真实图最短路径。有限资源会减少资源库存，当前地图以无限矿为主。矿优先级会与运输长度、分配人数和容量一起决定下次矿位。控制与减速会影响在途工人，单体军团法术不接受工人。

近战读取同路段或共享节点间的步行距离；远程读取二维欧氏距离。范围伤害覆盖世界圆，在画面上因X/Y缩放差异显示为椭圆。预览与实际施放使用同一落点，点到单位时定位其世界脚点。地图长度影响相机钳制和小地图，不使用固定56长度。

见 world/maps/ 下200份空间简报：真实长度、矿点回款周期估计、路线承诺、施工位、任务与验收条件。几何可达性和工人归仓测试覆盖全部地图，仍须完整对局与画面验证。''')
    write(DOC/'19-战前编组与科技规范.md', '''# 战前编组与科技规范 · 2.0

十院各40个可招募作战单位，工人与临时召唤另外登记。角色向量涵盖前排、抗突进、护运、蓄力破阵、单挑、跃击、越阵、重盾、重击、减速、光环、治疗、施工修复、反弹、禁言、持续伤害、长射程、连射、攻城、弹射、斩杀、吸血、赏金、反施工、召唤、遗纸复兵、复制、封禁、定身、残血奋战、巨像、护矿加货、回法和死亡爆发。

兵书桌面每页12条、触屏每页8条，选择阵营后可读完整40兵、工人、5法术。部署桌面每页20个、触屏每页10个，从当前战役开放库或遭遇战完整库选择4–8个；编组存档不等于本局科技已研究。非完整科技开局自动保留基础作战兵，避免没有合法出兵项。局内工人与编组共有9个招募项，桌面一次显示，移动端分两组并可切换法术。

金币共享且招募串行生产2.4秒/个，上限6队列、60军团；取消按当前队列位置及单位ID验证，位置改变则拒绝，避免退错单位。移动端有独立队列面板。科技1项同时进行，公共兵法4阶开放高阶兵研究，只有本局编组单位能研究或招募。科技桌面每页8项、触屏每页4项，明确金币、研究秒数和前置；状态是未解锁、等待前置、研究中、已完成。

法术有费用、冷却、友敌限制、单位类别限制、场地边界和召唤上限。任务对象的唯一证据禁止献弃、夺印与复印。克隆、临时守卫与遗纸召回有数量/寿命约束；克隆不产生遗纸，不可无限互相复制。''')
    write(DOC/'20-战役与任务执行规范.md', '''# 战役与任务执行规范 · 2.0

十章各20关，共200个前后相接的事件。顺序是朱印疆伪令→旧册泽提前死亡名单→青灯都复制王命→铜折炉被更改生产次序→雁信岭封锁消息→契金埠虚假货运账→活纤林记忆侵蚀→冻页台被冻结的和平协定→余烬渡幸存者被注销→留白庭归零印。最终十位统帅拆除覆写结构，共同建立不能替代私人记忆的留名印。

每关记录索引、稳定ID、前置与下一关、双方阵营、实际地图、军库开放、初始科技、敌方部署、初始金币、AI倾向、任务参数、战前对话、战后对话和证据标记。敌方编组保留两项开局兵，并随着章节内推进引入不同的反制角色。完整事件、角色转折与结局见 world/04-完整故事路线.md 与 story.json。

六类主任务为拆城、真实归仓、限时守城、保护指定前哨、护送携证者、矿线前截巨。保护和生存可提前拆城取胜；护送必须携证者走到交接点；截巨的失败线是实际近矿锚点。原作成就不是一概等于主任务，本作任务是基于对标研究的原创展开。

胜利按基地保全和时间发1–3星，更新线性解锁、星章和故事证据后原子替换profile.json；败局不开放下一关。第200关接入明确终章并汇总十位角色归宿。旧版15关进度保存在legacy_campaign中，新200关从故事开端开始，设置和挑战记录保留。QA会备份并恢复当前档案。

对局AI与玩家同一命令、费用、施工、生产和射程规则。AI读取公开部队与地图信息、自己的钱与队列，不读取敌方钱包和队列；考虑矿线风险、节点选路、施工安全、兵种比例、反制目标、关键对象与二维施法聚集。决策节奏分入门/标准/强敌。自动战役测试使用同一60Hz模拟，胜率用于难度检查，不冒充人类可玩验收。''')
    write(DOC/'21-十院素材与动画规范.md', '''# 十院素材与动画规范 · 2.0

统一使用用户指定sub2-image-gen技能和gpt-image-2.5，由技能脚本管理网关配置，项目不复制密钥。400作战兵按每张8个、4列2行生产50张源图；十院统帅、工人、基地、塔、纸灯与环境道具生产独立辅助图，新增区域背景独立生成。每院武器轮廓和纸材纹样服务职责识别，拒绝把同一图换色计作新角色。

源图必须含可信原生alpha。第一张不符合透明规范的旧输出单独留在rejected，不能进入运行素材。生成网格位置可能漂移，因此以全图连通轮廓提取人物，验证八个轮廓不重复、未触碰画布边缘，不能按猜测格子截断长矛和武器。切图规整到512×512、脚底基线476，人物向右，归一化保留完整武器、两足和车轮。运行版人物使用独立body、leg-back、leg-front；车使用body和两个wheel，建立关节重叠与明确枢轴。腿部切线与水平落脚锚点从底部实际alpha分布确定，不依赖画布中线；旗帜和长武器会使全身包围盒偏心。行走、攻击与死亡读取同一实际落脚锚点。

战斗表现分待机、行走、前摇、攻击、受击、束缚、死亡与临时召唤。腿部交替摆动、身体纸片倾斜与炮轮旋转，受击短暂停顿、纸屑、伤害数字、重击震屏、被打断标记、炮口与投射物、复制体着色、阵营与归属脚线、状态图形都由渲染层读取模拟事件；不会用特效改写伤害或单位世界位置。

法术与攻击反馈使用真实X/Y锚点，支路上死亡和命中不掉到另一条纸路。施工显示进度条，完工发纸屑与独立声音；设施封禁显示标记和下行状态音。减弱动态设置减少震动，音乐/声效可独立调节。纸灯辉光和背景装饰不能伪装成可点击路标或矿位。

资产清单是game/data/assets.json，来源与模型记录在world-art-provenance.json，源图和提示词在output/imagegen/paper-warfront/world-v2与world-support，审图板对应各院40兵。技术切图检查、源图人眼检查、运行截图与动作检查是不同验收项，不能由PNG存在替代。400兵库按需加载并限制纹理缓存，避免在单局预装完整世界。''')
    write(DOC/'16-玩家手册.md', '''# 纸上兵戈：十院留名 · 玩家手册

Windows双击PaperWarfront.exe；Android安装已签名APK，首次安装需允许当前文件来源。游戏离线单人，不要求网络账户。

开始战役后在简报阅读任务与地图预览，可先调整4–8兵部署。部队自动进军，你负责投资和时机。招募扣金币，2.4秒生产一个；金币必须由工人运回，点击矿点设置下次出发优先。点击我方路标切换后续部队的路径，已进路的兵不会即时换路。地图上的箭头显示当前所选方向。

科技解锁部署里的兵种与兵法阶位，研究需要付费等待；施工只能点地图给定建筑位，保护4/5秒施工期，完工才有回法或火力。金币花在经济、科技、施工与当前兵力之间会产生机会成本。

桌面1–9招募、Q/W/E/R/T选择法术、F科技、B建造、P暂停；选法术后点友军、敌军或合法纸面。右键或Esc取消选择；A/D与方向键移动视野，Home回纸城，Space跟随交锋。拖动战场或点击下方真实小地图也可导航。队列图标可取消并退款。

移动端按HUD的下一组切换招募前后组与法术，队列按钮提供完整取消面板；拖动战场、点小地图、点纸城/交锋按钮导航，Android返回键关闭当前面板或打开暂停。暂停中可查操作，设置支持独立音乐/声效和减弱动态。

任务不限拆城：归仓关只统计真实运回的金币；守城和保护关需到指定时间；护送关必须携证者存活并抵达交接点；截巨关需在近矿失败线之前阻止巨兵。任务对象不能献弃、夺印或复印。胜利自动保存星章、证据和下一关。十章二百关后有明确终章；遭遇战可自选十阵营和任意一张地图。

纸路高差影响实际距离和位置，近战不能隔支路砍人，远程在实际射程内可以跨路支援。兵书可读取每院40兵的职责与能力。优先保护运输线、远程与辅助，再决定把法力花在当前交换还是保留给关键对象。

旧1.0的15关记录单独保留，新战役从开端开始；进度与设置仍保存在user://profile.json。''')
    print('Wrote 200 spatial briefs and current runtime/UI/art/story specifications.')
if __name__=='__main__':main()
