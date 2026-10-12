"""Bind the code effect and scale specification to checked rc21 artifacts."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
QA = ROOT / 'output/qa/godot/fog-render-rc21'
RELEASE = ROOT / 'release/3.0.0-rc21-preview'
def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))
def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

verification = read(RELEASE / 'preview-verification.json')
assert verification['preview_artifacts_verified'] and verification['fog_and_stage_verified']
current = read(QA / 'release/apk-logic/report.json')['extracted_inputs']
historical = read(ROOT / 'output/qa/godot/ui-rc20/release/apk-logic/report.json')['extracted_inputs']
unchanged = {}
for name in ['scripts/battle_sim.gdc', 'scripts/map_runtime.gdc', 'scripts/tactical_ai.gdc',
             'scripts/unit_abilities.gdc', 'scripts/match_projection.gdc',
             'data/balance-prototype.json', 'data/technology.json', 'data/maps.json',
             'data/campaign.json', 'data/unit-actions.json', 'data/unit-frames.json']:
    assert current[name] == historical[name], name
    unchanged[name] = current[name]
paths = [
    'game/project.godot', 'game/export_presets.cfg',
    'game/scripts/theatre_fog.gd', 'game/scripts/battle_visibility.gd',
    'game/scripts/battle_view.gd', 'game/scripts/main.gd', 'game/scripts/mobile_ui.gd', 'game/scripts/local_duel.gd',
    'assets/paper-warfront/style-tokens.json', 'game/data/style-tokens.json',
    'game/tests/test_fog_presentation.gd', 'game/tests/mobile_ui_qa.gd',
    'tools/paper-warfront/probe_fog_rendering.gd', 'tools/paper-warfront/probe_stage_proportions.gd',
    'tools/paper-warfront/probe_duel_stage.gd',
    'docs/paper-warfront/130-迷雾呈现与地图比例修复及rc21交付.md',
    'docs/paper-warfront/03-美术风格圣经.md', 'docs/paper-warfront/07-交互与UI规范.md',
    'docs/paper-warfront/11-Godot架构与数据契约.md', 'docs/paper-warfront/16-玩家手册.md',
    'output/qa/godot/fog-render-rc21/release/fog-render/report.json',
    'output/qa/godot/fog-render-rc21/release/stage-proportions/report.json',
    'output/qa/godot/fog-render-rc21/stage-short-boundary/report.json',
    'output/qa/godot/fog-render-rc21/stage-short-boundary/short/report.json',
    'output/qa/godot/fog-render-rc21/release/duel-stage/report.json',
    'output/qa/godot/fog-render-rc21/release/mobile/mobile-matrix.json',
    'output/qa/godot/fog-render-rc21/formal-reach/regression/report.json',
    'output/qa/godot/fog-render-rc21/figures/comparisons.json',
    'release/3.0.0-rc21-preview/build-manifest.json', 'release/3.0.0-rc21-preview/preview-verification.json',
]
manifest = read(RELEASE / 'build-manifest.json')
ui = read(ROOT / 'assets/paper-warfront/ui/paper-ui.json')
record = {
    'revision': 'rc21-fog-stage-r1', 'version': manifest['version'], 'status': 'verified-preview',
    'assets': [{'id': 'effect.common.theatre_fog', 'implementation': 'native Godot ArrayMesh',
                'source': 'game/scripts/theatre_fog.gd', 'new_raster_generation': False}],
    'style_tokens_version': '1.1.0',
    'reused_ui_asset_version': ui['version'], 'reused_ui_assets': len(ui['assets']),
    'reused_ui_generation_model': ui['model'],
    'unchanged_actual_rc20_rc21_gameplay_bytecode_and_data': unchanged,
    'original_reference_scope': 'Publisher screenshot visual analysis and existing PC HD screenshot; original games not run or measured frame by frame.',
    'checks': verification['fog_and_stage_verified'],
    'android_hardware_verified': False, 'full_balance_verified': False,
    'files': {name: sha(ROOT / name) for name in paths},
    'builds_and_archives': manifest['builds'] + manifest['archives'],
}
for item in record['builds_and_archives']:
    assert sha(ROOT / item['path']) == item['sha256']
target = ROOT / 'assets/paper-warfront/presentation-revisions/rc21-fog-stage-r1.json'
target.parent.mkdir(parents=True, exist_ok=True)
target.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
assert all(sha(ROOT / name) == value for name, value in record['files'].items())
print('Presentation revision verified:', len(record['files']), 'references;', len(unchanged), 'unchanged compiled gameplay/data inputs')
