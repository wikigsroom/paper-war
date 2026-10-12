"""Narrow R3 to measured shard savings; reject the slower sprite cache."""
from pathlib import Path
import hashlib
import json
import shutil

ROOT = Path(__file__).resolve().parents[2]
QA = ROOT / "output/qa/godot/render-runtime-rc34"
SOURCE = QA / "geometry-r2-runtime"
TRIAL = QA / "shards-r3-runtime"
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert not TRIAL.exists()
performance = json.loads((QA / "geometry-r2-natural-observation.json").read_text("utf-8"))
assert performance["passed"]
assert json.loads((QA / "geometry-r2-source-gates.json").read_text("utf-8"))["passed"]
assert json.loads((QA / "geometry-r2-render/report.json").read_text("utf-8"))["passed"]
shutil.copytree(SOURCE, TRIAL)
p = TRIAL / "scripts/battle_view.gd"
s = p.read_text("utf-8")
s = s.replace("var frame_geometry_cache: Dictionary={}\nconst FRAME_GEOMETRY_LIMIT: int=128\n", "")
start = s.index("\nclass FrameGeometry:")
end = s.index("\nfunc draw_paper_shard", start)
s = s[:start] + s[end:]
old = '''\tvar geometry: FrameGeometry=frame_geometry(str(u.id),profile)
\tdraw_set_transform(pos+canvas_shift,0,Vector2(float(u.facing)*sf,sf))
\tdraw_texture_rect_region(db.texture(profile.atlas),geometry.destination,geometry.region(int(selected.frame)),modulation)'''
new = '''\tvar anchor=Vector2(profile.anchor[0],profile.anchor[1])
\tdraw_set_transform(pos+canvas_shift,0,Vector2(float(u.facing)*sf,sf))
\tdraw_texture_rect_region(db.texture(profile.atlas),Rect2(-anchor,Vector2(profile.frame_size[0],profile.frame_size[1])),FramePlayer.region(profile,selected.frame),modulation)'''
assert s.count(old) == 1
s = s.replace(old, new)
p.write_text(s, "utf-8")
(QA / "shards-r3-preparation.json").write_text(json.dumps({"passed": True,
    "generator_sha256": sha(Path(__file__)), "previous_performance_sha256": sha(QA / "geometry-r2-natural-observation.json"),
    "trial_scripts": {q.name: sha(q) for q in (TRIAL / "scripts").glob("*.gd")},
    "scope": "R3 removes all frame-geometry cache/class and restores original live anchor/region calculation. Only reuse the already-computed unit height, original-size shard meshes and current-draw mesh keepalive. Entire simulation/data and formal RC33 unchanged. R2 unit snapshot cost exceeded baseline; shard snapshot cost improved. No R3 performance/adoption claim yet."
}, indent=2)+"\n", "utf-8")
(QA / "geometry-r2-rejection.json").write_text(json.dumps({"passed": False, "rejected": True,
    "performance_sha256": sha(QA / "geometry-r2-natural-observation.json"),
    "reason": "Correct pixels/boundaries, but sprite cache increased both measured unit-layer snapshots and offset most shard savings. Natural FPS improvement was negligible. Retain measured evidence, remove sprite cache and test a narrower R3; no R2 formal adoption."
}, indent=2)+"\n", "utf-8")
observer = QA / "shards-render-observer.gd"
runner = ROOT / "tools/paper-warfront/check_rc34_shards_render.py"
assert not observer.exists() and not runner.exists()
s = (QA / "geometry-render-observer.gd").read_text("utf-8")
s = s.replace("var shots: Array=[]\n", "var shots: Array=[]\nvar mesh_checks: Array=[]\n")
needle = '\t\t\tawait render(map_id+"-shards-"+str(phase))'
extra = '''
\t\t\tif app.view.get_property_list().any(func(info):return str(info.name)=="retained_shard_meshes"):
\t\t\t\tmesh_checks.append({"pose":map_id+"-"+str(phase),"cached":app.view.shard_meshes.size(),"in_flight":app.view.retained_shard_meshes.size(),"passed":app.view.shard_meshes.size()<=32 and app.view.retained_shard_meshes.size()==40})
\t\t\t\tif not mesh_checks[-1].passed:print("SHARD_REFERENCE_FAILURE ",mesh_checks[-1]);quit(1);return
'''
assert s.count(needle) == 1
s = s.replace(needle, needle + extra)
s = s.replace('"captures":shots}', '"captures":shots,"mesh_checks":mesh_checks}')
observer.write_text(s, "utf-8")
s = (ROOT / "tools/paper-warfront/check_rc34_geometry_render.py").read_text("utf-8")
s = s.replace("geometry-render-observer.gd", "shards-render-observer.gd")
runner.write_text(s, "utf-8")
source_runner = ROOT / "tools/paper-warfront/run_rc34_shards_gates.py"
assert not source_runner.exists()
s = (ROOT / "tools/paper-warfront/run_rc34_render_gates_r2.py").read_text("utf-8")
s = s.replace("geometry-r2", "shards-r3")
start = s.index('    ("boundary",')
end = s.index('\n]', start)
s = s[:start] + s[end:]
s = s.replace("len(jobs) == 2", "len(jobs) == 1")
s = s.replace("Complete78 source regression plus exact geometry/invalidation/eviction boundary checks.", "Fresh complete78 source regression. Native shard reference/eviction checks are in the separate42-pose render gate; the retired sprite-cache boundary is not counted.")
source_runner.write_text(s, "utf-8")
natural_runner = ROOT / "tools/paper-warfront/observe_rc34_shards.py"
assert not natural_runner.exists()
s = (ROOT / "tools/paper-warfront/observe_rc34_geometry.py").read_text("utf-8")
s = s.replace("geometry-r2", "shards-r3").replace("view-only R2", "view-only shard R3")
natural_runner.write_text(s, "utf-8")
print("Prepared narrowed shard R3 and independent native reference checks", flush=True)
