"""Preserve R1 and prepare a native R2 trial with motion bypass and invalidation."""
from pathlib import Path
import hashlib
import json
import shutil

ROOT = Path(__file__).resolve().parents[2]
QA = ROOT / "output/qa/godot/pressure-runtime-rc31"
before = QA / "terrain-commands-r1-runtime"
target = QA / "terrain-commands-r2-runtime"
assert not target.exists(), "Never overwrite a started native trial"
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
shutil.copytree(before, target)
cache = target / "scripts/theatre_ground_cache.gd"
source = cache.read_text("utf-8")
source = source.replace("var terrain_rebuilds: int=0\n", """var terrain_rebuilds: int=0
var terrain_bypasses: int=0
var terrain_mesh_key: int=0
var terrain_meshes: Array=[]
var pending_ready: bool=false
var pending_owner: WeakRef
var pending_map: WeakRef
var pending_db: WeakRef
var pending_scalars: Array=[]
""", 1)
source = source.replace("\tif shapes(sim)!=terrain_shapes:return false\n", "\tif geometry_key!=terrain_mesh_key or meshes!=terrain_meshes:return false\n\tif shapes(sim)!=terrain_shapes:return false\n", 1)
source = source.replace("""\t\tif not view.db.assets.has(id) or view.db.assets[id]!=terrain_assets[id]:return false
\t\tvar path: String=str(view.db.assets[id].path)""", """\t\tif terrain_assets[id]==null:
\t\t\tif view.db.assets.has(id):return false
\t\t\tcontinue
\t\tif not view.db.assets.has(id) or view.db.assets[id]!=terrain_assets[id]:return false
\t\t# Failed loads can become available later; never freeze a null resource.
\t\tif terrain_textures[id]==null:return false
\t\tvar path: String=str(view.db.assets[id].path)""", 1)
source = source.replace("""\tif not same_inputs(view,sim,values):
\t\tvar recorder=RecordingCanvas.new(view,self)""", """\tif not same_inputs(view,sim,values):
\t\tvar finite: bool=true
\t\tfor value in values:
\t\t\tif not is_finite(float(value)):finite=false;break
\t\tvar settled: bool=finite and pending_ready and pending_owner.get_ref()==view and pending_map.get_ref()==sim.map and pending_db.get_ref()==view.db and pending_scalars==values
\t\tif not settled:
\t\t\t# Moving cameras should not pay the cost of recording a plan that is
\t\t\t# invalid on the next frame. The unchanged renderer draws this frame.
\t\t\tpending_ready=finite;pending_owner=weakref(view);pending_map=weakref(sim.map);pending_db=weakref(view.db);pending_scalars=values
\t\t\tterrain_bypasses+=1
\t\t\tTerrain.ground(view,sim)
\t\t\tTerrain.decorations(view,sim)
\t\t\treturn
\t\tpending_ready=false
\t\tvar recorder=RecordingCanvas.new(view,self)""", 1)
source = source.replace("""\t\t\tif command[0]==Operation.ART and view.db.assets.has(command[1]):
\t\t\t\tterrain_assets[command[1]]=view.db.assets[command[1]].duplicate(true)""", """\t\t\tif command[0]==Operation.ART:
\t\t\t\tterrain_assets[command[1]]=view.db.assets[command[1]].duplicate(true) if view.db.assets.has(command[1]) else null""", 1)
source = source.replace("\t\tterrain_ready=true;terrain_rebuilds+=1\n", "\t\tterrain_mesh_key=geometry_key;terrain_meshes=meshes.duplicate()\n\t\tterrain_ready=true;terrain_rebuilds+=1\n", 1)
source = source.replace("\tterrain_reuses+=1\n", "\tpending_ready=false\n\tterrain_reuses+=1\n", 1)
source = source.replace("\tterrain_owner=null;terrain_map=null;terrain_db=null\n", """\tterrain_owner=null;terrain_map=null;terrain_db=null
\tterrain_meshes.clear();pending_ready=false;pending_scalars.clear()
\tpending_owner=null;pending_map=null;pending_db=null
""", 1)
assert "terrain_bypasses+=1" in source and "terrain_assets[id]==null" in source
cache.write_text(source, "utf-8")
observer = QA / "terrain-abba-observer-r2.gd"
assert not observer.exists()
text = (QA / "terrain-abba-observer-r1.gd").read_text("utf-8")
text = text.replace("\t\t\tvar rebuild_before: int=ground_mesh_cache.terrain_rebuilds\n", "\t\t\tvar rebuild_before: int=ground_mesh_cache.terrain_rebuilds\n\t\t\tvar bypass_before: int=ground_mesh_cache.terrain_bypasses\n", 1)
text = text.replace('"rebuilt":ground_mesh_cache.terrain_rebuilds>rebuild_before}', '"rebuilt":ground_mesh_cache.terrain_rebuilds>rebuild_before,"bypassed":ground_mesh_cache.terrain_bypasses>bypass_before}', 1)
observer.write_text(text, "utf-8")
(QA / "terrain-commands-r2-inputs.json").write_text(json.dumps({
    "generator_sha256": sha(Path(__file__)),
    "r1_native_abba_report_sha256": sha(QA / "terrain-abba-native-r1/terrain-abba.json"),
    "r1_scripts": {p.name: sha(p) for p in (before / "scripts").glob("*.gd")},
    "r2_scripts": {p.name: sha(p) for p in (target / "scripts").glob("*.gd")},
    "observer_sha256": sha(observer),
    "scope": "Isolated R2 trial. Stable exact camera/layout commands only; unchanged original terrain on motion. Missing asset, failed texture and mesh reset invalidate. Formal source and completed R1 evidence remain unchanged."
}, ensure_ascii=False, indent=2) + "\n", "utf-8")
print("Prepared isolated terrain R2 and its native ABBA observer")
