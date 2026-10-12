"""Build an isolated source-play trial from all rc29 manifest/import inputs."""
from pathlib import Path
import hashlib
import json
import shutil

ROOT = Path(__file__).resolve().parents[2]
QA = ROOT / 'output/qa/godot/dense-runtime-rc30'
TARGET = QA / 'native-phase-reuse-r2-runtime'
assert not TARGET.exists(), 'Do not overwrite a started native-play trial'
manifest = json.loads((QA / 'baseline-build-manifest.json').read_text('utf-8'))
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert all(sha(ROOT / name) == digest for name, digest in manifest['source_inputs'].items())
imports = set()
for name in manifest['source_inputs']:
    source = ROOT / name
    destination = TARGET / source.relative_to(ROOT / 'game')
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    if source.suffix == '.import':
        for token in source.read_text('utf-8').split('"'):
            if token.startswith('res://.godot/imported/'):
                imports.add(token.removeprefix('res://'))
for name in imports:
    source = ROOT / 'game' / name
    if source.is_file():
        destination = TARGET / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
uid_cache = ROOT / 'game/.godot/uid_cache.bin'
if uid_cache.exists():shutil.copy2(uid_cache, TARGET / '.godot/uid_cache.bin')
for name in ['battle_sim.gd','map_runtime.gd','battle_visibility.gd']:
    shutil.copy2(QA / 'phase-reuse-r2-runtime/scripts' / name, TARGET / 'scripts' / name)
(QA / 'native-phase-reuse-r2-inputs.json').write_text(json.dumps({
    'release_asset_inputs': manifest['source_inputs'],
    'changed_script_inputs': {name: sha(TARGET / 'scripts' / name) for name in ['battle_sim.gd','map_runtime.gd','battle_visibility.gd']},
    'copied_import_inputs': {name: sha(TARGET / name) for name in imports if (TARGET / name).is_file()},
    'generator_sha256': sha(Path(__file__)),
    'scope': 'Isolated native source gameplay trial, unchanged current rc29 raster/font/audio and project settings. Import cache derives from unchanged bound source assets. This is not an exported preview.'
}, indent=2) + '\n', 'utf-8')
print('Prepared complete native-play candidate:', len(manifest['source_inputs']), 'source files')
