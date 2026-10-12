"""Register the reviewed rc27 story/map revision without changing exported inputs."""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[2]
VERSION = '3.0.0-rc27-preview'
QA = ROOT / 'output/qa/godot/capacity-performance-rc27'
FINAL = QA / 'release-final'
RELEASE = ROOT / 'release' / VERSION


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def sha(path):
    result = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            result.update(block)
    return result.hexdigest()


def main():
    target = ROOT / 'assets/paper-warfront/system-revisions/rc27-story-routes-r1.json'
    assert not target.exists(), 'Never overwrite a registered revision'
    manifest = read(RELEASE / 'build-manifest.json')
    proof = read(RELEASE / 'preview-verification.json')
    assert manifest['version'] == proof['version'] == VERSION
    assert proof['source_inputs_verified'] and proof['render_cache_comparisons_verified'] == 12
    assert not proof['android_hardware_verified'] and not proof['full_balance_verified']
    assert all(sha(ROOT / name) == digest for name, digest in manifest['source_inputs'].items())
    for build in manifest['builds'] + manifest['archives']:
        assert (ROOT / build['path']).stat().st_size == build['bytes']
        assert sha(ROOT / build['path']) == build['sha256']
    regression = read(QA / 'formal-reach/regression/report.json')
    assert regression['passed'] and regression['source_unchanged']
    assert len(regression['tests']) == 75 and sum(test['checks'] for test in regression['tests']) == 95386
    for platform in ('apk', 'windows'):
        result = read(FINAL / f'{platform}-logic/report.json')
        assert result['passed'] and len(result['tests']) == 33
        assert sum(test['checks'] for test in result['tests']) == 87200
    paid = read(QA / 'paid-runtime-equivalence.json')
    assert paid['passed'] and paid['checks'] == 73103
    assert paid['simulation_sha256'] == sha(ROOT / 'game/scripts/battle_sim.gd')
    bindings = read(QA / 'story-input-bindings.json')
    assert bindings['passed']
    assert all(sha(ROOT / name) == digest for name, digest in bindings['inputs'].items())
    assert bindings['rule_proof_sha256'] == sha(QA / 'campaign-routes-final.json')
    for name in ('campaign.json', 'campaign-flow.json', 'campaign-narrative.json'):
        assert (ROOT / 'assets/paper-warfront' / name).read_bytes() == (ROOT / 'game/data' / name).read_bytes()
    leap = read(QA / 'leap-blocker-all-maps.json')
    assert leap['checks'] == 1200 and not leap['failures']
    assert leap['simulation_sha256'] == paid['simulation_sha256']
    story = proof['story_map_progression_verified']
    assert story['opening_authored_maps'] == 20 and story['optional_pairs'] == 6
    assert story['compiled_native_ui_checks'] == 66
    mobile = read(FINAL / 'mobile/mobile-matrix.json')
    assert mobile['passed'] and mobile['checks'] == 26721
    references = set(manifest['source_inputs'])
    references.update(bindings['inputs'])
    references.update([
        'README.md', 'docs/paper-warfront/README.md',
        'docs/paper-warfront/136-单机剧情地图与章内分支.md',
        'docs/paper-warfront/07-交互与UI规范.md',
        'docs/paper-warfront/08-关卡与内容规划.md',
        'docs/paper-warfront/11-Godot架构与数据契约.md',
        'docs/paper-warfront/16-玩家手册.md',
        'docs/paper-warfront/20-战役与任务执行规范.md',
        'docs/paper-warfront/world/04-完整故事路线.md',
        'assets/paper-warfront/style-tokens.json',
        'assets/paper-warfront/ui/paper-ui.json',
        'assets/paper-warfront/system-revisions/rc26-runtime-cache-r1.json',
        'assets/paper-warfront/presentation-revisions/rc21-fog-stage-r1.json',
        f'release/{VERSION}/README.md',
        f'release/{VERSION}/build-manifest.json',
        f'release/{VERSION}/preview-verification.json',
        f'release/{VERSION}/windows/preview-verification.json',
        f'release/{VERSION}/SHA256SUMS.txt',
    ])
    for name in [
        'author_story_routes.py', 'prepare_capacity_runtime.py',
        'capacity_cpu_profiler.gd', 'probe_capacity_cpu.gd',
        'prepare_capacity_candidate.py', 'probe_leap_blocker_consistency.gd',
        'probe_story_routes_ui.gd', 'check_story_routes_ui.py',
        'test_paid_runtime_equivalence.gd', 'check_ai_engagement.py',
        'check_packaged_apk_logic.py', 'check_packaged_windows_logic.py',
        'check_realtime_battle.py', 'probe_realtime_battle.gd',
        'check_render_cache_equivalence.py', 'probe_render_cache_equivalence.gd',
        'run_realtime_release.py', 'run_preview_checks.py',
        'run_paid_release_recipes.py', 'audit_preview_build.py',
        'package_release.py', 'write_story_route_release_docs.py',
        'write_story_route_revision.py',
    ]:
        references.add('tools/paper-warfront/' + name)
    references.update(row['path'] for row in manifest['builds'] + manifest['archives'])
    for path in QA.rglob('*'):
        if not path.is_file():
            continue
        if any(part in ('.godot', '.keys', '__pycache__', 'extracted-runtime') for part in path.parts):
            continue
        if path.name == 'export_credentials.cfg':
            continue
        if path.suffix.lower() in ('.json', '.csv', '.png', '.gd', '.py', '.log', '.exe', '.apk', '.zip', '.ttf', '.cfg'):
            references.add(path.relative_to(ROOT).as_posix())
    bound = {
        name: {'sha256': sha(ROOT / name), 'bytes': (ROOT / name).stat().st_size}
        for name in sorted(references)
    }
    revision = {
        'id': 'system.paper-warfront.rc27-story-routes-r1',
        'version': VERSION,
        'engine': 'Godot4.7.2',
        'review_status': 'native_package_and_route_checks_passed',
        'asset_generation': 'Previously reviewed sub2-image-gen/gpt-image-2.5 raster resources reused. No new raster generation or changed raster asset IDs.',
        'adopted': [
            'Explicit first-chapter20 map-specific conflict, dialogue, stakes and evidence',
            'Independent campaign graph: six optional pairs with convergence and revisits',
            'Schema3 actual completed IDs, schema2 historical migration, highest-star replays',
            'Desktop/mobile story selection and complete concise mission summaries',
            'Original movement anchor for a leaping actor while creating the lazy friendly blocker index',
        ],
        'map_topology': {'single_road_maps': 140, 'fork_maps': 60, 'scope': 'Existing battlefield road graphs retained; campaign unlock choices do not invent extra battlefield roads.'},
        'authored_story_maps': 20,
        'remaining_story_maps': {'count': 180, 'status': 'Existing stories retained; equivalent per-map narrative revision pending'},
        'source_checks': 95386,
        'packaged_checks_each': 87200,
        'story_native_ui_checks': 66,
        'paid_exact_steps': 73103,
        'mobile_display_checks': 26721,
        'realtime': proof['realtime_frame_observations'],
        'performance_scope': 'Sequential native observations under concurrent user-project CPU load. No performance improvement claim; full-capacity target remains pending.',
        'retained_negatives': [
            'Prior blocker leap mismatch, both directions',
            'First story brief export:15 of20 summaries clipped',
            'Initial save test compared JSON numeric dictionary types instead of runtime reconstruction',
            'Initial UI observer hashed a logical remapped source resource instead of compiled bytes',
        ],
        'pending': [
            'Chapters2-10 narrative revision at the depth of chapter1',
            'Sustained full-capacity smooth FPS',
            'Android physical device performance and touch',
            'Complete200-map and faction balance',
            'Original game precise vision and timing alignment',
        ],
        'references': bound,
    }
    target.write_text(json.dumps(revision, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    assert all(sha(ROOT / name) == entry['sha256'] for name, entry in bound.items())
    print('Story/map revision registered:', len(bound), 'references')


if __name__ == '__main__':
    main()
