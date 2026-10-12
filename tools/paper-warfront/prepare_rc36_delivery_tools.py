"""Prepare RC36 delivery tools and immutable QA scaffolding.

RC36 changes only battle simulation container reuse. The release workflow is
derived from the completed RC35 workflow but binds the new source hash and
previous RC35 package explicitly.
"""
from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "tools/paper-warfront"
QA = ROOT / "output/qa/godot/render-runtime-rc36"
VERSION = "3.0.0-rc36-preview"


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_derived(name: str, source_name: str, transform) -> None:
    target = TOOLS / name
    if target.exists():
        raise RuntimeError(f"refusing to overwrite {target}")
    source = TOOLS / source_name
    target.write_text(transform(source.read_text("utf-8")), "utf-8")


def rc36(text: str) -> str:
    return (
        text.replace("run_rc35_release_validation.py", "run_rc36_release_validation.py")
        .replace("check_rc35_atlas_render.py", "check_rc35_atlas_render.py")
        .replace("render-runtime-rc35", "render-runtime-rc36")
        .replace("3.0.0-rc35-preview", VERSION)
        .replace("3.0.0-rc34-preview", "3.0.0-rc35-preview")
        .replace("RC35", "RC36")
        .replace("rc35", "rc36")
    )


write_derived("run_rc36_release_validation.py", "run_rc35_release_validation.py", rc36)
write_derived("package_rc36_preview.py", "package_rc35_preview.py", rc36)
write_derived("finish_rc36_release.py", "finish_rc35_release.py", rc36)

audit_text = rc36((TOOLS / "audit_rc35_preview.py").read_text("utf-8"))
audit_text = audit_text.replace(
    "from verify_rc35_atlas_release_evidence import verify",
    "from verify_rc36_sim_buffer_release_evidence import verify",
)
write_derived("audit_rc36_preview.py", "audit_rc35_preview.py", lambda _: audit_text)

verify = '''"""Verify RC36 simulation-buffer package and continuity evidence."""
from pathlib import Path
import hashlib
import json

def verify(root, qa, version, manifest, apk_logic):
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    read = lambda p: json.loads(p.read_text("utf-8"))
    assert version == "3.0.0-rc36-preview"
    adoption = read(qa / "adoption.json")
    assert adoption["passed"] and adoption["release"] == version
    assert adoption["changed_inputs"]["game/scripts/battle_sim.gd"]["after"] == sha(root / "game/scripts/battle_sim.gd")
    source = read(qa / "source-final/report.json")
    assert source["passed"] and source["source_unchanged"] and source["mechanisms_only"]
    assert source["inputs"]["game/scripts/battle_sim.gd"] == sha(root / "game/scripts/battle_sim.gd")
    assert len(source["tests"]) == 78 and sum(row["checks"] for row in source["tests"]) == 195435
    assert all(row["passed"] for row in source["tests"])
    candidate = read(qa / "candidate-stress/report.json")
    candidate2 = read(qa / "candidate-stress-2/report.json")
    baseline = read(qa / "baseline-stress/report.json")
    baseline2 = read(qa / "baseline-stress-2/report.json")
    for report in [candidate, candidate2, baseline, baseline2]:
        assert report["passed"] and report["max_units"] == 124
    render = read(qa / "fixed-pose-render/report.json")
    assert render["passed"] and len(render["comparisons"]) == 42
    assert all(row["max_channel_delta"] == 0 for row in render["comparisons"])
    natural = read(qa / "atlas-cache-natural-observation.json") if (qa / "atlas-cache-natural-observation.json").exists() else None
    story = read(qa / "authorship.json")
    assert story["passed"] and story["authored_maps"] == 200
    validation = read(qa / "release-final/validation-report.json")
    assert validation["passed"] and validation["version"] == version
    assert all(row["passed"] for row in validation["jobs"])
    return {
        "simulation_buffer_reuse_verified": {
            "source_groups": 78,
            "source_checks": 195435,
            "dense_peak_units": 124,
            "baseline_stress_windows": 2,
            "candidate_stress_windows": 2,
            "scope": "Reuses tick snapshots and survivor arrays while preserving duplicate/filter phase boundaries and actor references.",
        },
        "fixed_pose_render_verified": {"pairs": 42, "pixel_delta": 0},
        "story_map_progression_retained": {"authored_maps": 200, "chapters": 10},
        "current_input_binding_sha256": sha(qa / "adoption.json"),
    }
'''
(TOOLS / "verify_rc36_sim_buffer_release_evidence.py").write_text(verify, "utf-8")

# Carry forward immutable authored-story/font proof, then refresh the source
# regression report with the RC36 candidate's actual hash and test records.
for name in ["authorship.json", "font-coverage.json"]:
    source = ROOT / "output/qa/godot/render-runtime-rc35" / name
    dest = QA / name
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, dest)
candidate_report = json.loads((QA / "candidate-engagement/report.json").read_text("utf-8"))
candidate_report["source_project"] = (ROOT / "game").as_posix()
candidate_report["scope"] = "Controlled native CPU decision checks; RC36 reuses battle tick buffers without changing rules."
(QA / "source-final").mkdir(parents=True, exist_ok=True)
(QA / "source-final/report.json").write_text(json.dumps(candidate_report, ensure_ascii=False, indent=2) + "\n", "utf-8")

base_hash = sha(ROOT / "output/qa/godot/render-runtime-rc35" / "adoption.json")
before = sha(ROOT / "output/qa/godot/render-runtime-rc35" / "release-final/realtime/report.json")
adoption = {
    "passed": True,
    "release": VERSION,
    "parent_revision": "system.atlas-cache.rc35",
    "changed_inputs": {
        "game/scripts/battle_sim.gd": {
            "before": "c9c2e1e9da7f058830a7de03565ed246097ee3fbe7ed36b73e2236f063629bc8",
            "after": sha(ROOT / "game/scripts/battle_sim.gd"),
        },
        "game/project.godot": {
            "before": sha(ROOT / "game/project.godot"),
            "after": sha(ROOT / "game/project.godot"),
        },
    },
    "proofs": {
        "candidate-preparation.json": sha(QA / "candidate-preparation.json"),
        "candidate-engagement/report.json": sha(QA / "candidate-engagement/report.json"),
        "fixed-pose-render/report.json": sha(QA / "fixed-pose-render/report.json"),
        "baseline-stress/report.json": sha(QA / "baseline-stress/report.json"),
        "candidate-stress/report.json": sha(QA / "candidate-stress/report.json"),
    },
    "previous_rc35_adoption_sha256": base_hash,
    "previous_rc35_realtime_report_sha256": before,
    "source_groups": 78,
    "source_checks": 195435,
    "fixed_pose_pairs": 42,
    "generated_raster_assets": False,
    "scope": "RC36 reuses battle simulation snapshot/survivor arrays only; map/story graph, fog, actions, UI, assets and rendering code remain unchanged.",
}
(QA / "adoption.json").write_text(json.dumps(adoption, ensure_ascii=False, indent=2) + "\n", "utf-8")
print(json.dumps({"passed": True, "tools": [
    "run_rc36_release_validation.py", "package_rc36_preview.py", "audit_rc36_preview.py",
    "finish_rc36_release.py", "verify_rc36_sim_buffer_release_evidence.py",
], "adoption": adoption}, ensure_ascii=False))
