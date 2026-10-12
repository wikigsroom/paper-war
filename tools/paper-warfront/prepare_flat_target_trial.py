"""Freeze ranged sight records without changing the original linear order."""
from pathlib import Path
import hashlib,json,shutil
ROOT=Path(__file__).resolve().parents[2]
QA=ROOT/'output/qa/godot/realtime-performance-rc26'
target=QA/'flat-target-runtime'
assert not target.exists(), 'Never overwrite frozen candidates'
shutil.copytree(QA/'blocker-query-r2-runtime',target)
p=target/'scripts/battle_sim.gd';s=p.read_text('utf-8')
s=s.replace('var melee_neighbor_edges: Dictionary={}', 'var melee_neighbor_edges: Dictionary={}\nvar ranged_query_records: Array=[[],[]]\nvar ranged_query_revision: int=-1\nvar ranged_query_valid: bool=true')
s=s.replace('\tmelee_query_roads=[{},{}];melee_query_revision=-1;melee_neighbor_edges.clear()', '\tmelee_query_roads=[{},{}];melee_query_revision=-1;melee_neighbor_edges.clear()\n\tranged_query_records=[[],[]];ranged_query_revision=-1')
s=s.replace('\tmelee_query_revision=-1\n\tmovement_side_units=', '\tmelee_query_revision=-1;ranged_query_revision=-1\n\tmovement_side_units=')
helper='''func prepare_ranged_queries():
\tif ranged_query_revision==visibility.revision:return
\tranged_query_records=[[],[]];ranged_query_valid=true
\tfor observer in [0,1]:
\t\tfor actor_value in visibility.enemies[observer]:
\t\t\tvar anchor: Dictionary=physical_anchor(actor_value)
\t\t\tvar point: Vector2=Vector2(anchor.x,anchor.y)
\t\t\tif not is_finite(point.x) or not is_finite(point.y):ranged_query_valid=false
\t\t\tvar support: bool=not actor_value.get("building",false) and db.balance.units[actor_value.id].get("role","") in ["medic","engineer","scribe","necromancer","summoner","illusionist","oracle"]
\t\t\tranged_query_records[observer].append({"actor":actor_value,"point":point,"support":support})
\tranged_query_revision=visibility.revision

'''
s=s.replace('func nearest_enemy(u: Dictionary)', helper+'func nearest_enemy(u: Dictionary)')
old='\tfor e in visibility.enemies[side]:\n\t\tif e.side==side or e.hp<=0:continue'
assert s.count(old)==1
s=s.replace(old,'''\tif not melee and movement_sides_active:
\t\tprepare_ranged_queries()
\t\tif ranged_query_valid:
\t\t\tfor record in ranged_query_records[side]:
\t\t\t\tvar e: Dictionary=record.actor
\t\t\t\tif int(e.side)==side or e.hp<=0:continue
\t\t\t\tvar d: float=origin.distance_to(record.point)
\t\t\t\tvar score: float=d*.35 if priority and record.support and d<=reach else d
\t\t\t\tif score<distance:best=e;distance=score
\t\t\treturn best
'''+old)
p.write_text(s,'utf-8')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
(target/'flat-target-inputs.json').write_text(json.dumps({'scope':'Frozen per-phase sight record trial. Original order, exact Vector2 distances and support priorities retained. Parent receipts historical.', 'generator_sha256':sha(Path(__file__)), 'inputs':{p.relative_to(target).as_posix():sha(p) for p in target.rglob('*') if p.is_file() and p.suffix in ['.gd','.json']}},indent=2),'utf-8')
print('Frozen ranged sight records')
