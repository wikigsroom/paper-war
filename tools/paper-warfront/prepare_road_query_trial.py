"""Freeze exact melee candidate queries on the simultaneous phase geometry."""
import difflib
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[2]
QA = ROOT / 'output/qa/godot/realtime-performance-rc26'
prior = QA / 'combined-runtime'
target = QA / 'road-query-runtime'
assert not target.exists(), 'Never overwrite frozen candidates'
shutil.copytree(prior, target)
for name in ['test_target_search_equivalence.gd', 'reference_target_search.gd']:
    shutil.copyfile(ROOT/'game/tests'/name, target/'tests'/name)
p = target/'scripts/battle_visibility.gd'
v = p.read_text('utf-8')
assert v.count('var owner_ref: WeakRef') == 1 and v.count('func refresh():') == 1
v = v.replace('var owner_ref: WeakRef', 'var owner_ref: WeakRef\nvar revision: int=0')
v = v.replace('func refresh():', 'func refresh():\n\trevision+=1')
p.write_text(v, 'utf-8')
p = target/'scripts/battle_sim.gd'
s = p.read_text('utf-8')

def replace(old, new):
    global s
    assert s.count(old) == 1, old
    s = s.replace(old, new)

replace('var movement_sides_active: bool=false', '''var movement_sides_active: bool=false
var melee_query_roads: Array=[{},{}]
var melee_query_revision: int=-1
var melee_query_valid: bool=true
var melee_neighbor_edges: Dictionary={}''')
replace('\tformation_ranges.clear();movement_side_units=[[],[]];movement_sides_active=false',
        '\tformation_ranges.clear();movement_side_units=[[],[]];movement_sides_active=false\n\tmelee_query_roads=[{},{}];melee_query_revision=-1;melee_neighbor_edges.clear()')
replace('func cast(side: int, id: String, x: float, target_uid: int, y: float = NAN) -> String:',
        'func cast(side: int, id: String, x: float, target_uid: int, y: float = NAN) -> String:\n\tmelee_query_revision=-1')
replace('func prepare_movement_sides():\n\tmovement_side_units=[[],[]]',
        'func prepare_movement_sides():\n\tmelee_query_revision=-1\n\tmovement_side_units=[[],[]]')
replace('\tvar side: int=int(u.side)\n\tfor e in visibility.enemies[side]:',
        '''\tvar side: int=int(u.side)
\tif melee and movement_sides_active:
\t\tprepare_melee_queries()
\t\tif melee_query_valid and offset>=0 and offset<=float(map.edges[edge].length):
\t\t\treturn nearest_melee_query(anchor,side,priority,reach)
\tfor e in visibility.enemies[side]:''')

