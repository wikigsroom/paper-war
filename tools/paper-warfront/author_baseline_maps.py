"""Integrate six explicitly authored theatre maps; preserve all other map/story IDs."""
from __future__ import annotations
import copy
import hashlib
import json
import math
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
DATA=ROOT/'game/data'
SPEC=ROOT/'docs/research/swords-and-soldiers-map/recheck-20261008/whitebox-specs.json'


def read(name):return json.loads((DATA/name).read_text(encoding='utf-8'))
def save(name,value):(DATA/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


def y_at(points,x):
    for a,b in zip(points,points[1:]):
        if a[0]<=x<=b[0]:return a[1]+(b[1]-a[1])*(x-a[0])/(b[0]-a[0])
    raise ValueError(x)


def placement(edges,x):
    for e in edges:
        if e['points'][0][0]<=x<=e['points'][-1][0]:
            distance=0.0
            for a,b in zip(e['points'],e['points'][1:]):
                if x<=b[0]:
                    point=[x,y_at([a,b],x)]
                    distance+=math.dist(a,point)
                    return {'edge':e['id'],'s':round(distance,6),'x':x,'y':round(point[1],6)}
                distance+=math.dist(a,b)
    raise ValueError(x)


def make(old,spec,node_xs):
    m=copy.deepcopy(old)
    node_ids=['west','home','fork','merge','away','east']
    nodes=[{'id':key,'position':[x,y_at(spec['surface'],x)]} for key,x in zip(node_ids,node_xs)]
    edges=[]
    for i in range(5):
        start,end=node_xs[i:i+2]
        points=[[start,y_at(spec['surface'],start)]]+[p for p in spec['surface'] if start<p[0]<end]+[[end,y_at(spec['surface'],end)]]
        edges.append({'id':f'ground.{i}','from':node_ids[i],'to':node_ids[i+1],'points':points,'route_role':'ground'})
    if spec.get('branch'):
        branch=spec['branch']
        edges.append({'id':'bridge','from':'fork','to':'merge','points':branch['surface'],'route_role':'bridge','label':'纸桥绕行'})
    mines=[];sites=[]
    for a in spec['anchors']:
        if a['kind']=='mine':
            side=a['owner'];index=sum(p['owner']==side for p in mines)
            # Real service saturation, rather than an arbitrary assignment cap.
            slow_near=spec['id']=='W02' and a['label']=='近矿'
            mines.append({'id':f'mine.{side}.{index}','owner':side,'label':a['label'],'capacity':a['service_capacity'],'capacity_meaning':'simultaneous_mining','cargo_bonus':0,'mine_seconds':4.0 if slow_near else 1.6 if spec['id']=='W02' else 1.05,'resource':-1,**placement(edges,a['x'])})
        elif a['kind']=='site':
            side=a['owner'];index=sum(p['owner']==side for p in sites)
            sites.append({'id':f'site.{side}.{index}','owner':side,'label':a['label'],'types':a['functions'],**placement(edges,a['x'])})
    mines.sort(key=lambda mine:(mine['owner'],abs(mine['x']-node_xs[0 if mine['owner']==0 else -1])))
    for side in [0,1]:
        for index,mine in enumerate(p for p in mines if p['owner']==side):mine['id']=f'mine.{side}.{index}'
    # Mission maps still give the regular opponent a working rear economy.
    if not any(mine['owner']==1 for mine in mines):
        x=node_xs[-2]
        mines.append({'id':'mine.1.0','owner':1,'label':'后方矿','capacity':3,'capacity_meaning':'simultaneous_mining','cargo_bonus':0,'mine_seconds':1.05,'resource':-1,**placement(edges,x)})
    if spec['id'] in ['W04','W05']:
        for side,x in [(0,node_xs[2]),(1,node_xs[3])]:
            sites.append({'id':f'site.{side}.0','owner':side,'label':'前哨位','types':['tower'],**placement(edges,x)})
    distance=sum(sum(math.dist(a,b) for a,b in zip(e['points'],e['points'][1:])) for e in edges[:5])
    longest=distance
    if spec.get('branch'):
        longest=distance-sum(math.dist(a,b) for a,b in zip(edges[2]['points'],edges[2]['points'][1:]))+sum(math.dist(a,b) for a,b in zip(edges[-1]['points'],edges[-1]['points'][1:]))
    m.update(name='朱印疆·'+spec['name'],length=spec['length'],nodes=nodes,edges=edges,mines=mines,build_sites=sites,
             bases=[{'node':'west','owner':0},{'node':'east','owner':1}],objective_anchor=placement(edges,node_xs[-1]-1),
             route_lengths={'shortest':round(distance,4),'longest':round(longest,4)},decision=spec['question']+' '+spec['tradeoff'],
             alternative='；'.join(spec['plans']),design_card={k:spec[k] for k in ['id','name','question','plans','tradeoff','measure','first_30_seconds','enemy_response']})
    m['presentation'].update(style='paper-theatre',archetype=spec['name'],ground_edges=[e['id'] for e in edges[:5]],forks=1 if spec.get('branch') else 0,terrain_color='#AC8D68',landmark=spec['name'])
    m['geometry_sha256']=hashlib.sha256(json.dumps({k:m[k] for k in ['length','nodes','edges','mines','build_sites']},sort_keys=True).encode()).hexdigest()
    return m


def main():
    maps=read('maps.json');campaign=read('campaign.json')
    specs=json.loads(SPEC.read_text(encoding='utf-8'))['maps']
    targets=[('map.01.01',[2,6,12,30,36,40]),('map.01.07',[2,6,17,29,40,44]),('map.01.11',[2,7,21,37,51,56]),('map.01.04',[2,6,14,30,38,42]),('map.01.12',[2,9,16,29,38,42]),('map.01.06',[2,9,18,33,43,48])]
    story=[
        ('归金坡','第一批纸工踏着归金坡回城，赤砚决定把散兵编成能护住矿路的队伍。','金币只有运回纸城才入账。前排护住远程；对手投入经济时，可以抢先压制。','赤砚守住了矿路，也看见攻到敌矿的军团被反扑打散。每一步推进都需要下一批援军。'),
        ('前哨外矿','近矿的窄洞容不下更多纸工，另一座金矿却在双方哨线之间。','近矿采集较慢；增加工人时观察排队。外矿能扩张收入，先给运输线准备护卫。','外矿的金车回到了纸城。赤砚在账页上添了一句：赚到的钱，必须有人护送。'),
        ('灯台长坡','长坡把纸城与前哨隔开，敌军的灯台在安静积攒法力。','炮车和重兵增援较慢。快兵可争取投资窗口，控制法术则能等来援军。','前哨灯台亮了起来。赤砚学会在施法与增援之间，给整支军团争取时间。'),
        ('纸桥岔口','纸桥架在主路阵地上方，下一批军团要在岔口决定去向。','主路增援较快；纸桥绕开地面近战，弓矛仍能打到两端。改路标只影响尚未通过的军团。','赤砚看着两批纸军先后汇流，记住了绕行付出的时间。'),
        ('矿线阻击','一尊覆写巨兵正向归金矿推进，若越过矿线，账页便会被撕去。','画面和战线图标出矿线与指定巨兵。先打出伤害，也要留法力或锤击延长阻击时间。','覆写巨兵在矿线前碎成纸屑。赤砚把截击位置与施法时机留在战图上。'),
        ('守签接力','携证者从后方矿路出发，沿途两处伏兵入口已经被标在地图上。','护卫比携证者走得快；中途塔位可掩护下一段。救援法术与早期建造共同争用预算。','携证者抵达交接点，带回了完整的账页，也带回一路守护它的名字。')]
    authored={}
    for spec,(map_id,xs),copytext in zip(specs,targets,story):
        index=next(i for i,m in enumerate(maps['maps']) if m['id']==map_id)
        maps['maps'][index]=make(maps['maps'][index],spec,xs)
        authored[map_id]=maps['maps'][index]
        for level in campaign['levels']:
            if level['map']!=map_id:continue
            level.update(title='朱印疆·'+copytext[0],line=copytext[1],tip=copytext[2],map_brief=spec['question']+' '+spec['tradeoff'],
                         story_before=[{'speaker':'赤砚','text':copytext[1]},{'speaker':'战地纸签','text':copytext[2]}],
                         story_after=[{'speaker':'赤砚','text':copytext[3]}],objective_anchor=authored[map_id]['objective_anchor'])
            if spec['id']=='W01':
                level['default_roster']=['unit.yin.axe','unit.yin.spear','unit.yin.hammer']
                level['starting_gold']=190;level['enemy_starting_gold']=160;level['ai_army_limit']=12
                level['ai_warmup']=6
            elif spec['id']=='W02':
                level['default_roster']=['unit.yin.axe','unit.yin.spear','unit.yin.cannon']
                level['enemy_roster']=['unit.mo.raider','unit.mo.needle','unit.mo.giant']
                level['starting_gold']=230;level['enemy_starting_gold']=210
            elif spec['id']=='W03':
                level['enemy']='deng';level['enemy_roster']=['unit.deng.mirror','unit.deng.fire','unit.deng.shadow','unit.deng.guard']
                level['enemy_unlocked']=['unit.deng.mirror','unit.deng.fire'];level['ai_style']='economy'
                level['starting_gold']=230;level['enemy_starting_gold']=230
            elif spec['id']=='W04':
                level.update(default_roster=['unit.yin.axe','unit.yin.spear','unit.yin.hammer'],starting_gold=230,enemy_starting_gold=260)
                level['opening_forces']=[dict(id='unit.mo.giant',side=1,stationary=True,label='主路守卫',**placement(authored[map_id]['edges'],22))]
            elif spec['id']=='W05':
                level.update(default_roster=['unit.yin.axe','unit.yin.spear','unit.yin.hammer'],intercept_start_x=36,intercept_hp=420,intercept_speed=.5,starting_gold=230,enemy_starting_gold=150,ai_army_limit=8)
                level['objective_anchor']=placement(authored[map_id]['edges'],9)
            elif spec['id']=='W06':
                level.update(default_roster=['unit.yin.axe','unit.yin.spear','unit.yin.hammer'],escort_id='unit.yin.axe',escort_start_x=6,escort_hp=470,escort_speed=.45,starting_gold=230,enemy_starting_gold=190,ai_army_limit=10,ai_warmup=5)
                level['objective_anchor']=placement(authored[map_id]['edges'],44)
                level['enemy_entries']=[dict(label='前段伏兵',unlock_time=16,**placement(authored[map_id]['edges'],33)),dict(label='后段伏兵',unlock_time=70,**placement(authored[map_id]['edges'],47))]
    save('maps.json',maps);save('campaign.json',campaign)
    save('theatre-baseline-maps.json',{'schema_version':1,'status':'implemented_pending_native_and_visual_acceptance','maps':list(authored),'source_spec':str(SPEC.relative_to(ROOT)).replace('\\','/'),'economic_adjustment':'W02 near mining time 4s, outer 1.6s, same 8 gold cargo; assignment estimates real service throughput and travel, capacity is simultaneous mining.'})
    print(json.dumps({'authored':list(authored),'preserved_map_entries':len(maps['maps']),'preserved_campaign_entries':len(campaign['levels'])},ensure_ascii=False))


if __name__=='__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main()
