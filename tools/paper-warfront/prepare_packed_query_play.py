"""Native-play candidate with current reviewed assets and frozen rc27 gameplay."""
from pathlib import Path
import hashlib
import json
import shutil
from runtime_asset_inputs import runtime_asset_inputs

ROOT=Path(__file__).resolve().parents[2]
QA=ROOT/'output/qa/godot/packed-query-rc28'
source=QA/'all-r2-runtime'
target=QA/'play-all-r2-r3-runtime'
assert not target.exists(), 'Never overwrite a started native candidate'
target.mkdir(parents=True)
manifest=json.loads((ROOT/'release/3.0.0-rc27-preview/build-manifest.json').read_text('utf-8'))
public_files=list(manifest['source_inputs'])
public_files.extend(p.relative_to(ROOT).as_posix() for p in runtime_asset_inputs(ROOT/'game'))
for suffix in ['*.tscn','*.tres','*.gd.uid']:
    public_files.extend(p.relative_to(ROOT).as_posix() for p in (ROOT/'game').rglob(suffix) if '.godot' not in p.parts)
imports=[]
for name in sorted(set(public_files)):
    original=ROOT/name
    destination=target/original.relative_to(ROOT/'game')
    destination.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(original,destination)
    descriptor=Path(str(original)+'.import')
    if descriptor.exists():
        shutil.copy2(descriptor,Path(str(destination)+'.import'))
        imports.extend(descriptor.read_text('utf-8').splitlines())
for name in ['battle_sim.gd','battle_view.gd']:
    shutil.copy2(source/'scripts'/name,target/'scripts'/name)
# Texture/font import bytes correspond to the unchanged source resources. Copy
# only import artifacts; script/editor caches are deliberately excluded.
for line in imports:
    if 'res://.godot/imported/' not in line:continue
    for token in line.split('"'):
        if token.startswith('res://.godot/imported/'):
            artifact=ROOT/'game'/token.removeprefix('res://')
            if artifact.is_file():
                destination=target/token.removeprefix('res://');destination.parent.mkdir(parents=True,exist_ok=True)
                shutil.copy2(artifact,destination)
uid_cache=ROOT/'game/.godot/uid_cache.bin'
if uid_cache.exists():shutil.copy2(uid_cache,target/'.godot/uid_cache.bin')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
inputs={p.relative_to(target).as_posix():sha(p) for p in target.rglob('*') if p.is_file() and '.godot' not in p.parts}
(target/'play-inputs.json').write_text(json.dumps({'scope':'Isolated native source candidate, current rc27 assets/project settings, typed queries and exact cached draw ordering. Not an exported release. Copied import artifacts only serve unchanged raster/font sources.','parent':str(source.relative_to(ROOT)),'generator_sha256':sha(Path(__file__)),'inputs':inputs},ensure_ascii=False,indent=2)+'\n','utf-8')
print('Prepared native candidate',target)
