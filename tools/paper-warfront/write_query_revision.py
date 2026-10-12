"""Register reviewed rc28 runtime changes and immutable evidence references."""
from pathlib import Path
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parents[2]
QA = ROOT / 'output/qa/godot/packed-query-rc28'
VERSION = '3.0.0-rc28-preview'
RELEASE = ROOT / 'release' / VERSION
target = ROOT / 'assets/paper-warfront/system-revisions/rc28-packed-queries-r1.json'
assert not target.exists(), 'Never overwrite a registered revision'
read = lambda p: json.loads(p.read_text('utf-8'))

def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            digest.update(block)
    return digest.hexdigest()

manifest = read(RELEASE / 'build-manifest.json')
proof = read(RELEASE / 'preview-verification.json')
assert manifest['version'] == proof['version'] == VERSION
assert proof['source_inputs_verified'] and proof['render_cache_comparisons_verified'] == 12
assert not proof['android_hardware_verified'] and not proof['full_balance_verified']
assert all(sha(ROOT / name) == digest for name, digest in manifest['source_inputs'].items())
for row in manifest['builds'] + manifest['archives']:
    assert (ROOT / row['path']).stat().st_size == row['bytes']
    assert sha(ROOT / row['path']) == row['sha256']
reg = read(QA / 'formal-reach/regression/report.json')
assert reg['passed'] and reg['source_unchanged']
assert len(reg['tests']) == 77 and sum(t['checks'] for t in reg['tests']) == 96606
for platform in ('apk', 'windows'):
    result = read(QA / f'release-final/{platform}-logic/report.json')
    assert result['passed'] and len(result['tests']) == 35
    assert sum(t['checks'] for t in result['tests']) == 88420
adoption = read(QA / 'adoption.json')
completion = read(QA / 'adoption-completion.json')
assert completion['passed'] and completion['adoption_sha256'] == sha(QA / 'adoption.json')
assert adoption['passed'] and all(sha(ROOT / n) == completion['updated_inputs'].get(n,h) for n, h in adoption['adopted_inputs'].items())
assert completion['source_regression_sha256'] == sha(QA / 'formal-reach/regression/report.json')
assert all(sha(ROOT / n) == h for n, h in adoption['proofs'].items())
closure = read(QA / 'oracle-runtime/closure-inputs.json')
old_manifest = read(ROOT / 'release/3.0.0-rc27-preview/build-manifest.json')
for name, row in closure['scripts'].items():
    original = QA / 'baseline-runtime/scripts' / name
    oracle = QA / 'oracle-runtime/scripts' / name
    assert sha(original) == row['original_sha256'] == old_manifest['source_inputs']['game/scripts/' + name]
    assert sha(oracle) == row['oracle_sha256']
    expected = re.sub(r'res://scripts/([^"\s]+\.gd)',
        lambda m: (QA / 'oracle-runtime/scripts' / m.group(1)).as_posix(), original.read_text('utf-8'))
    assert oracle.read_bytes() == expected.encode('utf-8'), 'Only reference paths may change'
for original in (QA / 'baseline-runtime/data').glob('*.json'):
    assert original.read_bytes() == (ROOT / 'game/data' / original.name).read_bytes()
