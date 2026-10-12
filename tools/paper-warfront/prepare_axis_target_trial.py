"""Exact Euclidean ranged candidates with conservative native-float X bounds."""
from pathlib import Path
import hashlib,json,shutil
ROOT=Path(__file__).resolve().parents[2]
QA=ROOT/'output/qa/godot/packed-query-rc28'
parent=QA/'packed-typed-runtime';target=QA/'axis-target-r2-runtime'
assert not target.exists(), 'Do not overwrite frozen candidates'
shutil.copytree(parent,target,ignore=shutil.ignore_patterns('.godot','field-inputs.json'))
p=target/'scripts/battle_sim.gd';s=p.read_text('utf-8')
marker='\tvar supports: PackedByteArray=PackedByteArray()\n\nclass BlockerQueryRecords:'
replacement='''	var supports: PackedByteArray=PackedByteArray()
	var by_x: PackedInt32Array=PackedInt32Array()
	var support_by_x: PackedInt32Array=PackedInt32Array()
	func order_x():
		var xs: PackedFloat64Array=PackedFloat64Array();var indices: Array[int]=[]
		for index in range(points.size()):xs.append(points[index].x);indices.append(index)
		indices.sort_custom(func(a: int,b: int):return a<b if xs[a]==xs[b] else xs[a]<xs[b])
		by_x=PackedInt32Array(indices);support_by_x=PackedInt32Array()
		for index in indices:
			if supports[index]!=0:support_by_x.append(index)

class BlockerQueryRecords:''' 
assert s.count(marker)==1;s=s.replace(marker,replacement,1)
marker='\tranged_query_revision=visibility.revision\n\nfunc nearest_enemy('
assert s.count(marker)==1
s=s.replace(marker,'\tif ranged_query_valid:\n\t\tfor records in ranged_query_records:records.order_x()\n\tranged_query_revision=visibility.revision\n\n'+'''func nearest_ranged_query(origin: Vector2,side: int,priority: bool,reach: float) -> Dictionary:
	var records: RangedQueryRecords=ranged_query_records[side]
	var actors: Array[Dictionary]=records.actors
	var points: PackedVector2Array=records.points
	var best_index: int=-1;var distance: float=10000.0
	# Pass0 finds the raw nearest actor. Pass1 separately finds weighted
	# supports in range, so a weighted best never prunes another support.
	for pass_index in range(2 if priority else 1):
		var indices: PackedInt32Array=records.by_x if pass_index==0 else records.support_by_x
		if pass_index==1 and best_index>=0 and records.supports[best_index]!=0 and distance<=reach:distance*=.35
		var lo: int=0;var hi: int=indices.size()
		while lo<hi:
			var middle: int=(lo+hi)/2
			if points[indices[middle]].x<origin.x:lo=middle+1
			else:hi=middle
		for direction in [-1,1]:
			var at: int=lo-1 if direction<0 else lo
			while at>=0 and at<indices.size():
				var index: int=indices[at];var point: Vector2=points[index]
				# Use the same native Vector2 length arithmetic as distance_to.
				# A scalar float64 abs(dx) can exceed the rounded float32 full
				# distance and incorrectly discard an equal-score earlier rank.
				var lower: float=Vector2(origin.x-point.x,0).length()
				if lower>distance if pass_index==0 else (lower>reach or lower*.35>distance):break
				at+=direction
				var actor_value: Dictionary=actors[index]
				if int(actor_value.side)==side or actor_value.hp<=0:continue
				var d: float=origin.distance_to(point)
				if pass_index==1 and d>reach:continue
				var score: float=d if pass_index==0 else d*.35
				if score<distance or (best_index>=0 and score==distance and index<best_index):best_index=index;distance=score
	return {} if best_index<0 else actors[best_index]

func nearest_enemy(''',1)
start=s.index('\t\t\tvar records: RangedQueryRecords=ranged_query_records[side]',s.index('func nearest_enemy('))
end=s.index('\tfor e in visibility.enemies[side]:',start)
s=s[:start]+'\t\t\treturn nearest_ranged_query(origin,side,priority,reach)\n'+s[end:]
p.write_text(s,'utf-8')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
(target/'axis-inputs.json').write_text(json.dumps({'parent':parent.relative_to(ROOT).as_posix(),'generator_sha256':sha(Path(__file__)),'scope':'Isolated exact ranged candidate. Sorted native Vector2 X points; separate support pass, strict score/rank tie and10000 sentinel. Live ownership/death filtering and original visibility-order rank preserved. No rendering/FPS or adoption claim.','inputs':{p.relative_to(target).as_posix():sha(p) for p in target.rglob('*') if p.is_file()}},ensure_ascii=False,indent=2)+'\n','utf-8')
print('Prepared',target)
