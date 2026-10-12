"""Extend native fixed-pose comparison with warm-cache ownership/color changes."""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[2]
QA = ROOT / "output/qa/godot/phase-runtime-rc33"
observer = QA / "ownership-render-observer.gd"
runner = ROOT / "tools/paper-warfront/check_rc33_ownership_render.py"
assert not observer.exists() and not runner.exists()
original = ROOT / "tools/paper-warfront/probe_render_cache_equivalence.gd"
s = original.read_text("utf-8")
needle = '\tvar inputs: Dictionary={}\n'
assert s.count(needle) == 1
extra = '''
\t\t# Keep the existing view/meshes warm while allegiance, observer and shake
\t\t# change. These are fixed native poses, not command or balance evidence.
\t\tapp.sim.config.fog=false
\t\tfor i in range(app.sim.units.size()):
\t\t\tvar u: Dictionary=app.sim.units[i]
\t\t\tu.side=1-int(u.side);u.hp=u.max_hp*.63;u.hurt=.15 if i%2==0 else 0
\t\t\tu.clone=i%4==0;u.facing=-u.facing
\t\t\tu.statuses.clear()
\t\t\tfor state in ["poison","silence","protect","bind","burn"]:u.statuses[state]={"left":2,"source":u.side}
\t\t\tapp.sim.map.apply_anchor(u,app.sim.map.project(Vector2(app.sim.map.length*.5-3.4+float(i)*.43,0)))
\t\tapp.sim.visibility.refresh();app.view.visual_time=3.271;app.view.shake=4.5
\t\tapp.view.camera_x=app.sim.map.length*.5+.237;app.view.target_camera=app.view.camera_x
\t\tapp.view.selected_uid=app.sim.units[0].uid
\t\tfor observer_side in [0,1]:
\t\t\tapp.view.player_side=observer_side
\t\t\tawait render(map_id+"-ownership-"+str(observer_side))
'''
s = s.replace(needle, extra + needle)
observer.write_text(s, "utf-8")
source_runner = ROOT / "tools/paper-warfront/check_render_cache_equivalence.py"
r = source_runner.read_text("utf-8")
needle = "shutil.copyfile(ROOT/'tools/paper-warfront/probe_render_cache_equivalence.gd',observer)"
assert r.count(needle) == 1
r = r.replace(needle, "shutil.copyfile(ROOT/'output/qa/godot/phase-runtime-rc33/ownership-render-observer.gd',observer)")
r = r.replace("delta.getdata()", "delta.get_flattened_data()")
runner.write_text(r, "utf-8")
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
(QA / "ownership-render-observer-generation.json").write_text(json.dumps({
    "generator_sha256": sha(Path(__file__)), "original_observer_sha256": sha(original),
    "observer_sha256": sha(observer), "original_runner_sha256": sha(source_runner),
    "runner_sha256": sha(runner),
    "scope": "Existing three maps/two subpixel cameras plus two observer-relative warm-cache allegiance, damaged, hurt, clone, statuses and shaken poses per map; two native display/GPU configurations. Preserves immutable original observers and completed comparisons."
}, indent=2) + "\n", "utf-8")
print("Prepared warm-cache allegiance and shake render comparison", flush=True)
