"""Freeze rc27 and build an isolated typed-array query candidate; no adoption."""
from pathlib import Path
import argparse
import hashlib
import json
import shutil

ROOT = Path(__file__).resolve().parents[2]
QA = ROOT / 'output/qa/godot/packed-query-rc28'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


CLASSES = '''class RoadQueryRecords:
	extends RefCounted
	var actors: Array[Dictionary]=[]
	var offsets: PackedFloat64Array=PackedFloat64Array()
	var ranks: PackedInt32Array=PackedInt32Array()
	var supports: PackedByteArray=PackedByteArray()
	var anchors: Array[Dictionary]=[]
	func add(actor_value: Dictionary,offset: float,rank: int,support: bool,edge: String):
		actors.append(actor_value);offsets.append(offset);ranks.append(rank);supports.append(1 if support else 0)
		anchors.append({"edge":edge,"s":offset})
	func order(keep_rank: bool):
		var indices: Array[int]=[]
		for index in range(actors.size()):indices.append(index)
		indices.sort_custom(func(a: int,b: int):return ranks[a]<ranks[b] if keep_rank and offsets[a]==offsets[b] else offsets[a]<offsets[b])
		var sorted_actors: Array[Dictionary]=[];var sorted_offsets: PackedFloat64Array=PackedFloat64Array()
		var sorted_ranks: PackedInt32Array=PackedInt32Array();var sorted_supports: PackedByteArray=PackedByteArray()
		var sorted_anchors: Array[Dictionary]=[]
		for index in indices:
			sorted_actors.append(actors[index]);sorted_offsets.append(offsets[index]);sorted_ranks.append(ranks[index])
			sorted_supports.append(supports[index]);sorted_anchors.append(anchors[index])
		actors=sorted_actors;offsets=sorted_offsets;ranks=sorted_ranks;supports=sorted_supports;anchors=sorted_anchors

class RangedQueryRecords:
	extends RefCounted
	var actors: Array[Dictionary]=[]
	var points: PackedVector2Array=PackedVector2Array()
	var supports: PackedByteArray=PackedByteArray()

class BlockerQueryRecords:
	extends RefCounted
	var actors: Array[Dictionary]=[]
	var offsets: PackedFloat64Array=PackedFloat64Array()
	func order():
		var indices: Array[int]=[]
		for index in range(actors.size()):indices.append(index)
		indices.sort_custom(func(a: int,b: int):return offsets[a]<offsets[b])
		var sorted_actors: Array[Dictionary]=[];var sorted_offsets: PackedFloat64Array=PackedFloat64Array()
		for index in indices:sorted_actors.append(actors[index]);sorted_offsets.append(offsets[index])
		actors=sorted_actors;offsets=sorted_offsets

'''

