"""Keep original rank when different arc offsets round to equal weapon distance."""
import difflib
import hashlib
import json
from pathlib import Path
import shutil

ROOT=Path(__file__).resolve().parents[2]
QA=ROOT/'output/qa/godot/realtime-performance-rc26'
prior=QA/'road-query-runtime'
target=QA/'road-query-r2-runtime'
assert not target.exists(), 'Never overwrite frozen candidates'
shutil.copytree(prior,target)
p=target/'scripts/battle_sim.gd';s=p.read_text('utf-8')
start=s.index('func nearest_road_record(');end=s.index('func nearest_melee_query(',start)
helper='''# Broad candidate tolerance only: final scores still use the exact old
# road-distance calculation and original rank. Neighboring distinct offsets
# can become exactly equal after adding the source-to-junction distance.
func nearest_road_records(records: Array,offset: float,side: int) -> Array:
\tvar lo: int=0;var hi: int=records.size()
\twhile lo<hi:
\t\tvar middle: int=(lo+hi)/2
\t\tif float(records[middle].offset)<offset:lo=middle+1
\t\telse:hi=middle
\tvar candidates: Array=[];var distance: float=INF
\tfor direction in [-1,1]:
\t\tvar index: int=lo-1 if direction<0 else lo
\t\twhile index>=0 and index<records.size():
\t\t\tvar record: Dictionary=records[index]
\t\t\tvar next_distance: float=absf(float(record.offset)-offset)
\t\t\tif next_distance>distance+0.000000001:break
\t\t\tvar candidate: Dictionary=record.actor
\t\t\tif candidate.hp>0 and int(candidate.side)!=side:
\t\t\t\tdistance=minf(distance,next_distance)
\t\t\t\tvar same: int=-1
\t\t\t\tfor i in range(candidates.size()):
\t\t\t\t\tif float(candidates[i].offset)==float(record.offset):same=i;break
\t\t\t\tif same<0:candidates.append(record)
\t\t\t\telif int(record.rank)<int(candidates[same].rank):candidates[same]=record
\t\t\tindex+=direction
\treturn candidates

'''
s=s[:start]+helper+s[end:]
old='''\t\t\tvar normal: Dictionary=nearest_road_record(road.all,float(offset),side)
\t\t\tif not normal.is_empty():candidates.append(normal)
\t\t\tif priority:
\t\t\t\tvar support: Dictionary=nearest_road_record(road.support,float(offset),side)
\t\t\t\tif not support.is_empty():candidates.append(support)'''
new='''\t\t\tcandidates.append_array(nearest_road_records(road.all,float(offset),side))
\t\t\tif priority:candidates.append_array(nearest_road_records(road.support,float(offset),side))'''
assert s.count(old)==1;s=s.replace(old,new)
s=s.replace('if offset<0 or offset>float(map.edges[body.edge].length):melee_query_valid=false',
            'if not is_finite(offset) or offset<0 or offset>float(map.edges[body.edge].length):melee_query_valid=false')
p.write_text(s,'utf-8')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
diff=QA/'road-query-r2.diff'
diff.write_text(''.join(difflib.unified_diff((prior/'scripts/battle_sim.gd').read_text('utf-8').splitlines(keepends=True),s.splitlines(keepends=True),fromfile='road-query-r1/battle_sim.gd',tofile='road-query-r2/battle_sim.gd')),'utf-8')
(target/'precision-inputs.json').write_text(json.dumps({'scope':'Frozen float-rank boundary correction; older receipts refer to parent inputs. Shipping runtime unchanged.',
 'generator_sha256':sha(Path(__file__)),'parent_receipt_sha256':sha(prior/'road-query-inputs.json'),'diff_sha256':sha(diff),
 'inputs':{p.relative_to(target).as_posix():sha(p) for p in sorted(target.rglob('*')) if p.is_file() and (p.suffix in ['.gd','.json'] or p.name=='project.godot')}},indent=2),'utf-8')
print('Frozen exact-rank road query r2')
