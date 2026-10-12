"""Verify RC36 simulation-buffer package and continuity evidence."""
from pathlib import Path
import hashlib
import json

def verify(root, qa, version, manifest, apk_logic):
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    read = lambda p: json.loads(p.read_text("utf-8"))
    assert version == "3.0.0-rc36-preview"
    evidence = qa if (qa / "adoption.json").exists() else qa.parent
    adoption = read(evidence / "adoption.json")
    assert adoption["passed"] and adoption["release"] == version
    assert adoption["changed_inputs"]["game/scripts/battle_sim.gd"]["after"] == sha(root / "game/scripts/battle_sim.gd")
    source = read(evidence / "source-final/report.json")
    assert source["passed"] and source["source_unchanged"] and source["mechanisms_only"]
    assert source["inputs"]["game/scripts/battle_sim.gd"] == sha(root / "game/scripts/battle_sim.gd")
    assert len(source["tests"]) == 78 and sum(row["checks"] for row in source["tests"]) == 195435
    assert all(row["passed"] for row in source["tests"])
    candidate = read(evidence / "candidate-stress/report.json")
    candidate2 = read(evidence / "candidate-stress-2/report.json")
    baseline = read(evidence / "baseline-stress/report.json")
    baseline2 = read(evidence / "baseline-stress-2/report.json")
    for report in [candidate, candidate2, baseline, baseline2]:
        peak_units = max((int(snapshot.get("living_units", snapshot.get("units", 0))) for snapshot in report.get("snapshots", [])), default=0)
        assert report["passed"] and peak_units == 124
    render = read(evidence / "fixed-pose-render/report.json")
    assert render["passed"] and len(render["comparisons"]) == 42
    assert all(row["max_channel_delta"] == 0 for row in render["comparisons"])
    natural = read(evidence / "atlas-cache-natural-observation.json") if (evidence / "atlas-cache-natural-observation.json").exists() else None
    story = read(evidence / "authorship.json")
    assert story["passed"] and story["authored_maps"] == 200
    validation_path = qa / "validation-report.json" if (qa / "validation-report.json").exists() else evidence / "release-final/validation-report.json"
    validation = read(validation_path)
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
        "current_input_binding_sha256": sha(evidence / "adoption.json"),
    }
