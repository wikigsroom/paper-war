"""Audit matched paid research-start experiments and their recruitment outcomes."""
import hashlib
import json
import argparse
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
QA=ROOT/'output/qa/godot/core-alignment-rc13'
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--prefix',default='purchase-recovery')
parser.add_argument('--ai-archive',type=Path)
args=parser.parse_args()
technology={n['id']: n for n in json.loads((ROOT/'game/data/technology.json').read_text(encoding='utf-8'))['nodes']}
rows=[]
inputs=None
for seed in [137,419]:
    pair=[json.loads((QA/f'{args.prefix}-{seed}-{name}.json').read_text(encoding='utf-8')) for name in ['control','trial']]
    assert pair[0]['inputs']==pair[1]['inputs']
    if inputs is None:inputs=pair[0]['inputs']
    assert inputs==pair[0]['inputs']
    for path,digest in inputs.items():
        source=args.ai_archive if args.ai_archive and path=='res://scripts/tactical_ai.gd' else ROOT/'game'/path.removeprefix('res://')
        assert hashlib.sha256(source.read_bytes()).hexdigest()==digest
    for i,data in enumerate(pair):
        assert data['seed']==seed and data['map']=='map.01.04' and data['duration_seconds']==300
        assert data['experimental_ai_sequential_deployment'] and bool(data['experimental_ai_sequential_funded_start'])==bool(i)
        assert len(data['records'])==4 and [r['index'] for r in data['records']]==[19,51,59,96]
        for key,value in data.items():
            if key.startswith('experimental_') and key not in ['experimental_ai_sequential_deployment','experimental_ai_sequential_funded_start','experimental_policy_faction']:
                assert not value,(key,value)
    for before,after in zip(pair[0]['records'],pair[1]['records'],strict=True):
        item={'seed':seed,'index':before['index'],'west':before['west'],'east':before['east'],'control':{},'trial':{}}
        for name,record in [('control',before),('trial',after)]:
            sides=[]
            for side in [0,1]:
                events=[e for e in record['investment_trace'] if e['side']==side]
                paid=completed=recruited=0
                for event in events:
                    if event['kind']!='research_start':continue
                    grant=technology[event['id']]['grant']
                    if not grant.startswith('unit.'):continue
                    paid+=1
                    done=[e['time'] for e in events if e['kind']=='research_done' and e['id']==grant and e['time']>=event['time']]
                    if not done:continue
                    completed+=1
                    recruited+=any(e['kind']=='recruit' and e['id']==grant and e['time']>=min(done) for e in events)
                own=record['sides'][side]
                sides.append({'unit_studies_paid':paid,'unit_studies_completed':completed,'unit_studies_recruited':recruited,
                              'workers_including_orders':own['workers'],'base_hp':own['base_hp'],'healed_all_sources':own['stats']['healed'],
                              'gold_delivered':own['stats']['gold_delivered']})
            item[name]={'winner':record['winner'],'time':record['time'],'sides':sides}
        rows.append(item)
result={'scope':'16 full paid AI games, 8 matched pairs, mid map two seeds and 300s ceiling; both AI policies change. Recruitment is not combat benefit; healed counts all sources, not advanced unit attribution.',
        'inputs':inputs,'source_unchanged':not bool(args.ai_archive),'archived_ai_verified':bool(args.ai_archive),'analysis_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'rows':rows}
(QA/f'{args.prefix}-comparison.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
for r in rows:
    print(r['seed'],r['index'], 'winner',r['control']['winner'],r['trial']['winner'],
          'research->recruit',[(s['unit_studies_completed'],s['unit_studies_recruited']) for s in r['control']['sides']],
          [(s['unit_studies_completed'],s['unit_studies_recruited']) for s in r['trial']['sides']])