helpers = '''# The unit phase restores every movement intent before the next actor runs.
# Query records therefore share one physical geometry. They retain live actors
# for immediate death/ownership filtering and the original sight-list rank.
func prepare_melee_queries():
\tif melee_query_revision==visibility.revision:return
\tmelee_query_revision=visibility.revision;melee_query_roads=[{},{}];melee_query_valid=true
\tif melee_neighbor_edges.is_empty():
\t\tfor edge_id in map.edges:
\t\t\tvar source: Dictionary=map.edges[edge_id]
\t\t\tvar neighbors: Dictionary={}
\t\t\tfor node_id in [source.from,source.to]:
\t\t\t\tfor link in map.adjacency[node_id]:
\t\t\t\t\tif link.edge==edge_id:continue
\t\t\t\t\tvar edge: Dictionary=map.edges[link.edge]
\t\t\t\t\tif not neighbors.has(link.edge):neighbors[link.edge]=[]
\t\t\t\t\tneighbors[link.edge].append(0.0 if node_id==edge.from else float(edge.length))
\t\t\tmelee_neighbor_edges[edge_id]=neighbors
\tfor side in [0,1]:
\t\tvar rank: int=0
\t\tfor actor_value in visibility.enemies[side]:
\t\t\tvar body: Dictionary=physical_anchor(actor_value)
\t\t\tvar offset: float=float(body.s)
\t\t\tif offset<0 or offset>float(map.edges[body.edge].length):melee_query_valid=false
\t\t\tif not melee_query_roads[side].has(body.edge):melee_query_roads[side][body.edge]={"all":[],"support":[]}
\t\t\tvar support: bool=not actor_value.get("building",false) and db.balance.units[actor_value.id].get("role","") in ["medic","engineer","scribe","necromancer","summoner","illusionist","oracle"]
\t\t\tvar record: Dictionary={"actor":actor_value,"offset":offset,"rank":rank,"support":support,"anchor":{"edge":body.edge,"s":offset}}
\t\t\tmelee_query_roads[side][body.edge].all.append(record)
\t\t\tif support:melee_query_roads[side][body.edge].support.append(record)
\t\t\trank+=1
\t\tfor road in melee_query_roads[side].values():
\t\t\tfor records in [road.all,road.support]:
\t\t\t\trecords.sort_custom(func(a,b):return int(a.rank)<int(b.rank) if float(a.offset)==float(b.offset) else float(a.offset)<float(b.offset))

func nearest_road_record(records: Array,offset: float,side: int) -> Dictionary:
\tvar lo: int=0;var hi: int=records.size()
\twhile lo<hi:
\t\tvar middle: int=(lo+hi)/2
\t\tif float(records[middle].offset)<offset:lo=middle+1
\t\telse:hi=middle
\tvar best: Dictionary={};var distance: float=INF
\tfor direction in [-1,1]:
\t\tvar index: int=lo-1 if direction<0 else lo
\t\twhile index>=0 and index<records.size():
\t\t\tvar record: Dictionary=records[index]
\t\t\tvar next_distance: float=absf(float(record.offset)-offset)
\t\t\tif next_distance>distance:break
\t\t\tvar candidate: Dictionary=record.actor
\t\t\tif candidate.hp>0 and int(candidate.side)!=side:
\t\t\t\tif next_distance<distance or best.is_empty() or int(record.rank)<int(best.rank):
\t\t\t\t\tbest=record;distance=next_distance
\t\t\tindex+=direction
\treturn best

func nearest_melee_query(anchor: Dictionary,side: int,priority: bool,reach: float) -> Dictionary:
\tvar candidates: Array=[]
\tvar roads: Dictionary=melee_query_roads[side]
\tvar requests: Dictionary=melee_neighbor_edges[anchor.edge].duplicate(false)
\trequests[anchor.edge]=[float(anchor.s)]
\tfor edge_id in requests:
\t\tif not roads.has(edge_id):continue
\t\tvar road: Dictionary=roads[edge_id]
\t\tfor offset in requests[edge_id]:
\t\t\tvar normal: Dictionary=nearest_road_record(road.all,float(offset),side)
\t\t\tif not normal.is_empty():candidates.append(normal)
\t\t\tif priority:
\t\t\t\tvar support: Dictionary=nearest_road_record(road.support,float(offset),side)
\t\t\t\tif not support.is_empty():candidates.append(support)
\tvar best: Dictionary={};var distance: float=10000.0;var rank: int=2147483647
\tfor record in candidates:
\t\tvar d: float=map.melee_distance(anchor,record.anchor)
\t\tvar score: float=d*.35 if priority and record.support and d<=reach else d
\t\tif score<distance or (not best.is_empty() and score==distance and int(record.rank)<rank):
\t\t\tbest=record.actor;distance=score;rank=int(record.rank)
\treturn best

'''
replace('func nearest_enemy(u: Dictionary) -> Dictionary:', helpers+'func nearest_enemy(u: Dictionary) -> Dictionary:')
p.write_text(s, 'utf-8')
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
diff = QA/'road-query.diff'
diff.write_text(''.join(difflib.unified_diff((prior/'scripts/battle_sim.gd').read_text('utf-8').splitlines(keepends=True),
                                          s.splitlines(keepends=True), fromfile='combined/battle_sim.gd', tofile='road-query/battle_sim.gd')), 'utf-8')
(target/'road-query-inputs.json').write_text(json.dumps({
    'scope':'Frozen exact-road-query CPU trial, not a rendered performance or paid balance result. Older input receipts are the copied parent baselines.',
    'generator_sha256':sha(Path(__file__)),'prior_candidate_sha256':sha(prior/'candidate-inputs.json'),
    'diff_sha256':sha(diff),'inputs':{p.relative_to(target).as_posix():sha(p) for p in sorted(target.rglob('*')) if p.is_file() and (p.suffix in ['.gd','.json'] or p.name=='project.godot')}
},indent=2),'utf-8')
print('Exact road query candidate frozen; shipping files unchanged')