refs = set(manifest['source_inputs']) | set(adoption['proofs']) | set(adoption['adopted_inputs'])
refs.update(ROOT.joinpath('game/tests', t['script']).relative_to(ROOT).as_posix() for t in reg['tests'])
refs.update([
    'README.md', 'docs/paper-warfront/README.md',
    'docs/paper-warfront/137-密集交战查询与运行资源绑定.md',
    'docs/paper-warfront/136-单机剧情地图与章内分支.md',
    'docs/paper-warfront/11-Godot架构与数据契约.md', 'docs/paper-warfront/16-玩家手册.md',
    'assets/paper-warfront/ui/paper-ui.json', 'assets/paper-warfront/style-tokens.json',
    'assets/paper-warfront/system-revisions/rc27-story-routes-r1.json',
    'assets/paper-warfront/system-revisions/rc26-runtime-cache-r1.json',
    f'release/{VERSION}/README.md', f'release/{VERSION}/build-manifest.json',
    f'release/{VERSION}/preview-verification.json', f'release/{VERSION}/windows/preview-verification.json',
    f'release/{VERSION}/SHA256SUMS.txt',
])
refs.update(row['path'] for row in manifest['builds'] + manifest['archives'])
for name in [
    'prepare_packed_query_trial.py', 'prepare_unit_field_trial.py', 'prepare_axis_target_trial.py',
    'prepare_frozen_reference.py', 'prepare_native_query_candidate.py', 'adopt_packed_queries.py', 'complete_query_reference_checks.py',
    'test_capacity_runtime_equivalence.gd', 'test_paid_runtime_equivalence.gd',
    'test_axis_target_boundaries.gd', 'probe_unit_order_equivalence.gd',
    'runtime_asset_inputs.py', 'build_game.py', 'package_release.py',
    'check_ai_engagement.py', 'check_packaged_windows_logic.py', 'check_packaged_apk_logic.py',
    'audit_preview_build.py', 'run_preview_checks.py', 'run_realtime_release.py',
    'check_realtime_battle.py', 'probe_realtime_battle.gd',
    'check_render_cache_equivalence.py', 'probe_render_cache_equivalence.gd',
    'write_query_release_docs.py', 'write_query_revision.py',
]:
    refs.add('tools/paper-warfront/' + name)
for path in QA.rglob('*'):
    if not path.is_file() or any(p in ('.godot', '.keys', '__pycache__', 'extracted-runtime') for p in path.parts):
        continue
    if path.name == 'export_credentials.cfg':
        continue
    # Authoring/native staging rasters are unchanged copies. Their input JSON
    # binds them; the actual public assets and captured frames are bound here.
    if path.suffix.lower() == '.png' and any(p.startswith('play-') and p.endswith('-runtime') for p in path.parts):
        continue
    if path.suffix.lower() in ('.json', '.csv', '.gd', '.py', '.log', '.cfg', '.png'):
        refs.add(path.relative_to(ROOT).as_posix())
references = {name: {'sha256': sha(ROOT / name), 'bytes': (ROOT / name).stat().st_size} for name in sorted(refs)}
revision = {
    'id': 'system.paper-warfront.rc28-packed-queries-r1', 'version': VERSION, 'engine': 'Godot4.7.2',
    'review_status': 'native_package_state_and_render_checks_passed',
    'asset_generation': 'Existing reviewed sub2-image-gen/gpt-image-2.5 assets reused without raster regeneration or changed stable IDs.',
    'adopted': ['Typed packed live query records with float64 road offsets',
        'Exact sorted-X ranged query with independent weighted support pass and native Vector2 bounds',
        'Typed per-call immutable unit fields and live status dictionary aliases',
        'Population queries only for defined automatic guardian/clone abilities',
        'Original draw comparator with cached physical heights and immutable simulation order',
        'Runtime legacy asset/import/scene/license build-input bindings'],
    'unchanged_contracts': ['60Hz simulation', '60 combat population per side', 'Original map/vision/range/economy',
        'Whole-body animation and combat particles', 'Chapter1 map narratives and optional campaign graph',
        '70 percent minimum battlefield display'],
    'source_checks': 96606, 'packaged_checks_each': 88420,
    'capacity_exact_steps': 3600, 'paid_exact_steps': 73103, 'original_helper_closure_scripts': len(closure['scripts']),
    'realtime': proof['realtime_frame_observations'],
    'pending': ['Sustained full-capacity smooth FPS', 'Other180 deeply authored story maps',
        'Complete faction and campaign balance', 'Android physical device performance/touch',
        'Original game exact vision/timing alignment', 'Human multiplayer playtest'],
    'references': references,
}
target.write_text(json.dumps(revision, ensure_ascii=False, indent=2) + '\n', 'utf-8')
print('Registered rc28 runtime revision:', len(references), 'references')
