"""Twenty authored stage briefs × ten regional spatial profiles; keep six baseline maps intact."""
from __future__ import annotations
from pathlib import Path
import copy
import json
import sys
from author_baseline_maps import make, placement, read, save

ROOT=Path(__file__).resolve().parents[2]
EVIDENCE=ROOT/'docs/paper-warfront/redesign-3.0'
PROFILES={
 'yin':dict(length=0,near=4,front=.36,bridge=4.0,soil='#AC8D68',reason='重甲集结需要短回款与明确的前哨线。'),
 'mo':dict(length=1,near=5,front=.39,bridge=3.6,soil='#97857D',reason='矿线离纸城更远，复兵祭司要随军抵达实际阵亡位置。'),
 'deng':dict(length=4,near=4.5,front=.33,bridge=4.2,soil='#91A494',reason='较长战线给纸灯投资留出时间，前位灯仍须军团保护。'),
 'ji':dict(length=2,near=5.5,front=.40,bridge=3.8,soil='#B79472',reason='较靠前的设施让完工回法与设施支援必须付出施工风险。'),
 'yuan':dict(length=2,near=6,front=.37,bridge=3.2,soil='#A89879',reason='矿线与岔口分开，经过路口的回法需要实际行军。'),
 'qi':dict(length=0,near=4.2,front=.38,bridge=3.4,soil='#B49C6D',reason='短近矿回款与长外矿护运形成真实归仓节奏。'),
 'mu':dict(length=1,near=5,front=.42,bridge=4.1,soil='#89946B',reason='靠前的保护位置让修复部队必须承受交战与腐蚀。'),
 'shuang':dict(length=3,near=6,front=.34,bridge=4.8,soil='#A0BCC2',reason='长回款线与较高纸桥要求控制敌军并守住接近段。'),
 'jin':dict(length=-2,near=4.8,front=.44,bridge=3.7,soil='#AE8A75',reason='短战线和前置塔位提前形成交战，受伤回法只来自真实敌伤。'),
 'bai':dict(length=3,near=5.2,front=.38,bridge=4.4,soil='#AAA49F',reason='增援较长，研究回法需与即时出兵竞争同一预算。'),
}
# Lengths, economy patterns and defenses are chosen per stage, not random height noise.
STAGES=[
 dict(stage=1,name='归金坡',kind='close',length=38,hill=1.2,economy='near',sites='rear_front',question='多造一名工人，还是让下一批前排先抵达？',plans=['增工守矿','双兵种抢先推进']),
 dict(stage=2,name='外矿岔',kind='outer',length=42,hill=.8,economy='outer',sites='outer',question='窄近矿已经排队，是否带护卫扩到外矿？',plans=['近矿维持小军团','增工并护送外矿运输']),
 dict(stage=3,name='前哨坡',kind='protect',length=42,hill=1.5,economy='near',sites='protect',question='在城边集合，还是把护卫与修复预算送到指定前哨？',plans=['前置护卫守塔','后方补兵加手动救援']),
 dict(stage=4,name='纸桥岔',kind='bridge',length=44,hill=0,economy='near',sites='fork',question='主路阵地正在蓄力，下一批军团走主路还是较长的纸桥？',plans=['正面破阵','切路绕行再汇流']),
 dict(stage=5,name='金车线',kind='outer',length=46,hill=1.3,economy='outer',sites='outer',question='归仓目标尚未完成，预算用于更多运金还是更安全的矿线？',plans=['快速扩工','塔与护卫先保回款']),
 dict(stage=6,name='守签路',kind='escort',length=48,hill=1.4,economy='near',sites='escort',question='护卫先清第一处伏兵，还是为接力防护位保留预算？',plans=['快兵先行清路','建塔与救援接力']),
 dict(stage=7,name='争矿埠',kind='outer',length=44,hill=.6,economy='finite_outer',sites='outer',question='有限外矿的早期收入，能否在枯竭前转成前线优势？',plans=['抢采外矿推进','留工近矿稳守']),
 dict(stage=8,name='长援岭',kind='long',length=54,hill=2.0,economy='near',sites='rear_front',question='援军仍在长坡上，怎样用塔、控制或修复熬过缺口？',plans=['提前守前位','保住纸城等下一批']),
 dict(stage=9,name='桥矿汇',kind='bridge_mine',length=48,hill=.4,economy='bridge',sites='fork',question='运输线在纸桥上，选路能兼顾护矿和攻城吗？',plans=['走桥护运','走主路抢汇流']),
 dict(stage=10,name='护运页',kind='escort',length=50,hill=1.0,economy='outer',sites='escort',question='金矿与携证者同时需要护卫，先护住哪一段？',plans=['维持少量工人与前护卫','扩经济建接力塔']),
 dict(stage=11,name='灯台岭',kind='long',length=56,hill=2.6,economy='near',sites='rear_front',question='长坡让重兵迟到，先投资法力还是持续招募快兵？',plans=['灯或回法研究换施法','快兵压制投资窗口']),
 dict(stage=12,name='矿线阻',kind='intercept',length=44,hill=1.0,economy='near',sites='intercept',question='指定巨兵正向矿线推进，在哪一段集中伤害与控制？',plans=['早期伤害阻击','前塔拖延再补控制']),
 dict(stage=13,name='三矿埠',kind='outer',length=50,hill=1.4,economy='triple',sites='outer',question='三处矿点有不同周转时间，新增工人投入哪个瓶颈？',plans=['先饱和近矿','分担外矿服务队列']),
 dict(stage=14,name='截巨岔',kind='intercept',length=48,hill=.7,economy='near',sites='intercept',question='巨兵走主路，绕行的援军能否及时在矿线前汇合？',plans=['主路早接战','切桥攻击随后汇流']),
 dict(stage=15,name='护印台',kind='protect',length=48,hill=1.8,economy='outer',sites='protect',question='指定塔位靠近外矿，先保工人还是保前哨生命？',plans=['前排与治疗守塔','经济换持续增援']),
 dict(stage=16,name='双路渡',kind='escort',length=48,hill=0,economy='near',sites='escort',question='携证者尚未过岔口，护卫与它应走哪条路？',plans=['主路护送','改纸桥绕行并守汇流']),
 dict(stage=17,name='高折原',kind='long',length=56,hill=3.0,economy='near',sites='rear_front',question='两段坡折拉长运输与射程接近，怎样衔接前后两批军团？',plans=['快兵衔接空档','等重兵并保留控制']),
 dict(stage=18,name='围灯阵',kind='protect',length=50,hill=1.2,economy='bridge',sites='protect',question='纸桥矿线与指定前哨分开，护卫应如何分配？',plans=['主路保护指定塔','纸桥护运再返汇流']),
 dict(stage=19,name='反攻页',kind='survive',length=52,hill=1.6,economy='outer',sites='rear_front',question='晚段敌军入口改变，继续压前线还是回守矿路？',plans=['压制后方供兵','回守前哨与近矿']),
 dict(stage=20,name='合印门',kind='finale',length=56,hill=1.5,economy='outer',sites='fork',question='收官预算在矿线、纸桥与重兵之间，先争取哪一个窗口？',plans=['正面军团配施法','纸桥护矿后集中攻城']),
]

