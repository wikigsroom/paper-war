"""Correct in-flight mesh ownership in a fresh R2, preserving the failed R1."""
from pathlib import Path
import hashlib
import json
import shutil

ROOT = Path(__file__).resolve().parents[2]
QA = ROOT / "output/qa/godot/render-runtime-rc34"
SOURCE = QA / "geometry-r1-runtime"
TRIAL = QA / "geometry-r2-runtime"
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert not TRIAL.exists()
gate = QA / "geometry-r1-source-gates.json"
assert json.loads(gate.read_text("utf-8"))["passed"]
log = QA / "geometry-r1-render/desktop-after/runtime.log"
assert 'Parameter "mesh" is null.' in log.read_text("utf-8")
shutil.copytree(SOURCE, TRIAL)
p = TRIAL / "scripts/battle_view.gd"
s = p.read_text("utf-8")
needle = "var shard_meshes: Dictionary={}\n"
assert s.count(needle) == 1
s = s.replace(needle, needle + "var retained_shard_meshes: Array[ArrayMesh]=[]\n")
needle = "func _draw():\n\tif db==null: return\n"
assert s.count(needle) == 1
s = s.replace(needle, needle + "\t# The engine clears this canvas's old commands before invoking _draw.\n\t# Keep every newly submitted mesh alive until the next drawing pass.\n\tretained_shard_meshes.clear()\n")
needle = "\tdraw_mesh(shard_meshes[size_value],null,Transform2D.IDENTITY,color)"
assert s.count(needle) == 1
s = s.replace(needle, "\tretained_shard_meshes.append(shard_meshes[size_value])\n" + needle)
p.write_text(s, "utf-8")
prep = QA / "geometry-r2-preparation.json"
prep.write_text(json.dumps({
    "passed": True, "generator_sha256": sha(Path(__file__)), "r1_source_gate_sha256": sha(gate),
    "failed_r1_render_log_sha256": sha(log), "r1_view_sha256": sha(SOURCE / "scripts/battle_view.gd"),
    "trial_scripts": {q.name: sha(q) for q in (TRIAL / "scripts").glob("*.gd")},
    "scope": "R2 holds a reference to each submitted shard mesh until next _draw, after old canvas commands are cleared. Persistent shape cache remains bounded32; in-flight references are bounded by actual visible particles per drawing pass. Failed R1 overflow/GPU errors and original regression are preserved. No new simulation or formal game changes. Not yet rendered or FPS verified."
}, indent=2) + "\n", "utf-8")
runner = ROOT / "tools/paper-warfront/run_rc34_render_gates_r2.py"
assert not runner.exists()
s = (ROOT / "tools/paper-warfront/run_rc34_render_gates.py").read_text("utf-8")
s = s.replace("geometry-r1", "geometry-r2")
s = s.replace('freeze = json.loads((QA / "freeze.json").read_text("utf-8"))', 'freeze = json.loads((QA / "geometry-r2-preparation.json").read_text("utf-8"))')
s = s.replace('"freeze_sha256": sha(QA / "freeze.json")', '"preparation_sha256": sha(QA / "geometry-r2-preparation.json"), "freeze_sha256": sha(QA / "freeze.json")')
runner.write_text(s, "utf-8")
(QA / "geometry-r1-rejection.json").write_text(json.dumps({
    "passed": False, "rejected": True, "source_gate_sha256": sha(gate), "failed_native_log_sha256": sha(log),
    "render_observer_sha256": sha(QA / "geometry-render-observer.gd"),
    "reason": "Native Vulkan overflow fixture evicted meshes already submitted in the same canvas drawing pass. RIDs became invalid before commands were consumed. Source-only coordinate assertions cannot establish mesh lifetime. Formal RC33 remains unchanged; do not adopt R1."
}, indent=2) + "\n", "utf-8")
print("Prepared R2 with bounded per-draw mesh keepalive; R1 rejected", flush=True)
