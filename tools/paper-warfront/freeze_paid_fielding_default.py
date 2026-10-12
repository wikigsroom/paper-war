"""Freeze the working normal pipeline for paid CPU observations on both sides."""
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[2]
QA = ROOT / "output/qa/godot/paid-fielding-rc24"
baseline = QA / "rc23-control-runtime"
target = QA / "formal-default-runtime"
assert not target.exists(), "Do not overwrite frozen default observations"
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
manifest = json.loads((ROOT / "release/3.0.0-rc23-preview/build-manifest.json").read_text(encoding="utf-8-sig"))
changed = []
for folder, pattern in [("scripts", "*.gd"), ("data", "*.json")]:
    (target / folder).mkdir(parents=True)
    for path in sorted((ROOT / "game" / folder).glob(pattern)):
        key = f"game/{folder}/{path.name}"
        if sha(path) != manifest["source_inputs"][key]:
            changed.append(key)
        shutil.copy2(path, target / folder / path.name)
assert changed == ["game/scripts/tactical_ai.gd"], changed
(target / "tests").mkdir()
shutil.copy2(QA / "roles-r3-runtime/tests/probe_faction_matchups.gd", target / "tests/probe_faction_matchups.gd")
shutil.copy2(baseline / "project.godot", target / "project.godot")
shutil.copy2(baseline / "snapshot.json", target / "snapshot.json")
(target / "candidate.json").write_text(json.dumps({
    "policy": "formal-default", "baseline": manifest["version"], "current_source_version": "3.0.0-rc24-preview",
    "changed_gameplay_inputs": changed, "normal_pipeline_enabled_on_both_sides": True,
    "current_ai_source_sha256": sha(ROOT / "game/scripts/tactical_ai.gd"),
    "prices_times_roads_fog_unchanged": True,
    "minimal_project_scope": "Keep control project's viewport/version metadata to isolate normal AI policy. This is an unrendered CPU cohort, not executable/UI/version verification.",
    "generator_sha256": sha(Path(__file__)),
}, indent=2), encoding="utf-8")
print("Frozen default fielding source prepared; only the tactical AI differs")
