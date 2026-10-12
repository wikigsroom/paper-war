"""Adopt the verified render-only helpers; bind unchanged RC30 combat/story."""
from pathlib import Path
import hashlib
import json
import shutil

ROOT = Path(__file__).resolve().parents[2]
QA = ROOT / "output/qa/godot/pressure-runtime-rc31"
VERSION = "3.0.0-rc31-preview"
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
read = lambda p: json.loads(p.read_text("utf-8"))
assert not (QA / "adoption.json").exists()
baseline = read(QA / "baseline-build-manifest.json")
assert baseline["version"] == "3.0.0-rc30-preview"
assert all(sha(ROOT / n) == d for n, d in baseline["source_inputs"].items())
candidate = QA / "terrain-commands-final-runtime"
frozen = read(QA / "final-validation-inputs.json")
assert all(sha(candidate / n.removeprefix("game/")) == d for n, d in frozen["source_inputs"].items())
regression = read(QA / "candidate-regression-final/report.json")
assert regression["passed"] and regression["source_unchanged"] and len(regression["tests"]) == 78
assert sum(r["checks"] for r in regression["tests"]) == 195435
reference = read(QA / "terrain-command-reference-r3.json")
assert reference["passed"] and not reference["failures"] and reference["checks"] == 5873
assert reference["source_sha256"] == sha(candidate / "scripts/theatre_ground_cache.gd")
assert reference["observer_sha256"] == sha(ROOT / "tools/paper-warfront/test_terrain_command_retention.gd")
pixel = read(QA / "terrain-command-pixels-r3/report.json")
assert pixel["passed"] and len(pixel["comparisons"]) == 12 and all(r["max_channel_delta"] == 0 for r in pixel["comparisons"])
abba = read(QA / "terrain-abba-native-r3/terrain-abba.json")
assert abba["source_sha256"] == reference["source_sha256"]
assert abba["observer_sha256"] == sha(QA / "terrain-abba-observer-r3.gd")
backup = QA / "pre-adoption"
backup.mkdir()
changed = {}
for name in ["scripts/battle_view.gd", "scripts/theatre_ground_cache.gd", "project.godot", "export_presets.cfg"]:
    before = ROOT / "game" / name
    saved = backup / name
    saved.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(before, saved)
    if name.startswith("scripts/"):
        shutil.copy2(candidate / name, before)
    else:
        old = before.read_text("utf-8")
        new = old.replace(baseline["version"], VERSION)
        if name == "export_presets.cfg":
            assert new.count("version/code=30029") == 1
            new = new.replace("version/code=30029", "version/code=30030")
        assert new != old
        before.write_text(new, "utf-8")
    changed["game/" + name] = {"before": sha(saved), "after": sha(before)}
assert all(sha(ROOT / n) == d for n, d in regression["inputs"].items())
shutil.copytree(QA / "candidate-regression-final", QA / "source-final")
shutil.copytree(QA / "candidate-regression-final", QA / "formal-reach/regression")
historical = ROOT / "output/qa/godot/dense-runtime-rc30"
story = ROOT / "output/qa/godot/story-atlas-rc29"
shutil.copy2(story / "authorship.json", QA / "authorship.json")
font = read(historical / "font-coverage.json")
assert font["passed"] and all(sha(ROOT / r["path"]) == r["sha256"] for r in font["records"])
font["retained_from_version"] = font["version"]
font["version"] = VERSION
font["retained_report_sha256"] = sha(historical / "font-coverage.json")
font["retention_scope"] = "Byte-identical RC30 narrative, fonts and runtime data; retained coverage, no new text or glyph generation."
(QA / "font-coverage.json").write_text(json.dumps(font, ensure_ascii=False, indent=2) + "\n", "utf-8")
unchanged = {n: d for n, d in baseline["source_inputs"].items() if n not in changed}
assert all(sha(ROOT / n) == d for n, d in unchanged.items())
history = ["phase-reuse-r2-capacity.json", "phase-reuse-r2-paid-r3.json", "combat-history-binding.json", "font-coverage.json"]
binding = {"passed": True, "previous_version": baseline["version"], "current_version": VERSION,
    "changed_inputs": changed, "unchanged_inputs": unchanged,
    "all_campaign_data_unchanged": True, "campaign_battle_fields_unchanged": True,
    "retained_combat_evidence": {str((historical / n).relative_to(ROOT)).replace("\\", "/"): sha(historical / n) for n in history},
    "retained_previous_verification": {"path": "release/3.0.0-rc30-preview/preview-verification.json", "sha256": sha(ROOT / "release/3.0.0-rc30-preview/preview-verification.json")},
    "scope": "Render-only change; all42 other scripts, all200 map/story/AI/balance/action inputs and imported raster/font/audio source bytes remain RC30. The3600 dense and73103 paid original-closure comparisons are retained for identical combat inputs, not rerun or new FPS claims. Fresh source and compiled rendering checks are separate."}
(QA / "combat-history-binding.json").write_text(json.dumps(binding, ensure_ascii=False, indent=2) + "\n", "utf-8")
proofs = ["terrain-command-reference-r3.json", "candidate-regression-final/report.json", "terrain-command-pixels-r3/report.json", "terrain-abba-native-r3/terrain-abba.json", "final-validation-inputs.json"]
(QA / "adoption.json").write_text(json.dumps({"passed": True, "release": VERSION, "changed_inputs": changed,
    "proofs": {n: sha(QA / n) for n in proofs}, "generated_raster_assets": False,
    "source_checks": 201308, "scope": "Verified original terrain commands on movement; one exact static plan after settling. Weak owners and conservative geometry/asset/texture/mesh invalidation. Source proof retained without claiming a second execution; actual compiled export checks remain."}, indent=2) + "\n", "utf-8")
print("Adopted verified rendering helpers; RC31 native export checks remain")
