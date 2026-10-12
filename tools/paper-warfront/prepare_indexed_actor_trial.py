"""Freeze tick-local actor lookup and identical melee-origin query reuse."""
import difflib
import hashlib
import json
from pathlib import Path
import shutil

ROOT=Path(__file__).resolve().parents[2]
QA=ROOT/'output/qa/godot/realtime-performance-rc26'
prior=QA/'road-query-r2-runtime'
target=QA/'actor-index-runtime'
assert not target.exists(), 'Never overwrite frozen trials'
shutil.copytree(prior,target)
p=target/'scripts/battle_sim.gd';s=p.read_text('utf-8')
def replace(old,new):
 global s
 assert s.count(old)==1,old
 s=s.replace(old,new)
replace('var melee_neighbor_edges: Dictionary={}', '''var melee_neighbor_edges: Dictionary={}
var melee_query_results: Dictionary={}
var tick_actor_index: Dictionary={}
var tick_actor_index_active: bool=false''')
replace('\tmelee_query_roads=[{},{}];melee_query_revision=-1;melee_neighbor_edges.clear()',
        '\tmelee_query_roads=[{},{}];melee_query_revision=-1;melee_neighbor_edges.clear()\n\tmelee_query_results.clear();tick_actor_index.clear();tick_actor_index_active=false')
replace('func actor(uid: int) -> Dictionary:\n\tfor a in units:', '''func actor(uid: int) -> Dictionary:
\tif tick_actor_index_active:
\t\tfor entry in tick_actor_index.get(uid,[]):
\t\t\tvar cached: Dictionary=entry.actor
\t\t\tif int(cached.uid)==uid and cached.hp>0:return cached
\t# External fixtures can clear/reorder collections or modify a UID; preserve
\t# the public linear API outside ticks and fall back for missing/dead entries.
\tfor a in units:''')
replace('\tnext_uid+=1; units.append(u)\n\tif movement_sides_active:',
        '\tnext_uid+=1; units.append(u)\n\tif tick_actor_index_active:index_tick_actor(u,0)\n\tif movement_sides_active:')
# Ordinary construction can occur during the AI tail of a tick.
old='buildings.append(b)'
assert s.count(old)==1
s=s.replace(old,old+'\n\tif tick_actor_index_active:index_tick_actor(b,1)')
replace('func tick(dt: float):\n\tif winner!=-2: return\n\ttime+=dt;',
        'func tick(dt: float):\n\tif winner!=-2: return\n\tprepare_tick_actors();tick_actor_index_active=true\n\ttime+=dt;')
replace('\tif winner!=-2:\n\t\tevent("result",{"winner":winner}); return',
        '\tif winner!=-2:\n\t\ttick_actor_index_active=false\n\t\tevent("result",{"winner":winner}); return')
replace('\t\t\tai_turn(side)\n\n# Used only during', '\t\t\tai_turn(side)\n\ttick_actor_index_active=false\n\n# Used only during')
replace('func prepare_melee_queries():\n\tif melee_query_revision==visibility.revision:return\n\tmelee_query_revision=visibility.revision;',
        'func prepare_melee_queries():\n\tif melee_query_revision==visibility.revision:return\n\tmelee_query_results.clear()\n\tmelee_query_revision=visibility.revision;')
replace('\t\t\treturn nearest_melee_query(anchor,side,priority,reach)', '''\t\t\tvar signature: Array=[side,edge,offset,priority,reach]
\t\t\tvar key: int=signature.hash()
\t\t\tvar memo: Dictionary=melee_query_results.get(key,{})
\t\t\tif not memo.is_empty() and memo.signature==signature:
\t\t\t\tvar cached: Dictionary=memo.actor
\t\t\t\tif cached.is_empty() or (cached.hp>0 and int(cached.side)!=side):return cached
\t\t\tvar selected: Dictionary=nearest_melee_query(anchor,side,priority,reach)
\t\t\tmelee_query_results[key]={"signature":signature,"actor":selected}
\t\t\treturn selected''')
helpers='''func index_tick_actor(a: Dictionary,category: int):
\tvar group: Array=tick_actor_index.get(int(a.uid),[])
\tvar entry: Dictionary={"actor":a,"category":category}
\tvar position: int=group.size()
\tfor i in range(group.size()):
\t\tif int(group[i].category)>category:position=i;break
\tgroup.insert(position,entry);tick_actor_index[int(a.uid)]=group

func prepare_tick_actors():
\ttick_actor_index.clear()
\tfor a in units:index_tick_actor(a,0)
\tfor a in buildings:index_tick_actor(a,1)
\tfor a in bases:index_tick_actor(a,2)

'''
replace('func actor(uid: int) -> Dictionary:', helpers+'func actor(uid: int) -> Dictionary:')
p.write_text(s,'utf-8')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
diff=QA/'actor-index.diff'
diff.write_text(''.join(difflib.unified_diff((prior/'scripts/battle_sim.gd').read_text('utf-8').splitlines(keepends=True),s.splitlines(keepends=True),fromfile='road-query-r2/battle_sim.gd',tofile='actor-index/battle_sim.gd')),'utf-8')
(target/'actor-index-inputs.json').write_text(json.dumps({'scope':'Frozen tick-local lookup trial; prior receipts refer to parents. Formal source unchanged by this generator.',
 'generator_sha256':sha(Path(__file__)),'parent_receipt_sha256':sha(prior/'precision-inputs.json'),'diff_sha256':sha(diff),
 'inputs':{p.relative_to(target).as_posix():sha(p) for p in sorted(target.rglob('*')) if p.is_file() and (p.suffix in ['.gd','.json'] or p.name=='project.godot')}},indent=2),'utf-8')
print('Tick-local actor and melee-result trial frozen')
