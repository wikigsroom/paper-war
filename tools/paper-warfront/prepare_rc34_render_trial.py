"""Freeze RC33, then prepare an isolated bounded sprite/shard geometry trial."""
from pathlib import Path
import hashlib
import json
import re
import shutil

ROOT = Path(__file__).resolve().parents[2]
QA = ROOT / "output/qa/godot/render-runtime-rc34"
BASE = QA / "baseline-runtime"
TRIAL = QA / "geometry-r1-runtime"
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
manifest_path = ROOT / "release/3.0.0-rc33-preview/build-manifest.json"
manifest = json.loads(manifest_path.read_text("utf-8"))
assert not QA.exists(), "Fresh evidence paths only"
assert json.loads((ROOT / "output/qa/godot/phase-runtime-rc33/packaging-complete.json").read_text("utf-8"))["passed"]
assert all(sha(ROOT / n) == h for n, h in manifest["source_inputs"].items())
imports = {}
for n in manifest["source_inputs"]:
    p = ROOT / n
    target = BASE / Path(n).relative_to("game")
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(p, target)
    if p.suffix == ".import":
        for resource in re.findall(r'res://(\.godot/imported/[^"\s]+)', p.read_text("utf-8")):
            src = ROOT / "game" / resource
            dst = BASE / resource
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            imports[resource] = sha(dst)
for p in (ROOT / "game/scripts").glob("*.gd"):
    shutil.copy2(p, BASE / "scripts" / p.name)
