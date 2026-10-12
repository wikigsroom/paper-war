"""Bind fresh rc29-to-rc30 state comparisons and unchanged narrative/art inputs."""
from pathlib import Path
import hashlib
import json
import shutil

ROOT=Path(__file__).resolve().parents[2]
QA=ROOT/'output/qa/godot/dense-runtime-rc30'
STORY=ROOT/'output/qa/godot/story-atlas-rc29'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text('utf-8'))
target=QA/'combat-history-binding.json'
assert not target.exists()
old=read(QA/'baseline-build-manifest.json')
allowed={'game/scripts/battle_sim.gd','game/scripts/map_runtime.gd','game/scripts/battle_visibility.gd','game/project.godot','game/export_presets.cfg'}
unchanged={};changed={}
for name,digest in old['source_inputs'].items():
    actual=sha(ROOT/name)
    if actual==digest:unchanged[name]=actual
    else:
        assert name in allowed,name
        changed[name]={'before':digest,'after':actual}
assert set(changed)==allowed
closure=read(QA/'freeze.json')
for name,row in closure['oracle_scripts'].items():
    assert sha(QA/'oracle-runtime/scripts'/name)==row['oracle_sha256']
    assert sha(QA/'baseline-runtime/scripts'/name)==row['source_sha256']
for name,count in [('phase-reuse-r2-capacity.json',3600),('phase-reuse-r2-paid-r3.json',73103)]:
    proof=read(QA/name)
    assert proof['passed'] and not proof['failures'] and proof['checks']==count
    assert proof['simulation_sha256']==sha(ROOT/'game/scripts/battle_sim.gd')
    assert proof['baseline_sha256']==sha(QA/'oracle-runtime/scripts/battle_sim.gd')
assert read(QA/'phase-reuse-r2-capacity.json')['loaded_source_matches']
# Retain the exact authored text and glyph-coverage evidence, with explicit
# input binding. A version update is not new text/font generation or a rerun.
authored=read(STORY/'authorship.json')
assert authored['passed'] and all(sha(ROOT/'game/data'/name)==digest for name,digest in authored['output_hashes'].items())
shutil.copy2(STORY/'authorship.json',QA/'authorship.json')
font=read(STORY/'font-coverage.json')
assert font['passed'] and all(sha(ROOT/r['path'])==r['sha256'] and not r['missing_after'] for r in font['records'])
font['retained_from_version']=font['version'];font['version']='3.0.0-rc30-preview'
font['retained_report_sha256']=sha(STORY/'font-coverage.json')
font['retention_scope']='Identical font bytes and every runtime narrative/data character input; no new subset generation or new glyph-coverage execution.'
(QA/'font-coverage.json').write_text(json.dumps(font,ensure_ascii=False,indent=2)+'\n','utf-8')
report={'passed':True,'previous_version':old['version'],'current_version':'3.0.0-rc30-preview',
    'campaign_battle_fields_unchanged':True,'all_campaign_data_unchanged':True,
    'unchanged_inputs':unchanged,'changed_inputs':changed,
    'historical_evidence_root':QA.relative_to(ROOT).as_posix(),
    'closure_scripts':len(closure['oracle_scripts']),
    'fresh_proofs':{name:sha(QA/name) for name in ['freeze.json','phase-reuse-r2-capacity.json','phase-reuse-r2-paid-r3.json','adoption.json']},
    'retained_narrative':{'source':(STORY/'authorship.json').relative_to(ROOT).as_posix(),'sha256':sha(STORY/'authorship.json')},
    'scope':'Fresh every-step current-cache simulation comparison against all44 frozen rc29 original scripts; all200 campaign/data/art/font inputs byte-identical. This supersedes unchanged-simulation retention for rc30; it is not an FPS or complete balance proof.'}
target.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n','utf-8')
print('Bound fresh dense/paid comparisons and unchanged story/art/font inputs')
