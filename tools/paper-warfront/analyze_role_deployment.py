"""Audit scoped role pilots and distinguish paid recruitment, spawn and hit events."""
from pathlib import Path
import hashlib
import json

ROOT=Path(__file__).resolve().parents[2]
QA=ROOT/'output/qa/godot/core-alignment-rc13'
rows=[]
inputs=None
for faction,indices,target in [('qi',[15,51,59,95],'unit.qi.sniper'),('bai',[19,59,91,95],'unit.bai.scribe')]:
    pair=[json.loads((QA/f'role-{faction}-{name}.json').read_text(encoding='utf-8')) for name in ['control','trial']]
    assert pair[0]['inputs']==pair[1]['inputs']
    if inputs is None:inputs=pair[0]['inputs']
    assert inputs==pair[0]['inputs']
    for path,digest in inputs.items():
        assert hashlib.sha256((ROOT/'game'/path.removeprefix('res://')).read_bytes()).hexdigest()==digest
    for i,data in enumerate(pair):
        assert data['map']=='map.01.04' and data['seed']==137 and data['duration_seconds']==300
        assert data['combat_trace_seconds']==300 and [r['index'] for r in data['records']]==indices
        assert data['experimental_ai_sequential_deployment'] and data['experimental_policy_faction']=='both'
        assert data['experimental_ai_role_deployment']==bool(i)
        assert data['experimental_role_policy_faction']==(faction if i else '')
        for key,value in data.items():
            if key.startswith('experimental_') and key not in ['experimental_ai_sequential_deployment','experimental_policy_faction','experimental_ai_role_deployment','experimental_role_policy_faction']:
                assert not value,(key,value)
    for before,after in zip(pair[0]['records'],pair[1]['records'],strict=True):
        assert (before['index'],before['west'],before['east'])==(after['index'],after['west'],after['east'])
        side=0 if before['west']==faction else 1
        row={'faction':faction,'target':target,'index':before['index'],'side':side,'west':before['west'],'east':before['east']}
        for name,record in [('control',before),('trial',after)]:
            recruits=[e['time'] for e in record['investment_trace'] if e['kind']=='recruit' and e['side']==side and e['id']==target]
            spawns=[e for e in record['combat_trace'] if e['kind']=='spawn' and e['side']==side and e['id']==target]
            clone_casts=[e for e in record['combat_trace'] if e['kind']=='cast' and e['side']==side and e['id'].endswith('.clone') and e['actor_id']==target]
            copy_uids={e['uid'] for e in spawns if any(abs(e['time']-c['time'])<1e-8 for c in clone_casts)}
            own_uids={e['uid'] for e in spawns}
            hits=[e for e in record['combat_trace'] if e['kind']=='hit' and e.get('source_id')==target and e.get('source_uid') in own_uids and e.get('attacker_side')==side]
            own=record['sides'][side]
            row[name]={'winner':record['winner'],'time':record['time'],'paid_recruit_times':recruits,
                       'spawn_times':[e['time'] for e in spawns],'registered_hit_count':len(hits),
                       'copies_spawned_during_matching_clone_cast':len(copy_uids),
                       'original_registered_hit_count':sum(e['source_uid'] not in copy_uids for e in hits),
                       'copy_registered_hit_count':sum(e['source_uid'] in copy_uids for e in hits),
                       'registered_hit_amount':sum(e['amount'] for e in hits),
                       'first_hit_time':min((e['time'] for e in hits),default=None),
                       'workers_including_orders':own['workers'],'base_hp':own['base_hp']}
        rows.append(row)
result={'scope':'16 paid full-AI games, 8 scoped pairs: sequential pilot on both sides, role pilot only on qi or bai. One map/seed, 300s ceiling. Registered hit amount is event damage, not proof of net extra damage or causal victory; no all-map/human acceptance.',
        'inputs':inputs,'source_unchanged':True,'analysis_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'rows':rows}
(QA/'role-scoped-comparison.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
for r in rows:
    print(r['faction'],r['index'],'winner',r['control']['winner'],r['trial']['winner'],
          'paid/spawn/hit',[(len(r[n]['paid_recruit_times']),len(r[n]['spawn_times']),r[n]['registered_hit_count']) for n in ['control','trial']])