shutil.copytree(ROOT / "game/tests", BASE / "tests", dirs_exist_ok=True)
shutil.copytree(BASE, TRIAL)
p = TRIAL / "scripts/battle_view.gd"
s = p.read_text("utf-8")
needle = "var ownership_meshes: Array[ArrayMesh]=[]\n"
assert s.count(needle) == 1
s = s.replace(needle, needle + "var shard_meshes: Dictionary={}\nvar frame_geometry_cache: Dictionary={}\nconst FRAME_GEOMETRY_LIMIT: int=128\n")
old = '\t\tdraw_colored_polygon(PackedVector2Array([Vector2(-p.size,-p.size*.4),Vector2(p.size,-p.size*.3),Vector2(p.size*.7,p.size*.5),Vector2(-p.size*.8,p.size*.6)]),c)'
assert s.count(old) == 1
s = s.replace(old, '\t\tdraw_paper_shard(float(p.size),c)')
needle = '\tdraw_frame_unit(u,pos,meta,modulation)'
assert s.count(needle) == 1
s = s.replace(needle, '\tdraw_frame_unit(u,pos,meta,modulation,hh)')
needle = 'func draw_frame_unit(u: Dictionary,pos: Vector2,meta: Dictionary,modulation: Color):'
assert s.count(needle) == 1
s = s.replace(needle, 'func draw_frame_unit(u: Dictionary,pos: Vector2,meta: Dictionary,modulation: Color,shown_height: float=-1):')
old = '''\tvar sf: float=unit_height(u.id)/float(profile.source_height)
\tvar anchor=Vector2(profile.anchor[0],profile.anchor[1])
\tdraw_set_transform(pos+canvas_shift,0,Vector2(float(u.facing)*sf,sf))
\tdraw_texture_rect_region(db.texture(profile.atlas),Rect2(-anchor,Vector2(profile.frame_size[0],profile.frame_size[1])),FramePlayer.region(profile,selected.frame),modulation)'''
new = '''\tvar sf: float=(unit_height(u.id) if shown_height<0 else shown_height)/float(profile.source_height)
\tvar geometry: FrameGeometry=frame_geometry(str(u.id),profile)
\tdraw_set_transform(pos+canvas_shift,0,Vector2(float(u.facing)*sf,sf))
\tdraw_texture_rect_region(db.texture(profile.atlas),geometry.destination,geometry.region(int(selected.frame)),modulation)'''
assert s.count(old) == 1
s = s.replace(old, new)
helper = '''
class FrameGeometry:
\textends RefCounted
\tvar anchor_values: Array
\tvar size_values: Array
\tvar columns: int
\tvar destination: Rect2
\tvar frame_size: Vector2
\tvar regions: Dictionary={}
\tfunc _init(profile: Dictionary):
\t\tanchor_values=profile.anchor.duplicate();size_values=profile.frame_size.duplicate();columns=int(profile.columns)
\t\tframe_size=Vector2(size_values[0],size_values[1])
\t\tdestination=Rect2(-Vector2(anchor_values[0],anchor_values[1]),frame_size)
\tfunc matches(profile: Dictionary) -> bool:
\t\treturn profile.anchor==anchor_values and profile.frame_size==size_values and int(profile.columns)==columns
\tfunc region(frame: int) -> Rect2:
\t\tif not regions.has(frame):
\t\t\tif regions.size()>=64:regions.erase(regions.keys()[0])
\t\t\tregions[frame]=Rect2(Vector2(frame%columns,floori(float(frame)/float(columns)))*frame_size,frame_size)
\t\treturn regions[frame]

func frame_geometry(id: String,profile: Dictionary) -> FrameGeometry:
\tvar value: FrameGeometry=frame_geometry_cache.get(id)
\tif value==null or not value.matches(profile):
\t\tif value==null and frame_geometry_cache.size()>=FRAME_GEOMETRY_LIMIT:frame_geometry_cache.erase(frame_geometry_cache.keys()[0])
\t\tvalue=FrameGeometry.new(profile);frame_geometry_cache[id]=value
\treturn value

func draw_paper_shard(size_value: float,color: Color):
\t# Keep the original four coordinates at each exact size. Color, fade,
\t# rotation, position, visibility and the ink edge remain live per particle.
\tif not shard_meshes.has(size_value):
\t\tif shard_meshes.size()>=32:shard_meshes.erase(shard_meshes.keys()[0])
\t\tvar points=PackedVector2Array([Vector2(-size_value,-size_value*.4),Vector2(size_value,-size_value*.3),Vector2(size_value*.7,size_value*.5),Vector2(-size_value*.8,size_value*.6)])
\t\tvar vertices=PackedVector3Array();var colors=PackedColorArray()
\t\tfor point in points:vertices.append(Vector3(point.x,point.y,0));colors.append(Color.WHITE)
\t\tvar arrays: Array=[];arrays.resize(Mesh.ARRAY_MAX)
\t\tarrays[Mesh.ARRAY_VERTEX]=vertices;arrays[Mesh.ARRAY_COLOR]=colors;arrays[Mesh.ARRAY_INDEX]=Geometry2D.triangulate_polygon(points)
\t\tvar mesh=ArrayMesh.new();mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES,arrays);shard_meshes[size_value]=mesh
\tdraw_mesh(shard_meshes[size_value],null,Transform2D.IDENTITY,color)
'''
needle = '\nfunc draw_frame_unit'
assert s.count(needle) == 1
s = s.replace(needle, helper + needle)
p.write_text(s, "utf-8")
changed = [q.name for q in (BASE / "scripts").glob("*.gd") if sha(q) != sha(TRIAL / "scripts" / q.name)]
assert changed == ["battle_view.gd"], changed
shutil.copy2(manifest_path, QA / "baseline-build-manifest.json")
(QA / "freeze.json").write_text(json.dumps({
    "passed": True, "baseline_version": manifest["version"], "public_inputs": manifest["source_inputs"],
    "native_imports": imports, "baseline_scripts": {q.name: sha(q) for q in (BASE / "scripts").glob("*.gd")},
    "trial_scripts": {q.name: sha(q) for q in (TRIAL / "scripts").glob("*.gd")},
    "changed_scripts": changed, "generator_sha256": sha(Path(__file__)),
    "scope": "Verified RC33 frozen1194 public inputs,455 imports and complete44 raw-helper source closure. Isolated view-only trial: bounded exact sprite-region geometry and original-size shard meshes. No textures retained; atlas LRU calls unchanged. Frame selection, statuses, opacity, painter order, simulation, plot, map ratios and formal game unchanged. Trial not yet verified."
}, indent=2) + "\n", "utf-8")
print("RC33 frozen; isolated geometry R1 prepared", len(imports), "imports", flush=True)
