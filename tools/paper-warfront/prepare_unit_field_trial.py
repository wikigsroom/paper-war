"""Typed live dictionary references; preserve mutation order and combat timing."""
from pathlib import Path
import argparse,hashlib,json,shutil
ROOT=Path(__file__).resolve().parents[2]
QA=ROOT/'output/qa/godot/packed-query-rc28'
ap=argparse.ArgumentParser();ap.add_argument('variant',choices=['typed','packed-typed']);args=ap.parse_args()
parent=QA/('baseline-runtime' if args.variant=='typed' else 'all-r2-runtime')
target=QA/(args.variant+'-runtime');assert not target.exists()
shutil.copytree(parent,target,ignore=shutil.ignore_patterns('.godot','inputs.json','candidate-inputs.json'))
path=target/'scripts/battle_sim.gd';text=path.read_text('utf-8')
text=text.replace('var map\n','var map: MapRuntime\n',1)
start=text.index('func tick_unit(');end=text.index('func update_ranged_formations(',start)
chunk=text[start:end]
chunk=chunk.replace('var def=db.balance.units[u.id]','var def: Dictionary=db.balance.units[u.id]\n\tvar statuses: Dictionary=u.statuses',1)
chunk=chunk.replace('u.statuses','statuses').replace('var statuses: Dictionary=statuses','var statuses: Dictionary=u.statuses')
chunk=chunk.replace('var status=statuses[key]','var status: Dictionary=statuses[key]')
chunk=chunk.replace('var enemy=nearest_enemy(u)','var enemy: Dictionary=nearest_enemy(u)')
chunk=chunk.replace('float(def.range)','weapon_range')
chunk=chunk.replace('if def.get("economy",false): tick_worker(u,dt); return','if def.get("economy",false): tick_worker(u,dt); return\n\tvar weapon_range: float=float(def.range)',1)
text=text[:start]+chunk+text[end:]
text=text.replace('var def = db.balance.buildings[u.id] if u.get("building",false) else db.balance.units[u.id]','var def: Dictionary = db.balance.buildings[u.id] if u.get("building",false) else db.balance.units[u.id]',1)
path.write_text(text,'utf-8')
path=target/'scripts/unit_abilities.gd';text=path.read_text('utf-8')
old='if u.clone or def.get("summoned",false) or sim.population(u.side)>=60: return'
assert text.count(old)==1
text=text.replace(old,'if u.clone or def.get("summoned",false):return\n\tif not def.has("auto_guardian_seconds") and not def.has("auto_clone_seconds"):return\n\tif sim.population(u.side)>=60:return',1)
path.write_text(text,'utf-8')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
(target/'field-inputs.json').write_text(json.dumps({'parent':parent.relative_to(ROOT).as_posix(),'generator_sha256':sha(Path(__file__)),'scope':'Isolated candidate. Typed dictionary/MapRuntime access, aliased live status dictionary and immutable per-call weapon range; clock and mutation order retained. Skip pure population query only for definitions without automatic spawn abilities.','inputs':{p.relative_to(target).as_posix():sha(p) for p in target.rglob('*') if p.is_file()}},ensure_ascii=False,indent=2)+'\n','utf-8')
print('Prepared',target)
