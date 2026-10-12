"""Bind the observer navigation change to actually verified rc22 packages."""
import difflib
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
QA = ROOT / 'output/qa/godot/observer-camera-rc22'
RELEASE = ROOT / 'release/3.0.0-rc22-preview'
read = lambda path: json.loads(path.read_text(encoding='utf-8-sig'))
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
proof = read(RELEASE / 'preview-verification.json')
assert proof['preview_artifacts_verified'] and proof['observer_camera_verified']
manifest = read(RELEASE / 'build-manifest.json')
prior_manifest = read(ROOT / 'release/3.0.0-rc21-preview/build-manifest.json')
baseline = ROOT / 'output/qa/godot/core-alignment-rc21/rc20-control-runtime/scripts/battle_sim.gd'
assert sha(baseline) == prior_manifest['source_inputs']['game/scripts/battle_sim.gd']
old = baseline.read_text(encoding='utf-8')
new = (ROOT / 'game/scripts/battle_sim.gd').read_text(encoding='utf-8')
def without_navigation(text):
    start = text.index('func front(')
    end = text.index('func ai_turn(', start)
    return text[:start] + text[end:]
assert without_navigation(old) == without_navigation(new)
snapshot = QA / 'rc21-battle_sim.gd'
snapshot.write_bytes(baseline.read_bytes())
diff = QA / 'simulation-navigation.diff'
diff.write_text(''.join(difflib.unified_diff(old.splitlines(keepends=True), new.splitlines(keepends=True),
                fromfile='rc21/battle_sim.gd', tofile='rc22/battle_sim.gd')), encoding='utf-8')
current = read(QA / 'release/apk-logic/report.json')['extracted_inputs']
prior = read(ROOT / 'output/qa/godot/fog-render-rc21/release/apk-logic/report.json')['extracted_inputs']
unchanged = {}
for name in ['scripts/map_runtime.gdc', 'scripts/battle_visibility.gdc', 'scripts/theatre_fog.gdc',
             'scripts/tactical_ai.gdc', 'scripts/unit_abilities.gdc', 'scripts/match_projection.gdc',
             'scripts/battle_command_rules.gdc', 'scripts/manual_spell_rules.gdc',
             'data/balance-prototype.json', 'data/technology.json', 'data/maps.json',
             'data/campaign.json', 'data/unit-actions.json', 'data/unit-frames.json']:
    assert current[name] == prior[name], name
    unchanged[name] = current[name]
paths = [
    'game/project.godot', 'game/export_presets.cfg', 'game/scripts/battle_sim.gd',
    'game/scripts/battle_view.gd', 'game/scripts/local_duel.gd', 'game/scripts/main.gd', 'game/scripts/mobile_ui.gd',
    'assets/paper-warfront/style-tokens.json', 'game/data/style-tokens.json',
    'game/tests/test_observer_camera.gd', 'tools/paper-warfront/check_observer_camera.py',
    'tools/paper-warfront/probe_camera_rendering.gd', 'tools/paper-warfront/check_camera_rendering.py',
    'docs/paper-warfront/131-玩家视野与前线导航修复及rc22交付.md',
    'docs/paper-warfront/11-Godot架构与数据契约.md', 'docs/paper-warfront/16-玩家手册.md',
    'output/qa/godot/observer-camera-rc22/rc21-battle_sim.gd',
    'output/qa/godot/observer-camera-rc22/simulation-navigation.diff',
    'output/qa/godot/observer-camera-rc22/before-final/report.json',
    'output/qa/godot/observer-camera-rc22/render-before/report.json',
    'output/qa/godot/observer-camera-rc22/release/camera-render/report.json',
    'output/qa/godot/observer-camera-rc22/release/fog-render/report.json',
    'output/qa/godot/observer-camera-rc22/release/stage-proportions/report.json',
    'output/qa/godot/observer-camera-rc22/release/mobile/mobile-matrix.json',
    'output/qa/godot/observer-camera-rc22/formal-reach/regression/report.json',
    'output/qa/godot/observer-camera-rc22/figures/comparisons.json',
    'release/3.0.0-rc22-preview/build-manifest.json', 'release/3.0.0-rc22-preview/preview-verification.json',
]
ui = read(ROOT / 'assets/paper-warfront/ui/paper-ui.json')
record = {'revision': 'rc22-observer-camera-r1', 'version': manifest['version'], 'status': 'verified-preview',
          'assets': [{'id': 'camera.common.observer_front', 'implementation': 'native Godot observer query and Control input',
                      'source': 'game/scripts/battle_sim.gd', 'new_raster_generation': False}],
          'style_tokens_version': '1.2.0', 'reused_fog_stage_revision': 'rc21-fog-stage-r1',
          'reused_ui_asset_version': ui['version'], 'reused_ui_assets': len(ui['assets']), 'reused_ui_generation_model': ui['model'],
          'simulation_source_outside_front_identical_to_verified_rc21': True,
          'rc21_baseline_source_sha256': sha(snapshot), 'unchanged_actual_rc21_rc22_rules_and_rendering': unchanged,
          'checks': proof['observer_camera_verified'], 'source_mechanism_checks': proof['source_mechanism_checks'],
          'android_hardware_verified': False, 'full_balance_verified': False, 'original_game_numeric_equivalence_verified': False,
          'files': {name: sha(ROOT / name) for name in paths}, 'builds_and_archives': manifest['builds'] + manifest['archives']}
for item in record['builds_and_archives']:
    assert sha(ROOT / item['path']) == item['sha256']
target = ROOT / 'assets/paper-warfront/presentation-revisions/rc22-observer-camera-r1.json'
target.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
assert all(sha(ROOT / name) == value for name, value in record['files'].items())
print('Camera revision verified:', len(record['files']), 'references;', len(unchanged), 'unchanged compiled inputs')