def assemble(old,stage,profile):
    length=stage['length']+profile['length'];left,right=2,length-2
    near=left+profile['near'];away=right-profile['near']
    fork=round(length*.32,2);merge=round(length*.68,2)
    hill=stage['hill'];mid=length*.5
    surface=[[left,0],[near,0],[fork,-hill*.65],[mid,-hill],[merge,-hill*.55],[away,0],[right,0]]
    if stage['stage']==17:surface=[[left,0],[near,0],[fork,-hill],[mid,-hill*.42],[merge,-hill*.92],[away,0],[right,0]]
    spec={k:copy.deepcopy(stage[k]) for k in ['name','question','plans']}
    spec.update(id='stage.%02d'%stage['stage'],length=length,surface=surface,anchors=[],tradeoff='塔、研究与招募共享金币；矿金在真实运回纸城后入账。'+profile['reason'],measure=['归仓时间','前哨受击','增援到达','任务对象位置'],first_30_seconds='观察第一轮归仓与下一批援军；任务地图明确标出指定对象和边界。',enemy_response='对手使用公开资源、所选军团与同一指令接口，根据矿线、前哨和路线压力调整。')
    has_bridge=stage['kind'] in ['bridge','bridge_mine','finale'] or stage['stage'] in [14,16,18]
    if has_bridge:
        spec['branch']=dict(surface=[[fork,surface[2][1]],[fork+3,-hill-profile['bridge']*.55],[mid,-hill-profile['bridge']],[merge-3,-hill-profile['bridge']*.55],[merge,surface[-3][1]]])
    outer=stage['economy'] in ['outer','finite_outer','triple','bridge']
    for side,x in [(0,near),(1,away)]:
        spec['anchors'].append(dict(kind='mine',owner=side,label='近矿',x=x,service_capacity=1 if outer else 3))
    if outer:
        for side,x in [(0,fork+1.6),(1,merge-1.6)]:spec['anchors'].append(dict(kind='mine',owner=side,label='桥矿' if stage['economy']=='bridge' else '外矿',x=x,service_capacity=2))
    if stage['economy']=='triple':
        for side,x in [(0,mid-3.8),(1,mid+3.8)]:spec['anchors'].append(dict(kind='mine',owner=side,label='争矿',x=x,service_capacity=1))
    site_mode=stage['sites']
    for side in [0,1]:
        rear=left+2 if side==0 else right-2
        front=round(length*profile['front'],2) if side==0 else round(length*(1-profile['front']),2)
        if site_mode in ['rear_front','protect']:
            spec['anchors'].append(dict(kind='site',owner=side,label='后灯位',x=rear,functions=['mana']))
            spec['anchors'].append(dict(kind='site',owner=side,label='保护前哨' if site_mode=='protect' and side==0 else '前哨位',x=front,functions=['tower']))
        elif site_mode=='escort':
            if side==0:spec['anchors'].append(dict(kind='site',owner=side,label='接力防护',x=round(length*.47,2),functions=['tower']))
        else:
            x=fork if side==0 else merge
            spec['anchors'].append(dict(kind='site',owner=side,label='矿线塔' if site_mode=='intercept' else '前哨位',x=x,functions=['tower','mana'] if old['region']=='ji' else ['tower']))
    m=make(old,spec,[left,near,fork,merge,away,right]);m['name']=old['name'].split('·')[0]+'·'+stage['name']
    m['presentation']['terrain_color']=profile['soil'];m['lesson']=stage['question'];m['regional_rule']=profile['reason']
    for mine in m['mines']:
        if mine['label']=='近矿':mine['mine_seconds']=4.0 if outer else 1.05
        else:mine['mine_seconds']=1.6;mine['resource']=320 if stage['economy']=='finite_outer' else -1
        if mine['label']=='桥矿':mine.update(placement([m['edges'][-1]],mine['x']))
    # make() hashed before changing real mining service / branch anchors.
    import hashlib
    m['geometry_sha256']=hashlib.sha256(json.dumps({k:m[k] for k in ['length','nodes','edges','mines','build_sites']},sort_keys=True).encode()).hexdigest()
    return m

