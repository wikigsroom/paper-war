"""Current design documents from authored game data; preserve research and 2.0 history."""
from pathlib import Path
from collections import Counter
import json, sys, hashlib, zipfile, html, argparse
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[2]
DOC=ROOT/'docs/paper-warfront'
NEW=DOC/'redesign-3.0'
VERSION='3.0.0-rc1'

def read(p):return json.loads((ROOT/p).read_text(encoding='utf-8'))
def write(p,text):
    p=ROOT/p if isinstance(p,str) else p
    p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text.rstrip()+'\n',encoding='utf-8')
def table(headers,rows):
    def cell(x):return str(x).replace('|','／').replace('\n','；')
    return '\n'.join(['| '+' | '.join(headers)+' |','| '+' | '.join(['---']*len(headers))+' |']+['| '+' | '.join(map(cell,row))+' |' for row in rows])+'\n'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def archive_previous():
    target=ROOT/'docs/archive/paper-warfront-2.0-before-map-rework.zip'
    if target.exists():return
    files=[p for p in DOC.rglob('*') if p.is_file() and 'redesign-3.0' not in p.parts]
    files += [ROOT/p for p in ['README.md','docs/README.md','game/README.md','release/README.md','assets/paper-warfront/README.md'] if (ROOT/p).exists()]
    target.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as z:
        for p in files:z.write(p,p.relative_to(ROOT).as_posix())
    with zipfile.ZipFile(target) as z:assert z.testzip() is None

def ground_y(m,x):
    ground=set(m['presentation']['ground_edges'])
    for edge in m['edges']:
        if edge['id'] not in ground:continue
        for a,b in zip(edge['points'],edge['points'][1:]):
            if min(a[0],b[0])<=x<=max(a[0],b[0]):return a[1]+(b[1]-a[1])*(x-a[0])/max(.0001,b[0]-a[0])
    return 0

def task_markers(m,c):
    markers=[]
    def add(x,y,label,kind):markers.append(dict(x=x,y=y,label=label,kind=kind))
    if c['win']=='intercept':
        a=c['objective_anchor'];add(a['x'],a['y'],'矿线','goal')
        x=c.get('intercept_start_x',m['length']-8);add(x,ground_y(m,x),'来袭','enemy')
    if c['win']=='escort':
        a=c['objective_anchor'];add(a['x'],a['y'],'交接','goal')
        x=c.get('escort_start_x',6);add(x,ground_y(m,x),'携证者','ally')
        for e in c.get('enemy_entries',[]):add(e['x'],e['y'],str(e['unlock_time'])+'s','enemy')
    return markers

def map_svg(m,c,w=920,h=164):
    ys=[float(p[1]) for e in m['edges'] for p in e['points']]
    low=min(ys+[-.5]);high=max(ys+[.5]);scale=min(17,(h-60)/(high-low))
    def point(x,y):return 22+float(x)/m['length']*(w-44),22+(float(y)-low)*scale
    shapes=[f'<rect width="{w}" height="{h}" rx="10" fill="#e8deca"/>']
    for e in m['edges']:
        pts=' '.join(f'{x:.2f},{y:.2f}' for x,y in [point(*p) for p in e['points']])
        shapes.append(f'<polyline points="{pts}" fill="none" stroke="{"#3c8196" if e.get("route_role")=="bridge" else "#8e7859"}" stroke-width="5"/>')
    for mine in m['mines']:
        x,y=point(mine['x'],mine['y']);shapes.append(f'<circle cx="{x}" cy="{y}" r="7" fill="#ad8a32"/><text x="{x}" y="{y+24}" text-anchor="middle" font-size="13">{mine["capacity"]}工</text>')
    for s in m['build_sites']:
        x,y=point(s['x'],s['y']);name='灯' if s['types']==['mana'] else '塔'
        shapes.append(f'<rect x="{x-5}" y="{y-5}" width="10" height="10" fill="#397e9e"/><text x="{x}" y="{y-12}" text-anchor="middle" font-size="13">{name}</text>')
    for b in m['bases']:
        n=next(n for n in m['nodes'] if n['id']==b['node']);x,y=point(*n['position']);shapes.append(f'<circle cx="{x}" cy="{y}" r="5" fill="{"#397e9e" if b["owner"]==0 else "#b74532"}"/>')
    for marker in task_markers(m,c):
        x,y=point(marker['x'],marker['y']);color={'goal':'#7469b1','enemy':'#b74532','ally':'#397e9e'}[marker['kind']]
        shapes.append(f'<line x1="{x}" y1="{y-26}" x2="{x}" y2="{y+8}" stroke="{color}" stroke-width="2"/><text x="{x}" y="{y-30}" text-anchor="middle" font-size="13" fill="{color}">{marker["label"]}</text>')
    shapes.append(f'<text x="22" y="{h-10}" font-size="13" fill="#746d61">金点＝矿位及同时开采容量　方块＝指定设施位　横向长度 {m["length"]}　坡面不附加伤害倍率</text>')
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" role="img" aria-label="{html.escape(m["name"])}">'+''.join(shapes)+'</svg>'

