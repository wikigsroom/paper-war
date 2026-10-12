"""Retain canonical zero-travel projections and avoid repeated weak-owner reads."""
from pathlib import Path
import difflib
import hashlib
import json
import re
import shutil

ROOT = Path(__file__).resolve().parents[2]
QA = ROOT / 'output/qa/godot/dense-runtime-rc30'
BASE = QA / 'target-reuse-r1-runtime'
TARGET = QA / 'phase-reuse-r2-runtime'
assert not TARGET.exists(), 'Started candidates are immutable'
shutil.copytree(BASE, TARGET)
path = TARGET / 'scripts/map_runtime.gd'
original_map = path.read_text('utf-8')
source = original_map.replace('var ground_surface: PackedVector2Array = PackedVector2Array()', '''var ground_surface: PackedVector2Array = PackedVector2Array()
# A zero-distance advance still canonicalizes its input the first time. Retain
# only exact finite canonical projections; raw or edited anchors use the old path.
var stationary_projections: Dictionary={}
var stationary_projection_order: Array[int]=[]
const STATIONARY_PROJECTION_LIMIT: int=256
var stationary_projection_hits: int=0

class StationaryProjection:
	extends RefCounted
	var actor_ref: Dictionary
	var edge_id: String
	var offset: float
	var x: float
	var y: float
	var edge_length: float
	var points: Array
	var cumulative: Array
	func _init(actor: Dictionary,edge: Dictionary):
		actor_ref=actor;edge_id=str(actor.edge);offset=float(actor.s);x=float(actor.x);y=float(actor.y)
		edge_length=float(edge.length);points=edge.points.duplicate();cumulative=edge.cumulative.duplicate()
	func matches(actor: Dictionary,edge: Dictionary) -> bool:
		return is_same(actor,actor_ref) and typeof(actor.edge)==TYPE_STRING and typeof(actor.s)==TYPE_FLOAT and typeof(actor.x)==TYPE_FLOAT and typeof(actor.y)==TYPE_FLOAT and actor.edge==edge_id and actor.s==offset and actor.x==x and actor.y==y and float(edge.length)==edge_length and edge.points==points and edge.cumulative==cumulative
''', 1)
source = source.replace('func advance(actor: Dictionary, distance: float, side: int) -> Array:\n', '''func advance(actor: Dictionary, distance: float, side: int) -> Array:
	var stationary: bool=is_finite(distance) and distance<=0 and actor.has("uid") and int(actor.uid)>0
	if stationary and stationary_projections.has(int(actor.uid)):
		var previous: StationaryProjection=stationary_projections[int(actor.uid)]
		if previous.matches(actor,edges[actor.edge]):stationary_projection_hits+=1;return []
''', 1)
old = '\tapply_anchor(actor,anchor(actor.edge,float(actor.s)))\n\treturn crossed'
assert source.count(old) == 1
source = source.replace(old, '''	apply_anchor(actor,anchor(actor.edge,float(actor.s)))
	if stationary and is_finite(float(actor.s)) and is_finite(float(actor.x)) and is_finite(float(actor.y)):
		var uid: int=int(actor.uid)
		if not stationary_projections.has(uid):
			if stationary_projection_order.size()>=STATIONARY_PROJECTION_LIMIT:stationary_projections.erase(stationary_projection_order.pop_front())
			stationary_projection_order.append(uid)
		stationary_projections[uid]=StationaryProjection.new(actor,edges[actor.edge])
	return crossed''', 1)
path.write_text(source, 'utf-8')
(QA / 'phase-reuse-r2-map.patch').write_text(''.join(difflib.unified_diff(original_map.splitlines(True), source.splitlines(True), fromfile='rc29/map_runtime.gd', tofile='phase-reuse-r2/map_runtime.gd')), 'utf-8')
path = TARGET / 'scripts/battle_visibility.gd'
original_vision = path.read_text('utf-8')
parts = re.split(r'(?=^func )', original_vision, flags=re.MULTILINE)
for index, part in enumerate(parts):
    if not part.startswith('func ') or 'sim.' not in part:
        continue
    header, body = part.split('\n', 1)
    parts[index] = header + '\n\tvar battle=sim\n' + body.replace('sim.', 'battle.')
source = ''.join(parts)
path.write_text(source, 'utf-8')
(QA / 'phase-reuse-r2-vision.patch').write_text(''.join(difflib.unified_diff(original_vision.splitlines(True), source.splitlines(True), fromfile='rc29/battle_visibility.gd', tofile='phase-reuse-r2/battle_visibility.gd')), 'utf-8')
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
(QA / 'phase-reuse-r2-inputs.json').write_text(json.dumps({
    'candidate_inputs': {name:sha(TARGET / 'scripts' / name) for name in ['battle_sim.gd','map_runtime.gd','battle_visibility.gd']},
    'generator_sha256': sha(Path(__file__)),
    'scope': 'Isolated exact target/zero-travel retention and method-scoped weak-owner reads. Projection reuse checks actor identity, exact normalized values and every edge point/cumulative distance; bounded256 entries. Counters are diagnostic only. No simulation-frequency, data or visual changes.'
}, indent=2) + '\n', 'utf-8')
print('Prepared exact phase-cache candidate')
