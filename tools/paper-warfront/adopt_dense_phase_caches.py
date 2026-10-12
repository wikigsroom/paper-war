"""Adopt only the exact three scripts verified against the complete rc29 closure."""
from pathlib import Path
import hashlib
import json
import shutil

ROOT = Path(__file__).resolve().parents[2]
QA = ROOT / 'output/qa/godot/dense-runtime-rc30'
VERSION = '3.0.0-rc30-preview'
target = QA / 'adoption.json'
assert not target.exists(), 'Do not repeat a recorded adoption'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
read = lambda p: json.loads(p.read_text('utf-8'))
manifest = read(QA / 'baseline-build-manifest.json')
assert all(sha(ROOT / name) == digest for name, digest in manifest['source_inputs'].items())
proofs = {}
for filename, expected in [('phase-reuse-r2-capacity.json',3600),('phase-reuse-r2-paid-r3.json',73103),
                           ('test_exact_query_retention-external-reference-r3.json',25600),
                           ('test_stationary_projection-external-reference-r3.json',77320)]:
    result = read(QA / filename)
    assert result['passed'] and not result['failures'] and result['checks']==expected, filename
    proofs[filename] = sha(QA / filename)
regression = read(QA / 'candidate-regression-r2/report.json')
assert regression['passed'] and regression['source_unchanged'] and len(regression['tests'])==78
assert sum(row['checks'] for row in regression['tests'])==195435
assert all(sha(ROOT/name)==digest if not name.startswith('game/') else
           sha(QA/'native-phase-reuse-r2-runtime'/name.removeprefix('game/'))==digest
           for name,digest in regression['inputs'].items())
render = read(QA / 'native-phase-r2-pixel-comparison/report.json')
assert render['passed'] and len(render['comparisons'])==12
assert all(row['max_channel_delta']==0 for row in render['comparisons'])
proofs['candidate-regression-r2/report.json']=sha(QA/'candidate-regression-r2/report.json')
proofs['native-phase-r2-pixel-comparison/report.json']=sha(QA/'native-phase-r2-pixel-comparison/report.json')
before = QA / 'pre-adoption'
assert not before.exists()
before.mkdir()
changed = {}
for name in ['battle_sim.gd','map_runtime.gd','battle_visibility.gd']:
    live = ROOT/'game/scripts'/name
    candidate = QA/'phase-reuse-r2-runtime/scripts'/name
    assert sha(candidate)==sha(QA/'native-phase-reuse-r2-runtime/scripts'/name)
    shutil.copy2(live,before/name)
    changed['game/scripts/'+name]={'before':sha(live),'after':sha(candidate)}
for name in ['project.godot','export_presets.cfg']:
    shutil.copy2(ROOT/'game'/name,before/name)
for name in ['battle_sim.gd','map_runtime.gd','battle_visibility.gd']:
    shutil.copy2(QA/'phase-reuse-r2-runtime/scripts'/name,ROOT/'game/scripts'/name)
for name in ['project.godot','export_presets.cfg']:
    live=ROOT/'game'/name
    old=live.read_text('utf-8');new=old.replace('3.0.0-rc29-preview',VERSION)
    if name=='export_presets.cfg':
        assert new.count('version/code=30028')==1
        new=new.replace('version/code=30028','version/code=30029')
    assert new!=old
    live.write_text(new,'utf-8')
    changed['game/'+name]={'before':sha(before/name),'after':sha(live)}
# Copy the completed source check as-is. Its recorded source_project remains
# the actual isolated project that ran; this receipt binds identical live bytes.
final=QA/'source-final';final.mkdir()
shutil.copytree(QA/'candidate-regression-r2',final,dirs_exist_ok=True)
assert all(sha(ROOT/name)==digest for name,digest in regression['inputs'].items())
assert all(sha(ROOT/'game/tests'/row['script'])==row['sha256'] for row in regression['tests'])
(QA/'source-check-retention.json').write_text(json.dumps({
    'passed':True,'original_report':'candidate-regression-r2/report.json',
    'report_sha256':sha(final/'report.json'),'live_gameplay_inputs_identical':True,
    'project_config_difference':'Only release version/application export code; compiled-package checks will verify current project settings.',
    'scope':'78 completed controlled checks retained for identical gameplay/data/observer inputs. Does not claim a second execution.'
},indent=2)+'\n','utf-8')
target.write_text(json.dumps({'passed':True,'release':VERSION,'proofs':proofs,'changed_inputs':changed,
    'generated_raster_assets':False,'source_groups':78,'source_checks':195435,
    'additional_exact_retention_checks':102920,'normal_paid_steps':73103,'dense_capacity_steps':3600,
    'scope':'Exact target-source validation, finite canonical zero-travel projection retention and method-scoped weak-owner reads. Gameplay fields/events/RNG/vision stay identical to the complete frozen rc29 closure in observed cases. No claim of60FPS, Android hardware or global balance; compiled export/native checks still required.'},ensure_ascii=False,indent=2)+'\n','utf-8')
print('Adopted verified dense-phase caches; native export verification remains')