def draw_actual_map_overview(maps,levels):
    font=lambda s:ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',s)
    canvas=Image.new('RGB',(1800,1500),'#f4eddd');d=ImageDraw.Draw(canvas)
    d.text((44,28),'六张基准地图 · 当前游戏实际坐标',font=font(40),fill='#343332')
    d.text((44,86),'长度、矿位、设施与任务锚点来自 game/data；这是空间示意，原生战斗另见截图与录像。',font=font(23),fill='#746d61')
    for i,m in enumerate(maps):
        x=40+i%2*880;y=150+i//2*445
        d.rounded_rectangle((x,y,x+842,y+410),radius=12,fill='#e8deca',outline='#baaa8a',width=2)
        card=m['design_card'];d.text((x+22,y+15),card['id']+' '+m['name'],font=font(27),fill='#b74532')
        d.text((x+22,y+65),card['question'],font=font(24),fill='#343332')
        ys=[float(p[1]) for e in m['edges'] for p in e['points']];low=min(ys+[-.5]);high=max(ys+[.5]);scale=min(24,130/(high-low))
        def point(a,b):return x+28+float(a)/m['length']*782,y+130+(float(b)-low)*scale
        for e in m['edges']:
            pts=[point(*p) for p in e['points']];d.line(pts,fill='#397e9e' if e.get('route_role')=='bridge' else '#8e7859',width=6)
        for mine in m['mines']:
            a,b=point(mine['x'],mine['y']);d.ellipse((a-7,b-7,a+7,b+7),fill='#ad8a32');d.text((a-16,b+13),str(mine['capacity'])+'工',font=font(17),fill='#343332')
        for s in m['build_sites']:
            a,b=point(s['x'],s['y']);d.rectangle((a-5,b-5,a+5,b+5),fill='#397e9e')
            d.text((a-8,b-28),'灯' if s['types']==['mana'] else '塔',font=font(17),fill='#397e9e')
        for base in m['bases']:
            n=next(n for n in m['nodes'] if n['id']==base['node']);a,b=point(*n['position']);d.ellipse((a-5,b-5,a+5,b+5),fill='#397e9e' if base['owner']==0 else '#b74532')
        for marker in task_markers(m,levels[m['id']]):
            a,b=point(marker['x'],marker['y']);color={'goal':'#7469b1','enemy':'#b74532','ally':'#397e9e'}[marker['kind']]
            d.line((a,b-32,a,b+8),fill=color,width=3);d.text((a,b-59),marker['label'],anchor='mt',font=font(17),fill=color)
        c=levels[m['id']]
        if c['win']=='intercept':d.text((x+22,y+252),f'矿线x{c["objective_anchor"]["x"]} ／ 来袭x{c["intercept_start_x"]}；越线前截击',font=font(18),fill='#7469b1')
        if c['win']=='escort':
            entries='、'.join(f'{e["x"]}@{e["unlock_time"]}s' for e in c.get('enemy_entries',[]))
            d.text((x+22,y+252),f'交接x{c["objective_anchor"]["x"]} ／ 付费入口{entries}',font=font(18),fill='#7469b1')
        for j,plan in enumerate(card['plans']):d.text((x+22,y+290+j*34),str(j+1)+' · '+plan,font=font(19),fill='#343332')
        d.text((x+22,y+374),f'全线长度 {m["length"]} ｜ 走路 {m["route_lengths"]["shortest"]:.1f}–{m["route_lengths"]["longest"]:.1f} ｜ {m["id"]}',font=font(18),fill='#746d61')
    target=NEW/'figures/actual-six-maps.png';target.parent.mkdir(parents=True,exist_ok=True);canvas.save(target)

