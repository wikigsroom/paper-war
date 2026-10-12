"""Freeze current RC31 before diagnosing repeated movement-index construction."""
from pathlib import Path
import hashlib
import json
import re
import shutil

ROOT = Path(__file__).resolve().parents[2]
QA = ROOT / "output/qa/godot/contact-runtime-rc32"
BASE = QA / "baseline-runtime"
ORACLE = QA / "oracle-runtime"
assert not BASE.exists() and not ORACLE.exists()
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
manifest = json.loads((ROOT / "release/3.0.0-rc31-preview/build-manifest.json").read_text("utf-8"))
assert all(sha(ROOT / n) == d for n, d in manifest["source_inputs"].items())
QA.mkdir(parents=True, exist_ok=True)
shutil.copy2(ROOT / "release/3.0.0-rc31-preview/build-manifest.json", QA / "baseline-build-manifest.json")
for name in ["scripts", "data", "tests"]:shutil.copytree(ROOT / "game" / name, BASE / name)
(BASE / "project.godot").write_text('config_version=5\n[application]\nconfig/name="Frozen RC31 contact diagnosis"\n[rendering]\nrenderer/rendering_method="gl_compatibility"\n', "utf-8")
shutil.copy2(ROOT / "output/qa/godot/pressure-runtime-rc31/baseline-runtime/capacity-config.json", BASE / "capacity-config.json")
shutil.copytree(BASE / "scripts", ORACLE / "scripts")
absolute = (ORACLE / "scripts").as_posix() + "/"
closure = {}
for p in sorted((ORACLE / "scripts").glob("*.gd")):
    p.write_text(re.sub(r"res://scripts/", absolute, p.read_text("utf-8")), "utf-8")
    closure[p.name] = {"original_sha256": sha(BASE / "scripts" / p.name), "oracle_sha256": sha(p)}
profile = QA / "profile-r1-runtime"
shutil.copytree(BASE, profile)
old = ROOT / "output/qa/godot/pressure-runtime-rc31/current-profile-r1-runtime/tests"
for name in ["capacity_cpu_profiler.gd", "dense_visibility_profiler.gd", "probe_capacity_cpu.gd"]:
    shutil.copy2(old / name, profile / "tests" / name)
p = profile / "tests/capacity_cpu_profiler.gd"
source = p.read_text("utf-8")
source += '''\nfunc prepare_blocker_roads():
\tvar before: int=Time.get_ticks_usec();super.prepare_blocker_roads();record("blocker_index",before)
'''
p.write_text(source, "utf-8")
(QA / "freeze.json").write_text(json.dumps({"release": manifest["version"], "public_inputs": manifest["source_inputs"],
    "runtime_inputs": {p.relative_to(BASE).as_posix(): sha(p) for p in BASE.rglob("*") if p.is_file()},
    "oracle_scripts": closure, "generator_sha256": sha(Path(__file__)),
    "scope": "Entire current RC31 helper/data/test closure; only internal oracle paths rewritten. Nested native diagnosis additionally measures blocker-index rebuild calls. No formal game or release modifications."
}, indent=2) + "\n", "utf-8")
print("Frozen RC31 closure", len(closure), "scripts; prepared blocker-index diagnosis")
