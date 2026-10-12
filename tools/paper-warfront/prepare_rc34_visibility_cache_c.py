"""Prepare R4c from the complete RC33 simulation/ownership candidate."""
from pathlib import Path
import hashlib
import json
import shutil

ROOT=Path(__file__).resolve().parents[2]
QA=ROOT/"output/qa/godot/render-runtime-rc34"
HISTORY=ROOT/"output/qa/godot/phase-runtime-rc33"
SOURCE=HISTORY/"native-ownership-r1-runtime"
TRIAL=QA/"visibility-r4c-runtime"
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert not TRIAL.exists()
assert json.loads((HISTORY/"ownership-r1-source-gates.json").read_text("utf-8"))["passed"]
assert json.loads((ROOT/"release/3.0.0-rc33-preview/preview-verification.json").read_text("utf-8"))["preview_artifacts_verified"]
shutil.copytree(SOURCE,TRIAL)
p=TRIAL/"scripts/battle_view.gd";s=p.read_text("utf-8")
needle="var ownership_meshes: Array[ArrayMesh]=[]\n";assert s.count(needle)==1
s=s.replace(needle,needle+"var draw_visibility_cache: Dictionary={}\n")
needle="func _draw():\n\tif db==null: return\n";assert s.count(needle)==1
s=s.replace(needle,needle+"\tdraw_visibility_cache.clear()\n")
calls=s.count("sim.location_visible(player_side,");assert calls==10,calls
s=s.replace("sim.location_visible(player_side,","location_visible_cached(")
needle="\nfunc ordered_units() -> Array:";assert s.count(needle)==1
helper='''
func location_visible_cached(x: float,y: float) -> bool:
\t# Cache only inside one draw pass. Fog revision and observer side remain live.
\tvar key:=Vector2(x,y)
\tif not draw_visibility_cache.has(key):draw_visibility_cache[key]=sim.location_visible(player_side,x,y)
\treturn bool(draw_visibility_cache[key])
'''
s=s.replace(needle,helper+needle);p.write_text(s,"utf-8")
(QA/"visibility-r4c-preparation.json").write_text(json.dumps({"passed":True,"generator_sha256":sha(Path(__file__)),"source_kind":"complete_RC33_native_ownership_r1","source_view_sha256":sha(SOURCE/"scripts/battle_view.gd"),"trial_view_sha256":sha(p),"replaced_calls":calls,"formal_rc33_source_gate_sha256":sha(HISTORY/"ownership-r1-source-gates.json"),"scope":"Complete RC33 simulation/ownership candidate with all imported assets; one view-only per-draw visibility cache added. Existing marching, ownership meshes, map/story, fog, animation, particle and UI code are copied byte-identically. Cache clears each draw and never crosses fog revisions or frames."
},indent=2)+"\n","utf-8")
print("Prepared RC33-derived visibility cache R4c",flush=True)
