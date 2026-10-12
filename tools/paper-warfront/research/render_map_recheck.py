"""Render research diagrams from measured evidence and explicit draft specifications.

No remote downloads. No game asset or runtime changes. Uses bundled licensed font.
"""
from __future__ import annotations

import hashlib
import json
import math
import sys
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[3]
REPORT = ROOT / 'docs/research/swords-and-soldiers-map/recheck-20261008'
OUT = REPORT / 'figures'
FONT = ROOT / 'assets/paper-warfront/fonts/source/NotoSansSC.full.ttf'
BG, PAPER, INK = '#EDE9E0', '#FFFCF5', '#29323A'
MUTED, LINE = '#65716F', '#D8D5CA'
BLUE, RED, GOLD, GREEN = '#357D8B', '#B95140', '#B98A30', '#64856B'


@lru_cache(maxsize=60)
def font(size):
    face = ImageFont.truetype(str(FONT), size)
    try:
        axes = face.get_variation_axes()
        face.set_variation_by_axes([600 if size >= 28 else 450 for _ in axes])
    except OSError:
        pass
    return face


def text(d, xy, value, size=25, color=INK):
    d.text(xy, str(value), font=font(size), fill=color)


def wrap(d, value, size, width):
    lines = []
    for paragraph in str(value).split('\n'):
        current = ''
        for char in paragraph:
            if d.textlength(current + char, font=font(size)) > width and current:
                lines.append(current)
                current = char
            else:
                current += char
        lines.append(current)
    return lines


def paragraph(d, xy, value, size=25, width=700, color=INK, leading=1.55):
    x, y = xy
    for line in wrap(d, value, size, width):
        text(d, (x, y), line, size, color)
        y += int(size * leading)
    return y


def panel(d, box, fill=PAPER, outline=LINE):
    d.rounded_rectangle(box, radius=20, fill=fill, outline=outline, width=2)


def arrow(d, a, b, color=BLUE, width=4):
    d.line([a, b], fill=color, width=width)
    ang = math.atan2(b[1]-a[1], b[0]-a[0])
    pts = [b]
    for delta in (-.5, .5):
        pts.append((b[0]-15*math.cos(ang+delta), b[1]-15*math.sin(ang+delta)))
    d.polygon(pts, fill=color)


def at_y(points, x):
    for a, b in zip(points, points[1:]):
        if a[0] <= x <= b[0]:
            return a[1] + (b[1]-a[1])*(x-a[0])/(b[0]-a[0])
    return points[0][1] if x < points[0][0] else points[-1][1]


