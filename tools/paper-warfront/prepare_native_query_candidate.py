"""Stage an immutable native query candidate with resolved release assets."""
import argparse
import hashlib
import json
import shutil
from pathlib import Path

from runtime_asset_inputs import runtime_asset_inputs

ROOT = Path(__file__).resolve().parents[2]
ap = argparse.ArgumentParser()
ap.add_argument('--candidate', type=Path, required=True)
ap.add_argument('--output', type=Path, required=True)
args = ap.parse_args()
source = args.candidate.resolve()
target = args.output.resolve()
assert source.is_dir() and not target.exists(), 'Preserve every started candidate'
game = ROOT / 'game'
manifest = json.loads((ROOT / 'release/3.0.0-rc27-preview/build-manifest.json').read_text('utf-8'))
paths = {ROOT / name for name in manifest['source_inputs']}
paths.update(runtime_asset_inputs(game))
for pattern in ('*.tscn', '*.tres', '*.gd.uid'):
    paths.update(p for p in game.rglob(pattern) if '.godot' not in p.parts)
target.mkdir(parents=True)
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
imports = set()
for original in sorted(paths):
    relative = original.relative_to(game)
    destination = target / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    candidate_file = source / relative
    # Candidate changes are limited to three individually reviewed scripts.
    staged = candidate_file if relative.as_posix() in {
        'scripts/battle_sim.gd', 'scripts/battle_view.gd', 'scripts/unit_abilities.gd'
    } else original
    shutil.copy2(staged, destination)
    descriptor = Path(str(original) + '.import')
    if descriptor.is_file():
        shutil.copy2(descriptor, Path(str(destination) + '.import'))
        for token in descriptor.read_text('utf-8').split('"'):
            if token.startswith('res://.godot/imported/'):
                imports.add(game / token.removeprefix('res://'))
for original in sorted(imports):
    assert original.is_file(), original
    destination = target / original.relative_to(game)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(original, destination)
uid = game / '.godot/uid_cache.bin'
shutil.copy2(uid, target / '.godot/uid_cache.bin')
inputs = {p.relative_to(target).as_posix(): sha(p) for p in sorted(target.rglob('*'))
          if p.is_file() and '.godot' not in p.parts}
(target / 'play-inputs.json').write_text(json.dumps({
    'scope': 'Isolated native source candidate, rc27 reviewed assets/settings; only simulation, draw ordering and ability query gate differ. Not a release or Android hardware test.',
    'candidate': source.relative_to(ROOT).as_posix(),
    'generator_sha256': sha(Path(__file__)),
    'asset_resolver_sha256': sha(Path(__file__).with_name('runtime_asset_inputs.py')),
    'inputs': inputs,
    'imports': {p.relative_to(game).as_posix(): sha(p) for p in sorted(imports)},
}, ensure_ascii=False, indent=2) + '\n', 'utf-8')
print('Prepared native candidate', target, 'files', len(inputs), flush=True)
