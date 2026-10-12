"""Adopt rc28 queries only after independent rules, full-state and pixel proofs."""
from pathlib import Path
import hashlib
import json
import shutil

ROOT = Path(__file__).resolve().parents[2]
QA = ROOT / 'output/qa/godot/packed-query-rc28'
CANDIDATE = QA / 'axis-target-r2-runtime'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
read = lambda p: json.loads(p.read_text('utf-8'))
receipt = QA / 'adoption.json'
assert not receipt.exists(), 'Never repeat a public adoption'
before = read(QA / 'pre-adoption/inputs.json')['inputs']
assert all(sha(ROOT / name) == row['sha256'] for name, row in before.items())
closure = read(QA / 'oracle-runtime/closure-inputs.json')
for name, row in closure['scripts'].items():
    assert sha(QA / 'baseline-runtime/scripts' / name) == row['original_sha256']
    assert sha(QA / 'oracle-runtime/scripts' / name) == row['oracle_sha256']
for folder in ('data', 'scripts'):
    for original in (QA / 'baseline-runtime' / folder).glob('*'):
        if original.is_file():
            assert sha(original) == sha(ROOT / 'game' / folder / original.name)
proofs = {}
for name, count in [('capacity-axis-original-closure', 3600),
                    ('paid-axis-original-closure', 73103),
                    ('target-axis-r2', 58576), ('marching-axis-r2', 13600),
                    ('leap-axis-r2', 1200), ('unit-order-axis-r2', 1200),
                    ('axis-boundaries-r2', 20)]:
    path = QA / (name + '.json')
    result = read(path)
    assert not result['failures'] and result['checks'] == count, name
    assert result.get('passed', True), name
    sim_hash = result.get('simulation_sha256', result.get('source_sha256',
        result.get('inputs', {}).get('res://scripts/battle_sim.gd')))
    assert sim_hash == sha(CANDIDATE / 'scripts/battle_sim.gd'), name
    proofs[path.relative_to(ROOT).as_posix()] = sha(path)
capacity = read(QA / 'capacity-axis-original-closure.json')
assert capacity['source_unchanged'] and capacity['loaded_source_matches']
oracle_hash = sha(QA / 'oracle-runtime/scripts/battle_sim.gd')
assert capacity['baseline_sha256'] == oracle_hash
assert read(QA / 'paid-axis-original-closure.json')['baseline_sha256'] == oracle_hash
pixel = read(QA / 'native-axis-render/report.json')
assert pixel['passed'] and len(pixel['comparisons']) == 12
proofs[(QA / 'native-axis-render/report.json').relative_to(ROOT).as_posix()] = sha(QA / 'native-axis-render/report.json')
for name in ('battle_sim.gd', 'battle_view.gd', 'unit_abilities.gd'):
    source = CANDIDATE / 'scripts' / name
    assert sha(source) == sha(QA / 'play-axis-r2-runtime/scripts' / name)
    shutil.copy2(source, ROOT / 'game/scripts' / name)

for original, destination in [
    ('probe_unit_order_equivalence.gd', 'test_unit_order_equivalence.gd'),
    ('test_axis_target_boundaries.gd', 'test_axis_target_boundaries.gd')
]:
    target = ROOT / 'game/tests' / destination
    assert not target.exists(), destination
    content = (ROOT / 'tools/paper-warfront' / original).read_text('utf-8')
    # The same meaningful observer can run without an output argument in both
    # compiled package suites; optional JSON output retains its full evidence.
    marker = '\tvar args=OS.get_cmdline_user_args();var output: String=args[args.find("--output")+1]\n'
    assert marker in content
    content = content.replace(marker, '\tvar args=OS.get_cmdline_user_args()\n\tif args.has("--output"):\n\t\tvar output: String=args[args.find("--output")+1]\n', 1)
    content = content.replace('\tFileAccess.open(output,FileAccess.WRITE).store_string', '\t\tFileAccess.open(output,FileAccess.WRITE).store_string', 1)
    target.write_bytes(content.encode('utf-8'))

for name in ('project.godot', 'export_presets.cfg'):
    path = ROOT / 'game' / name
    content = path.read_text('utf-8')
    assert '3.0.0-rc27-preview' in content
    content = content.replace('3.0.0-rc27-preview', '3.0.0-rc28-preview')
    if name == 'export_presets.cfg':
        assert 'version/code=30026' in content
        content = content.replace('version/code=30026', 'version/code=30027')
    path.write_bytes(content.encode('utf-8'))
changed = {p.relative_to(ROOT).as_posix(): sha(p) for p in [
    *(ROOT / 'game/scripts' / n for n in ('battle_sim.gd', 'battle_view.gd', 'unit_abilities.gd')),
    *(ROOT / 'game/tests' / n for n in ('test_unit_order_equivalence.gd', 'test_axis_target_boundaries.gd')),
    ROOT / 'game/project.godot', ROOT / 'game/export_presets.cfg']}
receipt.write_text(json.dumps({'passed': True, 'generator_sha256': sha(Path(__file__)),
    'proofs': proofs, 'adopted_inputs': changed,
    'scope': 'Behavior-preserving simulation/query and render-order implementation. No raster, map, story, price, hit rules, population or FX changes. Compilation, release rendering and real-time performance still require fresh checks.'},
    ensure_ascii=False, indent=2) + '\n', 'utf-8')
print('Adopted rc28 query implementation after independent proofs')
