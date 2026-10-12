"""RC33 evidence branch: exact marching and ownership changes, actual bytecode."""
from pathlib import Path
import hashlib
import json

sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
read = lambda p: json.loads(p.read_text("utf-8"))

def verify(root, qa, version, manifest, apk_logic):
    assert version == "3.0.0-rc33-preview"
    history = qa.parent
    baseline = read(history / "baseline-build-manifest.json")
    binding = read(history / "combat-history-binding.json")
    allowed = {"game/scripts/battle_sim.gd", "game/scripts/battle_view.gd", "game/project.godot", "game/export_presets.cfg"}
    assert binding["passed"] and binding["current_version"] == version and binding["previous_version"] == baseline["version"] == "3.0.0-rc32-preview"
    assert set(binding["changed_inputs"]) == allowed
    assert set(binding["unchanged_inputs"]) | allowed == set(manifest["source_inputs"]) == set(baseline["source_inputs"])
    assert len(binding["unchanged_inputs"]) == 1190
    for n, digest in binding["unchanged_inputs"].items():
        assert sha(root / n) == digest == baseline["source_inputs"][n] == manifest["source_inputs"][n]
    for n, row in binding["changed_inputs"].items():
        assert row["before"] == baseline["source_inputs"][n] == sha(history / "pre-adoption" / n.removeprefix("game/"))
        assert row["after"] == manifest["source_inputs"][n] == sha(root / n)
    previous = root / "release/3.0.0-rc32-preview/preview-verification.json"
    assert sha(previous) == binding["previous_verification_sha256"] and read(previous)["preview_artifacts_verified"]
    adopted = read(history / "adoption.json")
    assert adopted["passed"] and adopted["changed_inputs"] == binding["changed_inputs"]
    assert all(sha(history / n) == digest for n, digest in adopted["proofs"].items())
    freeze = read(history / "freeze.json")
    assert freeze["public_inputs"] == baseline["source_inputs"] and len(freeze["oracle_scripts"]) == 44
    for n, row in freeze["oracle_scripts"].items():
        assert sha(history / "baseline-runtime/scripts" / n) == row["original_sha256"]
        assert sha(history / "oracle-runtime/scripts" / n) == row["oracle_sha256"]
    for name, count, observer in [
        ("marching-capacity-r3.json", 3600, "marching-capacity-observer.gd"),
        ("marching-boundary-r3-r3.json", 432427, "marching-boundary-observer-r3.gd"),
        ("marching-phase-r3.json", 28811, "marching-phase-observer-r2.gd"),
        ("marching-paid-r3.json", 73103, "marching-paid-observer.gd")
    ]:
        report = read(history / name)
        assert report["passed"] and not report["failures"] and report["checks"] == count
        assert report["baseline_sha256"] == freeze["oracle_scripts"]["battle_sim.gd"]["oracle_sha256"]
        assert report["observer_sha256"] == sha(history / observer)
        assert report["simulation_sha256"] == sha(root / "game/scripts/battle_sim.gd")
        for p, digest in report.get("source_hashes", report.get("inputs_before", {})).items():
            assert sha(root / "game" / p.removeprefix("res://")) == digest
    capacity = read(history / "marching-capacity-r3.json")
    assert capacity["source_unchanged"] and capacity["loaded_source_matches"] and len(capacity["paired_cpu"]) == 3600
    for name in ["source-gates-final.json", "ownership-r1-source-gates.json"]:
        gate = read(history / name)
        assert gate["passed"] and gate["source_unchanged"]
    candidate = history / "marching-r3-runtime"
    trial_manifest = read(history / "marching-r3-manifest.json")
    assert all(sha(candidate / n) == digest for n, digest in trial_manifest["candidate_inputs"].items())
    assert sha(candidate / "scripts/battle_sim.gd") == sha(root / "game/scripts/battle_sim.gd")
    # All simulation dependencies match the tested closure; the one additional
    # formal renderer change has its own full source gate and GPU pixel proof.
    for n in freeze["oracle_scripts"]:
        if n != "battle_view.gd":
            assert sha(candidate / "scripts" / n) == sha(root / "game/scripts" / n)
    source_pixels = read(history / "ownership-r1-render-expanded/report.json")
    assert source_pixels["passed"] and len(source_pixels["comparisons"]) == 24
    assert all(r["max_channel_delta"] == 0 for r in source_pixels["comparisons"])
    validation = read(qa / "validation-report.json")
    assert validation["passed"] and validation["version"] == version
    assert validation["runner_sha256"] == sha(root / "tools/paper-warfront/run_phase_release_validation.py") == sha(qa / "validation-runner.py")
    for platform, artifact in [("windows", manifest["builds"][0]), ("apk", manifest["builds"][1])]:
        kind = "windows_embedded_pack" if platform == "windows" else "apk_extracted_bytecode_on_windows"
        phase_folder = qa / ("phase-" + platform)
        phase = read(phase_folder / "report.json")
        assert phase["passed"] and phase["checks"] == 461238 and phase["runtime_kind"] == kind and phase["artifact_sha256"] == artifact["sha256"]
        assert phase["runner_sha256"] == sha(phase_folder / "runner.py") == sha(root / "tools/paper-warfront/check_phase_packaged_logic.py")
        for row in phase["tests"]:
            native = read(phase_folder / (row["name"] + ".json"))
            assert native["passed"] and not native["failures"] and native["checks"] == row["checks"]
            assert row["report_sha256"] == sha(phase_folder / (row["name"] + ".json"))
            assert row["observer_sha256"] == native["observer_sha256"] == sha(phase_folder / (row["name"] + "-observer.gd"))
            assert row["compiled_simulation_sha256"] == apk_logic["extracted_inputs"]["scripts/battle_sim.gdc"]
            assert native["baseline_sha256"] == freeze["oracle_scripts"]["battle_sim.gd"]["oracle_sha256"]
        dense_folder = qa / ("dense-" + platform)
        dense = read(dense_folder / "report.json")
        assert dense["passed"] and dense["checks"] == 102920 and dense["runtime_kind"] == kind and dense["artifact_sha256"] == artifact["sha256"]
        for row in dense["tests"]:
            native = read(dense_folder / (row["name"] + ".json"))
            assert native["passed"] and not native["failures"] and sha(dense_folder / (row["name"] + ".json")) == row["report_sha256"]
            assert native["observer_sha256"] == sha(dense_folder / (row["name"] + ".gd"))
            script = "battle_sim" if row["name"] == "test_exact_query_retention" else "map_runtime"
            assert native["source_sha256"] == apk_logic["extracted_inputs"]["scripts/" + script + ".gdc"]
        terrain_folder = qa / ("terrain-" + platform)
        terrain = read(terrain_folder / "report.json")
        native = read(terrain_folder / "native.json")
        assert terrain["passed"] and native["passed"] and terrain["checks"] == native["checks"] == 5873 and not native["failures"]
        assert terrain["artifact_sha256"] == artifact["sha256"] and terrain["runtime_kind"] == kind
        assert terrain["native_report_sha256"] == sha(terrain_folder / "native.json")
        assert terrain["compiled_cache_sha256"] == native["source_sha256"] == apk_logic["extracted_inputs"]["scripts/theatre_ground_cache.gdc"]
        assert terrain["compiled_ground_sha256"] == native["ground_sha256"] == apk_logic["extracted_inputs"]["scripts/theatre_ground.gdc"]
        assert all(sha(terrain_folder / n) == digest for n, digest in terrain["references"].items())
    pixels = read(qa / "ownership-render/report.json")
    assert pixels["passed"] and len(pixels["comparisons"]) == 24 and all(r["max_channel_delta"] == 0 for r in pixels["comparisons"])
    for display in ["desktop", "phone"]:
        folder = qa / "ownership-render" / (display + "-after")
        assert read(folder / "request.json")["pack_sha256"] == manifest["builds"][0]["sha256"]
        native = read(folder / "report.json")
        assert all(n.endswith(".gdc") and digest == apk_logic["extracted_inputs"][n.removeprefix("res://")] for n, digest in native["inputs"].items())
        assert all(sha(Path(c["path"])) == c["sha256"] for c in native["captures"])
    return {
        "fresh_rc32_state_equivalence": {"capacity_steps": 3600, "normal_paid_steps": 73103, "complete_original_helper_scripts": 44,
            "source_marching_boundaries": 432427, "source_mixed_phase_checks": 28811, "compiled_scripts": 42,
            "new_checks_per_compiled_package": 461238, "total_source_assertions": 656673,
            "scope": "New exact marching and full-state phases against independent RC32 closure; byte-identical story/maps/AI/actions retained. CPU timings and native FPS separately measured; pending full balance and Android hardware."},
        "packed_query_equivalence_verified": {"fresh_retention_checks_per_package": 102920},
        "terrain_commands_verified": {"checks_per_compiled_package": 5873, "native_draw_comparisons_per_runtime": 2521, "maps": 200},
        "ownership_mesh_verified": {"compiled_native_pixel_pairs": 24, "pixel_delta": 0, "mesh_limit_per_view": 2},
        "current_input_binding_sha256": sha(history / "combat-history-binding.json")
    }
