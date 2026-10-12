"""Freeze an exact nearest eligible same-road marching blocker trial."""
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[2]
QA = ROOT / 'output/qa/godot/realtime-performance-rc26'
prior = QA / 'road-query-r2-runtime'
target = QA / 'blocker-query-runtime'
assert not target.exists(), 'Frozen trials cannot be overwritten'
shutil.copytree(prior, target)
p = target / 'scripts/battle_sim.gd'
s = p.read_text('utf-8')
old_start = s.index('\t\tvar blockers: Array=movement_side_units[int(u.side)]')
old_end = s.index('\t\tvar before_step: Vector2=', old_start)
original = s[old_start:old_end]
fallback = original.replace('\t\t', '\t', 1)
fallback = '\n'.join(line[1:] for line in original.rstrip().split('\n'))
fallback = fallback.replace('\tvar blockers: Array=movement_side_units[int(u.side)] if movement_sides_active else units', '\tvar blockers: Array=units')
helpers = '''func prepare_blocker_roads():
\tblocker_roads=[{},{}];blocker_roads_valid=true
\tfor ally in units:
\t\tvar offset: float=float(ally.s)
\t\tif not is_finite(offset):blocker_roads_valid=false
\t\tif ally.hp<=0 or db.balance.units[ally.id].get("economy",false):continue
\t\tvar roads: Dictionary=blocker_roads[int(ally.side)]
\t\tif not roads.has(ally.edge):roads[ally.edge]=[]
\t\troads[ally.edge].append({"actor":ally,"offset":offset})
\tfor roads in blocker_roads:
\t\tfor records in roads.values():records.sort_custom(func(a,b):return float(a.offset)<float(b.offset))
\tblocker_roads_dirty=false

func marching_step(u: Dictionary,def: Dictionary,enemy: Dictionary,step: float,forward: float) -> float:
\tif step<=0:return step
\tif movement_sides_active:
\t\tif blocker_roads_dirty:prepare_blocker_roads()
\t\tif blocker_roads_valid and is_finite(float(u.s)):
\t\t\tvar records: Array=blocker_roads[int(u.side)].get(u.edge,[])
\t\t\tvar lo: int=0;var hi: int=records.size()
\t\t\twhile lo<hi:
\t\t\t\tvar middle: int=(lo+hi)/2
\t\t\t\tif float(records[middle].offset)<=float(u.s):lo=middle+1
\t\t\t\telse:hi=middle
\t\t\tvar index: int=lo if forward>0 else lo-1
\t\t\tvar gap: float=.72 if def.get("role","")=="colossus" else .54
\t\t\twhile index>=0 and index<records.size():
\t\t\t\tvar record: Dictionary=records[index]
\t\t\t\tvar ahead: float=(float(record.offset)-float(u.s))*forward
\t\t\t\tif ahead>step+gap:break
\t\t\t\tvar ally: Dictionary=record.actor
\t\t\t\tindex+=1 if forward>0 else -1
\t\t\t\tif ahead<=0 or ally.uid==u.uid or ally.side!=u.side or ally.hp<=0 or ally.edge!=u.edge:continue
\t\t\t\tvar other: Dictionary=db.balance.units[ally.id]
\t\t\t\tif float(def.range)<=1.5 and (float(other.range)>1.5 or other.get("role","") in ["medic","engineer","necromancer","summoner","oracle","scribe"]):continue
\t\t\t\tif not enemy.is_empty() and float(def.range)>1.5 and float(other.range)>float(def.range)+.05:continue
\t\t\t\treturn minf(step,maxf(0,ahead-gap))
\t\t\treturn step
'''
helpers += fallback + '\n\treturn step\n\n'
s = s[:old_start] + '\t\tstep=marching_step(u,def,enemy,step,forward)\n' + s[old_end:]
s = s.replace('var movement_sides_active: bool=false', 'var movement_sides_active: bool=false\nvar blocker_roads: Array=[{},{}]\nvar blocker_roads_dirty: bool=true\nvar blocker_roads_valid: bool=true')
s = s.replace('if movement_sides_active:movement_side_units[side].append(u)', 'if movement_sides_active:\n\t\tmovement_side_units[side].append(u);blocker_roads_dirty=true')
s = s.replace('func prepare_movement_sides():\n', 'func prepare_movement_sides():\n\tblocker_roads_dirty=true\n')
s = s.replace('func movement_anchor(u: Dictionary)', helpers + 'func movement_anchor(u: Dictionary)')
p.write_text(s, 'utf-8')
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
(target/'blocker-inputs.json').write_text(json.dumps({'scope':'Frozen candidate; parent receipts refer only to prior inputs.',
    'generator_sha256':sha(Path(__file__)), 'parent_receipt_sha256':sha(prior/'precision-inputs.json'),
    'inputs':{p.relative_to(target).as_posix():sha(p) for p in sorted(target.rglob('*')) if p.is_file() and (p.suffix in ['.gd','.json'] or p.name=='project.godot')}},indent=2), 'utf-8')
print('Frozen nearest eligible marching blocker candidate')
