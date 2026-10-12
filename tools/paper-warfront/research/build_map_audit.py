"""Reproducible source audit and explicitly labelled research figures.

Run natively on Windows. No game rules, exports, or original screenshots are changed.
"""
from pathlib import Path
import hashlib
import json
from collections import Counter
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'docs/research/swords-and-soldiers-map'
FIG = OUT / 'figures'
FONT = ROOT / 'assets/paper-warfront/fonts/source/NotoSansSC.full.ttf'
PAPER = '#f4efdf'
INK = '#283a37'
RED = '#ad463b'
TEAL = '#397d79'
OCHRE = '#a97824'
MUTED = '#68736b'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def line_of(path, text):
    lines = path.read_text(encoding='utf-8-sig').splitlines()
    return next(i for i, line in enumerate(lines, 1) if text in line)


def write_audit():
    campaign_path = ROOT / 'game/data/campaign.json'
    balance_path = ROOT / 'game/data/balance-prototype.json'
    sim_path = ROOT / 'game/scripts/battle_sim.gd'
    view_path = ROOT / 'game/scripts/battle_view.gd'
    main_path = ROOT / 'game/scripts/main.gd'
    content = json.loads(campaign_path.read_text(encoding='utf-8-sig'))
    balance = json.loads(balance_path.read_text(encoding='utf-8-sig'))
    sim_source = sim_path.read_text(encoding='utf-8-sig')
    anchors = [
        (sim_path, 'func start(', 'bases and initial workers have fixed coordinates'),
        (sim_path, 'func slot_x(', 'two fixed building slots per side'),
        (sim_path, 'func build(', 'building immediately contributes; no construction phase'),
        (sim_path, 'func area_damage(', 'area targeting uses only horizontal distance'),
        (sim_path, 'func nearest_enemy(', 'target distance has no route identity'),
        (sim_path, 'func tick_worker(', 'one fixed mine per side; independent worker timers'),
        (sim_path, 'func front(', 'single scalar front'),
        (sim_path, 'func ai_turn(', 'no route selection or per-route threat'),
        (view_path, 'func floor_y(', 'constant ground height'),
        (view_path, 'var map_id=', 'map selector chooses visual theme'),
        (view_path, 'func draw_minimap(', 'flat minimap with x/56 projection'),
        (main_path, 'func navigate_minimap(', 'horizontal-only minimap navigation'),
    ]
    travel = []
    for unit_id in ['unit.yin.axe', 'unit.yin.cannon', 'unit.deng.shadow']:
        speed = balance['units'][unit_id]['speed']
        travel.append({'unit':unit_id, 'spawn_x':2.65, 'target_x':28, 'distance':25.35,
                       'speed':speed, 'ideal_travel_seconds':round(25.35 / speed, 3),
                       'exclusions':'Production delay, combat, target range, status and discrete-step rounding'})
    report = {
        'date':'2026-10-08',
        'scope':'Godot 1.0 source audit; mechanical map quality is separate from export/functional QA',
        'source_sha256':{str(p.relative_to(ROOT)).replace('\\','/'):sha(p) for p in [campaign_path,balance_path,sim_path,view_path,main_path]},
        'anchors':[{'file':str(p.relative_to(ROOT)).replace('\\','/'), 'line':line_of(p,t), 'finding':f} for p,t,f in anchors],
        'campaign_levels':len(content['levels']),
        'campaign_map_labels':dict(Counter(l['map'] for l in content['levels'])),
        'campaign_win_rules':dict(Counter(l['win'] for l in content['levels'])),
        'distinct_geometry_rules_found':1,
        'interpretation_of_geometry_count':'From fixed simulation coordinates and absent per-map geometry; not a claim about original Swords & Soldiers map count',
        'simulation_reads_config_map':('config.map' in sim_source or 'config.get("map"' in sim_source),
        'simulation_reads_balance_map':('balance.map' in sim_source or 'balance["map"]' in sim_source),
        'configured_map_block':balance['map'],
        'implemented_coordinates':{'bases':[2,54], 'mines':[6,50], 'building_slots':[[3.5,8.5],[52.5,47.5]]},
        'ideal_worker_cycle':{'one_way_distance':4, 'speed':1.25, 'mine_seconds':1.2, 'deposit_seconds':1,
                              'cargo':8, 'roundtrip_seconds':8.6, 'gold_per_second_per_worker':round(8/8.6,6),
                              'scope':'Formula for current rules in a safe, steady state; not original-game measurement'},
        'ideal_reinforcement_travel':travel,
        'headless_probe':'current-map-probe.json',
        'original_game_executed_this_research':False,
    }
    (OUT/'current-map-audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return report


def font(size):
    result = ImageFont.truetype(str(FONT), size)
    result.set_variation_by_axes([650 if size >= 38 else 470])
    return result


def txt(draw, xy, text, size=24, color=INK):
    draw.text(xy, text, font=font(size), fill=color)


def arrow(draw, points, color=TEAL, width=8):
    import math
    draw.line(points, fill=color, width=width, joint='curve')
    x,y=points[-1]; x0,y0=points[-2]
    a=math.atan2(y-y0,x-x0)
    p1=(x-18*math.cos(a-.48),y-18*math.sin(a-.48))
    p2=(x-18*math.cos(a+.48),y-18*math.sin(a+.48))
    draw.polygon([(x,y),p1,p2],fill=color)


def node(draw, x, y, kind, label, color=TEAL, above=False):
    if kind=='mine':
        draw.polygon([(x,y-20),(x+23,y),(x,y+20),(x-23,y)], fill=OCHRE)
    elif kind=='sign':
        draw.line([(x,y-28),(x,y+28)],fill=INK,width=5)
        draw.polygon([(x-17,y-24),(x+23,y-24),(x+35,y-13),(x+23,y-2),(x-17,y-2)],fill=RED)
    elif kind=='tower':
        draw.rectangle([x-13,y-23,x+13,y+18],fill=color)
        draw.line([(x-22,y-24),(x+22,y-24)],fill=color,width=7)
    else:
        draw.rounded_rectangle([x-22,y-22,x+22,y+22], radius=7, fill=color)
    w=draw.textlength(label,font=font(22))
    txt(draw,(x-w/2,y-64 if above else y+33),label,22)


def mechanisms_figure():
    im=Image.new('RGB',(1660,1030),PAPER); d=ImageDraw.Draw(im)
    txt(d,(58,35),'地图把“自动行军”变成战术承诺',43)
    txt(d,(60,105),'结构示意｜依据初代/移植版资料抽象；不是原作某一关的精确复刻',23,MUTED)
    d.rounded_rectangle([45,166,1615,478],radius=18,fill='#ffffff')
    txt(d,(68,185),'① 空间结构：路标改变后续来兵的去向，岔路最后可以重新汇流',29)
    arrow(d,[(155,342),(540,342)],TEAL)
    arrow(d,[(540,342),(725,279),(1040,279),(1190,342)],RED)
    arrow(d,[(540,342),(725,412),(1040,412),(1190,342)],TEAL)
    arrow(d,[(1190,342),(1495,342)],TEAL)
    node(d,155,342,'base','己方基地')
    node(d,319,342,'mine','经济区')
    node(d,540,342,'sign','分岔 / 路标')
    node(d,1190,342,'base','汇流点')
    node(d,1495,342,'base','敌方目标',RED)
    txt(d,(730,237),'部分关卡：更多阻力与资源',22,RED)
    txt(d,(720,441),'另一条路：绕行与收益取舍',22,TEAL)
    d.rounded_rectangle([45,506,1615,830],radius=18,fill='#e6eadf')
    txt(d,(68,526),'② 位置关系：经济、设施和增援时间共同决定能否把推进兑现',29)
    for x,y,title,body in [
        (74,588,'采矿空间','工人往返距离、暴露窗口\n与矿区防守决定现金流'),
        (590,588,'建筑位置','可防守设施影响回法积累\n建造阶段也是反制窗口'),
        (1100,588,'兵力到达时间','基地越远，补兵越迟\n进攻承诺越难及时修正')]:
        txt(d,(x,y),title,28,TEAL)
        for j,line in enumerate(body.split('\n')): txt(d,(x,y+48+j*37),line,23)
    txt(d,(74,759),'地表高度已见于开发者地图数据；高地伤害、视线遮挡、坡面减速均未证实。',23,RED)
    txt(d,(60,866),'证据：开发者地图/平衡文章 + Nintendo 战术说明 + 多平台岔路记录。',23,MUTED)
    txt(d,(60,909),'原作画面与布局测量仍需补证；本图中的节点数量、相对位置与路径长度只用于讲解。',22,MUTED)
    im.save(FIG/'map-mechanisms.png')


def proposed_figure():
    im=Image.new('RGB',(1660,1220),PAPER); d=ImageDraw.Draw(im)
    txt(d,(58,34),'《纸上兵戈》地图重做：先验证三张白盒',43)
    txt(d,(60,103),'原创设计提案｜尚未接入运行版｜不同地图必须改变玩家的有效决策',23,MUTED)
    for top,title in [(165,'M01 · 中型基准图：测经济与增援，再固定阵营基准'),
                      (483,'M02 · 折页岔口：路标选择、侧路承诺与汇流节奏'),
                      (833,'M03 · 灯台外矿：经济前置、设施保护与位置任务')]:
        d.rounded_rectangle([45,top,1615,top+(320 if top==483 else 285)],radius=18,fill='#ffffff')
        txt(d,(68,top+18),title,29)
    y=307
    arrow(d,[(145,y),(1495,y)])
    for x,k,l,c in [(145,'base','我城',TEAL),(300,'mine','近矿',TEAL),(435,'tower','守位',TEAL),(1220,'mine','敌矿',RED),(1495,'base','敌城',RED)]:node(d,x,y,k,l,c)
    txt(d,(585,368),'只改变矿距 / 前线槽位，观察战术是否改变',23,MUTED)
    y=668
    arrow(d,[(145,y),(475,y)])
    arrow(d,[(475,y),(700,y-84),(980,y-84),(1175,y)],RED)
    arrow(d,[(475,y),(610,y+78),(710,y+22),(810,y+78),(910,y+22),(1010,y+78),(1080,y+22),(1175,y)],TEAL)
    arrow(d,[(1175,y),(1495,y)])
    node(d,145,y,'base','我城');node(d,475,y,'sign','路标');node(d,875,y-84,'tower','敌哨位',RED)
    node(d,1175,y,'base','汇流');node(d,1495,y,'base','敌目标',RED)
    txt(d,(685,767),'短路接战早、压力大；长路绕行，增援更迟',23,MUTED)
    y=985
    arrow(d,[(145,y),(1495,y)])
    for x,k,l,c in [(145,'base','我城',TEAL),(310,'mine','安全矿',TEAL),(600,'tower','纸灯位',TEAL),(875,'mine','外矿',TEAL),(1150,'tower','敌压制位',RED),(1495,'base','敌城',RED)]:node(d,x,y,k,l,c)
    txt(d,(185,1067),'专门验证：护住外矿现金流，同时处理截击线 / 设施存活要求',23,MUTED)
    txt(d,(60,1160),'走路、施法、纸标、AI 与小地图共用同一份几何；先通过白盒验收，再生产场景美术。',23,RED)
    im.save(FIG/'whitebox-proposals.png')


def annotated_reference():
    src=ROOT/'docs/reference/hd-vikings-tech-tree.png'
    original=Image.open(src).convert('RGB')
    im=Image.new('RGB',(1660,970),PAPER);d=ImageDraw.Draw(im)
    txt(d,(50,25),'原作 PC 截图：高度与导航确实在画面中',38)
    txt(d,(50,91),'仅标注这张图能观察到的内容；科技菜单展开，未显示完整关卡',23,MUTED)
    # Preserve original pixels: no scaling or repainting inside screenshot.
    im.paste(original,(45,165));d=ImageDraw.Draw(im)
    txt(d,(1285,203),'A · 起伏地表',27,TEAL)
    txt(d,(1285,255),'基地附近地面',23)
    txt(d,(1285,292),'与中部高度不同',23)
    d.line([(1290,340),(1260,340),(420,693)],fill=RED,width=3)
    txt(d,(1285,465),'B · 地表 / 切面',27,TEAL)
    txt(d,(1285,517),'草边、泥土与前景',22)
    txt(d,(1285,553),'形成侧视舞台层次',22)
    txt(d,(1285,657),'C · 底部导航',27,TEAL)
    txt(d,(1285,709),'标记与当前视窗',23)
    d.line([(1290,757),(1258,757),(975,775)],fill=RED,width=3)
    txt(d,(50,872),'来源：MobyGames · Windows 截图 503975；原始文件保留在 docs/reference。',23,MUTED)
    txt(d,(50,916),'此图不证明岔路布局、矿点容量、高地加成或遮挡规则；这些不能从装饰倒推。',23,RED)
    im.save(FIG/'hd-reference-annotated.png')


def main():
    FIG.mkdir(parents=True,exist_ok=True)
    report=write_audit()
    mechanisms_figure(); proposed_figure(); annotated_reference()
    print(json.dumps({'levels':report['campaign_levels'],'win_rules':report['campaign_win_rules'],
                      'mechanical_maps':report['distinct_geometry_rules_found'],
                      'figures':[p.name for p in sorted(FIG.glob('*.png'))]},ensure_ascii=False))


if __name__=='__main__':
    main()