def main():
    sys.stdout.reconfigure(encoding='utf-8');maps=read('maps.json');campaign=read('campaign.json');factions={f['id']:f for f in read('factions.json')['factions']};balance=read('balance-prototype.json')
    baseline=set(read('theatre-baseline-maps.json')['maps']);index={m['id']:i for i,m in enumerate(maps['maps'])};rows=[]
    for level in campaign['levels']:
        if level['map'] in baseline:continue
        old=maps['maps'][index[level['map']]];stage=STAGES[int(level['map'].split('.')[-1])-1];profile=PROFILES[old['region']]
        m=assemble(old,stage,profile);maps['maps'][index[m['id']]]=m
        level.update(title=m['name'],map_brief=m['decision'],objective_anchor=m['objective_anchor'],production_limit=len(level['default_roster'])+1)
        if stage['kind']=='bridge' or stage['kind']=='finale':
            enemy=factions[level['enemy']];defender=enemy['core_roster'][0]
            level['opening_forces']=[dict(id=defender,side=1,stationary=True,label='主路守卫',**placement(m['edges'][:5],m['length']*.5))]
            # Preplaced defenders still pay the regular gold cost.
            level['enemy_starting_gold']=max(level['enemy_starting_gold'],balance['units'][defender]['gold']+95)
        if level['win']=='protect':level['protect_slot']=1
        elif level['win']=='intercept':
            level['objective_anchor']=dict(m['mines'][0]);level.update(intercept_start_x=m['length']-8,intercept_hp=420,intercept_speed=.5)
        elif level['win']=='escort':
            level.update(escort_id=factions[level['faction']]['core_roster'][0],escort_start_x=6,escort_hp=600,escort_speed=.48)
            level['objective_anchor']=placement(m['edges'][:5],m['length']-6)
            level['enemy_entries']=[dict(label='前段伏兵',unlock_time=14,**placement(m['edges'][:5],round(m['length']*.64,2))),dict(label='后段伏兵',unlock_time=72,**placement(m['edges'][:5],m['length']-3))]
        if stage['kind']=='survive':level['enemy_entries']=[dict(label='晚段入口',unlock_time=55,**placement(m['edges'][:5],round(m['length']*.72,2)))]
        road=m['route_lengths'];travel='全线步程 %.1f；纸桥增加 %.1f 步。'%(road['shortest'],road['longest']-road['shortest']) if len(m['edges'])>5 else '全线步程 %.1f。'%road['shortest']
        level['tip']=stage['question']+' 可选：'+'；'.join(stage['plans'])+'。'+travel+'坡面无隐藏伤害加成。'
        for line in level['story_before']:
            if line['speaker']=='战地纸签':line['text']=level['tip']+' '+profile['reason']
        rows.append(dict(map=m['id'],campaign=level['id'],stage=stage['stage'],kind=stage['kind'],economy=stage['economy'],sites=stage['sites'],length=m['length'],bridge=len(m['edges'])>5,objective=level['win'],geometry_sha256=m['geometry_sha256']))
    save('maps.json',maps);save('campaign.json',campaign)
    EVIDENCE.mkdir(parents=True,exist_ok=True)
    write=lambda path,data:path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    write(EVIDENCE/'campaign-map-plan.json',dict(stages=STAGES,regional_profiles=PROFILES,preserved_baselines=sorted(baseline),implemented=rows,scope='Twenty explicit stage briefs applied to ten mechanical regional profiles, plus six individually authored baseline maps. This is not a claim of 200 independently hand-playtested maps.'))
    print(json.dumps(dict(updated=len(rows),preserved_baselines=len(baseline),maps=len(maps['maps']),distinct_geometry=len({m['geometry_sha256'] for m in maps['maps']})),ensure_ascii=False))

if __name__=='__main__':main()
