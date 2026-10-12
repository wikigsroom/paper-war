"""Bind rc30 exact retention checks to fresh closure and actual compiled bytes."""
from pathlib import Path
import hashlib
import json


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def verify(root, qa, version, manifest, apk_logic):
    history = qa.parent
    binding = read(history / "combat-history-binding.json")
    assert binding["passed"] and binding["current_version"] == version
    assert binding["campaign_battle_fields_unchanged"] and binding["all_campaign_data_unchanged"]
    assert (root / binding["historical_evidence_root"]).resolve() == history.resolve()
    assert all(sha(root / name) == digest for name, digest in binding["unchanged_inputs"].items())
    assert all(sha(root / name) == row["after"] for name, row in binding["changed_inputs"].items())
    changed = {"game/scripts/battle_sim.gd", "game/scripts/map_runtime.gd",
               "game/scripts/battle_visibility.gd", "game/project.godot", "game/export_presets.cfg"}
    assert set(binding["changed_inputs"]) == changed
    assert set(binding["unchanged_inputs"]) | changed == set(manifest["source_inputs"])
    for name, digest in binding["fresh_proofs"].items():
        assert sha(history / name) == digest, name
    retained = binding["retained_narrative"]
    assert sha(root / retained["source"]) == retained["sha256"] == sha(history / "authorship.json")
    font = read(history / "font-coverage.json")
    assert font["retained_from_version"] == binding["previous_version"]
    original_font = root / Path(retained["source"]).parent / "font-coverage.json"
    assert sha(original_font) == font["retained_report_sha256"]

    frozen = read(history / "freeze.json")
    baseline_manifest = read(history / "baseline-build-manifest.json")
    assert frozen["release"] == binding["previous_version"] == baseline_manifest["version"]
    assert frozen["public_inputs"] == baseline_manifest["source_inputs"]
    for name, digest in frozen["public_inputs"].items():
        actual = binding["changed_inputs"].get(name, {}).get("before", binding["unchanged_inputs"].get(name))
        assert actual == digest, name
    for name, row in frozen["oracle_scripts"].items():
        assert sha(history / "oracle-runtime/scripts" / name) == row["oracle_sha256"]
        assert sha(history / "baseline-runtime/scripts" / name) == row["source_sha256"]
    assert len(frozen["oracle_scripts"]) == binding["closure_scripts"] == 44
    for name, digest in frozen["runtime_inputs"].items():
        assert sha(history / "baseline-runtime" / name) == digest, name
        if name.startswith(("scripts/", "data/", "tests/")):
            expected = sha(root / "game" / name) if "game/" + name in changed else digest
            assert sha(history / "phase-reuse-r2-runtime" / name) == expected, name

    capacity = read(history / "phase-reuse-r2-capacity.json")
    paid = read(history / "phase-reuse-r2-paid-r3.json")
    for proof, count, observer in [(capacity, 3600, "capacity-query-reuse-observer.gd"),
                                   (paid, 73103, "paid-phase-observer.gd")]:
        assert proof["passed"] and not proof["failures"] and proof["checks"] == count
        assert all(row["equal"] for row in proof["cases"])
        assert sum(row["steps"] for row in proof["cases"]) == count
        assert proof["simulation_sha256"] == sha(root / "game/scripts/battle_sim.gd")
        assert proof["baseline_sha256"] == sha(history / "oracle-runtime/scripts/battle_sim.gd")
        assert proof["observer_sha256"] == sha(history / observer)
    assert capacity["loaded_source_matches"] and capacity["source_unchanged"]
    assert all(sha(root / "game" / name.removeprefix("res://")) == digest
               for name, digest in capacity["inputs_before"].items())
    assert len(capacity["paired_cpu"]) == 3600 and len(paid["cases"]) == 6

    retention = read(history / "source-check-retention.json")
    assert retention["passed"] and retention["live_gameplay_inputs_identical"]
    assert sha(history / retention["original_report"]) == retention["report_sha256"]
    assert sha(history / "source-final/report.json") == retention["report_sha256"]
    counts = {}
    evidence = {}
    expected_tests = {"test_exact_query_retention": (25600, "battle_sim", "reference_sha256", "dense_reference_target_search.gd"),
                      "test_stationary_projection": (77320, "map_runtime", "baseline_sha256", "dense_reference_map_runtime.gd")}
    # Both raw references remain independent of the candidate implementation.
    assert sha(root / "tools/paper-warfront/dense_reference_map_runtime.gd") == frozen["oracle_scripts"]["map_runtime.gd"]["source_sha256"]
    assert sha(root / "tools/paper-warfront/dense_reference_target_search.gd") == sha(history / "baseline-runtime/tests/reference_target_search.gd")
    for platform, artifact in [("windows", manifest["builds"][0]), ("apk", manifest["builds"][1])]:
        folder = qa / ("dense-" + platform)
        proof = read(folder / "report.json")
        assert proof["passed"] and proof["artifact_sha256"] == artifact["sha256"] and proof["checks"] == 102920
        expected_kind = "windows_embedded_pack" if platform == "windows" else "apk_extracted_bytecode_on_windows"
        assert proof["runtime_kind"] == expected_kind
        assert {r["name"] for r in proof["tests"]} == set(expected_tests)
        assert sha(folder / "runner.py") == sha(root / "tools/paper-warfront/check_dense_packaged_logic.py")
        for name, digest in proof["observer_inputs"].items():
            assert sha(folder / name) == digest == sha(root / "tools/paper-warfront" / name)
        for row in proof["tests"]:
            count, script, reference_key, reference = expected_tests[row["name"]]
            native_path = folder / (row["name"] + ".json")
            native = read(native_path)
            assert sha(native_path) == row["report_sha256"]
            assert native["passed"] and not native["failures"] and row["checks"] == native["checks"] == count
            assert native["observer_sha256"] == sha(folder / (row["name"] + ".gd"))
            assert native[reference_key] == sha(folder / reference)
            assert native["source_sha256"] == row["compiled_script_sha256"] == apk_logic["extracted_inputs"]["scripts/" + script + ".gdc"]
            source_path = history / (row["name"] + "-external-reference-r3.json")
            source = read(source_path)
            assert source["passed"] and not source["failures"] and source["checks"] == count
            assert source["source_sha256"] == sha(root / "game/scripts" / (script + ".gd"))
            assert source["observer_sha256"] == native["observer_sha256"] and source[reference_key] == native[reference_key]
        counts[platform] = proof["checks"]
        evidence[platform] = sha(folder / "report.json")
    return {
        "fresh_combat_equivalence_binding_sha256": sha(history / "combat-history-binding.json"),
        "packed_query_equivalence_verified": {
            "capacity_steps": 3600, "normal_paid_steps": 73103, "complete_original_helper_scripts": 44,
            "exact_draw_order_checks_per_package": 1200, "native_float_boundary_checks_per_package": 20,
            "scope": "Fresh rc30 every-step exact comparison against the entire frozen rc29 helper closure, all unchanged campaign/assets bound. Same-process alternating CPU timing is separate from rendered FPS and balance."
        },
        "dense_retention_checks_on_windows": counts,
        "dense_retention_reports_sha256": evidence,
        "additional_source_retention_checks": 102920,
        "scope_of_dense_retention_checks": "Actual EXE/APK compiled code on Windows, two independent references across all200 maps/both directions and mutation/boundary/memory cases; not Android hardware. Source reports retained for identical adopted inputs, no repeated-run claim."
    }