MELEE = '''func prepare_melee_queries():
	if melee_query_revision==visibility.revision:return
	melee_query_revision=visibility.revision;melee_query_roads=[{},{}];melee_query_valid=true
	if melee_neighbor_edges.is_empty():
		for edge_id in map.edges:
			var source: Dictionary=map.edges[edge_id]
			var neighbors: Dictionary={}
			for node_id in [source.from,source.to]:
				for link in map.adjacency[node_id]:
					if link.edge==edge_id:continue
					var edge: Dictionary=map.edges[link.edge]
					if not neighbors.has(link.edge):neighbors[link.edge]=[]
					neighbors[link.edge].append(0.0 if node_id==edge.from else float(edge.length))
			melee_neighbor_edges[edge_id]=neighbors
	for side in [0,1]:
		var rank: int=0
		for actor_value in visibility.enemies[side]:
			var body: Dictionary=physical_anchor(actor_value)
			var offset: float=float(body.s)
			if not is_finite(offset) or offset<0 or offset>float(map.edges[body.edge].length):melee_query_valid=false
			if not melee_query_roads[side].has(body.edge):melee_query_roads[side][body.edge]={"all":RoadQueryRecords.new(),"support":RoadQueryRecords.new()}
			var support: bool=not actor_value.get("building",false) and db.balance.units[actor_value.id].get("role","") in ["medic","engineer","scribe","necromancer","summoner","illusionist","oracle"]
			var road: Dictionary=melee_query_roads[side][body.edge]
			var all_records: RoadQueryRecords=road.all
			all_records.add(actor_value,offset,rank,support,body.edge)
			if support:
				var support_records: RoadQueryRecords=road.support
				support_records.add(actor_value,offset,rank,true,body.edge)
			rank+=1
		for road in melee_query_roads[side].values():
			for records in [road.all,road.support]:records.order(true)

# Arc offsets stay float64, including the rounded-junction tie fixtures.
func nearest_road_records(records: RoadQueryRecords,offset: float,side: int) -> PackedInt32Array:
	var lo: int=0;var hi: int=records.actors.size()
	while lo<hi:
		var middle: int=(lo+hi)/2
		if records.offsets[middle]<offset:lo=middle+1
		else:hi=middle
	var candidates: PackedInt32Array=PackedInt32Array();var distance: float=INF
	for direction in [-1,1]:
		var index: int=lo-1 if direction<0 else lo
		while index>=0 and index<records.actors.size():
			var next_distance: float=absf(records.offsets[index]-offset)
			if next_distance>distance+0.000000001:break
			var candidate: Dictionary=records.actors[index]
			if candidate.hp>0 and int(candidate.side)!=side:
				distance=minf(distance,next_distance)
				var same: int=-1
				for i in range(candidates.size()):
					if records.offsets[candidates[i]]==records.offsets[index]:same=i;break
				if same<0:candidates.append(index)
				elif records.ranks[index]<records.ranks[candidates[same]]:candidates[same]=index
			index+=direction
	return candidates

func nearest_melee_query(anchor: Dictionary,side: int,priority: bool,reach: float) -> Dictionary:
	var roads: Dictionary=melee_query_roads[side]
	var requests: Dictionary=melee_neighbor_edges[anchor.edge].duplicate(false)
	requests[anchor.edge]=[float(anchor.s)]
	var best: Dictionary={};var distance: float=10000.0;var rank: int=2147483647
	for edge_id in requests:
		if not roads.has(edge_id):continue
		var road: Dictionary=roads[edge_id]
		var pools: Array[RoadQueryRecords]=[road.all]
		if priority:pools.append(road.support)
		for offset in requests[edge_id]:
			for records in pools:
				for index in nearest_road_records(records,float(offset),side):
					var d: float=map.melee_distance(anchor,records.anchors[index])
					var score: float=d*.35 if priority and records.supports[index]!=0 and d<=reach else d
					if score<distance or (not best.is_empty() and score==distance and records.ranks[index]<rank):
						best=records.actors[index];distance=score;rank=records.ranks[index]
	return best

'''

RANGED = '''func prepare_ranged_queries():
	if ranged_query_revision==visibility.revision:return
	ranged_query_records=[RangedQueryRecords.new(),RangedQueryRecords.new()];ranged_query_valid=true
	for observer in [0,1]:
		var records: RangedQueryRecords=ranged_query_records[observer]
		for actor_value in visibility.enemies[observer]:
			var anchor: Dictionary=physical_anchor(actor_value)
			var point: Vector2=Vector2(anchor.x,anchor.y)
			if not is_finite(point.x) or not is_finite(point.y):ranged_query_valid=false
			var support: bool=not actor_value.get("building",false) and db.balance.units[actor_value.id].get("role","") in ["medic","engineer","scribe","necromancer","summoner","illusionist","oracle"]
			records.actors.append(actor_value);records.points.append(point);records.supports.append(1 if support else 0)
	ranged_query_revision=visibility.revision

'''

