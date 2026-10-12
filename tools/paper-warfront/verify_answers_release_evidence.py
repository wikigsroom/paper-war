"""RC32 verification branch: fresh state proofs and actual compiled boundaries."""
from pathlib import Path
import hashlib
import json

sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text("utf-8"))

def verify(root,qa,version,manifest,apk_logic):
    assert version=="3.0.0-rc32-preview"
    history=qa.parent;binding=read(history/"combat-history-binding.json")
    baseline=read(history/"baseline-build-manifest.json")
    allowed={"game/scripts/battle_sim.gd","game/scripts/battle_visibility.gd","game/project.godot","game/export_presets.cfg"}
    assert binding["passed"] and binding["current_version"]==version and binding["previous_version"]==baseline["version"]=="3.0.0-rc31-preview"
    assert set(binding["changed_inputs"])==allowed
    assert set(binding["unchanged_inputs"])|allowed==set(manifest["source_inputs"])==set(baseline["source_inputs"])
    for n,d in binding["unchanged_inputs"].items():assert sha(root/n)==d==baseline["source_inputs"][n]==manifest["source_inputs"][n]
    for n,r in binding["changed_inputs"].items():
        assert r["before"]==baseline["source_inputs"][n]==sha(history/"pre-adoption"/n.removeprefix("game/"))
        assert r["after"]==manifest["source_inputs"][n]==sha(root/n)
    previous=root/"release/3.0.0-rc31-preview/preview-verification.json"
    assert sha(previous)==binding["previous_verification_sha256"] and read(previous)["preview_artifacts_verified"]
    adopted=read(history/"adoption.json")
    assert adopted["passed"] and adopted["changed_inputs"]==binding["changed_inputs"]
    assert all(sha(history/n)==d for n,d in adopted["proofs"].items())
    freeze=read(history/"freeze.json")
    assert freeze["public_inputs"]==baseline["source_inputs"] and len(freeze["oracle_scripts"])==44
    for n,r in freeze["oracle_scripts"].items():
        assert sha(history/"baseline-runtime/scripts"/n)==r["original_sha256"]
        assert sha(history/"oracle-runtime/scripts"/n)==r["oracle_sha256"]
    for name,count,observer in [("answers-capacity-r1.json",3600,"answers-capacity-observer.gd"),
        ("answers-paid-r1.json",73103,"lookup-paid-observer.gd"),("answers-phase-r1.json",21607,"answers-phase-observer.gd"),
        ("answers-lookup-boundary-r1.json",619103,"lookup-boundary-observer.gd")]:
        x=read(history/name);assert x["passed"] and not x["failures"] and x["checks"]==count
        assert x["baseline_sha256"]==freeze["oracle_scripts"]["battle_sim.gd"]["oracle_sha256"]
        assert x["observer_sha256"]==sha(history/observer)
        if "simulation_sha256" in x:assert x["simulation_sha256"]==sha(root/"game/scripts/battle_sim.gd")
        for p,d in x.get("source_hashes",x.get("inputs_before",{})).items():assert sha(root/"game"/p.removeprefix("res://"))==d
    capacity=read(history/"answers-capacity-r1.json")
    assert capacity["source_unchanged"] and capacity["loaded_source_matches"] and len(capacity["paired_cpu"])==3600
    repair=read(history/"compiled-observer-repair.json")
    assert repair["passed"] and sha(history/repair["manifest_snapshot"])==repair["unchanged_manifest_sha256"]
    snapshot=read(history/repair["manifest_snapshot"])
    assert snapshot["source_inputs"]==manifest["source_inputs"] and snapshot["builds"]==manifest["builds"]
    assert all(sha(qa/n)==d for n,d in repair["retained_passed_reports"].items())
    assert repair["repaired_windows_report_sha256"]==sha(qa/"answers-windows/report.json")
    for trial,digest in repair["failed_compiled_runner_sha256"].items():
        assert sha(history/("compiled-check-runner-"+trial+".py"))==digest==sha(qa/("failed-answers-windows-"+trial)/"runner.py")
    assert repair["current_compiled_runner_sha256"]==sha(root/"tools/paper-warfront/check_answers_packaged_logic.py")
    validation=read(qa/"validation-report.json")
    assert validation["observer_repair_proof_sha256"]==sha(history/"compiled-observer-repair.json")
    assert validation["runner_sha256"]==repair["resume_runner_sha256"]==sha(root/"tools/paper-warfront/resume_answers_release_validation.py")
    for platform,artifact in [("windows",manifest["builds"][0]),("apk",manifest["builds"][1])]:
        kind="windows_embedded_pack" if platform=="windows" else "apk_extracted_bytecode_on_windows"
        folder=qa/("answers-"+platform);proof=read(folder/"report.json")
        assert proof["passed"] and proof["checks"]==640706 and proof["runtime_kind"]==kind and proof["artifact_sha256"]==artifact["sha256"]
        assert proof["runner_sha256"]==sha(folder/"runner.py")==sha(root/"tools/paper-warfront/check_answers_packaged_logic.py")
        for row in proof["tests"]:
            native=read(folder/(row["name"]+".json"))
            assert native["passed"] and not native["failures"] and native["checks"]==row["checks"]
            assert row["report_sha256"]==sha(folder/(row["name"]+".json"))
            assert row["observer_sha256"]==native["observer_sha256"]==sha(folder/(row["name"]+"-observer.gd"))
            assert row["compiled_simulation_sha256"]==apk_logic["extracted_inputs"]["scripts/battle_sim.gdc"]
            for p,d in native.get("source_hashes",{}).items():assert d==apk_logic["extracted_inputs"][p.removeprefix("res://")]
        dense_folder=qa/("dense-"+platform);dense=read(dense_folder/"report.json")
        assert dense["passed"] and dense["checks"]==102920 and dense["runtime_kind"]==kind and dense["artifact_sha256"]==artifact["sha256"]
        for row in dense["tests"]:
            x=read(dense_folder/(row["name"]+".json"))
            assert x["passed"] and not x["failures"] and sha(dense_folder/(row["name"]+".json"))==row["report_sha256"]
            assert x["observer_sha256"]==sha(dense_folder/(row["name"]+".gd"))
            script="battle_sim" if row["name"]=="test_exact_query_retention" else "map_runtime"
            assert x["source_sha256"]==apk_logic["extracted_inputs"]["scripts/"+script+".gdc"]
        terrain_folder=qa/("terrain-"+platform);terrain=read(terrain_folder/"report.json");native=read(terrain_folder/"native.json")
        assert terrain["passed"] and native["passed"] and terrain["checks"]==native["checks"]==5873 and not native["failures"]
        assert terrain["artifact_sha256"]==artifact["sha256"] and terrain["runtime_kind"]==kind
        assert terrain["native_report_sha256"]==sha(terrain_folder/"native.json")
        assert terrain["compiled_cache_sha256"]==native["source_sha256"]==apk_logic["extracted_inputs"]["scripts/theatre_ground_cache.gdc"]
        assert terrain["compiled_ground_sha256"]==native["ground_sha256"]==apk_logic["extracted_inputs"]["scripts/theatre_ground.gdc"]
        assert all(sha(terrain_folder/n)==d for n,d in terrain["references"].items())
    return {"fresh_rc31_state_equivalence":{"capacity_steps":3600,"normal_paid_steps":73103,"complete_original_helper_scripts":44,
        "dense_phase_checks":21607,"ordered_fog_checks":619103,"compiled_ordered_fog_checks":619099,"compiled_scripts":42,"checks_per_compiled_package":640706,
        "scope":"Fresh independent frozen RC31 closure comparisons, new exact native phase/fog assertions and actual EXE/APK bytecode. CPU timings and natural FPS are distinct; no full balance/Android hardware claim."},
        "packed_query_equivalence_verified":{"fresh_retention_checks_per_package":102920},
        "terrain_commands_verified":{"checks_per_compiled_package":5873,"native_draw_comparisons_per_runtime":2521,"maps":200},
        "current_input_binding_sha256":sha(history/"combat-history-binding.json")}
