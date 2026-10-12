"""Freeze verified RC32, then profile its native unit/visibility phases in isolation."""
from pathlib import Path
import hashlib
import json
import re
import shutil

ROOT = Path(__file__).resolve().parents[2]
QA = ROOT / "output/qa/godot/phase-runtime-rc33"
BASE = QA / "baseline-runtime"
ORACLE = QA / "oracle-runtime"
PROFILE = QA / "profile-r1-runtime"
assert not QA.exists()
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
manifest = json.loads((ROOT / "release/3.0.0-rc32-preview/build-manifest.json").read_text("utf-8"))
assert all(sha(ROOT / n) == d for n, d in manifest["source_inputs"].items())
assert json.loads((ROOT / "output/qa/godot/contact-runtime-rc32/packaging-complete.json").read_text("utf-8"))["passed"]
QA.mkdir(parents=True)
shutil.copy2(ROOT / "release/3.0.0-rc32-preview/build-manifest.json", QA / "baseline-build-manifest.json")
for name in ["scripts", "data", "tests"]:
    shutil.copytree(ROOT / "game" / name, BASE / name)
(BASE / "project.godot").write_text('config_version=5\n[application]\nconfig/name="Frozen RC32 phase diagnosis"\n[rendering]\nrenderer/rendering_method="gl_compatibility"\n', "utf-8")
shutil.copy2(ROOT / "output/qa/godot/contact-runtime-rc32/baseline-runtime/capacity-config.json", BASE / "capacity-config.json")
shutil.copytree(BASE / "scripts", ORACLE / "scripts")
absolute = (ORACLE / "scripts").as_posix() + "/"
closure = {}
for p in sorted((ORACLE / "scripts").glob("*.gd")):
    p.write_text(re.sub(r"res://scripts/", absolute, p.read_text("utf-8")), "utf-8")
    closure[p.name] = {"original_sha256": sha(BASE / "scripts" / p.name), "oracle_sha256": sha(p)}
shutil.copytree(BASE, PROFILE)
old = ROOT / "output/qa/godot/contact-runtime-rc32/profile-r1-runtime/tests"
for name in ["capacity_cpu_profiler.gd", "dense_visibility_profiler.gd", "probe_capacity_cpu.gd"]:
    shutil.copy2(old / name, PROFILE / "tests" / name)
p = PROFILE / "tests/capacity_cpu_profiler.gd"
s = p.read_text("utf-8")
s += '''
func nearest_enemy_uncached(u: Dictionary) -> Dictionary:
\tvar before: int=Time.get_ticks_usec();var value: Dictionary=super.nearest_enemy_uncached(u);record("uncached_target",before);return value
func prepare_target_answers():
\tvar before: int=Time.get_ticks_usec();super.prepare_target_answers();record("answer_eligibility",before)
func prepare_target_snapshot():
\tvar before: int=Time.get_ticks_usec();super.prepare_target_snapshot();record("target_geometry",before)
func physical_anchor(a: Dictionary) -> Dictionary:
\tvar before: int=Time.get_ticks_usec();var value: Dictionary=super.physical_anchor(a);record("physical_anchor",before);return value
func hostile_target(target: Dictionary,side: int,source_uid: int=0) -> bool:
\tvar before: int=Time.get_ticks_usec();var value: bool=super.hostile_target(target,side,source_uid);record("hostility",before);return value
'''
p.write_text(s, "utf-8")
(QA / "freeze.json").write_text(json.dumps({"release": manifest["version"], "public_inputs": manifest["source_inputs"],
    "runtime_inputs": {p.relative_to(BASE).as_posix(): sha(p) for p in BASE.rglob("*") if p.is_file()},
    "oracle_scripts": closure, "generator_sha256": sha(Path(__file__)),
    "scope": "Complete verified RC32 helper/data/test closure; oracle paths rewritten only. Nested native phase diagnosis is neither FPS nor a candidate performance claim. Formal game and release files untouched."
}, indent=2) + "\n", "utf-8")
print("Frozen verified RC32", len(closure), "scripts; prepared phase diagnosis")
