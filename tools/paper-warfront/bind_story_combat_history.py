"""Retain rc28 simulation equivalence only when its battle inputs are unchanged."""
from pathlib import Path
import hashlib,json,re
ROOT=Path(__file__).resolve().parents[2]
QA=ROOT/'output/qa/godot/story-atlas-rc29'
HISTORY=ROOT/'output/qa/godot/packed-query-rc28'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text('utf-8'))
baseline=read(ROOT/'release/3.0.0-rc28-preview/build-manifest.json')
allowed={
 'game/project.godot','game/export_presets.cfg',
 'game/scripts/main.gd','game/scripts/mobile_ui.gd','game/scripts/campaign_progress.gd',
 'game/data/campaign.json','game/data/campaign-flow.json','game/data/campaign-narrative.json',
 'game/data/story.json','game/data/mobile-font-provenance.json',
 'game/assets/fonts/NotoSansSC.ttf','game/assets/fonts/NotoSerifSC.ttf',
}
unchanged={};changed={}
for name,digest in baseline['source_inputs'].items():
 actual=sha(ROOT/name)
 if actual==digest:unchanged[name]=actual
 else:
  assert name in allowed,(name,'unexpected battle or asset mutation')
  changed[name]={'before':digest,'after':actual}
old=read(QA/'pre-adoption/game/data/campaign.json')['levels']
new=read(ROOT/'game/data/campaign.json')['levels']
allowed_level={'title','line','story_before','story_after'}
for a,b in zip(old,new):
 assert a.keys()==b.keys()
 assert all(a[k]==b[k] for k in a if k not in allowed_level),a['id']
 assert a['id']==b['id'] and a['index']==b['index']
for name in ['capacity-axis-original-closure.json','paid-axis-original-closure.json']:
 proof=read(HISTORY/name)
 assert proof['passed'] and not proof['failures']
 assert proof['simulation_sha256']==sha(ROOT/'game/scripts/battle_sim.gd')
authorship=read(QA/'authorship.json')
assert authorship['passed'] and authorship['authored_maps']==200
assert all(sha(ROOT/'game/data'/n)==h for n,h in authorship['output_hashes'].items())
result={'passed':True,'previous_version':'3.0.0-rc28-preview','current_version':'3.0.0-rc29-preview',
 'historical_evidence_root':HISTORY.relative_to(ROOT).as_posix(),
 'historical_build_manifest_sha256':sha(ROOT/'release/3.0.0-rc28-preview/build-manifest.json'),
 'unchanged_inputs':unchanged,'changed_inputs':changed,
 'campaign_battle_fields_unchanged':True,'maps':200,'permitted_level_changes':sorted(allowed_level),
 'history':{n:sha(HISTORY/n) for n in ['capacity-axis-original-closure.json','paid-axis-original-closure.json','oracle-runtime/closure-inputs.json']},
 'authorship_sha256':sha(QA/'authorship.json'),
 'scope':'Retained rc28 every-step simulation equivalence with identical simulation/helper/map/balance inputs and all200 unchanged combat configurations. New story, progression, UI and font changes are separately exercised in rc29 compiled packages. This receipt is not a new CPU/FPS benchmark.'}
target=QA/'combat-history-binding.json';assert not target.exists();target.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n','utf-8')
print('Unchanged combat history bound:',len(unchanged),'inputs;',len(changed),'authorized story/UI/font/version inputs differ')