def main():
    sys.stdout.reconfigure(encoding='utf-8');args=argparse.ArgumentParser();args.add_argument('--refresh',action='store_true');opt=args.parse_args()
    if not opt.refresh:archive_previous()
    maps=read('game/data/maps.json')['maps'];lookup={m['id']:m for m in maps}
    camp=read('game/data/campaign.json')['levels'];levels={c['map']:c for c in camp}
    factions=read('game/data/factions.json')['factions'];fs={f['id']:f for f in factions}
    balance=read('game/data/balance-prototype.json');asset=read('game/data/assets.json')['assets']
    provenance=read('game/data/theatre-art-provenance.json')['records'];pv={a['id']:a for a in provenance}
    plan=read('docs/paper-warfront/redesign-3.0/campaign-map-plan.json')
    selected=[lookup[x] for x in read('game/data/theatre-baseline-maps.json')['maps']]
    draw_actual_map_overview(selected,levels)
    qa=ROOT/'output/qa/godot'
    baseline=[
      ('W01','归金坡','map.01.01','经济与招募的共同预算；保矿与救援时机'),
      ('W02','前哨外矿','map.01.07','近矿排队与外矿的增工收益；运输受保护成本'),
      ('W03','灯台长坡','map.01.11','兵速与距离拉开援军到达时间；灯、塔占用经济预算'),
      ('W04','纸桥岔口','map.01.04','正面阵地与更长桥路的实际二维距离；到分岔才提交路标选择'),
      ('W05','矿线阻击','map.01.12','来袭对象、真实矿线和控制预算；越线后击杀仍失败'),
      ('W06','守签接力','map.01.06','护送对象、塔位及付费敌军入口；必须活着交接')]
    common='当前为 **3.0.0-rc1 地图重做评审版**。自动规则与原生代表画面已有证据；原作 HD 未在本机运行，200 关人工平衡和 Android 真机尚未验收。参数以 `game/data` 为准。'
    research='[二次地图研究](../../research/swords-and-soldiers-map/recheck-20261008/README.md)'
    write(NEW/'README.md',f'''# 地图重做 · 3.0 评审入口

地图从“不同坐标的路径”改为“位置影响投资、抵达、保护和反制”的关卡。先验证六张有明确取舍的基准图，再把其空间语法用于其余194关。单局2–4个战斗兵种加1个工人，合计3–5项生产选择。

{common}

[研究依据](../../research/swords-and-soldiers-map/recheck-20261008/README.md) · [六张实际地图](01-六张基准地图.md) · [200关空间规划](02-战役空间目录.md) · [验证证据](03-实现与验证边界.md) · [素材与原生画面](../../../assets/paper-warfront/theatre-v3-gallery.html) · [Windows／APK](../../../release/{VERSION}/README.md)

![六张当前地图](figures/actual-six-maps.png)

地图数量不是质量证明。当前200个场景记录有193种实际几何，140单线、60单处分岔；7组几何复用有明确记录。20种阶段简报配10种地域配置，是批量设计框架，并不等于200张均已逐关人工评审。

研究目录保留重做前的审计和失败证据；其中“白盒尚未接入”是当时的结论。重做后的事实以本目录及绑定散列的验证报告为准。''')
    cards=['# 六张基准地图 · 已接入游戏\n\n主菜单选择“地图试演 · 六张基准”即可直接进入战前简报。试演使用当前关卡规则和预算，以遭遇战运行，不推进故事存档。战役相应关卡沿线解锁。\n']
    for code,title,mid,mechanic in baseline:
        m=lookup[mid];c=levels[mid];d=m['design_card']
        cards.append(f'## {code}《{title}》\n\n{d["question"]}\n\n{mechanic}。\n\n'+table(['参数','当前值'],[['地图／关卡',mid+' ／ '+c['id']],['长度／最短–最长步程',f'{m["length"]} ／ {m["route_lengths"]["shortest"]:.3f}–{m["route_lengths"]["longest"]:.3f}'],['开局金币（我／敌）',str(c['starting_gold'])+' ／ '+str(c['enemy_starting_gold'])],['生产类型数',len(c['default_roster'])+1],['兵种',[balance['units'][x]['name'] for x in c['default_roster']]],['目标',c['win']],['两种打法',' ／ '.join(d['plans'])],['代价',d['tradeoff']],['敌方反制',d['enemy_response']],['开局30秒意图',d['first_30_seconds']]]))
        cards.append('\n'+table(['矿点','阵营','位置 x/y','同时开采','服务秒／趟货物','总矿量'],[[n['label'],n['owner'],f'{n["x"]:.2f} / {n["y"]:.2f}',n['capacity'],f'{n["mine_seconds"]} / 8',n['resource']] for n in m['mines']]))
        cards.append('\n'+table(['设施位','阵营','位置 x/y','允许设施'],[[s['label'],s['owner'],f'{s["x"]:.2f} / {s["y"]:.2f}',' ／ '.join(s['types'])] for s in m['build_sites']]))
        if c.get('opening_forces'):cards.append('\n预置阵地从该方开局金币按普通兵价扣款：`'+json.dumps(c['opening_forces'],ensure_ascii=False)+'`。\n')
        if c.get('enemy_entries'):cards.append('\n敌军入口以正常生产队列付费，解锁入口不是免费刷兵：`'+json.dumps(c['enemy_entries'],ensure_ascii=False)+'`。\n')
        cards.append(f'\n[全图配置简报](../world/maps/{mid}.md) · [原生决策区域画面](../../../output/qa/godot/v3-ui-final-desktop/{mid}-decision.png)\n')
    cards.append('## 已测量的空间效果\n\n外矿基准图双侧各2／3／4／6工人，180秒真实回款分别256／344／408／536金；两侧相同。近矿容量1、外矿容量2，工人到达顺序决定服务，排队不会凭空产金。增加工人的结果含行走、采矿和归仓，不是矿点光环。\n\n长坡图同一援军目标点，折斧兵13.800秒，卷轴炮车28.117秒；双侧镜像一致。纸桥空路汇流22.383秒对23.867秒，绕行约多1.48秒；主路近战守卫在场时，直走折斧兵死亡，绕桥者到达汇流点仍160生命；把守卫改到桥路，结果互换。实际4.2射程仍能击中进入二维范围的桥上目标，桥路没有隐藏无敌。\n\n这些是受控合法命令测量。首次接敌、矿工骚扰、人工两策略胜率等未全部完成，不把列出的测量目标等同于全部通过。[40项决策检查](../../../output/qa/godot/v3-map-decisions.json) · [外矿实测](../../../output/qa/godot/v3-theatre-economy.json)。\n')
    economy=read('output/qa/godot/v3-theatre-economy.json')
    if economy.get('paid_investments'):
        cards.append('## 正常招募的增工回本\n\nW02另以双侧230金、正常两名开局工人开始，经公共命令付费招工、完成真实生产后跑180秒。没有交战、塔或研究；每秒比较现金与不增工对照。首次追平可能暂时跌回对照以下，因此同时列出本测量窗口最后一次短缺之后的时间。\n\n'+table(['额外工人','支出','首次追平秒','至180秒未再短缺的起点','180秒净优势'],[[r['extra_workers'],r['expense_each_side'],r['first_break_even_second'],r['no_further_shortfall_in_180s_after_second'],r['net_advantage_at_180s']] for r in economy['paid_investments']])+'\n增工的后续现金优势要约一分半才建立；其间金币和生产队列无法同时购买相同护卫，外矿运输还承受前沿攻击。这个实测支持投资窗口的设计，未包含骚扰和护卫费用，不代表实战保证利润。\n')
    write(NEW/'01-六张基准地图.md','\n'.join(cards))
    duplicate=Counter(m['geometry_sha256'] for m in maps)
    geometry_groups=[[m['id'] for m in maps if m['geometry_sha256']==s] for s,count in duplicate.items() if count>1]
    write(NEW/'02-战役空间目录.md','# 200关空间规划\n\n'+common+'\n\n20种阶段题型与十个地域的长度、矿距、塔位及桥高共同构成关卡。六张基准图保留独立手工规格；194张按显式阶段简报重写。原故事ID、十章顺序和200关前后因果链保留。\n\n'+table(['阶段','空间题型','问题','两种投入'],[[s['stage'],s['name'],s['question'],' ／ '.join(s['plans'])] for s in plan['stages']])+'\n'+table(['地图','地域','问题','单／分路','任务','生产类型'],[[f'[{m["id"]}](../world/maps/{m["id"]}.md)',fs[m['region']]['name'],m['design_card']['question'],m['presentation']['forks'],levels[m['id']]['win'],len(levels[m['id']]['default_roster'])+1] for m in maps])+f'\n几何复用组：`{json.dumps(geometry_groups,ensure_ascii=False)}`。复用对应地域不同阵营能力，仍需人工验证是否产生不同策略；不能以地域换色自动判为新设计。\n\n有限外矿共20座，矿量320；近矿保持无限。无限矿602座已测持续往返。有桥矿的图必须兼顾经济路径与交战射程；并非每张分路都靠更高产量成立。\n')
    for m in maps:
        c=levels[m['id']];d=m['design_card']
        content=f'# {m["name"]} · {VERSION}\n\n{d["question"]}\n\n'+table(['项目','设计'],[['地图ID',m['id']],['场景任务',c['win']],['两种选择',' ／ '.join(d['plans'])],['代价',d['tradeoff']],['地域依据',m['regional_rule']],['总长',m['length']],['真实步程',m['route_lengths']],['生产编组',[balance['units'][u]['name'] for u in c['default_roster']]],['双侧开局金',[c['starting_gold'],c['enemy_starting_gold']]],['目标锚点',c['objective_anchor']],['几何SHA256',m['geometry_sha256']]])+'\n'+table(['路径','连接','坐标'],[[e['id'],e['from']+' → '+e['to'],e['points']] for e in m['edges']])+'\n'+table(['矿点','阵营','x/y','容量','采矿秒','矿量'],[[n['label'],n['owner'],[n['x'],n['y']],n['capacity'],n['mine_seconds'],n['resource']] for n in m['mines']])+'\n'+table(['设施位','阵营','x/y','允许'],[[s['label'],s['owner'],[s['x'],s['y']],s['types']] for s in m['build_sites']])+f'\n关前：{c["line"]}\n\n战术提示：{c["map_brief"]}\n\n自动图与运输验证覆盖此图；逐关人工体验仍待评审。图形／行为设计使用本作参数，不是原作数值复刻。[空间规划入口](../../redesign-3.0/02-战役空间目录.md)。'
        write(DOC/'world/maps'/(m['id']+'.md'),content)
    topics={
      '01-项目章程与硬约束.md':('项目章程与硬约束','以横向军团自动推进为骨架，玩家操作招募、研究、设施投资、矿点优先、后续部队选路与手动施法。地图位置必须改变到达时间、保护压力或任务窗口。\n\nGodot4.7.2原生GDScript与Control；战斗60Hz；2D分层纸偶、厚纸边与粒子，无外部三维建模需求。Windows原生EXE、Android离线APK，禁止Docker／WSL／虚拟环境／模拟器。生成位图使用指定sub2-image-gen与gpt-image-2.5。\n\n3–5个生产类型含工人；战斗编组2–4兵种。400兵种是全局军库规模，不能全部塞进同一局。关卡数量与散列不能作为设计验收；六张基准图须具备可比较的取舍。'),
      '02-玩法与十阵营规则.md':('玩法与十阵营规则','金币在工人实际归仓时入账。容量指同时服务工人数，队列按实际到达排序。士兵自动推进与搜索二维射程目标；投射物有飞行、延迟技能有预警。\n\n招募、研究、设施共享金币；法术消耗法力与冷却。基地产法每秒0.5，完成产法建筑／科技及阵营事件提供实际增益。建筑施工期间不产法、不攻击。每局仅研究选中兵种及阵营法术／升级；基础选中前两兵种可用，其他选择仍要科技。\n\n阵营规则依据见下表。全局能力并不保证每局只有一种最优开局；平衡需实战。'),
      '03-美术风格圣经.md':('美术风格圣经','主视觉为暖纸色、墨线与剪纸厚片；角色大头短肢、武器剪影鲜明，纸纤维留在大色块中，细碎纹理不占据读敌所需空间。十院主色沿用阵营定义，拥有方还由蓝／红标识和前进方向表达。\n\n背景是远景，不生成假道路。地面连续填充纸层实体，脚点贴实际路径；纸桥有坡面、平台及桥墩。装饰避开基地、矿点、设施，主要互动标牌必须靠近实体并可点击。HUD保持上下纸带，中部为完整战场；特效短而明确，受击闪白、纸屑和重击震动分层。\n\n生成画不充当运行证明。基础角色采用40张专属核心造型；角色家族复用需在素材库注明来源。部分彩色变体会保留供体装饰，不宣称所有角色均为独立原画。'),
      '04-素材库与命名规范.md':('素材库与命名规范','正式绑定以game/data/assets.json为准，稳定ID区分unit／spell／building／background／prop／resource。整身切图512×512，头像192×192；绑定含content_box、world_height、animation.parts及脚点。当前473条新来源加工记录；40专属核心兵、360按角色母版派生的阵营变体，加2个召唤别名，另有工人、建筑、背景和装饰。\n\n40种角色母版并不等于400次独立生成。来源、母版、供体阵营、目标调色与文件散列在theatre-role-library.json及theatre-art-provenance.json中。状态字段是制作成熟度；详细人工目视及原生代表覆盖另记visual-review.json，不把headless招募检查视为每个角色的画面验收。'),
      '05-素材生成与加工指导.md':('素材生成与加工指导','图像生成严格使用用户指定sub2-image-gen／gpt-image-2.5；提示词与原PNG保留在output/imagegen/paper-warfront/theatre-v3。透明原生alpha，整件轮廓留足边距，武器、脚、旗帜不得切到格边。\n\n整身、建筑、背景分批。切格后按连通alpha取完整主体，去除远离主体的小杂点，统一512画布与脚底基线476；头像按头部焦点裁切。body／前后腿或车轮分件由加工脚本生成，枢轴入manifest。微弱洞口辉光裁掉，金矿轮廓仍完整。\n\n原props-yin存在裁边，已拒用并由repairs/props-yin.png替代；common-mine为独立修复源。16缺失角色用三张3×2板补齐；再与核心供体共同形成40角色母版。派生色仅处理有彩度区域并保留alpha／墨线，供体细节复用需披露。'),
      '06-Godot纸偶与动画规范.md':('Godot纸偶与动画规范','脚点是移动和命中坐标；纸偶整身围绕固定脚点变换。body与前后腿交替转动，炮车转轮；行军节奏关联模拟walk。待机轻微呼吸，攻击前摇倾身压缩，释放回弹；受击闪白并短暂停留、纸屑飞散，死亡落纸或碎片后清理。\n\n当前是分层纸偶程序动画。武器随主体动作，尚未逐兵种制作独立肩肘武器骨骼或手绘连续帧。重兵缩放更大，桥上与桥下脚点不同；单位美术高度不替代规则射程。\n\n投射物、技能预警、粒子和飘字来自真实事件。减少动态开关使绘制不施加相机震动。原生7组姿态夹具只检视枢轴／剪影；完整合法对战录像检视事件反馈。'),
      '07-交互与UI规范.md':('交互与UI规范','入口含线性战役、六图试演、遭遇战、编组、军库、挑战、设置、帮助与鸣谢。战前简报显示整张真实路线、矿容量、设施、目标、空间问题及预算；可在可用军库范围内选择2–4战斗兵种。\n\n桌面底部左侧3–5生产卡，右侧五个法术，中间小地图、研究、建造、队列及导航。移动横屏仅“军阵／法术”两组切换，不另分页展示一整套军库。顶部为金币、法力速率、目标、城生命及暂停。\n\n点矿设置下次出发优先；点独立蓝色路标切换后续部队路线；点空设施牌打开当前位允许的塔／灯。选择建筑不扣费，点合法位后才付费施工。路标与设施不共用触区。施法先选卡，再点合法角色或地面；右键／取消／返回键退出选取。小地图、拖动、左右键均可平移。\n\n原生注入指针检查覆盖招募、退款、设施、路线、矿、导航和研究；50法术UI用信号夹具，不声称全部由真实触摸完成。Android触摸与dp尺寸仍待真机。'),
      '08-关卡与内容规划.md':('关卡与内容规划','六张基准图分别验证基本对推、前沿经济、长援军窗口、阵地绕行、矿线阻击和护送接力。其余194关来自20种显式阶段简报与10种地域布局规则，200场景／193几何／140单线＋60分岔。\n\n单线关卡通过矿距、塔位、回款、援军及对象窗口成立；分岔须有阵地、任务或经济用途。所有桥均保留可读汇流点，没有额外高地伤害。外矿服务速度与容量可以不同，回报必须结合实际往返，不能只比较每趟金量。\n\n六任务为攻城、守城计时、保护指定设施、真实归仓、护送活体、矿线截击。线性故事保存前后关ID及证据旗；六图試演不推进战役。详细地图坐标、经济和设计意图在world/maps及redesign-3.0目录。'),
      '09-验收与制作计划.md':('验收与制作计划','证据分层：原作公开来源、当前参数审计、受控模拟决策、全图运输、完整自动对战、原生指针与GPU画面、导出程序、Android包结构、人工／真机体验。不同层不能相互代替。\n\n规则检查用真实消费与对象结果，避免只检查字段存在。当前运输包含每座无限矿双侧300秒、预计周期与最后完整周期回款；长图不会套用短图每分钟十趟要求。护送边界、截击越线事件、死基地生产及任务严格结算需单独回归。\n\n后续优先做六图两种人工打法、工人骚扰回款、地图首次接战窗口、十院默认编组和Android真机，再扩展全战役平衡。未验证的原作PC路标权限、跨路数值和坡面移速仍留缺证据项。'),
      '10-变更与决策记录.md':('变更与决策记录','2026-10-08重做：停止把200个不同散列当作地图设计成立。保留当时原作证据与当前失败报告，新实现单独登记。\n\n修复外矿返程重选同一边造成停运；矿队列改真实同时服务；优先矿命令控制下一趟；恢复连续实体地面与支持桥；独立路标触区；减少战斗HUD及生产类型。\n\n六基准独立规格接入；194关由阶段空间简报重写；护送在边段交接点跨段仍可判定活体到达，死亡不得成功；越矿线后死亡仍判截击失败；攻破敌城不能跳过其它任务。AI正常付费保留研究预算与入场路径。\n\n美术修复裁边源，十院核心及40角色家族统一纸偶风格。3.0使用400全局军库＋每局小编组；废止4–8兵及units2战斗分页。'),
      '11-Godot架构与数据契约.md':('Godot架构与数据契约','data_store读取maps／campaign／factions／balance／technology／assets；main管理Control菜单、模态、指针输入与原子存档；battle_sim独立60Hz，map_runtime管理节点、边、真实坐标与路径提交；unit_abilities管理能力；tactical_ai仅发公共命令。battle_view／theatre_ground／theatre_hud消费状态和事件；audio_controller消费同一反馈事件。\n\n地图必须包含nodes、edges、bases、mines、build_sites、presentation、design_card；地表边单独标明，ground_y_at在实际请求x插值。工人目标路径不能立即重入当前位置同一边；岔路选择在到节点后承诺，已进入边的单位不瞬移。\n\n命令带序号防重复支付。先校验阵营、编组、科技、资源、目标和位置，再修改。事件附位置y及命中进攻方；渲染不能回写战斗。存档schema2，通过.tmp原子替换；QA以--profile-path隔离用户档。'),
      '12-AI与关卡导演规范.md':('AI与关卡导演规范','AI与玩家使用同一招募／研究／建造／施法／路标命令及金币、法力、排队时间。矿选择评估剩余吞吐、往返周期及可见威胁；设施检查位型与真实费用，前线威胁时保战力。\n\n安全前线已有两兵后可积累研究预算，优先解锁当前编组，再研究后续法术。前排与后排配比按己方实际人数调整，避免永远只补两个起始近战。rush／counter／economy影响矿距、路程、军队配比，没有免费金钱或读入隐形加成。\n\n关卡预置守卫从敌方开局金按普通兵价扣；敌军前沿入口只有达到unlock_time后可选，仍从普通生产队列出生，不定时免费刷兵。入口旗帜与小地图提供位置。\n\n200关默认AI互战：136胜／61负／1平／2局540秒未分胜负；两局改counter后582.6与242.0秒正常败北。表明不同策略可推进，不代表全部关卡已证明人类可胜。'),
      '13-运行素材与反馈矩阵.md':('运行素材与反馈矩阵','军队：body＋双腿／车轮、脚点、武器剪影、前摇、命中、受击、死亡。建筑：底座脚点、施工填充、完成事件、二维攻击圈、停用与摧毁。经济：矿洞、容量／排队、工人来回、实际归仓金币。路线：独立路标、第一段方向提示、桥与汇流、阵营箭头。\n\n法术：选中卡、合法对象／地面、资源校验、冷却、预警、特效、真实效果事件。任务：指定对象的真实生命与距离、实际矿线／交接点、可见敌入口、独立严格胜败。\n\n音频为原创程序合成：战斗纸步、斩击、投射、重击、炮响、死亡、建成、路标、危险和阵营循环音乐。音频限流与16声部池；远离镜头的局部战斗降低输出。录像为静音离线画面，不冒称已录制原生声音或测量帧率。'),
      '14-双平台构建与安装.md':('双平台构建与安装','Windows程序资源内嵌，解压Windows ZIP后双击EXE。支持原生窗口；旧显卡可用附带兼容启动脚本选择gl_compatibility。当前本机Win11／RTX3060执行新包画面检查。\n\nAndroid签名APK包含arm64-v8a与armeabi-v7a、离线无INTERNET权限、横屏，版本3.0.0-rc1／versionCode30000。本地安装后允许系统的“安装未知应用”；存档在应用私有目录。无真机连接，不保证特定手机触控、热量、音频焦点与帧率。\n\nbuild_game.py使用原生Godot导出模板、Java21及本地AndroidSDK工具（模板compile SDK36）构建，校验签名、zipalign16KB与arm64 ELF加载段对齐。私钥／口令位于项目外.keys，仅构建时通过环境传递，不进入源包。升级保持包ID和本地签名；清除应用数据会删除进度。'),
      '15-运行验收与交付报告.md':('运行验收与交付报告','当前完整报告在redesign-3.0/03-实现与验证边界.md，构建在release/3.0.0-rc1。旧2.0的截图、自动胜率与文档不用于证明当前版本；重做前二次研究保留，不覆盖失败审计。\n\n检查通过范围包括当前规则、400兵付费招募及伤害、200图运输、六地图取舍、桌面／横屏移动原生指针夹具、真实预算完整原生录像、Windows新EXE烟测、APK签名和结构。全战役人工平衡、Android真机和原作逐关对照尚未完成。'),
      '16-玩家手册.md':('玩家手册','建议从“地图试演 · 六张基准”的归金坡开始。阅读问题与地图，招前排＋远程保护工人；金币要等工人归城才增加。近矿排队时可增工往外矿，但更远的收入需要护卫。\n\n生产卡上显示费用、锁定和排队。兵种由战前2–4个战斗位选择，另有工人。研究只解锁当前编组内兵种及五个阵营法术／升级。灯和塔各有允许位置：点牌选设施，合法位置发亮，再点位付费；施工时要保护。\n\n岔口蓝牌“我主路／我纸桥”切换后续部队，已进入路线的军队继续前进。桥路更长，但可绕开主路近战阵地；敌远程在真实范围内仍能射到。法术选卡后点对象／地面；非法目标不会扣费；右键或取消退出。\n\n拖战场／点小地图导航；A/D或左右键平移，Home回城，Space跟前线。数字1–5招募，Q/W/E/R/T施法选择，F研究，B建造，Esc暂停。移动横屏在“军阵／法术”切换，Android返回键关闭选择或暂停。\n\n任务以顶部文字、矿线和目标标记为准：护送必须活着到交接点，截击必须越线前打倒，守护必须守满时间。胜利解锁故事下一关，试演不记战役进度。暂停可调音量、减少动态、跟前线；继续／重试／返回均有菜单。'),
      '17-规模扩展与实施进度.md':('规模扩展与实施进度','200场景与故事链、十院各40战斗兵、50法术、六挑战保留；当前200场景有193实际几何、26种空间问题文本。基础库容量与本局编组严格区分，不能以规模替代地图体验。\n\n已实现六手工基准、194显式空间简报、真实回款、阵地绕行、任务锚点、纸桥实体、工人容量、独立指针触区与新版小HUD。新素材为40专属核心与40角色母版派生，不冒称400张独立生成原画。\n\n后续体验评审项仍为六图多打法、工人骚扰、全战役默认难度、窄屏／真机触摸、音频与性能。当前交付是可运行评审版，未宣称与HD品质相等。'),
      '18-路径与经济执行规范.md':('路径与经济执行规范','节点与边都是实际战斗坐标，矿、设施和任务锚点有edge／s／x／y；长度沿折线累计。工人路径选择将当前位置与目的地的边纳入首尾，避免同边立即回接形成零距离循环。ground_y_at只用指定地表边，桥高不会替代地面。\n\n容量为同时服务数量，工人在抵矿FIFO队列等待，等待不推进采矿时间；运回基地完成deposit后才入账。每趟8金，外矿通过真实服务周期／容量扩展收入；指定优先矿影响下一趟，在无剩余吞吐时才另选。有限矿枯竭时换目标。\n\nAI经济估计包含去程、服务、回程、1秒归仓与已有工人负载；玩家点击命令优先级高于自动选择。法术和塔用实际二维距离，不给坡面或桥自动加伤／无敌。两侧运输与长坡援军时间有镜像检查。'),
      '19-战前编组与科技规范.md':('战前编组与科技规范','每局2–4个战斗兵種，加工人共3–5项生产。关卡default_roster决定首次默认阵容，已保存的自选编组在available_roster内规范化；旧8兵存档迁移到最多4战斗兵种。科技面板过滤未选兵种；完整科技也不能直接招募编组之外的兵。\n\n生产队列最多6，工人上限10，战斗人数上限60；人数上限包含待生产订单，取消未出生订单全额退金。军库400种仅用于战前选择与资料浏览。移动HUD只军阵／法术两组，废止units2。\n\n选择建筑不扣费，提交合法施工才收费。基础建筑无需虚构科技前置；当前阶段剩余兵种科技以technology.json的真实id、requires和seconds为准。选中前两种开局可用，其余科技在真实完成时解锁。'),
      '20-战役与任务执行规范.md':('战役与任务执行规范','十章每章20关保留线性因果与英雄对话，predecessor／next_level／story_flag原ID不重排。当前空间提示根据地图重写。各任务的胜败独立于敌基地是否已毁。\n\n攻城看敌城生命；survive看城存活到duration；protect看指定实际塔位存活到duration；deliver_gold只看stats.gold_delivered；escort看唯一对象存活且经过交接锚点；intercept在移动跨过矿线时记失败，后续同tick死亡不撤销越线。\n\n护送不能献弃／夺印／复印。目标恰位于边终点时，用经过节点记录识别跨段到达，死亡优先于完成。纸城死亡后不能继续招募，队列不出生；非攻城任务即使毁敌城，仍需完成显式目标。胜利原子保存下一关与证据旗，试演／遭遇战不写战役解锁。'),
      '21-十院素材与动画规范.md':('十院素材与动画规范','十院各四个专属核心造型、工人、基地、塔、产法设施、地域远景与两类装饰；40角色家族覆盖360个其余军库单位的阵营调色。两召唤体为明确别名复用。\n\n原生十院核心战斗夹具、400全局军库浏览、7姿态及合法完整对局互补。全部调色联系板已目视，角色母版及修复源已检查，alpha裁切与边距由加工脚本检查。仍有供体装饰复用和彩色肤部位，不能称400独立美术。\n\n角色主体、双腿／车轮有枢轴；独立武器关节未逐兵种制作。所有动作和特效需以原生过程验收；整身切图、头像和源图不等于独立手绘帧动画。素材表／来源／规则位置可从离线theatre-v3-gallery.html查询。'),
      '22-双平台验收与发布.md':('双平台验收与发布','3.0.0-rc1作为地图重做评审包，WindowsEXE／ZIP、Android签名APK、源码ZIP、SHA256清单及构建日志集中在release/3.0.0-rc1。旧2.0包和研究审计保留。\n\n原生Windows检查启动菜单、桥路战场与OpenGL兼容路径；Android检查包ID、版本、架构、签名、离线权限、ZIP及arm64ELF16KB对齐。包结构检查不能代替真机可运行、触控、音频和帧率。\n\n源包包含当前game、docs、assets、生成源、工具和验证证据，排除.keys／.tools／.godot／缓存及export_credentials.cfg。签名口令与图像网关配置不在项目；重打包需当前签名私钥保持升级关系。完整结果以redesign-3.0/03-实现与验证边界.md为准。')
    }
    for filename,(title,body) in topics.items():
        extra=''
        if filename.startswith('02-'):extra='\n\n'+table(['阵营','主色','法力设定','规则类型'],[[f['name'],f['color'],f['mana'],f['trait']] for f in factions])
        write(DOC/filename,f'# {title} · {VERSION}\n\n{common}\n\n{body}{extra}\n\n[制作入口](README.md) · [地图重做与证据](redesign-3.0/README.md)')
    write(DOC/'README.md',f'''# 纸上兵戈：十院留名 · {VERSION}

当前版本重做地图的空间取舍：归仓与前沿经济、援军距离、分岔阵地、矿线截击、护送接力。Godot原生纸偶舞台，每局2–4个战斗兵种加一个工人，生产选择合计3–5项。

{common}

[地图研究](../research/swords-and-soldiers-map/recheck-20261008/README.md) · [六图试演与实施](redesign-3.0/README.md) · [下载评审版](../../release/{VERSION}/README.md) · [玩家手册](16-玩家手册.md) · [离线素材与地图浏览](../../assets/paper-warfront/theatre-v3-gallery.html)

'''+table(['文档','范围'],[[f'[{title}]({filename})',body.split('。')[0]+'。'] for filename,(title,body) in topics.items()])+'''

研究保留重做前事实，不改写历史失败以获得“通过”。旧2.0文档快照在[版本档案](../archive/paper-warfront-2.0-before-map-rework.zip)，旧发布仍在release/2.0.0。当前地图规范和军库参数只以game/data及本版文档为准。''')
    write(DOC/'world/README.md',f'# 十院世界与军库 · {VERSION}\n\n[当前地图规划](../redesign-3.0/02-战役空间目录.md) · [六张基准图](../redesign-3.0/01-六张基准地图.md) · [完整故事路线](04-完整故事路线.md) · [十院设定](02-十阵营设定.md)\n\n400作战兵种是全局资料规模；每局2–4个战斗类型和工人。当前200关有193几何、140单线、60单处分岔，逐关人工平衡尚未完成。\n\n'+table(['阵营','兵种表'],[[f['name'],f'[{f["id"]}](units/{f["id"]}.md)'] for f in factions]))
    write(DOC/'world/01-核心博弈.md','# 核心博弈 · 地图位置改变投入\n\n[完整六图规格](../redesign-3.0/01-六张基准地图.md)。\n\n多投一工会推迟第一批护卫，但只有矿点剩余吞吐和归仓路安全时，额外服务才形成真实后续收入。长图中重兵到达晚，研究、回法与前位设施需要用控制或修复接住空窗。纸桥多花行军时间，回避的是特定阵地的位置压力；远程在实际二维范围内仍能打到。任务图把矿线、活体与交接点变为明确地理条件。\n\n每局少量兵种通过先后顺序、路线、回款和法术组合形成局部博弈；不从场外操作每名士兵走位。')
    write(DOC/'world/03-200地图目录.md','# 地图目录 · 当前实施入口\n\n[200关逐图空间问题、任务、生产数和坐标](../redesign-3.0/02-战役空间目录.md) · [六基准手工规格](../redesign-3.0/01-六张基准地图.md)\n\n200场景含193几何与7组有记录复用，数量不作为设计质量证据；研究和原生测试以当前版本散列为准。')
    for f in factions:
        rows=[]
        for uid in f['combat_units']:
            u=balance['units'][uid];p=pv.get(uid,{})
            rows.append([uid,u['name'],u['role'],u['gold'],u['hp'],u['damage'],p.get('source','共享来源'),p.get('master_id','专属核心')])
        write(DOC/'world/units'/(f['id']+'.md'),f'# {f["name"]}军库 · {VERSION}\n\n{f["premise"]}\n\n法力：{f["mana"]}；规则类型 `{f["trait"]}`。全局40兵可从战前选2–4种；出生方向与拥有方决定敌我。\n\n'+table(['ID','名称','角色','金币','生命','伤害','源图','母版'],rows)+'\n素材母版与调色共享已标明；表中数值来自当前balance-prototype.json，独立动画和人工平衡并未逐兵种完成。')
    # Historical documents remain available and visibly dated.
    for old in ['02-玩法与三阵营规则.md','06-Threejs厚片与动画规范.md']:
        p=DOC/old
        if p.exists():
            text=p.read_text(encoding='utf-8')
            if not text.startswith('> 历史方案'):write(p,'> 历史方案：此文件属于旧原型，当前Godot／十院／3–5生产规则见[制作入口](README.md)。\n\n'+text)
    write('README.md',f'# 纸上兵戈：十院留名 / Paper Warfront {VERSION}\n\nGodot4.7.2原生纸偶即时策略。地图围绕真实回款、援军距离、分岔阵地和任务对象组织；每局2–4战斗兵种＋工人，3–5项生产选择。\n\n[地图研究](docs/research/swords-and-soldiers-map/recheck-20261008/README.md) · [六图重做](docs/paper-warfront/redesign-3.0/README.md) · [Windows／Android评审包](release/{VERSION}/README.md) · [完整文档](docs/paper-warfront/README.md) · [素材与地图浏览](assets/paper-warfront/theatre-v3-gallery.html) · [Godot工程](game/project.godot)\n\n![真实预算原生战斗](output/qa/godot/v3-native-play/battle-022.png)\n\n200场景有193几何，十院400全局兵种库；素材采用40专属核心和40角色母版派生。原生规则、指针与画面已有证据，200关人工平衡、Android真机和原作逐关数值对照仍未完成。本版为可运行评审候选，未宣称已达HD品质。')
    write('docs/README.md','# 项目文档入口\n\n[原作地图二次研究](research/swords-and-soldiers-map/recheck-20261008/README.md) · [当前制作文档](paper-warfront/README.md) · [六图重做与证据](paper-warfront/redesign-3.0/README.md) · [200关空间目录](paper-warfront/redesign-3.0/02-战役空间目录.md)\n\n研究目录保存当时的审计与失败；当前实现、证据散列、包版本和剩余评审项独立登记，旧数量不替代体验验收。')
    write('game/README.md',f'# Godot工程 · {VERSION}\n\n用Godot4.7.2导入project.godot，F5运行，无需重新生成素材。main.tscn为入口，battle_sim与map_runtime独立60Hz；UI与渲染只消费状态和事件。\n\n[制作文档](../docs/paper-warfront/README.md) · [六图试演](../docs/paper-warfront/redesign-3.0/README.md) · [下载](../release/{VERSION}/README.md)\n\n规则检查：test_world_foundation.gd、test_world_combat.gd、test_map_transport.gd、test_theatre_decisions.gd、test_simulation.gd。完整对战：test_campaign_play.gd。原生UI：`-- --qa-theatre <绝对目录> --profile-path <隔离JSON路径>`；横屏布局增加`--mobile-ui`，并不等于Android真机。\n\n导出EXE可用`-- --demo --capture <绝对PNG路径> --quit-after-capture --profile-path <隔离JSON>`烟测；测试脚本从发布包排除。旧test_campaign_paths.gd针对2.0编组，不作为当前验收。签名凭据、网关配置、引擎缓存不在源包。')
    write('release/README.md',f'# 本地游戏包\n\n[3.0.0-rc1地图重做评审版]({VERSION}/README.md) · [2.0历史包](2.0.0/README.md)\n\n新包以当前构建清单和源码／原生验证报告为准，旧2.0不作为当前地图重做证据。Android尚未连接真机。')
    write('assets/paper-warfront/README.md',f'# 当前素材库 · {VERSION}\n\n[离线素材与地图浏览](theatre-v3-gallery.html) · [来源与加工规范](../../docs/paper-warfront/04-素材库与命名规范.md) · [真实原生画面](../../output/qa/godot/v3-native-play/battle-022.png)\n\n运行素材权威绑定在game/data/assets.json及game/assets；本目录的早期原型PNG与gallery保留为历史参考，不能替代当前运行绑定。新源图、提示词、修复和调色联系板在output/imagegen/paper-warfront/theatre-v3；473加工记录、40专属核心／40角色母版／360变体／2召唤别名已标记来源。\n\n[来源目视与代表运行覆盖](visual-review-v3.json)。源图、headless规则和原生画面各有不同覆盖范围。')
    # Offline production gallery: actual graph geometry and linked assets, not concept images.
    units=[]
    for f in factions:
        for uid in f['combat_units']:
            u=balance['units'][uid];p=pv.get(uid,{})
            units.append(dict(id=uid,name=u['name'],role=u['role'],faction=f['id'],gold=u['gold'],hp=u['hp'],damage=u['damage'],image='../../game/'+asset[uid]['path'].removeprefix('res://'),source=p.get('source',''),master=p.get('master_id','专属核心')))
    maps_html=''.join(f'<article><h3>{html.escape(m["name"])}</h3><p>{html.escape(m["design_card"]["question"])}</p>{map_svg(m,levels[m["id"]])}<p>{html.escape(" ／ ".join(m["design_card"]["plans"]))}</p><a href="../../docs/paper-warfront/world/maps/{m["id"]}.md">坐标、预算与目标 →</a></article>' for m in selected)
    options=''.join(f'<option value="{f["id"]}">{html.escape(f["name"])}</option>' for f in factions)
    gallery='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>纸上兵戈 · 地图与素材库</title><style>
    :root{color-scheme:light;font-family:"Microsoft YaHei",sans-serif;background:#f4eddd;color:#343332}*{box-sizing:border-box}body{margin:0}header,main{max-width:1320px;margin:auto;padding:32px}header{border-bottom:2px solid #b74532}h1{font-family:serif;font-size:44px;margin:0 0 14px}h2{margin:48px 0 18px}p{line-height:1.8}a{color:#a7372b}article{background:#ece3d1;border:1px solid #c5b491;border-radius:12px;padding:22px}article h3{margin-top:0}.maps{display:grid;grid-template-columns:1fr 1fr;gap:20px}svg{width:100%;height:auto}.filters{display:flex;gap:12px;flex-wrap:wrap;position:sticky;top:0;padding:16px;background:#f4eddd;z-index:2;border-bottom:1px solid #c5b491}input,select,button{font:inherit;padding:12px;border:1px solid #8e7859;border-radius:8px;background:#fff8e9;color:#343332}button{cursor:pointer}button:hover{background:#e2cfaa}button:focus-visible,a:focus-visible,input:focus-visible,select:focus-visible{outline:3px solid #397e9e;outline-offset:3px}.army{display:grid;grid-template-columns:repeat(auto-fill,minmax(190px,1fr));gap:18px;margin-top:24px}.unit{text-align:left;display:flex;flex-direction:column;padding:12px;background:#eee3cd}.unit img{width:100%;height:180px;object-fit:contain}.unit strong{margin:12px 0 6px}.unit small{line-height:1.8;overflow-wrap:anywhere}dialog{background:#fff4db;color:#343332;border:2px solid #8e7859;border-radius:16px;max-width:720px;width:90vw}dialog::backdrop{background:#282734b3}dialog img{width:100%;max-height:52vh;object-fit:contain}dialog p{overflow-wrap:anywhere}.native{width:100%;border-radius:12px}.note{color:#746d61}@media(max-width:720px){header,main{padding:20px}h1{font-size:32px}.maps{grid-template-columns:1fr}.army{grid-template-columns:repeat(2,1fr);gap:12px}.unit img{height:140px}}@media(prefers-reduced-motion:reduce){*{scroll-behavior:auto}}
    </style><header><p>纸上兵戈 · 3.0.0-rc1 / 制作与评审</p><h1>地图让位置成为决策</h1><p>六张基准纸场 · 十院军库 · 真实运行素材</p><p class="note">40专属核心＋40角色母版覆盖360个变体。此处为素材与空间资料；人工平衡、Android真机与HD逐关对照尚未验收。</p><a href="../../docs/paper-warfront/redesign-3.0/README.md">设计与验证文档</a></header><main><h2>六张纸场</h2><section class="maps">MAPS</section><h2>原生对战</h2><img class="native" src="../../output/qa/godot/v3-native-play/battle-022.png" alt="正常预算下部队经过纸桥，主路守卫仍在地面"><p><a href="../../output/qa/godot/v3-native-play/battle-replay.mp4">20秒静音原生对战片段</a> · <a href="../../output/qa/godot/v3-native-play/report.json">完整对战与事件记录</a></p><p class="note">采用正式预算与付费招募。片段在14–24秒选路与40–50秒交战之间剪切；离线15fps取帧不作为实测性能。</p><h2>十院军库</h2><p>点击查看整身和来源。每局从军库挑2–4个战斗兵种，加工人共3–5项生产。</p><div class="filters"><label>阵营 <select id="faction">OPTIONS</select></label><label>查找 <input id="search" placeholder="名称、角色或 ID"></label><span id="count" role="status"></span></div><section class="army" id="army"></section><dialog id="details"><button id="close" type="button">关闭</button><h3 id="title"></h3><img id="picture" alt="整身纸偶"><p id="data"></p></dialog></main><script>
    const units=DATA;const army=document.querySelector('#army'),faction=document.querySelector('#faction'),search=document.querySelector('#search'),dialog=document.querySelector('#details');
    function show(u){document.querySelector('#title').textContent=u.name+' · '+u.id;document.querySelector('#picture').src=u.image;document.querySelector('#picture').alt=u.name;document.querySelector('#data').textContent=`角色 ${u.role} / 金币 ${u.gold} / 生命 ${u.hp} / 伤害 ${u.damage}\n来源 ${u.source} / 母版 ${u.master}`;dialog.showModal();}
    function render(){army.replaceChildren();let q=search.value.trim().toLowerCase();let list=units.filter(u=>u.faction===faction.value&&[u.name,u.role,u.id].join(' ').toLowerCase().includes(q));document.querySelector('#count').textContent=list.length+' / 40';for(let u of list){let b=document.createElement('button');b.type='button';b.className='unit';let im=document.createElement('img');im.src=u.image;im.alt=u.name;im.loading='lazy';let name=document.createElement('strong');name.textContent=u.name;let detail=document.createElement('small');detail.textContent=u.role+' · '+u.gold+'金 / '+u.hp+'生命';let id=document.createElement('small');id.textContent=u.id;b.append(im,name,detail,id);b.onclick=()=>show(u);army.append(b);}}
    faction.onchange=render;search.oninput=render;document.querySelector('#close').onclick=()=>dialog.close();render();
    </script></html>'''.replace('MAPS',maps_html).replace('OPTIONS',options).replace('DATA',json.dumps(units,ensure_ascii=False).replace('</',r'<\/'))
    write('assets/paper-warfront/theatre-v3-gallery.html',gallery)
    write('assets/paper-warfront/current-index-v3.json',json.dumps({'version':VERSION,'runtime_manifest':'game/data/assets.json','theatre_provenance_records':len(provenance),'maps':len(maps),'geometry_records':len(duplicate),'unit_gallery_entries':len(units),'baseline_ids':[m['id'] for m in selected]},ensure_ascii=False,indent=2))
    print(json.dumps({'documents':len(topics),'map_briefs':len(maps),'gallery_units':len(units),'geometry_records':len(duplicate),'history':'docs/archive/paper-warfront-2.0-before-map-rework.zip'},ensure_ascii=False))

if __name__=='__main__':main()
