"""Verify research artifacts, not game acceptance. Writes an evidence manifest."""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path
from urllib.parse import unquote

from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
REPORT = ROOT / 'docs/research/swords-and-soldiers-map/recheck-20261008'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    read=lambda name:json.loads((REPORT/name).read_text(encoding='utf-8'))
    audit,probe,specs,sources = (read(n) for n in ('current-map-audit.json','native-probes.json','whitebox-specs.json','sources.json'))
    stale = [name for name,expected in audit['source_sha256'].items() if digest(ROOT/name)!=expected]
    if stale:
        raise RuntimeError('Current inputs differ from research baseline: '+', '.join(stale))
    assert audit['data_version']=='3.0.0-dev'
    assert audit['summary']['map_entries']==200
    assert audit['summary']['anchor_arrangement_families']==2
    assert [len(probe[key]) for key in ('economics','routes','first_contact')]==[36,10,3]
    assert all(row['merge_seconds']>0 for row in probe['routes'])
    assert all(row['first_hit_seconds']>0 for row in probe['first_contact'])
    result=lambda priority:next(r for r in probe['economics'] if r['map']=='map.01.01' and r['side']==0 and r['worker_count']==1 and r['priority']==priority)
    assert result('near')['gold_delivered']==160
    outer=result('outer')
    assert outer['gold_delivered']==11 and outer['gold_per_30_second_interval']==[11,0,0,0]
    worker=outer['final_worker_states'][0]
    assert worker['edge']==worker['route_plan']['next_edge']=='ground.0' and worker['s']==0
    ids={s['id'] for s in sources['sources']}
    assert len(specs['maps'])==6 and len({m['id'] for m in specs['maps']})==6
    for m in specs['maps']:
        assert 3<=len(m['production_roles'])<=5 and '工人' in m['production_roles']
        assert len(m['plans'])==2 and len({a['id'] for a in m['anchors']})==len(m['anchors'])
        assert all(0<=a['x']<=m['length'] for a in m['anchors'])
        assert all(a[0]<b[0] for a,b in zip(m['surface'],m['surface'][1:]))
        assert set(m['original_evidence'])<=ids
        assert m['surface'][0][0]==0 and m['surface'][-1][0]==m['length']
        if m['branch']:
            branch=m['branch']
            assert branch['surface'][0][0]==branch['from_x']
            assert branch['surface'][-1][0]==branch['to_x']
    # Register immutable local reference originals separately from derived figures.
    ledger_changed=False
    for s in sources['sources']:
        if 'local_artifact' not in s:
            continue
        p=(REPORT/s['local_artifact']).resolve()
        assert p.exists(),str(p)
        sha=digest(p)
        if s['local_sha256'] is None:
            s['local_sha256']=sha
            ledger_changed=True
        else:
            assert s['local_sha256']==sha,'Local original reference changed: '+str(p)
    if ledger_changed:
        (REPORT/'sources.json').write_text(json.dumps(sources,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    docs=list(REPORT.glob('*.md'))+[
        ROOT/'docs/paper-warfront/README.md',
        ROOT/'docs/paper-warfront/redesign/01-重做目标与验收.md',
        ROOT/'docs/research/swords-and-soldiers-map/README.md',
        ROOT/'tools/paper-warfront/research/README.md',
    ]
    links=0
    for doc in docs:
        content=doc.read_text(encoding='utf-8')
        assert '\ufffd' not in content,'Replacement character: '+str(doc)
        for target in re.findall(r'!?\[[^\]]*\]\(([^)\n]+)\)',content):
            target=target.strip().strip('<>')
            if re.match(r'^(https?://|mailto:|#|codex:)',target):
                continue
            target=unquote(target.split('#')[0])
            target=re.sub(r':\d+$','',target)
            path=(doc.parent/target).resolve()
            assert path.exists(),f'Missing link: {doc.relative_to(ROOT)} -> {target}'
            links+=1
    for path in (REPORT/'figures').glob('*.png'):
        with Image.open(path) as im:
            im.verify()
    tools=[ROOT/'tools/paper-warfront/research'/name for name in (
        'recheck_map_design.py','probe_map_decisions.gd','collect_primary_map_sources.py',
        'render_map_recheck.py','verify_map_recheck.py','README.md')]
    artifacts=[p for p in REPORT.rglob('*') if p.is_file() and p.name!='evidence-manifest.json' and '-rerun' not in p.name]
    manifest={
        'date':'2026-10-08',
        'status':'research_artifacts_verified_game_acceptance_not_passed',
        'baseline_game_source_sha256':audit['source_sha256'],
        'supplemental_source_sha256':{name:digest(ROOT/name) for name in ['game/scripts/tactical_ai.gd','game/project.godot']},
        'research_sha256':{str(p.relative_to(ROOT)).replace('\\','/'):digest(p) for p in sorted(artifacts+tools)},
        'checks':{'local_links':links,'whitebox_proposals':6,'economic_fixtures':36,'route_fixtures':10,'contact_fixtures':3},
        'known_failure':{'kind':'P0 worker route stall','map':'map.01.01','side':0,'mine':'mine.0.1','gold_120_seconds':11,'near_gold_120_seconds':160,'state':worker},
        'visual_review':{'files':['figures/research-overview.png','figures/reference-vs-delivered.png','figures/whitebox-archetypes.png'],'review':'Viewed locally after fixing label collisions, type weight, diagram overlap and screenshot card bounds'},
        'browser_cleanup':'Temporary research tab closed; browser.tabs.list() returned []',
        'not_completed':['Original PC runtime measurement','Transport repair','Whitebox integration','Human gameplay acceptance','New Windows/Android release']
    }
    (REPORT/'evidence-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'research_materials_verified':True,'game_acceptance_passed':False,**manifest['checks']},ensure_ascii=False))


if __name__=='__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main()
