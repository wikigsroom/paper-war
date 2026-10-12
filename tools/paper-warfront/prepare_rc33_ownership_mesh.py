"""Reuse the two original six-vertex ownership shapes in an isolated view trial."""
from pathlib import Path
import hashlib
import json
import shutil

ROOT = Path(__file__).resolve().parents[2]
QA = ROOT / "output/qa/godot/phase-runtime-rc33"
SOURCE = QA / "native-marching-r3-runtime"
TRIAL = QA / "native-ownership-r1-runtime"
assert not TRIAL.exists()
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
source_gate = QA / "source-gates-final.json"
assert json.loads(source_gate.read_text("utf-8"))["passed"]
shutil.copytree(SOURCE, TRIAL)
p = TRIAL / "scripts/battle_view.gd"
s = p.read_text("utf-8")
s = s.replace("var paper_ellipse_mesh: ArrayMesh\n", "var paper_ellipse_mesh: ArrayMesh\nvar ownership_meshes: Array[ArrayMesh]=[]\n")
old = '\tdraw_colored_polygon(PackedVector2Array([pos+Vector2(-15,5),pos+Vector2(15,5),pos+Vector2(15+direction*5,9),pos+Vector2(15,12),pos+Vector2(-15,12),pos+Vector2(-15+direction*5,9)]),side_color)'
assert s.count(old) == 1
s = s.replace(old, "\tdraw_ownership(pos,direction,side_color)")
helper = '''
func draw_ownership(pos: Vector2,direction: float,color: Color):
\tif ownership_meshes.is_empty():
\t\t# Preserve both native shapes, including their opposite inward notch.
\t\tfor sign_value in [1.0,-1.0]:
\t\t\tvar points=PackedVector2Array([Vector2(-15,5),Vector2(15,5),Vector2(15+sign_value*5,9),Vector2(15,12),Vector2(-15,12),Vector2(-15+sign_value*5,9)])
\t\t\tvar vertices=PackedVector3Array();var colors=PackedColorArray()
\t\t\tfor point in points:vertices.append(Vector3(point.x,point.y,0));colors.append(Color.WHITE)
\t\t\tvar arrays: Array=[];arrays.resize(Mesh.ARRAY_MAX)
\t\t\tarrays[Mesh.ARRAY_VERTEX]=vertices;arrays[Mesh.ARRAY_COLOR]=colors;arrays[Mesh.ARRAY_INDEX]=Geometry2D.triangulate_polygon(points)
\t\t\tvar mesh=ArrayMesh.new();mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES,arrays);ownership_meshes.append(mesh)
\tdraw_mesh(ownership_meshes[0 if direction==1 else 1],null,Transform2D(0,pos),color)
'''
needle = "\nfunc draw_frame_unit"
assert s.count(needle) == 1
s = s.replace(needle, helper + needle)
p.write_text(s, "utf-8")
changed = [n.name for n in (SOURCE / "scripts").glob("*.gd") if sha(n) != sha(TRIAL / "scripts" / n.name)]
assert changed == ["battle_view.gd"], changed
(QA / "ownership-r1-preparation.json").write_text(json.dumps({
    "passed": True, "generator_sha256": sha(Path(__file__)),
    "source_gates_sha256": sha(source_gate),
    "baseline_view_sha256": sha(SOURCE / "scripts/battle_view.gd"),
    "candidate_view_sha256": sha(p),
    "candidate_simulation_sha256": sha(TRIAL / "scripts/battle_sim.gd"),
    "candidate_scripts": {n.name: sha(n) for n in (TRIAL / "scripts").glob("*.gd")},
    "changed_from_verified_R3": changed,
    "scope": "Isolated candidate changes only ownership polygon submission in battle_view. Two fixed original six-vertex shapes; per-unit position, observer-relative color, ownership and painter order remain live. Full-body frame selection, statuses, texture LRU, unit/map ratios and original plot untouched. Not yet pixel or performance verified; formal RC32 unchanged."
}, indent=2) + "\n", "utf-8")
print("Prepared isolated two-mesh ownership trial", flush=True)
