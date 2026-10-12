"""Apply explicit map stories and authored chapter graphs to the frozen rc28 data.

Dialogue lives in story-chapters/*.psv. This tool never generates dialogue from
templates and never changes a map, roster, combat rule, objective or economy.
"""
from pathlib import Path
import hashlib
import itertools
import json

ROOT = Path(__file__).resolve().parents[2]
QA = ROOT / 'output/qa/godot/story-atlas-rc29'
BASE = QA / 'pre-adoption/game/data'
read = lambda p: json.loads(p.read_text('utf-8'))
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()

# (parallel pages, condition to leave this layer). "all" means every actual
# victory is required; "any" leaves the companions optional and revisitable.
LAYERS = [
 [([1],'all'),([2,3],'any'),([4],'all'),([5,6],'any'),([7],'all'),([8,9],'any'),([10],'all'),([11,12],'any'),([13],'all'),([14,15],'any'),([16],'all'),([17],'all'),([18,19],'any'),([20],'all')],
 [([1],'all'),([2,3],'all'),([4],'all'),([5,6],'any'),([7],'all'),([8,9],'all'),([10],'all'),([11,12],'all'),([13],'all'),([14,15],'any'),([16],'all'),([17],'all'),([18,19],'all'),([20],'all')],
 [([1],'all'),([2,3],'any'),([4],'all'),([5,6],'all'),([7],'all'),([8,9],'any'),([10],'all'),([11],'all'),([12],'all'),([13],'all'),([14,15],'all'),([16],'all'),([17],'all'),([18,19],'any'),([20],'all')],
 [([1],'all'),([2,3,4],'all'),([5],'all'),([6],'all'),([7],'all'),([8,9],'any'),([10],'all'),([11,12],'all'),([13],'all'),([14],'all'),([15],'all'),([16],'all'),([17],'all'),([18,19],'all'),([20],'all')],
 [([1],'all'),([2,3,4],'any'),([5],'all'),([6],'all'),([7],'all'),([8,9],'all'),([10],'all'),([11,12],'any'),([13],'all'),([14,15],'all'),([16],'all'),([17],'all'),([18],'all'),([19],'all'),([20],'all')],
 [([1],'all'),([2,3],'any'),([4],'all'),([5,6],'all'),([7],'all'),([8,9],'any'),([10],'all'),([11,12],'all'),([13],'all'),([14,15,16],'any'),([17],'all'),([18],'all'),([19],'all'),([20],'all')],
 [([1],'all'),([2,3],'all'),([4],'all'),([5,6],'all'),([7],'all'),([8,9],'any'),([10],'all'),([11,12],'any'),([13],'all'),([14,15],'all'),([16],'all'),([17],'all'),([18,19],'any'),([20],'all')],
 [([1],'all'),([2],'all'),([3],'all'),([4],'all'),([5,6],'all'),([7],'all'),([8,9],'all'),([10],'all'),([11,12],'any'),([13],'all'),([14,15,16],'all'),([17],'all'),([18,19],'all'),([20],'all')],
 [([1],'all'),([2,3],'any'),([4],'all'),([5],'all'),([6],'all'),([7],'all'),([8,9],'any'),([10],'all'),([11,12],'all'),([13],'all'),([14,15],'all'),([16],'all'),([17],'all'),([18],'all'),([19],'all'),([20],'all')],
 [([1],'all'),([2,3],'all'),([4],'all'),([5,6],'all'),([7],'all'),([8,9],'all'),([10],'all'),([11,12],'all'),([13],'all'),([14,15,16],'all'),([17],'all'),([18],'all'),([19],'all'),([20],'all')],
]
HEROES = ['赤砚','墨归','灯照','榫七','飞笺','契衡','纤枝','霜律','烬禾','白匣']
SUMMARIES = [
 '六处分支可先择一线，之后汇合。未走纸页可回访；合印门后展开第二章。',
 '活薪与埋名、投递与发运均须取证。发行戳或本人可择一；末段同时保页、送人。',
 '入口线索择一；支付与本人必须齐备。母页后拦机，末段双样齐备再送渡。',
 '材料、断齿、送料三处可任意先查，齐备后核账。拆架副本与工人撤离都要保全。',
 '运费、前哨、桥口三线择一。真实时刻两处齐备；禁递契与原符都在才送渡。',
 '收入入口择一；真支付与本人、母页与清账令须齐备。撤债实证三线可择一路。',
 '种纤账与根样、批号与本人须齐备。污染来源可择一；封根令与活纸同送渡。',
 '逐步开审，再并行取证。撤约令、共审原话、本人交付三项齐备才解冻总约。',
 '先保原名，再查归零。旧原序与删除令、原名与印头均须齐备；拒焚城并保全本人。',
 '并行复核可任选先后，关键原件须全部齐备。共阅原话、本人离城后再解除归零。',
]

