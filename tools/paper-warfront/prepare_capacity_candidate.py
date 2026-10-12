"""Isolated, immutable-per-run candidates for rc27 CPU/correctness work."""
from pathlib import Path
import argparse, hashlib, json, shutil
ROOT=Path(__file__).resolve().parents[2]
QA=ROOT/'output/qa/godot/capacity-performance-rc27'
p=argparse.ArgumentParser();p.add_argument('name');a=p.parse_args()
source=QA/'baseline-v2-runtime';dest=QA/a.name
assert not dest.exists(), 'Never overwrite a completed candidate'
shutil.copytree(source,dest,ignore=shutil.ignore_patterns('.godot','inputs.json','corrected-inputs.json'))
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
for probe in ['probe_leap_blocker_consistency.gd']:
 shutil.copyfile(ROOT/'tools/paper-warfront'/probe,dest/'tests'/probe)
if a.name=='blocker-correction-runtime':
 path=dest/'scripts/battle_sim.gd';text=path.read_text('utf-8')
 text=text.replace('var movement_sides_active: bool=false','var movement_sides_active: bool=false\nvar movement_current_uid: int=0\nvar movement_current_anchor: Dictionary={}',1)
 text=text.replace('movement_sides_active=false\n','movement_sides_active=false;movement_current_uid=0;movement_current_anchor={}\n',1)
 text=text.replace('\t\tvar original_anchor: Dictionary=movement_anchor(u)\n\t\ttick_unit(u,dt)', '\t\tvar original_anchor: Dictionary=movement_anchor(u)\n\t\tmovement_current_uid=int(u.uid);movement_current_anchor=original_anchor\n\t\ttick_unit(u,dt)',1)
 text=text.replace('\tcollecting_attacks=false;movement_sides_active=false','\tmovement_current_uid=0;movement_current_anchor={}\n\tcollecting_attacks=false;movement_sides_active=false',1)
 text=text.replace('\t\tvar offset: float=float(ally.s)\n\t\tif not is_finite(offset):blocker_roads_valid=false', '\t\t# A closing leap can request the lazy index before its movement intent\n\t\t# is restored. Other actors must still observe its original position.\n\t\tvar anchor: Dictionary=movement_current_anchor if int(ally.uid)==movement_current_uid else ally\n\t\tvar offset: float=float(anchor.s)\n\t\tif not is_finite(offset):blocker_roads_valid=false',1)
 text=text.replace('if not roads.has(ally.edge):roads[ally.edge]=[]\n\t\troads[ally.edge].append', 'if not roads.has(anchor.edge):roads[anchor.edge]=[]\n\t\troads[anchor.edge].append',1)
 path.write_text(text,'utf-8')
else:raise ValueError('Unknown candidate; define the exact change first')
(dest/'candidate-inputs.json').write_text(json.dumps({'parent':str(source.relative_to(ROOT)), 'scope':'Isolated candidate only, not exported or adopted.', 'inputs':{p.relative_to(dest).as_posix():sha(p) for p in sorted(dest.rglob('*')) if p.is_file()}},indent=2),'utf-8')
print(dest)