def symbol(d, pos, kind, owner=None, scale=1):
    x, y = pos
    color = BLUE if owner == 0 else RED if owner == 1 else MUTED
    s = int(14*scale)
    if kind == 'base':
        d.rectangle((x-s,y-2*s,x+s,y), fill=color)
        d.polygon([(x-s-4,y-2*s),(x,y-3*s),(x+s+4,y-2*s)], fill=color)
        d.rectangle((x-4,y-s,x+4,y), fill=PAPER)
    elif kind == 'mine':
        d.polygon([(x-s,y),(x-s//2,y-s),(x+s//2,y-s),(x+s,y)],fill=GOLD)
        d.ellipse((x-5,y-11,x+5,y+5),fill=INK)
    elif kind == 'site':
        d.rectangle((x-s,y-2*s,x+s,y),outline=color,width=3)
        d.line([(x-s,y-2*s),(x+s,y)], fill=color,width=2)
        d.line([(x+s,y-2*s),(x-s,y)], fill=color,width=2)
    elif kind == 'route_sign':
        d.line([(x,y),(x,y-3*s)],fill=color,width=4)
        d.polygon([(x-2,y-3*s),(x+s+7,y-3*s),(x+s+13,y-2*s),(x-2,y-2*s)],fill=color)
    elif kind == 'merge':
        d.ellipse((x-7,y-7,x+7,y+7), fill=GREEN)
    elif kind in ('enemy_entry', 'enemy_position'):
        d.polygon([(x-s,y-2*s),(x+s,y-2*s),(x,y)],fill=RED)
    elif kind in ('task_target', 'escort_target'):
        d.ellipse((x-s,y-2*s,x+s,y),fill=color,outline=PAPER,width=3)
        text(d,(x-6,y-2*s-1),'!',20*int(scale),PAPER)
    elif kind in ('goal', 'failure_line'):
        color = RED if kind == 'failure_line' else BLUE
        d.line([(x,y+8),(x,y-4*s)],fill=color,width=4)
        d.polygon([(x,y-4*s),(x+2*s,y-4*s),(x+2*s,y-3*s),(x,y-3*s)],fill=color)


def draw_whitebox(d, spec, box):
    x0,y0,x1,y1 = box
    panel(d,box)
    text(d,(x0+28,y0+20),f"{spec['id']}  {spec['name']}",38)
    text(d,(x0+28,y0+75),spec['question'],28,BLUE)
    text(d,(x0+28,y0+118),f"长度 {spec['length']} · {len(spec['production_roles'])} 生产类型（含工人）",22,MUTED)
    sx = (x1-x0-110) / spec['length']
    sy = sx
    ground_y = y0+330
    project = lambda p: (x0+55+p[0]*sx, ground_y+p[1]*sy)
    pts = [project(p) for p in spec['surface']]
    d.polygon(pts+[(pts[-1][0],ground_y+45),(pts[0][0],ground_y+45)],fill='#D8C4A0')
    d.line(pts,fill=GREEN,width=6)
    if spec['branch']:
        bp = [project(p) for p in spec['branch']['surface']]
        d.polygon(bp+[(x,y+10) for x,y in reversed(bp)],fill='#B7A28D')
        d.line(bp,fill=GREEN,width=5)
        for xp in (18,26):
            a = project((xp,at_y(spec['branch']['surface'],xp)+.4))
            b = project((xp,at_y(spec['surface'],xp)))
            d.line([a,b],fill='#B7A28D',width=8)
        text(d,(x0+300,y0+165),'较长纸桥 · 跨路射程待测',21,MUTED)
    # Label lanes are separated by kind and leader lines, never placed over the floor.
    labelled_x = set()
    for anchor in spec['anchors']:
        x,y = project((anchor['x'],at_y(spec['surface'],anchor['x'])))
        symbol(d,(x,y),anchor['kind'],anchor.get('owner'))
        bottom = anchor['kind'] in ('mine','merge','goal')
        label_y = ground_y+68 if bottom else y0+(240 if anchor['kind'] in ('site','escort_target') else 207)
        label = anchor['label']
        tw = d.textlength(label,font=font(20))
        tx = max(x0+22,min(x-tw/2,x1-tw-22))
        leader_end = label_y-5 if bottom else label_y+28
        d.line([(x,y+15 if bottom else y-45),(x,leader_end)],fill=LINE,width=2)
        label_color = RED if anchor.get('owner') == 1 or anchor['kind']=='failure_line' else BLUE if anchor.get('owner') == 0 else MUTED
        text(d,(tx,label_y),label,20,label_color)
        if anchor['x'] not in labelled_x:
            text(d,(x-9,ground_y+32),f"{anchor['x']:g}",16,MUTED)
            labelled_x.add(anchor['x'])
    if spec['id']=='W05':
        arrow(d,project((34,-2)),project((12,-2)),RED,4)
    if spec['id']=='W06':
        arrow(d,project((11,-2.5)),project((42,-2.5)),BLUE,4)
    d.line([(x0+28,y0+440),(x1-28,y0+440)],fill=LINE,width=2)
    yy = paragraph(d,(x0+28,y0+456),'A  '+spec['plans'][0],23,x1-x0-56)
    yy = paragraph(d,(x0+28,yy+7),'B  '+spec['plans'][1],23,x1-x0-56)
    paragraph(d,(x0+28,yy+12),'代价 / 收益：'+spec['tradeoff'],21,x1-x0-56,MUTED)


def whitebox_figure(specs):
    im = Image.new('RGB',(2280,2210),BG)
    d = ImageDraw.Draw(im)
    text(d,(60,38),'让位置改变决策：六类手工地图白盒',48)
    text(d,(60,112),'《纸上兵戈》原创研究规格 · 未接入 / 未游玩验收 · 非原作关卡复刻',26,RED)
    text(d,(60,157),'侧视坐标保持 X / Y 同尺度；符号与地表为研究示意，最终美术另行制作。',23,MUTED)
    text(d,(60,192),'蓝：己方    红：敌方 / 失败线    金：矿    方框：可建位置    数字：世界 X',20,MUTED)
    for i,spec in enumerate(specs):
        x=60+(i%2)*1090
        y=220+(i//2)*635
        draw_whitebox(d,spec,(x,y,x+1060,y+610))
    text(d,(60,2140),'优先 W01 → W02 → W03；修复运输与容量后，验证两种计划及实际交互，再接入美术。',25,INK)
    im.save(OUT/'whitebox-archetypes.png')


def current_layout(d,m,box):
    x0,y0,x1,y1=box
    text(d,(x0,y0),m['id'],21,MUTED)
    left=x0+170
    sx=(x1-left-20)/m['length']
    edges={e['id']:e for e in m['edges']}
    for e in m['edges']:
        points=[(left+p[0]*sx,y0+30+p[1]*10) for p in e['points']]
        d.line(points,fill=GREEN if e['id']!='bridge' else MUTED,width=3)
    for a in m['mines']:
        edge=edges[a['edge']]
        # Arc interpolation, consistent with runtime anchors.
        remain=a['s']
        p=edge['points'][0]
        for start,end in zip(edge['points'],edge['points'][1:]):
            length=math.dist(start,end)
            if remain<=length:
                t=remain/length
                p=[start[0]+t*(end[0]-start[0]),start[1]+t*(end[1]-start[1])]
                break
            remain-=length
        x,y=left+p[0]*sx,y0+30+p[1]*10
        d.ellipse((x-5,y-5,x+5,y+5),fill=GOLD)


def overview(audit,probe,maps):
    im=Image.new('RGB',(1800,1680),BG)
    d=ImageDraw.Draw(im)
    text(d,(64,34),'《剑与勇士 / HD》地图设计：重新研究',48)
    text(d,(64,112),'2026-10-08 · 原作资料重读 + 当前工作区审计 + 原生 Godot 测量',25,MUTED)
    counts=[('200','地图配置','几何不同 ≠ 战术验收'),('2','锚定布置模板','180 / 20 图共享安排'),('49','原生研究夹具','36 经济 + 10 路线 + 3 接战'),('P0','外矿端点循环','真实收入选择被破坏')]
    for i,(n,label,note) in enumerate(counts):
        x=64+i*423
        panel(d,(x,178,x+400,344))
        text(d,(x+25,190),n,52,RED if i==3 else BLUE)
        text(d,(x+25,259),label,27)
        text(d,(x+25,302),note,21,MUTED)
    panel(d,(64,388,1736,703))
    text(d,(94,409),'原作地图的五层关系',33)
    layers=[('地表','实体地面与足点\n坡面 / 局部分岔'),('经济','矿点与运输\n暴露 / 投入 / 回款'),('交战','设施位置与覆盖\n到达先后 / 增援等待'),('任务','保护 / 截击 / 限兵\n对象与位置窗口'),('阅读','局部镜头与全图导航\n地标 / 点击反馈')]
    for i,(title,desc) in enumerate(layers):
        x=94+i*326
        d.rounded_rectangle((x,467,x+292,643),14,fill='#EEEFE7')
        text(d,(x+20,480),title,32,BLUE)
        paragraph(d,(x+20,535),desc,23,256)
        if i<4:arrow(d,(x+298,555),(x+320,555),MUTED,3)
    text(d,(94,661),'依据开发者与官方资料归纳；不是每关固定布局，也不要求每图都有分岔。',22,MUTED)
    panel(d,(64,742,909,1138))
    text(d,(94,766),'当前布局：变化需要设计依据',31)
    text(d,(94,818),'横向归一化，纵向示意；金点为矿，非游戏画面。',21,MUTED)
    lookup={m['id']:m for m in maps}
    for i,key in enumerate(('map.01.01','map.01.04','map.01.09','map.01.20')):
        current_layout(d,lookup[key],(94,861+i*55,880,906+i*55))
    text(d,(94,1098),'150 单线 / 50 岔路；两种 decision、一种 alternative。',22,MUTED)
    panel(d,(940,742,1736,1138))
    text(d,(970,766),'运输实测：不能以首次回款放行',31)
    text(d,(970,818),'map.01.01 · 左方单工人 · 无 AI · 120 秒',22,MUTED)
    for i,(priority,label,color) in enumerate((('near','近矿',BLUE),('outer','外矿',RED))):
        row=next(v for v in probe['economics'] if v['map']=='map.01.01' and v['side']==0 and v['worker_count']==1 and v['priority']==priority)
        y=875+i*85
        text(d,(970,y-4),label,26)
        x=1060
        d.rounded_rectangle((x,y,x+row['gold_delivered']*3.1,y+42),8,fill=color)
        text(d,(x+row['gold_delivered']*3.1+13,y-3),f"{row['gold_delivered']} 金",27,color)
    text(d,(970,1046),'外矿每 30 秒：11 / 0 / 0 / 0 金',25,RED)
    text(d,(970,1098),'一次成功往返后，next_edge 仍是所在边。',22,MUTED)
    panel(d,(64,1180,1736,1574))
    text(d,(94,1203),'新的制作顺序：修运输与容量 → 三张手工基准图 → 交互 / 美术',32)
    cards=[('W01 归金坡','对推与矿区反扑','先发展，还是先压制？'),('W02 前哨外矿','扩张的回本与暴露','增加吞吐，能否守住？'),('W03 灯台长坡','设施积累与长途增援','慢兵等待，快压抢窗口。')]
    for i,(name,what,q) in enumerate(cards):
        x=94+i*539
        d.rounded_rectangle((x,1283,x+510,1466),14,fill='#EEEFE7')
        text(d,(x+20,1302),name,30,BLUE)
        text(d,(x+20,1361),what,25)
        text(d,(x+20,1411),q,23,MUTED)
    text(d,(94,1507),'六类白盒均为原创待测规格；地图验收 = 规则日志 + 真正操作 + 正常战斗画面。',25)
    text(d,(64,1602),'本轮未运行原作 PC，也未重建交付包。原作精确数值与 PC 路标权限保留待补证。',24,RED)
    text(d,(64,1642),'来源与测量条件见同目录报告、sources.json、current-map-audit.json 和 native-probes.json。',21,MUTED)
    im.save(OUT/'research-overview.png')


def screenshot_comparison():
    im=Image.new('RGB',(1800,1340),BG)
    d=ImageDraw.Draw(im)
    text(d,(60,35),'地表阅读：原作已有画面与本作已交付画面',44)
    text(d,(60,109),'界面状态不同：这里只比较地表与地点阅读，不计算 HUD 占屏率。',25,RED)
    refs=[(ROOT/'docs/reference/hd-vikings-tech-tree.png','原作 PC HD · 科技面板打开','R08 / MobyGames 503975'),(ROOT/'output/qa/godot/v2/export/battle.png','《纸上兵戈》2.0 · 已交付战斗画面','L01 / 本地导出运行截图')]
    for i,(path,title,source) in enumerate(refs):
        y=177+i*528
        panel(d,(60,y,1740,y+512))
        text(d,(87,y+14),title,29)
        text(d,(87,y+58),source,20,MUTED)
        shot=Image.open(path).convert('RGB')
        shot.thumbnail((742,418),Image.Resampling.LANCZOS)
        im.paste(shot,(87,y+90))
        text(d,(880,y+94),'直接观察',29,BLUE)
        items=(['连续实体地表切面与草边。','坡面、基地与经济区处于同一土地上。','底部横向导航与视窗框。','这张图没有展示完整原作地图。'] if i==0 else ['地面主要呈现为悬在背景上的线段。','矿洞、路标与多条道路挤在一起。','单位互相遮挡，背景与对象竞争。','这是 2.0，不能冒充修改后画面。'])
        yy=y+150
        for n,item in enumerate(items,1):
            yy=paragraph(d,(880,yy),f'{n}.  {item}',24,790)+18
    text(d,(60,1260),'重做要求：先让土地、矿、设施、单位和目标的位置关系清楚，再加入纸艺材质和特效。',25)
    text(d,(60,1300),'原作截图仅用于研究；保持原始文件，不进入生产素材库。',22,MUTED)
    im.save(OUT/'reference-vs-delivered.png')


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    read=lambda name:json.loads((REPORT/name).read_text(encoding='utf-8'))
    specs=read('whitebox-specs.json')['maps']
    assert len(specs)==6
    whitebox_figure(specs)
    overview(read('current-map-audit.json'),read('native-probes.json'),json.loads((ROOT/'game/data/maps.json').read_text(encoding='utf-8'))['maps'])
    screenshot_comparison()
    print(json.dumps({p.name:{'size':Image.open(p).size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(OUT.glob('*.png'))},ensure_ascii=False))


if __name__=='__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main()
