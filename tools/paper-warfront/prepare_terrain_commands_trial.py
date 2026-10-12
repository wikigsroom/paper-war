"""Prepare full isolated native rendering inputs before editing a candidate."""
from pathlib import Path
import hashlib
import json
import shutil

ROOT = Path(__file__).resolve().parents[2]
QA = ROOT / "output/qa/godot/pressure-runtime-rc31"
TARGET = QA / "terrain-commands-r1-runtime"
assert not TARGET.exists(), "Started candidate projects remain immutable"
manifest = json.loads((QA / "baseline-build-manifest.json").read_text("utf-8"))
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert all(sha(ROOT / name) == digest for name, digest in manifest["source_inputs"].items())
imports = set()
for name in manifest["source_inputs"]:
    source = ROOT / name
    dest = TARGET / source.relative_to(ROOT / "game")
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, dest)
    if source.suffix == ".import":
        for token in source.read_text("utf-8").split('"'):
            if token.startswith("res://.godot/imported/"):
                imports.add(token.removeprefix("res://"))
for name in imports:
    source = ROOT / "game" / name
    if source.is_file():
        dest = TARGET / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, dest)
uid = ROOT / "game/.godot/uid_cache.bin"
if uid.exists():
    shutil.copy2(uid, TARGET / ".godot/uid_cache.bin")
(QA / "terrain-commands-base-inputs.json").write_text(json.dumps({"release": manifest["version"],
    "public_inputs": manifest["source_inputs"], "copied_imports": {n: sha(TARGET/n) for n in imports if (TARGET/n).is_file()},
    "generator_sha256": sha(Path(__file__)), "scope": "All current rc30 shipped raster/font/audio/source inputs and native imported artifacts, before isolated static-render experiment. No formal source or release edits."}, indent=2) + "\n", "utf-8")
print("Prepared isolated full native terrain trial", len(manifest["source_inputs"]), "source inputs")
