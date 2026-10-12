"""Prepare R4d: keep the R4c cache correct across map and fog revisions."""
from pathlib import Path
import hashlib
import json
import shutil

ROOT=Path(__file__).resolve().parents[2]
QA=ROOT/"output/qa/godot/render-runtime-rc34"
SOURCE=QA/"visibility-r4c-runtime"
TRIAL=QA/"visibility-r4d-runtime"
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert not TRIAL.exists()
assert json.loads((QA/"visibility-r4c-source-gates.json").read_text("utf-8"))["passed"]
shutil.copytree(SOURCE,TRIAL)
p=TRIAL/"scripts/battle_view.gd";s=p.read_text("utf-8")
needle="var draw_visibility_cache: Dictionary={}\n";assert s.count(needle)==1
s=s.replace(needle,needle+"var draw_visibility_revision: int=-1\nvar draw_visibility_side: int=-1\n")
needle="\tdraw_visibility_cache.clear()\n";assert s.count(needle)==1
s=s.replace(needle,"\tdraw_visibility_cache.clear()\n\tdraw_visibility_revision=int(sim.visibility.revision) if sim!=null and sim.visibility!=null else -1\n\tdraw_visibility_side=player_side\n",1)
needle="\tif not draw_visibility_cache.has(key):draw_visibility_cache[key]=sim.location_visible(player_side,x,y)\n"
assert s.count(needle)==1
s=s.replace(needle,"\tvar revision: int=int(sim.visibility.revision) if sim!=null and sim.visibility!=null else -1\n\tif revision!=draw_visibility_revision or player_side!=draw_visibility_side:\n\t\tdraw_visibility_cache.clear();draw_visibility_revision=revision;draw_visibility_side=player_side\n"+needle)
needle="\teconomy_warning.clear()\n";assert s.count(needle)==1
s=s.replace(needle,"\teconomy_warning.clear()\n\tdraw_visibility_cache.clear();draw_visibility_revision=-1;draw_visibility_side=-1\n")
p.write_text(s,"utf-8")
(QA/"visibility-r4d-preparation.json").write_text(json.dumps({"passed":True,"generator_sha256":sha(Path(__file__)),"source_view_sha256":sha(SOURCE/"scripts/battle_view.gd"),"trial_view_sha256":sha(p),"scope":"R4d retains R4c per-draw exact-coordinate cache but invalidates it on battle reset, visibility revision and observer side. This repairs route-sign queries made outside _draw after map/fog changes; no cache crosses a map or fog refresh. All RC33 simulation/ownership and R4c behavior otherwise identical."
},indent=2)+"\n","utf-8")
print("Prepared visibility cache R4d with revision-safe invalidation",flush=True)
