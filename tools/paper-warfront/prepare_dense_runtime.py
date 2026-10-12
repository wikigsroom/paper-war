"""Freeze rc29 inputs and its complete script closure for dense-combat trials."""
from pathlib import Path
import hashlib
import json
import re
import shutil

ROOT = Path(__file__).resolve().parents[2]
QA = ROOT / 'output/qa/godot/dense-runtime-rc30'
BASE = QA / 'baseline-runtime'
ORACLE = QA / 'oracle-runtime'
assert not BASE.exists() and not ORACLE.exists(), 'Started trials are immutable'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
manifest = json.loads((QA / 'baseline-build-manifest.json').read_text('utf-8'))
assert all(sha(ROOT / name) == digest for name, digest in manifest['source_inputs'].items())
for part in ['scripts', 'data', 'tests']:
    shutil.copytree(ROOT / 'game' / part, BASE / part)
(BASE / 'project.godot').write_text(
    'config_version=5\n[application]\nconfig/name="Dense-combat CPU trial"\n'
    '[rendering]\nrenderer/rendering_method="gl_compatibility"\n', 'utf-8')
config = json.loads((QA / 'native-baseline-layers-r1/report.json').read_text('utf-8'))['config']
(BASE / 'capacity-config.json').write_text(json.dumps(config, ensure_ascii=False, indent=2), 'utf-8')
for name in ['capacity_cpu_profiler.gd', 'probe_capacity_cpu.gd']:
    shutil.copyfile(ROOT / 'tools/paper-warfront' / name, BASE / 'tests' / name)
shutil.copytree(BASE / 'scripts', ORACLE / 'scripts')
absolute = (ORACLE / 'scripts').as_posix() + '/'
oracle_rows = {}
for path in sorted((ORACLE / 'scripts').glob('*.gd')):
    original = path.read_text('utf-8')
    rewritten = re.sub(r'res://scripts/', absolute, original)
    path.write_text(rewritten, 'utf-8')
    oracle_rows[path.name] = {'source_sha256': sha(BASE / 'scripts' / path.name), 'oracle_sha256': sha(path)}
inputs = {p.relative_to(BASE).as_posix(): sha(p) for p in sorted(BASE.rglob('*')) if p.is_file()}
(QA / 'freeze.json').write_text(json.dumps({
    'release': manifest['version'], 'public_inputs': manifest['source_inputs'],
    'runtime_inputs': inputs, 'oracle_scripts': oracle_rows,
    'generator_sha256': sha(Path(__file__)),
    'scope': 'Unmodified rc29 GDScript/data/test input snapshot. Oracle rewrites only internal script paths to the frozen absolute closure. No gameplay or raster edits.'
}, ensure_ascii=False, indent=2) + '\n', 'utf-8')
print('Frozen dense runtime:', len(inputs), 'files;', len(oracle_rows), 'original scripts')
