"""Create a new validation checkout, preserving every started native trial."""
from pathlib import Path
import hashlib
import json
import shutil
import sys

ROOT = Path(__file__).resolve().parents[2]
QA = ROOT / "output/qa/godot/pressure-runtime-rc31"
target = QA / "terrain-commands-final-runtime"
before = QA / "terrain-commands-r3-runtime"
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
manifest = json.loads((QA / "baseline-build-manifest.json").read_text("utf-8"))
if target.exists():
    assert "--resume-staged-copy" in sys.argv and not (QA / "final-validation-inputs.json").exists()
    assert all(sha(target / name.removeprefix("game/")) == sha(before / name.removeprefix("game/")) for name in manifest["source_inputs"])
else:
    shutil.copytree(before, target)
# Export manifests already include test UID sidecars, but omit test source.
for path in (target / "tests").rglob("*"):
    if path.is_file():assert sha(path) == sha(ROOT / "game" / path.relative_to(target))
shutil.copytree(ROOT / "game/tests", target / "tests", dirs_exist_ok=True)
inputs = {name: sha(target / name.removeprefix("game/")) for name in manifest["source_inputs"]}
changed = {name for name, digest in inputs.items() if digest != manifest["source_inputs"][name]}
assert changed == {"game/scripts/battle_view.gd", "game/scripts/theatre_ground_cache.gd"}
assert all(sha(target / "scripts" / p.name) == sha(p) for p in (before / "scripts").glob("*.gd"))
(QA / "final-validation-inputs.json").write_text(json.dumps({
    "generator_sha256": sha(Path(__file__)), "source_inputs": inputs,
    "additional_test_inputs": {p.relative_to(target).as_posix(): sha(p) for p in (target / "tests").rglob("*") if p.is_file()},
    "changed_inputs": sorted(changed),
    "scope": "New isolated validation project adds the established external source test suite. The played R1/R2/R3 projects remain unchanged; all1194 final game inputs match R3."
}, indent=2) + "\n", "utf-8")
print("Prepared final rendering validation with the complete original test suite")
