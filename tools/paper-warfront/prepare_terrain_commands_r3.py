"""Preserve R2 failures; invalidate retained commands after texture eviction."""
from pathlib import Path
import hashlib
import json
import shutil

ROOT = Path(__file__).resolve().parents[2]
QA = ROOT / "output/qa/godot/pressure-runtime-rc31"
target = QA / "terrain-commands-r3-runtime"
assert not target.exists()
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
before = QA / "terrain-commands-r2-runtime"
shutil.copytree(before, target)
path = target / "scripts/theatre_ground_cache.gd"
source = path.read_text("utf-8")
source = source.replace("""\t\t# The resource is held by its drawing command. A normal LRU removal can
\t\t# reload that same resource; replacing a cached texture invalidates it.
\t\tif view.db.textures.has(path) and not is_same(view.db.textures[path],terrain_textures[id]):return false""", """\t\t# After eviction, a new load can fail or resolve to another resource.
\t\t# Draw through the original loader until the exact texture is resident.
\t\tif not view.db.textures.has(path) or not is_same(view.db.textures[path],terrain_textures[id]):return false""", 1)
assert "not view.db.textures.has(path) or" in source
path.write_text(source, "utf-8")
observer = QA / "terrain-abba-observer-r3.gd"
shutil.copy2(QA / "terrain-abba-observer-r2.gd", observer)
(QA / "terrain-commands-r3-inputs.json").write_text(json.dumps({
    "generator_sha256": sha(Path(__file__)),
    "r2_reference_report_sha256": sha(QA / "terrain-command-reference-r2.json"),
    "r2_scripts": {p.name: sha(p) for p in (before / "scripts").glob("*.gd")},
    "r3_scripts": {p.name: sha(p) for p in (target / "scripts").glob("*.gd")},
    "observer_sha256": sha(observer),
    "scope": "Independent reference exposed stale terrain after a retained texture was evicted and its reload failed. R3 conservatively bypasses on absence or identity mismatch. R2 and its failed comparison remain intact."
}, indent=2) + "\n", "utf-8")
print("Prepared isolated R3 eviction fix")
