"""Adopt the proven dense marching and ownership mesh trial, retaining RC32."""
from pathlib import Path
import hashlib
import json
import shutil

ROOT = Path(__file__).resolve().parents[2]
QA = ROOT / "output/qa/godot/phase-runtime-rc33"
VERSION = "3.0.0-rc33-preview"
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
read = lambda p: json.loads(p.read_text("utf-8"))
assert not (QA / "adoption.json").exists()
baseline = read(QA / "baseline-build-manifest.json")
assert baseline["version"] == "3.0.0-rc32-preview"
assert all(sha(ROOT / n) == h for n, h in baseline["source_inputs"].items())
candidate = QA / "native-ownership-r1-runtime"
proofs = {}
for name in ["source-gates-final.json", "ownership-r1-source-gates.json", "ownership-r1-render-expanded/report.json", "ownership-r1-natural-observation.json"]:
    assert read(QA / name)["passed"], name
    proofs[name] = sha(QA / name)
regression = read(QA / "ownership-r1-regression/report.json")
assert regression["passed"] and regression["source_unchanged"] and len(regression["tests"]) == 78
assert sum(x["checks"] for x in regression["tests"]) == 195435
for name, checks in [("marching-capacity-r3.json", 3600), ("marching-boundary-r3-r3.json", 432427), ("marching-phase-r3.json", 28811), ("marching-paid-r3.json", 73103)]:
    report = read(QA / name)
    assert report["passed"] and report["checks"] == checks and not report["failures"]
    assert report["simulation_sha256"] == sha(candidate / "scripts/battle_sim.gd")
    assert report["baseline_sha256"] == sha(QA / "oracle-runtime/scripts/battle_sim.gd")
    proofs[name] = sha(QA / name)
pixels = read(QA / "ownership-r1-render-expanded/report.json")
assert len(pixels["comparisons"]) == 24 and all(r["max_channel_delta"] == 0 for r in pixels["comparisons"])
performance = read(QA / "ownership-r1-natural-observation.json")["cases"]
base = [r for r in performance if r["label"] == "baseline"]
trial = [r for r in performance if r["label"] == "candidate"]
assert len(base) == len(trial) == 2
assert min(r["fps"] for r in trial) > max(r["fps"] for r in base)
assert max(r["draw_mean_ms"] for r in trial) < min(r["draw_mean_ms"] for r in base)
backup = QA / "pre-adoption"
assert not backup.exists()
backup.mkdir()
changed = {}
for name in ["scripts/battle_sim.gd", "scripts/battle_view.gd", "project.godot", "export_presets.cfg"]:
    path = ROOT / "game" / name
    saved = backup / name
    saved.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, saved)
    if name.startswith("scripts/"):
        shutil.copy2(candidate / name, path)
    else:
        old = path.read_text("utf-8")
        new = old.replace(baseline["version"], VERSION)
        if name == "export_presets.cfg":
            assert new.count("version/code=30031") == 1
            new = new.replace("version/code=30031", "version/code=30032")
        assert new != old
        path.write_text(new, "utf-8")
    changed["game/" + name] = {"before": sha(saved), "after": sha(path)}
assert all(sha(ROOT / n) == h for n, h in regression["inputs"].items())
shutil.copytree(QA / "ownership-r1-regression", QA / "source-final")
shutil.copytree(QA / "ownership-r1-regression", QA / "formal-reach/regression")
previous = ROOT / "output/qa/godot/contact-runtime-rc32"
shutil.copy2(previous / "authorship.json", QA / "authorship.json")
font = read(previous / "font-coverage.json")
assert font["passed"] and all(sha(ROOT / r["path"]) == r["sha256"] for r in font["records"])
font["retained_report_sha256"] = sha(previous / "font-coverage.json")
font["retained_from_version"] = font["version"]
font["version"] = VERSION
font["retention_scope"] = "Byte-identical200-map story/data and fonts. No new narrative glyphs or raster generation."
(QA / "font-coverage.json").write_text(json.dumps(font, ensure_ascii=False, indent=2) + "\n", "utf-8")
unchanged = {n: h for n, h in baseline["source_inputs"].items() if n not in changed}
assert len(unchanged) == 1190 and all(sha(ROOT / n) == h for n, h in unchanged.items())
(QA / "combat-history-binding.json").write_text(json.dumps({
    "passed": True, "previous_version": baseline["version"], "current_version": VERSION,
    "changed_inputs": changed, "unchanged_inputs": unchanged,
    "campaign_battle_fields_unchanged": True, "story_progression_unchanged": True,
    "previous_verification_sha256": sha(ROOT / "release/3.0.0-rc32-preview/preview-verification.json"),
    "scope": "Two script changes and version fields;1190 identical other runtime inputs. Frozen full44-helper RC32 oracle, fresh marching/state comparisons. All200 plot/map/AI/price/action/art/UI/font inputs unchanged."
}, ensure_ascii=False, indent=2) + "\n", "utf-8")
proofs["ownership-r1-regression/report.json"] = sha(QA / "ownership-r1-regression/report.json")
(QA / "adoption.json").write_text(json.dumps({
    "passed": True, "release": VERSION, "changed_inputs": changed, "proofs": proofs,
    "generated_raster_assets": False, "source_base_checks": 195435,
    "new_source_boundary_checks": 461238, "source_total_assertions": 656673,
    "fresh_capacity_state_steps": 3600, "fresh_normal_paid_state_steps": 73103,
    "scope": "Bounded marching answers and sorted blockers only during dense simultaneous phase after exact ordered live blocker snapshot; original economy/invalid-offset fallback retained. Two fixed original ownership paper meshes; live observer-relative allegiance and painter order. Source ABBA samples show benefit; compiled exports and their natural FPS still require verification, not a60FPS/Android-hardware guarantee."
}, indent=2) + "\n", "utf-8")
print("Adopted proven marching/ownership trial; RC33 native exports still to validate", flush=True)
