"""Freeze the shipped rc30 implementation and current nested CPU diagnosis."""
from pathlib import Path
import hashlib
import json
import re
import shutil

ROOT = Path(__file__).resolve().parents[2]
QA = ROOT / "output/qa/godot/pressure-runtime-rc31"
BASE = QA / "baseline-runtime"
ORACLE = QA / "oracle-runtime"
assert not BASE.exists() and not ORACLE.exists()
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
manifest = json.loads((ROOT / "release/3.0.0-rc30-preview/build-manifest.json").read_text("utf-8"))
assert all(sha(ROOT / name) == digest for name, digest in manifest["source_inputs"].items())
QA.mkdir(parents=True, exist_ok=True)
shutil.copy2(ROOT / "release/3.0.0-rc30-preview/build-manifest.json", QA / "baseline-build-manifest.json")
for part in ["scripts", "data", "tests"]:
    shutil.copytree(ROOT / "game" / part, BASE / part)
(BASE / "project.godot").write_text('config_version=5\n[application]\nconfig/name="Current shipped CPU baseline"\n[rendering]\nrenderer/rendering_method="gl_compatibility"\n', "utf-8")
shutil.copy2(ROOT / "output/qa/godot/dense-runtime-rc30/baseline-runtime/capacity-config.json", BASE / "capacity-config.json")
shutil.copytree(BASE / "scripts", ORACLE / "scripts")
absolute = (ORACLE / "scripts").as_posix() + "/"
closure = {}
for path in sorted((ORACLE / "scripts").glob("*.gd")):
    path.write_text(re.sub(r"res://scripts/", absolute, path.read_text("utf-8")), "utf-8")
    closure[path.name] = {"original_sha256": sha(BASE / "scripts" / path.name), "oracle_sha256": sha(path)}
frozen = {p.relative_to(BASE).as_posix(): sha(p) for p in sorted(BASE.rglob("*")) if p.is_file()}
PROFILE = QA / "current-profile-r1-runtime"
shutil.copytree(BASE, PROFILE)
previous = ROOT / "output/qa/godot/dense-runtime-rc30/profile-r2-runtime/tests"
for name in ["capacity_cpu_profiler.gd", "dense_visibility_profiler.gd", "probe_capacity_cpu.gd"]:
    shutil.copy2(previous / name, PROFILE / "tests" / name)
(QA / "freeze.json").write_text(json.dumps({"release": manifest["version"], "public_inputs": manifest["source_inputs"],
    "runtime_inputs": frozen, "oracle_scripts": closure, "generator_sha256": sha(Path(__file__)),
    "scope": "Exact shipped rc30 helpers/data/tests. Oracle rewrites only internal script paths; new profile inherits this source. No gameplay, artwork or release edits."}, indent=2) + "\n", "utf-8")
print("Frozen current shipped closure", len(closure), "scripts; prepared current CPU diagnosis")