def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n','utf-8')

def actor_binding(level, definition, balance):
    kind = level['win']
    if kind == 'protect':
        towers = [s for s in definition['build_sites'] if s['owner']==0 and 'tower' in s['types']]
        site = towers[min(int(level.get('protect_slot',1)), len(towers)-1)]
        return {'kind':'prebuilt_tower','id':'building.'+level['faction']+'.tower',
                'site':site['id'],'anchor':{k:site[k] for k in ['edge','s','x','y']},'duration':level['duration']}
    if kind in ['escort','intercept']:
        ident = level[kind+'_id']
        return {'kind':kind,'id':ident,'name':balance['units'][ident]['name'],
                'start_x':level[kind+'_start_x'],'hp':level[kind+'_hp'],'speed':level[kind+'_speed'],
                'anchor':level['objective_anchor'],'must_be_original_actor':True}
    if kind=='deliver_gold':
        return {'kind':'actual_gold_delivered','side':0,'amount':level['goal_gold'],'initial_gold_counts':False}
    if kind=='survive':return {'kind':'player_base_survives','side':0,'duration':level['duration']}
    return {'kind':'destroy_enemy_base','side':1,'id':'building.'+level['enemy']+'.base'}

def main():
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    assert not (QA/'authorship.json').exists(), 'Authorship receipts are immutable; archive before changing inputs'
    campaign=read(BASE/'campaign.json'); previous=read(BASE/'campaign-flow.json');narrative=read(BASE/'campaign-narrative.json')
    story=read(BASE/'story.json');maps={m['id']:m for m in read(BASE/'maps.json')['maps']};balance=read(BASE/'balance-prototype.json')
    profiles=narrative['profiles'];nodes={};chapters=[];records=[]
    for chapter, (hero,layers) in enumerate(zip(HEROES,LAYERS)):
        local=campaign['levels'][chapter*20:(chapter+1)*20]
        assert sorted(n for group,_ in layers for n in group)==list(range(1,21))
        def ident(n):return local[n-1]['id']
        prior=[campaign['levels'][chapter*20-1]['id']] if chapter else []
        prior_mode='all'
        for group, mode in layers:
            for n in group:
                level=local[n-1];nodes[level['id']]={'index':level['index'],'chapter':chapter,
                  'unlock_any':prior if prior_mode=='any' else [],'unlock_all':prior if prior_mode=='all' else [],'successors':[]}
            prior=[ident(n) for n in group];prior_mode=mode
        if chapter:
            source=Path(__file__).parent/'story-chapters'/f'{chapter+1:02}-{local[0]["faction"]}.psv'
            lines=[x for x in source.read_text('utf-8').splitlines() if x and not x.startswith('#')]
            assert len(lines)==20
            for line in lines:
                columns=line.split('|');assert len(columns)==9,(source,line)
                number,title,npc,before,dialogue,goal,geography,after,evidence=columns
                level=local[int(number)-1];assert all(columns)
                assert len(goal)<=32 and len(geography)<=65
                assert before!=after and '这一页已经留下可见的证据' not in after
                level['title']=level['title'].split('·')[0]+'·'+title;level['line']=before
                level['story_before']=[{'speaker':hero,'text':before},{'speaker':npc,'text':dialogue}]
                level['story_after']=[{'speaker':hero,'text':after}]
                profiles[level['id']]={'id':'narrative.'+level['id'],'version':1,'map':level['map'],
                  'objective':level['win'],'title':title,'goal':goal,'geography_reason':geography,
                  'evidence_name':evidence,'evidence_flag':level['story_flag'],
                  'roads':[e['id'] for e in maps[level['map']]['edges']],'objective_anchor':level['objective_anchor'],
                  'status':'authored_runtime_text_and_progression_pending_native_review'}
            records.append({'source':source.relative_to(ROOT).as_posix(),'sha256':sha(source),'maps':20})
        for level in local:
            beat=profiles[level['id']];beat['objective_binding']=actor_binding(level,maps[level['map']],balance)
            beat['portrayal']='Brief/result dialogue. Named NPCs and joint-faction story events are not additional spawned battle actors.'
        paths=[[]]
        for group,mode in layers:
            options=[list(p) for p in itertools.permutations(group)] if mode=='all' else [[n] for n in group]
            paths=[p+q for p in paths for q in options]
        chapters.append({'index':chapter,'faction':local[0]['faction'],'summary':SUMMARIES[chapter],
          'layers':[{'pages':[ident(n) for n in group],'leave_condition':mode} for group,mode in layers],
          'minimal_routes':[[ident(n) for n in path] for path in paths],
          'minimum_actual_clears':min(map(len,paths)),'maximum_minimal_clears':max(map(len,paths))})
        story['chapters'][chapter]['route_summary']=SUMMARIES[chapter]
    for ident,node in nodes.items():
        for parent in node['unlock_all']+node['unlock_any']:nodes[parent]['successors'].append(ident)
    for ident,old in previous['nodes'].items():
        if old['index']<20:
            current=nodes[ident];assert sorted(current['unlock_all']+current['unlock_any'])==sorted(old['unlock_any'])
            assert current['successors']==old['successors']
    immutable={k for level in read(BASE/'campaign.json')['levels'] for k in level}-{ 'title','line','story_before','story_after' }
    for old,new in zip(read(BASE/'campaign.json')['levels'],campaign['levels']):
        assert all(old.get(k)==new.get(k) for k in immutable),(new['id'],'battle contract changed')
    assert len(profiles)==200 and len({p['evidence_name'] for p in profiles.values()})==200
    routing={'schema_version':2,'revision':'rc29-all-chapter-story-graph-r1','root':campaign['levels'][0]['id'],
      'finale':campaign['levels'][-1]['id'],'nodes':nodes,'chapters':chapters,
      'scope':'All200 stable maps; authored causal layers with optional alternatives and actual-clear conjunctions. Battle roads are independent.'}
    narrative.update({'schema_version':2,'revision':'rc29-all-map-narrative-r1'})
    for name,value in [('campaign.json',campaign),('campaign-flow.json',routing),('campaign-narrative.json',narrative)]:
        write(ROOT/'game/data'/name,value);write(ROOT/'assets/paper-warfront'/name,value)
    write(ROOT/'game/data/story.json',story)
    write(QA/'authorship.json',{'passed':True,'authored_maps':200,'new_explicit_records':180,'records':records,
      'battle_fields_unchanged':sorted(immutable),'battlefield_json_sha256':sha(ROOT/'game/data/maps.json'),
      'chapters':[{'index':c['index'],'minimal_routes':len(c['minimal_routes']),'clears':c['minimum_actual_clears']} for c in chapters],
      'output_hashes':{name:sha(ROOT/'game/data'/name) for name in ['campaign.json','campaign-flow.json','campaign-narrative.json','story.json']},
      'scope':'Written map-specific dialogue and objective/geometry bindings. Automated authored-layer validation; not native runtime or human playthrough evidence.'})
    print('Explicit stories applied:200 maps; new records180; local minimal-route orders',sum(len(c['minimal_routes']) for c in chapters))

if __name__=='__main__':main()
