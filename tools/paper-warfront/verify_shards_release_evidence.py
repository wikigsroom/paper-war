"""Verify view-only R3 evidence and explicitly retained RC33 simulation closure."""
from pathlib import Path
import hashlib
import json

def verify(root, qa, version, manifest, apk_logic):
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    read = lambda p: json.loads(p.read_text("utf-8"))
    history = qa.parent
    assert version == "3.0.0-rc34-preview"
    binding = read(history / "combat-history-binding.json")
    assert binding["passed"] and binding["current_version"] == version
    assert len(binding["unchanged_inputs"]) == 1191 and len(binding["changed_inputs"]) == 3
    assert all(sha(root/n) == h for n,h in binding["unchanged_inputs"].items())
    assert all(sha(root/n) == r["after"] for n,r in binding["changed_inputs"].items())
    freeze = read(history / "freeze.json")
    gate = read(history / "shards-r3-source-gates.json")
    assert gate["passed"] and gate["source_unchanged"]
    assert len(gate["jobs"]) == 1 and gate["jobs"][0]["groups"] == 78 and gate["jobs"][0]["checks"] == 195435
    assert all(sha(root / "game/scripts" / n) == h for n,h in gate["trial_scripts"].items())
    assert len(freeze["baseline_scripts"]) == 44
    assert all(n=="battle_view.gd" or sha(root / "game/scripts" / n)==h for n,h in freeze["baseline_scripts"].items())
    source_pixels = read(history / "shards-r3-render/report.json")
    assert source_pixels["passed"] and len(source_pixels["comparisons"]) == 42
    assert all(r["max_channel_delta"]==0 for r in source_pixels["comparisons"])
    for base in [history / "shards-r3-render", qa / "shards-render"]:
        pixels = read(base / "report.json")
        assert pixels["passed"] and len(pixels["comparisons"])==42 and all(r["max_channel_delta"]==0 for r in pixels["comparisons"])
        for display in ["desktop", "phone"]:
            folder = base / (display+"-after")
            native = read(folder / "report.json")
            assert len(native["mesh_checks"])==9 and all(r["passed"] and r["cached"]<=32 and r["in_flight"]==40 for r in native["mesh_checks"])
            assert all(sha(Path(r["path"]))==r["sha256"] for r in native["captures"])
            if base==qa / "shards-render":
                assert read(folder / "request.json")["pack_sha256"]==manifest["builds"][0]["sha256"]
                assert all(n.endswith(".gdc") and h==apk_logic["extracted_inputs"][n.removeprefix("res://")] for n,h in native["inputs"].items())
    validation = read(qa / "validation-report.json")
    assert validation["passed"] and validation["version"]==version and all(r["passed"] for r in validation["jobs"])
    assert validation["runner_sha256"]==sha(root / "tools/paper-warfront/run_rc34_release_validation.py")==sha(qa / "validation-runner.py")
    for platform, artifact in [("windows",manifest["builds"][0]),("apk",manifest["builds"][1])]:
        kind = "windows_embedded_pack" if platform=="windows" else "apk_extracted_bytecode_on_windows"
        for name, checks in [("dense",102920),("terrain",5873),("phase",461238)]:
            folder = qa / (name+"-"+platform)
            report = read(folder / "report.json")
            assert report["passed"] and report["checks"]==checks and report["artifact_sha256"]==artifact["sha256"] and report["runtime_kind"]==kind
            if name=="terrain":
                native = read(folder / "native.json")
                assert native["passed"] and not native["failures"] and native["checks"]==5873
                assert report["native_report_sha256"]==sha(folder / "native.json")
                assert native["source_sha256"]==report["compiled_cache_sha256"]==apk_logic["extracted_inputs"]["scripts/theatre_ground_cache.gdc"]
                assert all(sha(folder/n)==h for n,h in report["references"].items())
            else:
                for row in report["tests"]:
                    native_path = folder / (row["name"]+".json")
                    native = read(native_path)
                    assert native["passed"] and not native["failures"] and native["checks"]==row["checks"] and row["report_sha256"]==sha(native_path)
                    observer = folder / (row["name"]+("-observer.gd" if name=="phase" else ".gd"))
                    assert native["observer_sha256"]==sha(observer)
                    if name=="phase":assert row["observer_sha256"]==sha(observer)
                    script = "battle_sim" if name=="phase" or row["name"]=="test_exact_query_retention" else "map_runtime"
                    digest = native["source_sha256"] if name=="dense" else row["compiled_simulation_sha256"]
                    assert digest==apk_logic["extracted_inputs"]["scripts/"+script+".gdc"]
    prior = root / "output/qa/godot/phase-runtime-rc33"
    prior_native = prior / "native-ownership-r1-runtime/scripts"
    for n in freeze["baseline_scripts"]:
        assert sha(prior_native/n)==freeze["baseline_scripts"][n], n
    retained = {}
    for n, count in [("marching-capacity-r3.json",3600),("marching-paid-r3.json",73103),("marching-boundary-r3-r3.json",432427),("marching-phase-r3.json",28811)]:
        d = read(prior/n)
        assert d["passed"] and not d["failures"] and d["checks"]==count and d["simulation_sha256"]==sha(root / "game/scripts/battle_sim.gd")
        retained[n] = sha(prior/n)
    return {"retained_rc33_simulation_equivalence": {"capacity_steps":3600,"normal_paid_steps":73103,"raw_helpers_unchanged":43,"records":retained,
        "scope":"RC33 exact simulation evidence retained by all43 other helper/data hashes. No fresh simulation speed claim; current packages independently rerun legacy dense/terrain/marching gates."},
        "packed_query_equivalence_verified":{"fresh_retention_checks_per_package":102920},
        "terrain_commands_verified":{"checks_per_compiled_package":5873,"maps":200},
        "shard_mesh_verified":{"source_pixel_pairs":42,"compiled_pixel_pairs":42,"pixel_delta":0,"compiled_mesh_lifetime_assertions":36,"persistent_mesh_limit":32,
            "scope":"Exact original-size mesh coordinates; current-draw references survive eviction and are released at next draw. In-flight entries equal rendered particles; no sprite region cache, frame/status reduction or changed visibility."},
        "current_input_binding_sha256":sha(history / "combat-history-binding.json")}
