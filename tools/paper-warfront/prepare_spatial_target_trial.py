"""Freeze a spatial candidate tree; exact prior distances decide every target."""
from pathlib import Path
import hashlib,json,shutil
ROOT=Path(__file__).resolve().parents[2]
QA=ROOT/'output/qa/godot/realtime-performance-rc26'
target=QA/'spatial-target-runtime'
assert not target.exists(), 'Never overwrite frozen candidates'
shutil.copytree(QA/'blocker-query-r2-runtime',target)
tree='''extends RefCounted
# The tree only rejects distant candidates. The original Vector2 distance,
# support multiplier and sight-list rank still determine the selected actor.
var root: Dictionary={}
var valid: bool=true
var side: int=0
func rebuild(sim,owner_side: int,actors: Array):
\tside=owner_side;valid=true
\tvar records: Array=[]
\tfor i in range(actors.size()):
\t\tvar actor: Dictionary=actors[i]
\t\tvar anchor: Dictionary=sim.physical_anchor(actor)
\t\tvar point: Vector2=Vector2(anchor.x,anchor.y)
\t\tif not is_finite(point.x) or not is_finite(point.y):valid=false
\t\tvar support: bool=not actor.get("building",false) and sim.db.balance.units[actor.id].get("role","") in ["medic","engineer","scribe","necromancer","summoner","illusionist","oracle"]
\t\trecords.append({"actor":actor,"point":point,"rank":i,"support":support})
\troot=build(records) if valid and not records.is_empty() else {}
func build(records: Array) -> Dictionary:
\tvar low: Vector2=records[0].point;var high: Vector2=low;var support: bool=false
\tfor record in records:
\t\tlow=low.min(record.point);high=high.max(record.point);support=support or record.support
\tvar node: Dictionary={"low":low,"high":high,"support":support}
\tif records.size()<=4:node["records"]=records;return node
\tvar axis: int=0 if high.x-low.x>=high.y-low.y else 1
\trecords.sort_custom(func(a,b):return int(a.rank)<int(b.rank) if a.point[axis]==b.point[axis] else a.point[axis]<b.point[axis])
\tvar half: int=records.size()/2
\tnode["left"]=build(records.slice(0,half));node["right"]=build(records.slice(half))
\treturn node
func lower_bound(node: Dictionary,origin: Vector2,priority: bool) -> float:
\tvar distance: float=origin.distance_to(origin.clamp(node.low,node.high))
\treturn distance*.35 if priority and node.support else distance
func nearest(origin: Vector2,priority: bool,reach: float) -> Dictionary:
\tvar best: Dictionary={};var distance: float=10000.0;var rank: int=2147483647
\tif root.is_empty():return best
\tvar pending: Array=[root]
\twhile not pending.is_empty():
\t\tvar node: Dictionary=pending.pop_back()
\t\t# Generous broad-phase tolerance protects float32 Vector2 rounding.
\t\tif lower_bound(node,origin,priority)>distance+.0001:continue
\t\tif node.has("records"):
\t\t\tfor record in node.records:
\t\t\t\tvar actor: Dictionary=record.actor
\t\t\t\tif actor.hp<=0 or int(actor.side)==side:continue
\t\t\t\tvar d: float=origin.distance_to(record.point)
\t\t\t\tvar score: float=d*.35 if priority and record.support and d<=reach else d
\t\t\t\tif score<distance or (not best.is_empty() and score==distance and int(record.rank)<rank):
\t\t\t\t\tbest=actor;distance=score;rank=int(record.rank)
\t\telse:
\t\t\tvar left: Dictionary=node.left;var right: Dictionary=node.right
\t\t\tif lower_bound(left,origin,priority)<lower_bound(right,origin,priority):pending.append(right);pending.append(left)
\t\t\telse:pending.append(left);pending.append(right)
\treturn best
'''
(target/'scripts/battle_target_tree.gd').write_text(tree,'utf-8')
p=target/'scripts/battle_sim.gd';s=p.read_text('utf-8')
s=s.replace('var melee_neighbor_edges: Dictionary={}', 'var melee_neighbor_edges: Dictionary={}\nconst TargetTree=preload("res://scripts/battle_target_tree.gd")\nvar ranged_query_trees: Array=[TargetTree.new(),TargetTree.new()]\nvar ranged_query_revision: int=-1')
s=s.replace('\tmelee_query_roads=[{},{}];melee_query_revision=-1;melee_neighbor_edges.clear()', '\tmelee_query_roads=[{},{}];melee_query_revision=-1;melee_neighbor_edges.clear()\n\tranged_query_trees=[TargetTree.new(),TargetTree.new()];ranged_query_revision=-1')
s=s.replace('\tmelee_query_revision=-1\n\tmovement_side_units=', '\tmelee_query_revision=-1;ranged_query_revision=-1\n\tmovement_side_units=')
old='\tfor e in visibility.enemies[side]:\n\t\tif e.side==side or e.hp<=0:continue'
assert s.count(old)==1
s=s.replace(old, '''\tif not melee and movement_sides_active and is_finite(origin.x) and is_finite(origin.y):
\t\tif ranged_query_revision!=visibility.revision:
\t\t\tfor observer in [0,1]:ranged_query_trees[observer].rebuild(self,observer,visibility.enemies[observer])
\t\t\tranged_query_revision=visibility.revision
\t\tif ranged_query_trees[side].valid:return ranged_query_trees[side].nearest(origin,priority,reach)
'''+old)
p.write_text(s,'utf-8')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
(target/'spatial-inputs.json').write_text(json.dumps({'scope':'Frozen spatial candidate pruning; exact prior Vector2 distances, multipliers and sight ranks retained. Parent receipts historical.', 'generator_sha256':sha(Path(__file__)), 'inputs':{p.relative_to(target).as_posix():sha(p) for p in target.rglob('*') if p.is_file() and p.suffix in ['.gd','.json']}},indent=2),'utf-8')
print('Frozen ranged target spatial tree')
