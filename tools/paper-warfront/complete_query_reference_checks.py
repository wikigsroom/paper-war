"""Retain unchanged checks and verify the corrected external reference path."""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[2]
QA = ROOT / 'output/qa/godot/packed-query-rc28'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
name = 'test_axis_target_boundaries.gd'
source = ROOT / 'game/tests' / name
original = QA / 'package-reference-before' / name
assert source.read_text('utf-8') == original.read_text('utf-8').replace(
    'preload("res://tests/reference_target_search.gd")', 'preload("reference_target_search.gd")', 1)
folder = QA / 'formal-reach/regression'
report = json.loads((folder / 'report.json').read_text('utf-8'))
assert report['passed'] and report['source_unchanged']
assert all(sha(ROOT / n) == h for n, h in report['inputs'].items())
for test in report['tests']:
    assert sha(original if test['script'] == name else ROOT / 'game/tests' / test['script']) == test['sha256']
archive = QA / 'source-regression-before-package-reference'
assert not archive.exists(), 'Preserve the original complete rule checks'
shutil.move(folder, archive)
shutil.copytree(archive, folder)
run = subprocess.run([str(ROOT / '.tools/godot/Godot_v4.7.2-stable_win64_console.exe'),
    '--headless', '--path', str(ROOT / 'game'), '--script', 'res://tests/' + name],
    cwd=ROOT, capture_output=True, encoding='utf-8', errors='replace', timeout=90)
log = run.stdout + run.stderr
(folder / (name + '.log')).write_text(log, 'utf-8')
assert run.returncode == 0 and 'AXIS_TARGET_BOUNDARIES: 20 checks; failures=[]' in log
assert 'SCRIPT ERROR' not in log and 'ERROR:' not in log
binding = {'path': (archive / 'report.json').relative_to(ROOT).as_posix(), 'sha256': sha(archive / 'report.json')}
for test in report['tests']:
    if test['script'] == name:
        test['sha256'] = sha(source)
        test['reference_path_rechecked'] = True
    else:
        test['retained_identical_inputs'] = binding
report['source_unchanged'] = all(sha(ROOT / n) == h for n, h in report['inputs'].items())
assert report['source_unchanged']
report['reference_path_completion'] = {'changed_harness': name, 'original_report': binding,
    'generator_sha256': sha(Path(__file__)),
    'scope': '20 source checks rerun after a reference-only preload path change;76 unchanged harnesses retained with identical gameplay/data/reference inputs and original complete report hash. Final packages still require all35 checks.'}
(folder / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), 'utf-8')
adoption = QA / 'adoption.json'
completion = QA / 'adoption-completion.json'
assert not completion.exists()
completion.write_text(json.dumps({'passed': True, 'adoption_sha256': sha(adoption),
    'updated_inputs': {source.relative_to(ROOT).as_posix(): sha(source)},
    'previous_input_sha256': sha(original),
    'source_regression_sha256': sha(folder / 'report.json'),
    'reason': 'External packaged boundary observer resolves its unchanged independent reference next to the observer. Playable scripts are unchanged; the observer is excluded by export rules.'}, indent=2), 'utf-8')
print('Reference path20 checks passed;76 unchanged checks retained with input bindings')
