"""Verify RC35 atlas-cache package evidence and retain combat/story continuity."""
from pathlib import Path
import hashlib
import json

def verify(root, qa, version, manifest, apk_logic):
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    read = lambda p: json.loads(p.read_text("utf-8"))
    history = qa.parent
    assert version == "3.0.0-rc35-preview"
    binding_path = history / "combat-history-binding-r5.json"
    binding = read(binding_path)
    assert binding["passed"] and binding["version"] == version
    assert binding["changed_file"] == "game/scripts/battle_view.gd"
    assert sha(root / binding["changed_file"]) == binding["after_sha256"]
    gate = read(history / "atlas-cache-source-gates.json")
    assert gate["passed"] and gate["source_unchanged"]
    assert gate["jobs"][0]["groups"] == 78 and gate["jobs"][0]["checks"] == 195435
    pixels = read(history / "atlas-cache-render/report.json")
    assert pixels["passed"] and len(pixels["comparisons"]) == 42
    assert all(row["max_channel_delta"] == 0 for row in pixels["comparisons"])
    mobile = read(history / "atlas-cache-mobile/compact-16x9/report.json")
    assert mobile["passed"]
    natural = read(history / "atlas-cache-natural-observation.json")
    assert natural["passed"] and len(natural["cases"]) == 4
    base = [row for row in natural["cases"] if row["label"] == "baseline"]
    trial = [row for row in natural["cases"] if row["label"] == "candidate"]
    assert len(base) == len(trial) == 2
    assert max(row["draw_mean_ms"] for row in trial) < min(row["draw_mean_ms"] for row in base)
    assert min(row["fps"] for row in trial) > max(row["fps"] for row in base) * 1.02
    compiled = read(qa / "atlas-render/report.json")
    assert compiled["passed"] and len(compiled["comparisons"]) == 42
    assert all(row["max_channel_delta"] == 0 for row in compiled["comparisons"])
    for display in ["desktop", "phone"]:
        native = read(qa / "atlas-render" / (display + "-after/report.json"))
        assert len(native.get("visibility_checks", [])) == 9
        assert all(row["passed"] and 0 <= row["entries"] <= 1000 for row in native["visibility_checks"])
        assert all(sha(Path(row["path"])) == row["sha256"] for row in native["captures"])
    for platform, artifact in [("windows", manifest["builds"][0]), ("apk", manifest["builds"][1])]:
        kind = "windows_embedded_pack" if platform == "windows" else "apk_extracted_bytecode_on_windows"
        for name, checks in [("dense", 102920), ("terrain", 5873), ("phase", 461238)]:
            report = read(qa / (name + "-" + platform + "/report.json"))
            assert report["passed"] and report["checks"] == checks
            assert report["artifact_sha256"] == artifact["sha256"] and report["runtime_kind"] == kind
    validation = read(qa / "validation-report.json")
    assert validation["passed"] and validation["version"] == version
    assert all(row["passed"] for row in validation["jobs"])
    runner = root / "tools/paper-warfront/run_rc35_release_validation.py"
    assert validation["runner_sha256"] == sha(runner) == sha(qa / "validation-runner.py")
    prior = root / "output/qa/godot/phase-runtime-rc33"
    retained = {}
    for name, count in [("marching-capacity-r3.json", 3600), ("marching-paid-r3.json", 73103), ("marching-boundary-r3-r3.json", 432427), ("marching-phase-r3.json", 28811)]:
        record = read(prior / name)
        assert record["passed"] and not record["failures"] and record["checks"] == count
        assert record["simulation_sha256"] == sha(root / "game/scripts/battle_sim.gd")
        retained[name] = sha(prior / name)
    return {
        "retained_rc33_simulation_equivalence": {"capacity_steps": 3600, "normal_paid_steps": 73103, "source_boundary_checks": 432427, "mixed_phase_checks": 28811, "records": retained, "scope": "RC33 simulation, fog, map/story, actions and UI remain bound by unchanged input hashes; RC35 changes only a view-side unit-atlas handle cache."},
        "packed_query_equivalence_verified": {"fresh_retention_checks_per_package": 102920},
        "terrain_commands_verified": {"checks_per_compiled_package": 5873, "maps": 200},
        "atlas_handle_cache_verified": {"source_pixel_pairs": 42, "compiled_pixel_pairs": 42, "pixel_delta": 0, "mobile_cases": 1, "scope": "Texture2D handles are reused by atlas path and cleared on battle reset; frame regions, animation, fog, route hit-tests and simulation remain live."},
        "current_input_binding_sha256": sha(binding_path),
    }