RANGED_LOOP = '''			var records: RangedQueryRecords=ranged_query_records[side]
			var actors: Array[Dictionary]=records.actors
			var points: PackedVector2Array=records.points
			var supports: PackedByteArray=records.supports
			for index in range(actors.size()):
				var e: Dictionary=actors[index]
				if int(e.side)==side or e.hp<=0:continue
				var d: float=origin.distance_to(points[index])
				var score: float=d*.35 if priority and supports[index]!=0 and d<=reach else d
				if score<distance:best=e;distance=score
'''

BLOCKER = '''func prepare_blocker_roads():
	blocker_roads=[{},{}];blocker_roads_valid=true
	for ally in units:
		var anchor: Dictionary=movement_current_anchor if int(ally.uid)==movement_current_uid else ally
		var offset: float=float(anchor.s)
		if not is_finite(offset):blocker_roads_valid=false
		if ally.hp<=0 or db.balance.units[ally.id].get("economy",false):continue
		var roads: Dictionary=blocker_roads[int(ally.side)]
		if not roads.has(anchor.edge):roads[anchor.edge]=RoadQueryRecords.new()
		var records: RoadQueryRecords=roads[anchor.edge]
		records.add(ally,offset,0,false,anchor.edge)
	for roads in blocker_roads:
		for records in roads.values():records.order(false)
	blocker_roads_dirty=false

'''

BLOCKER_R2 = BLOCKER.replace('RoadQueryRecords.new()', 'BlockerQueryRecords.new()').replace('var records: RoadQueryRecords=', 'var records: BlockerQueryRecords=').replace('records.add(ally,offset,0,false,anchor.edge)', 'records.actors.append(ally);records.offsets.append(offset)').replace('records.order(false)', 'records.order()')

ORDERED_UNITS = '''func ordered_units() -> Array:
	# Cache each physical Y once. Keep the original comparator, including its
	# approximate-height threshold and uid%5 ties, and the original input order.
	var actors: Array=sim.units
	var heights: PackedFloat64Array=PackedFloat64Array()
	var ties: PackedByteArray=PackedByteArray()
	var indices: Array[int]=[]
	for index in range(actors.size()):
		heights.append(sim.physical_point(actors[index]).y)
		ties.append(int(actors[index].uid)%5);indices.append(index)
	indices.sort_custom(func(a: int,b: int):return heights[a]<heights[b] if absf(heights[a]-heights[b])>.05 else ties[a]<ties[b])
	var ordered: Array=[]
	for index in indices:ordered.append(actors[index])
	return ordered

'''


