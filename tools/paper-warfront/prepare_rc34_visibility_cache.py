"""Prepare a view-only per-draw visibility query cache from the verified RC33 baseline."""
from pathlib import Path
import hashlib
import json
import shutil

ROOT = Path(__file__).resolve().parents[2]
QA = ROOT / "output/qa/godot/render-runtime-rc34"
SOURCE = QA / "baseline-runtime"
TRIAL = QA / "visibility-r4-runtime"
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert not TRIAL.exists()
assert json.loads((QA / "shards-r3-source-gates.json").read_text("utf-8"))["passed"]
shutil.copytree(SOURCE, TRIAL)
p = TRIAL / "scripts/battle_view.gd"
s = p.read_text("utf-8")
needle = "var paper_ellipse_mesh: ArrayMesh\n"
assert s.count(needle) == 1
s = s.replace(needle, needle + "var draw_visibility_cache: Dictionary={}\n")
needle = "func _draw():\n\tif db==null: return\n"
assert s.count(needle) == 1
s = s.replace(needle, needle + "\tdraw_visibility_cache.clear()\n")
calls = 0
s = s.replace("sim.location_visible(player_side,", "location_visible_cached(")
calls = s.count("location_visible_cached(")
assert calls == 11, calls
needle = "\nfunc ordered_units() -> Array:"
assert s.count(needle) == 1
helper = '''
func location_visible_cached(x: float,y: float) -> bool:
\t# A single CanvasItem draw pass cannot observe a visibility revision between
\t# these queries. Keep exact Vector2 keys; player_side is the current view.
\tvar key:=Vector2(x,y)
\tif not draw_visibility_cache.has(key):draw_visibility_cache[key]=sim.location_visible(player_side,x,y)
\treturn bool(draw_visibility_cache[key])
'''
s = s.replace(needle, helper + needle)
p.write_text(s, "utf-8")
(QA / "visibility-r4-preparation.json").write_text(json.dumps({"passed": True,
    "generator_sha256": sha(Path(__file__)), "baseline_view_sha256": sha(SOURCE / "scripts/battle_view.gd"),
    "trial_view_sha256": sha(p), "changed_from_RC33": ["battle_view.gd"], "replaced_calls": calls,
    "scope": "Fresh baseline-derived view trial. Cache is cleared at every _draw, keyed by exact world coordinates, and calls the original location_visible once per key. No visibility state, fog revision, camera, simulation, map, animation, status, particle count or UI behavior is retained across draw passes. Not yet verified."
}, indent=2) + "\n", "utf-8")
print("Prepared per-draw location visibility cache R4", flush=True)
