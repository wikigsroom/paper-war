"""Adopt only the pixel-equivalent rendering candidate with measured CPU benefit."""
from pathlib import Path
import hashlib
import json
import shutil

ROOT = Path(__file__).resolve().parents[2]
QA = ROOT / "output/qa/godot/render-runtime-rc34"
VERSION = "3.0.0-rc34-preview"
TRIAL = QA / "geometry-r2-runtime"
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
read = lambda p: json.loads(p.read_text("utf-8"))
assert not (QA / "adoption.json").exists()
assert not (QA / "geometry-r2-rejection.json").exists(), "Rejected R2 must not be adopted"
baseline = read(QA / "baseline-build-manifest.json")
assert baseline["version"] == "3.0.0-rc33-preview"
assert all(sha(ROOT / n) == h for n, h in baseline["source_inputs"].items())
proofs = {}
for n in ["geometry-r2-preparation.json", "geometry-r2-source-gates.json", "geometry-r2-render/report.json", "geometry-r2-natural-observation.json"]:
    assert read(QA / n)["passed"], n
    proofs[n] = sha(QA / n)
regression = read(QA / "geometry-r2-regression/report.json")
assert regression["passed"] and regression["source_unchanged"] and len(regression["tests"]) == 78
assert sum(r["checks"] for r in regression["tests"]) == 195435
assert read(QA / "geometry-r2-boundary.json")["checks"] == 29184
pixels = read(QA / "geometry-r2-render/report.json")
assert len(pixels["comparisons"]) == 42 and all(r["max_channel_delta"] == 0 for r in pixels["comparisons"])
cases = read(QA / "geometry-r2-natural-observation.json")["cases"]
base = [r for r in cases if r["label"] == "baseline"]
trial = [r for r in cases if r["label"] == "candidate"]
assert len(base) == len(trial) == 2
assert max(r["draw_mean_ms"] for r in trial) < min(r["draw_mean_ms"] for r in base), "No unambiguous repeated draw-CPU benefit; do not adopt"
freeze = read(QA / "freeze.json")
for n, digest in freeze["baseline_scripts"].items():
    if n != "battle_view.gd":assert sha(TRIAL / "scripts" / n) == digest == sha(ROOT / "game/scripts" / n), n
backup = QA / "pre-adoption"
assert not backup.exists()
changed = {}
for n in ["scripts/battle_view.gd", "project.godot", "export_presets.cfg"]:
    path = ROOT / "game" / n
    old = backup / n;old.parent.mkdir(parents=True, exist_ok=True);shutil.copy2(path, old)
    if n.startswith("scripts/"):shutil.copy2(TRIAL / n, path)
    else:
        s = path.read_text("utf-8").replace(baseline["version"], VERSION)
        if n == "export_presets.cfg":
            assert s.count("version/code=30032") == 1;s = s.replace("version/code=30032", "version/code=30033")
        path.write_text(s, "utf-8")
    changed["game/" + n] = {"before": sha(old), "after": sha(path)}
assert all(sha(ROOT / n) == h for n, h in regression["inputs"].items())
for dest in [QA / "source-final", QA / "formal-reach/regression"]:
    shutil.copytree(QA / "geometry-r2-regression", dest)
previous = ROOT / "output/qa/godot/phase-runtime-rc33"
shutil.copy2(previous / "authorship.json", QA / "authorship.json")
font = read(previous / "font-coverage.json")
assert font["passed"] and all(sha(ROOT / r["path"]) == r["sha256"] for r in font["records"])
font["retained_report_sha256"] = sha(previous / "font-coverage.json")
font["retained_from_version"] = font["version"];font["version"] = VERSION
font["retention_scope"] = "Byte-identical200-map story/data and fonts. View-only optimization; no new glyphs or raster generation."
(QA / "font-coverage.json").write_text(json.dumps(font, ensure_ascii=False, indent=2)+"\n", "utf-8")
unchanged = {n: h for n, h in baseline["source_inputs"].items() if n not in changed}
assert len(unchanged) == 1191 and all(sha(ROOT / n) == h for n, h in unchanged.items())
(QA / "combat-history-binding.json").write_text(json.dumps({"passed": True,
    "previous_version": baseline["version"], "current_version": VERSION, "changed_inputs": changed, "unchanged_inputs": unchanged,
    "previous_verification_sha256": sha(ROOT / "release/3.0.0-rc33-preview/preview-verification.json"),
    "campaign_battle_fields_unchanged": True, "story_progression_unchanged": True,
    "scope": "One view change and version fields;1191 identical other runtime inputs and43 identical other raw helpers. RC33 simulation exact-state/phase evidence retained by full-helper/data hashes; no fresh simulation optimization or CPU benchmark claim. All200 story maps/branches, AI, prices, actions, art/UI/fonts unchanged."
}, indent=2)+"\n", "utf-8")
(QA / "adoption.json").write_text(json.dumps({"passed": True, "version": VERSION, "changed_inputs": changed,
    "proofs": proofs, "runner_sha256": sha(Path(__file__)), "source_tests": 78, "source_checks": 195435,
    "new_geometry_checks": 29184, "source_total_assertions": 224619, "source_pixel_pairs": 42,
    "generated_raster_assets": False,
    "scope": "Bounded exact sprite rectangles and original-size shard meshes; current-draw mesh references survive cache eviction. Real frame selection, observer visibility, tint/fade, particles, status effects, painter order, texture LRU and map/story logic unchanged. Repeated source draw-CPU benefit verified; compiled artifacts and FPS still need checks."
}, indent=2)+"\n", "utf-8")
print("Adopted verified view-only geometry R2; RC34 exports still pending", flush=True)