def replace_function(text, first, following, replacement):
    start = text.index('func ' + first + '(')
    end = text.index('func ' + following + '(', start)
    return text[:start] + replacement + text[end:]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('variant', choices=['freeze', 'ranged', 'roads', 'all', 'all-r2', 'targets'])
    args = parser.parse_args()
    baseline = QA / 'baseline-runtime'
    if args.variant == 'freeze':
        assert not baseline.exists(), 'Never overwrite frozen inputs'
        baseline.mkdir(parents=True)
        for part in ['scripts', 'data', 'tests']:
            shutil.copytree(ROOT / 'game' / part, baseline / part)
        (baseline / 'project.godot').write_text('config_version=5\n[application]\nconfig/name="Packed query diagnosis"\n[rendering]\nrenderer/rendering_method="gl_compatibility"\n', encoding='utf-8')
        for name in ['capacity_cpu_profiler.gd', 'probe_capacity_cpu.gd']:
            shutil.copy2(ROOT / 'tools/paper-warfront' / name, baseline / 'tests' / name)
        request = json.loads((ROOT / 'output/qa/godot/capacity-performance-rc27/release-final/realtime/stress/report.json').read_text('utf-8'))
        (baseline / 'capacity-config.json').write_text(json.dumps(request['config'], ensure_ascii=False, indent=2), encoding='utf-8')
        (baseline / 'inputs.json').write_text(json.dumps({
            'scope': 'Exact rc27 scripts, data and tests; diagnostic-only project settings and frozen CPU observers.',
            'release_manifest_sha256': digest(ROOT / 'release/3.0.0-rc27-preview/build-manifest.json'),
            'inputs': {p.relative_to(baseline).as_posix(): digest(p) for p in sorted(baseline.rglob('*')) if p.is_file()},
        }, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print('Frozen', baseline)
        return
    target = QA / (args.variant + '-runtime')
    assert not target.exists(), 'Never overwrite completed candidates'
    shutil.copytree(baseline, target, ignore=shutil.ignore_patterns('.godot', 'inputs.json'))
    path = target / 'scripts/battle_sim.gd'
    text = path.read_text('utf-8')
    text = text.replace('func _init(data):', CLASSES + 'func _init(data):', 1)
    if args.variant in ['roads', 'all', 'all-r2', 'targets']:
        text = replace_function(text, 'prepare_melee_queries', 'prepare_ranged_queries', MELEE)
    if args.variant in ['roads', 'all', 'all-r2']:
        text = replace_function(text, 'prepare_blocker_roads', 'marching_step', BLOCKER_R2 if args.variant == 'all-r2' else BLOCKER)
        old = 'var records: Array=blocker_roads[int(u.side)].get(u.edge,[])'
        assert text.count(old) == 1
        if args.variant == 'all-r2':
            text = text.replace(old, 'var roads: Dictionary=blocker_roads[int(u.side)]\n\t\t\tif not roads.has(u.edge):return step\n\t\t\tvar records: BlockerQueryRecords=roads[u.edge]\n\t\t\tvar actors: Array[Dictionary]=records.actors\n\t\t\tvar offsets: PackedFloat64Array=records.offsets')
        else:
            text = text.replace(old, 'var records: RoadQueryRecords=blocker_roads[int(u.side)].get(u.edge,RoadQueryRecords.new())')
        start = text.index('func marching_step(')
        end = text.index('func movement_anchor(', start)
        chunk = text[start:end].replace('records.size()', 'records.actors.size()')
        chunk = chunk.replace('float(records[middle].offset)', 'records.offsets[middle]')
        chunk = chunk.replace('var record: Dictionary=records[index]', 'var actor_index: int=index')
        chunk = chunk.replace('float(record.offset)', 'records.offsets[actor_index]')
        chunk = chunk.replace('var ally: Dictionary=record.actor', 'var ally: Dictionary=records.actors[actor_index]')
        if args.variant == 'all-r2':
            chunk = chunk.replace('records.actors.size()', 'actors.size()').replace('records.offsets[', 'offsets[').replace('records.actors[', 'actors[')
        text = text[:start] + chunk + text[end:]
    if args.variant in ['ranged', 'all', 'all-r2', 'targets']:
        text = replace_function(text, 'prepare_ranged_queries', 'nearest_enemy', RANGED)
        start = text.index('\t\t\tfor record in ranged_query_records[side]:')
        end = text.index('\t\t\treturn best', start)
        text = text[:start] + RANGED_LOOP + text[end:]
    path.write_text(text, encoding='utf-8')
    if args.variant in ['all-r2', 'targets']:
        view = target / 'scripts/battle_view.gd'
        text = view.read_text('utf-8')
        start = text.index('\tvar ordered=sim.units.duplicate()')
        end = text.index('\tfor u in ordered: draw_unit(u)', start)
        text = text[:start] + '\tvar ordered=ordered_units()\n' + text[end:]
        text = text.replace('func mark_draw_layer(', ORDERED_UNITS + 'func mark_draw_layer(', 1)
        view.write_text(text, encoding='utf-8')
    (target / 'candidate-inputs.json').write_text(json.dumps({
        'variant': args.variant,
        'parent': baseline.relative_to(ROOT).as_posix(),
        'generator_sha256': digest(Path(__file__)),
        'scope': 'Isolated typed-query candidate. Live actors, original rank, exact Vector2 distance, float64 arc offsets and current leaper original anchor retained. Not adopted or exported.',
        'inputs': {p.relative_to(target).as_posix(): digest(p) for p in sorted(target.rglob('*')) if p.is_file()},
    }, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('Prepared', target)


if __name__ == '__main__':
    main()
