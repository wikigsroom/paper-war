"""Trial exact geometry validation before retaining sorted target-query records."""
from pathlib import Path
import difflib
import hashlib
import json
import shutil

ROOT = Path(__file__).resolve().parents[2]
QA = ROOT / 'output/qa/godot/dense-runtime-rc30'
BASE = QA / 'baseline-runtime'
TARGET = QA / 'target-reuse-r1-runtime'
assert not TARGET.exists(), 'A started candidate must not be overwritten'
shutil.copytree(BASE, TARGET)
path = TARGET / 'scripts/battle_sim.gd'
before = path.read_text('utf-8')
source = before

def replace(old, new):
    global source
    assert source.count(old) == 1, old
    source = source.replace(old, new)

replace('var ranged_query_valid: bool=true', '''var ranged_query_valid: bool=true
# Sorted query pools may survive a phase only after every source reference,
# physical road offset, native point and support classification matches.
# Actor dictionaries remain live: hp/side filtering is never cached.
var target_snapshot_revision: int=-1
var target_snapshot_generation: int=0
var target_snapshot_ready: bool=false
var target_snapshots: Array=[]
var melee_snapshot_generation: int=-1
var ranged_snapshot_generation: int=-1
var target_snapshot_reuses: int=0
var target_snapshot_rebuilds: int=0

class TargetGeometrySnapshot:
	extends RefCounted
	var actors: Array[Dictionary]=[]
	var edges: Array[String]=[]
	var offsets: PackedFloat64Array=PackedFloat64Array()
	var points: PackedVector2Array=PackedVector2Array()
	var supports: PackedByteArray=PackedByteArray()
	func matches(source_actors: Array,simulation) -> bool:
		if actors.size()!=source_actors.size():return false
		for index in range(actors.size()):
			var a: Dictionary=source_actors[index]
			if not is_same(a,actors[index]):return false
			var anchor: Dictionary=simulation.physical_anchor(a)
			if anchor.edge!=edges[index] or float(anchor.s)!=offsets[index] or Vector2(anchor.x,anchor.y)!=points[index]:return false
			var support: bool=not a.get("building",false) and simulation.db.balance.units[a.id].get("role","") in ["medic","engineer","scribe","necromancer","summoner","illusionist","oracle"]
			if (1 if support else 0)!=supports[index]:return false
		return true
	func capture(source_actors: Array,simulation):
		for a in source_actors:
			var anchor: Dictionary=simulation.physical_anchor(a)
			actors.append(a);edges.append(anchor.edge);offsets.append(float(anchor.s));points.append(Vector2(anchor.x,anchor.y))
			var support: bool=not a.get("building",false) and simulation.db.balance.units[a.id].get("role","") in ["medic","engineer","scribe","necromancer","summoner","illusionist","oracle"]
			supports.append(1 if support else 0)

func prepare_target_snapshot():
	if target_snapshot_revision==visibility.revision:return
	var matches: bool=target_snapshot_ready
	if matches:
		for side in [0,1]:
			var previous: TargetGeometrySnapshot=target_snapshots[side]
			if not previous.matches(visibility.enemies[side],self):matches=false;break
	if matches:target_snapshot_reuses+=1
	else:
		target_snapshots=[TargetGeometrySnapshot.new(),TargetGeometrySnapshot.new()]
		for side in [0,1]:
			var snapshot: TargetGeometrySnapshot=target_snapshots[side]
			snapshot.capture(visibility.enemies[side],self)
		target_snapshot_ready=true;target_snapshot_generation+=1;target_snapshot_rebuilds+=1
	target_snapshot_revision=visibility.revision''')
replace('\tranged_query_records=[[],[]];ranged_query_revision=-1', '''	ranged_query_records=[[],[]];ranged_query_revision=-1
	target_snapshot_revision=-1;target_snapshot_generation=0;target_snapshot_ready=false;target_snapshots=[]
	melee_snapshot_generation=-1;ranged_snapshot_generation=-1;target_snapshot_reuses=0;target_snapshot_rebuilds=0''')
replace('func prepare_melee_queries():\n\tif melee_query_revision==visibility.revision:return\n', '''func prepare_melee_queries():
	if melee_query_revision==visibility.revision:return
	prepare_target_snapshot()
	if melee_snapshot_generation==target_snapshot_generation:
		melee_query_revision=visibility.revision;return
	melee_snapshot_generation=target_snapshot_generation
''')
replace('func prepare_ranged_queries():\n\tif ranged_query_revision==visibility.revision:return\n', '''func prepare_ranged_queries():
	if ranged_query_revision==visibility.revision:return
	prepare_target_snapshot()
	if ranged_snapshot_generation==target_snapshot_generation:
		ranged_query_revision=visibility.revision;return
	ranged_snapshot_generation=target_snapshot_generation
''')
path.write_text(source, 'utf-8')
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
(QA / 'target-reuse-r1.patch').write_text(''.join(difflib.unified_diff(before.splitlines(True), source.splitlines(True), fromfile='rc29/battle_sim.gd', tofile='target-reuse-r1/battle_sim.gd')), 'utf-8')
(QA / 'target-reuse-r1-inputs.json').write_text(json.dumps({
    'base_sha256': sha(BASE / 'scripts/battle_sim.gd'),
    'candidate_sha256': sha(path), 'generator_sha256': sha(Path(__file__)),
    'scope': 'Isolated exact target geometry retention candidate. No gameplay, data, map, population, sight interval, sprite or frame-rate changes. Reuse/rebuild counters are diagnostic fields only.'
}, indent=2) + '\n', 'utf-8')
print('Prepared exact target-query retention candidate')
