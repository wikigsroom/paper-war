"""Bind this runtime revision to final binaries, actual frames and retained negatives."""
from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parents[2]
QA=ROOT/'output/qa/godot/realtime-performance-rc26'
RELEASE=ROOT/'release/3.0.0-rc26-preview'
read=lambda p:json.loads(p.read_text('utf-8'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
manifest=read(RELEASE/'build-manifest.json');proof=read(RELEASE/'preview-verification.json')
assert manifest['version']==proof['version']=='3.0.0-rc26-preview'
assert proof['source_inputs_verified'] and proof['render_cache_comparisons_verified']==12
assert not proof['android_hardware_verified'] and not proof['full_balance_verified']
assert all(sha(ROOT/name)==digest for name,digest in manifest['source_inputs'].items())
reg=read(QA/'formal-reach/regression/report.json');assert reg['passed'] and reg['source_unchanged']
assert len(reg['tests'])==73 and sum(t['checks'] for t in reg['tests'])==87810
for platform in ['apk','windows']:
 r=read(QA/f'release/{platform}-logic/report.json');assert r['passed'] and len(r['tests'])==31 and sum(t['checks'] for t in r['tests'])==79624
paid=read(QA/'paid-runtime-equivalence.json');assert paid['passed'] and paid['checks']==73103
assert paid['simulation_sha256']==sha(ROOT/'game/scripts/battle_sim.gd')
for part in ['source-ellipse-cache-stress','source-blocker-cache-stress']:
 frozen=QA/part/'source-runtime';inputs=read(QA/part/'source-inputs.json')
 assert all(sha(frozen/name)==digest for name,digest in inputs.items())
refs=['README.md','docs/paper-warfront/README.md','docs/paper-warfront/135-单位地图比例与原生运行性能复核.md','docs/paper-warfront/11-Godot架构与数据契约.md','docs/paper-warfront/16-玩家手册.md',
 'game/tests/test_road_target_equivalence.gd','game/tests/test_marching_query_equivalence.gd','game/tests/test_target_search_equivalence.gd','game/tests/reference_target_search.gd',
 'assets/paper-warfront/style-tokens.json','assets/paper-warfront/ui/paper-ui.json','assets/paper-warfront/presentation-revisions/rc21-fog-stage-r1.json',
 'release/3.0.0-rc26-preview/README.md','release/3.0.0-rc26-preview/build-manifest.json','release/3.0.0-rc26-preview/preview-verification.json']
for name in ['prepare_blocker_query_trial.py','prepare_flat_target_trial.py','prepare_spatial_target_trial.py','prepare_indexed_actor_trial.py',
 'check_realtime_battle.py','probe_realtime_battle.gd','check_render_cache_equivalence.py','probe_render_cache_equivalence.gd','run_realtime_release.py',
 'test_paid_runtime_equivalence.gd','check_ai_engagement.py','check_packaged_apk_logic.py','check_packaged_windows_logic.py','run_preview_checks.py','audit_preview_build.py','write_realtime_release_docs.py','write_realtime_revision.py']:
 refs.append('tools/paper-warfront/'+name)
refs.extend(manifest['source_inputs'])
for p in QA.rglob('*'):
 if p.is_file() and '.godot' not in p.parts and '__pycache__' not in p.parts and 'extracted-runtime' not in p.parts and (p.suffix in ['.json','.csv','.png'] or p.name in ['observer.gd','runner.py','runtime.log']):refs.append(p.relative_to(ROOT).as_posix())
references={name:{'sha256':sha(ROOT/name),'bytes':(ROOT/name).stat().st_size} for name in sorted(set(refs))}
revision={'id':'system.paper-warfront.rc26-runtime-cache-r1','version':'3.0.0-rc26-preview','engine':'Godot4.7.2','asset_generation':'Existing reviewed sub2-image-gen/gpt-image-2.5 raster resources reused without regeneration. Stable raster IDs and generation versions retained.',
 'adopted':['Exact road melee candidate index with final score/rank ties','Same-road nearest eligible marching blocker index','Per-phase ranged physical point records in original sight order','Static terrain fill meshes','Shared24-point ellipse mesh','Whole-body frame selection without profile copies'],
 'not_adopted':['Tick-local actor lookup trials','Static canvas command replay','Ranged spatial tree'],
 'source_checks':87810,'packaged_checks_each':79624,'paid_exact_steps':73103,
 'realtime':proof['realtime_frame_observations'],'pending':['Sustained full-capacity smooth FPS','Android physical device performance/touch','Complete faction balance','Original game exact vision/timing alignment'],
 'references':references}
out=ROOT/'assets/paper-warfront/system-revisions/rc26-runtime-cache-r1.json'
assert not out.exists(), 'Never overwrite a registered system revision'
out.write_text(json.dumps(revision,ensure_ascii=False,indent=2)+'\n','utf-8')
print('Runtime revision registered',len(references),'references')
