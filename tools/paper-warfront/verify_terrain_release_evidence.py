"""Verify RC31 render-only evidence without rewriting the RC30 audit tools."""
from pathlib import Path
import hashlib
import json


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def read(path):return json.loads(path.read_text("utf-8"))


def verify(root, qa, version, manifest, apk_logic):
    assert version == "3.0.0-rc31-preview"
    history = qa.parent
    binding = read(history / "combat-history-binding.json")
    assert binding["passed"] and binding["current_version"] == version
    baseline = read(history / "baseline-build-manifest.json")
    assert baseline["version"] == binding["previous_version"] == "3.0.0-rc30-preview"
    allowed = {"game/scripts/battle_view.gd", "game/scripts/theatre_ground_cache.gd", "game/project.godot", "game/export_presets.cfg"}
    assert set(binding["changed_inputs"]) == allowed
    assert set(binding["unchanged_inputs"]) | allowed == set(manifest["source_inputs"]) == set(baseline["source_inputs"])
    for name, digest in binding["unchanged_inputs"].items():
        assert sha(root / name) == digest == baseline["source_inputs"][name] == manifest["source_inputs"][name]
    for name, row in binding["changed_inputs"].items():
        assert row["before"] == baseline["source_inputs"][name]
        assert row["after"] == sha(root / name) == manifest["source_inputs"][name]
        assert sha(history / "pre-adoption" / name.removeprefix("game/")) == row["before"]
    for name, digest in binding["retained_combat_evidence"].items():assert sha(root / name) == digest
    retained = binding["retained_previous_verification"]
    assert sha(root / retained["path"]) == retained["sha256"]
    previous = read(root / retained["path"])
    assert previous["version"] == baseline["version"] and previous["preview_artifacts_verified"]
    # Validate the retained comparisons themselves and their unchanged simulator.
    for name, expected in [("phase-reuse-r2-capacity.json", 3600), ("phase-reuse-r2-paid-r3.json", 73103)]:
        path = next(root / n for n in binding["retained_combat_evidence"] if n.endswith("/" + name))
        proof = read(path)
        assert proof["passed"] and not proof["failures"] and proof["checks"] == expected
        assert proof["simulation_sha256"] == sha(root / "game/scripts/battle_sim.gd")
    adopted = read(history / "adoption.json")
    assert adopted["passed"] and adopted["changed_inputs"] == binding["changed_inputs"]
    assert all(sha(history / n) == d for n, d in adopted["proofs"].items())
    frozen = read(history / "freeze.json")
    assert frozen["public_inputs"] == baseline["source_inputs"] and len(frozen["oracle_scripts"]) == 44
    for name, row in frozen["oracle_scripts"].items():
        assert sha(history / "baseline-runtime/scripts" / name) == row["original_sha256"]
        assert sha(history / "oracle-runtime/scripts" / name) == row["oracle_sha256"]
    source = read(history / "terrain-command-reference-r3.json")
    assert source["passed"] and source["checks"] == 5873 and source["mesh_geometry_present"]
    assert source["source_sha256"] == sha(root / "game/scripts/theatre_ground_cache.gd")
    assert source["observer_sha256"] == sha(root / "tools/paper-warfront/test_terrain_command_retention.gd")
    realtime = read(qa / "realtime/report.json")
    if realtime.get("resumed_after_confirmed_exit", False):
        resume = read(history / "native-resume.json")
        assert resume["confirmed_no_matching_processes"] and json.loads(resume["process_query"]) == []
        assert realtime["resume_proof_sha256"] == sha(history / "native-resume.json")
        assert resume["new_auditor_sha256"] == sha(root / "tools/paper-warfront/audit_terrain_preview.py")
        assert resume["old_auditor_sha256"] == sha(history / "auditor-r1-before-resume.py") == read(history / "auditor-generation.json")["derived_auditor_sha256"]
        assert all(sha(qa / "realtime" / n / "receipt.json") == d for n, d in resume["retained_cases"].items())
        assert not (history / resume["interrupted_directory"] / "receipt.json").exists()
    for platform, artifact in [("windows", manifest["builds"][0]), ("apk", manifest["builds"][1])]:
        folder = qa / ("terrain-" + platform)
        packaged = read(folder / "report.json")
        native = read(folder / "native.json")
        assert packaged["passed"] and native["passed"] and not native["failures"]
        assert packaged["checks"] == native["checks"] == 5873
        assert packaged["artifact_sha256"] == artifact["sha256"]
        assert packaged["native_report_sha256"] == sha(folder / "native.json")
        assert packaged["runner_sha256"] == sha(folder / "runner.py") == sha(root / "tools/paper-warfront/check_terrain_packaged_logic.py")
        assert native["observer_sha256"] == packaged["observer_sha256"] == sha(folder / "observer.gd") == source["observer_sha256"]
        assert packaged["compiled_cache_sha256"] == native["source_sha256"] == apk_logic["extracted_inputs"]["scripts/theatre_ground_cache.gdc"]
        assert packaged["compiled_ground_sha256"] == native["ground_sha256"] == apk_logic["extracted_inputs"]["scripts/theatre_ground.gdc"]
        assert native["reference_ground_sha256"] == source["reference_ground_sha256"]
        assert native["reference_cache_sha256"] == source["reference_cache_sha256"]
        assert all(sha(folder / n) == d for n, d in packaged["references"].items())
        expected_kind = "windows_embedded_pack" if platform == "windows" else "apk_extracted_bytecode_on_windows"
        assert packaged["runtime_kind"] == expected_kind
        # The simulation helpers are unchanged, but the current exports still
        # execute their independent invalidation tests instead of borrowing passes.
        dense_folder = qa / ("dense-" + platform)
        dense = read(dense_folder / "report.json")
        assert dense["passed"] and dense["checks"] == 102920 and dense["artifact_sha256"] == artifact["sha256"]
        assert dense["runtime_kind"] == expected_kind
        for row in dense["tests"]:
            test = read(dense_folder / (row["name"] + ".json"))
            assert test["passed"] and not test["failures"] and sha(dense_folder / (row["name"] + ".json")) == row["report_sha256"]
            assert test["observer_sha256"] == sha(dense_folder / (row["name"] + ".gd"))
            script = "battle_sim" if row["name"] == "test_exact_query_retention" else "map_runtime"
            assert test["source_sha256"] == apk_logic["extracted_inputs"]["scripts/" + script + ".gdc"]
    return {"retained_combat_equivalence_binding_sha256": sha(history / "combat-history-binding.json"),
        "packed_query_equivalence_verified": {"capacity_steps": 3600, "normal_paid_steps": 73103, "complete_original_helper_scripts": 44,
            "fresh_retention_checks_per_package": 102920,
            "scope": "RC30 every-step comparisons retained for byte-identical combat inputs; current EXE/APK freshly execute raw-reference invalidation checks. No new simulation CPU or full balance claim."},
        "terrain_commands_verified": {"source_checks": 5873, "checks_per_compiled_package": 5873, "native_draw_comparisons_per_runtime": 2521, "maps": 200,
            "scope": "Ordered native parameters, actual mesh arrays and invalidation against independent frozen RC30 ground/cache; raster comparison and natural FPS reported separately. Android bytecode exercised on Windows, not hardware."}}
