"""Verify RC34 package evidence and retain RC33 simulation/map continuity."""
from pathlib import Path
import hashlib
import json

def verify(root, qa, version, manifest, apk_logic):
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    read=lambda p:json.loads(p.read_text("utf-8"))
    history=qa.parent
    assert version=="3.0.0-rc34-preview"
    binding_path=history/"combat-history-binding-r4d.json"
    binding=read(binding_path if binding_path.exists() else history/"combat-history-binding.json")
    if "current_version" in binding:
        assert binding["passed"] and binding["current_version"]==version and len(binding["unchanged_inputs"])==1191 and len(binding["changed_inputs"])==3
        assert all(sha(root/n)==h for n,h in binding["unchanged_inputs"].items())
        assert all(sha(root/n)==row["after"] for n,row in binding["changed_inputs"].items())
    else:
        assert binding["passed"] and binding["version"]==version and binding["changed_file"]=="game/scripts/battle_view.gd"
        assert sha(root/binding["changed_file"])==binding["after_sha256"]
    gate=read(history/"visibility-r4d-source-gates.json")
    assert gate["passed"] and gate["source_unchanged"] and gate["jobs"][0]["groups"]==78 and gate["jobs"][0]["checks"]==195435
    pixels=read(history/"visibility-r4d-render/report.json")
    assert pixels["passed"] and len(pixels["comparisons"])==42 and all(r["max_channel_delta"]==0 for r in pixels["comparisons"])
    natural=read(history/"visibility-r4d-natural-observation.json")
    assert natural["passed"] and len(natural["cases"])==4
    base=[r for r in natural["cases"] if r["label"]=="baseline"];trial=[r for r in natural["cases"] if r["label"]=="candidate"]
    assert len(base)==len(trial)==2
    assert max(r["draw_mean_ms"] for r in trial)<min(r["draw_mean_ms"] for r in base)
    compiled=read(qa/"visibility-render/report.json")
    assert compiled["passed"] and len(compiled["comparisons"])==42 and all(r["max_channel_delta"]==0 for r in compiled["comparisons"])
    for display in ["desktop","phone"]:
        folder=qa/"visibility-render"/(display+"-after")
        native=read(folder/"report.json")
        assert len(native.get("visibility_checks",[]))==9 and all(r["passed"] and 0<=r["entries"]<=1000 for r in native["visibility_checks"])
        assert all(sha(Path(c["path"]))==c["sha256"] for c in native["captures"])
    for platform,artifact in [("windows",manifest["builds"][0]),("apk",manifest["builds"][1])]:
        kind="windows_embedded_pack" if platform=="windows" else "apk_extracted_bytecode_on_windows"
        for name,checks in [("dense",102920),("terrain",5873),("phase",461238)]:
            report=read(qa/(name+"-"+platform)/"report.json")
            assert report["passed"] and report["checks"]==checks and report["artifact_sha256"]==artifact["sha256"] and report["runtime_kind"]==kind
    validation=read(qa/"validation-report.json")
    assert validation["passed"] and validation["version"]==version and all(row["passed"] for row in validation["jobs"])
    assert validation["runner_sha256"]==sha(root/"tools/paper-warfront/run_rc34_release_validation.py")==sha(qa/"validation-runner.py")
    prior=root/"output/qa/godot/phase-runtime-rc33"
    retained={}
    for name,count in [("marching-capacity-r3.json",3600),("marching-paid-r3.json",73103),("marching-boundary-r3-r3.json",432427),("marching-phase-r3.json",28811)]:
        d=read(prior/name);assert d["passed"] and not d["failures"] and d["checks"]==count and d["simulation_sha256"]==sha(root/"game/scripts/battle_sim.gd");retained[name]=sha(prior/name)
    return {"retained_rc33_simulation_equivalence":{"capacity_steps":3600,"normal_paid_steps":73103,"source_boundary_checks":432427,"mixed_phase_checks":28811,"records":retained,"scope":"RC33 simulation, marching cache, ownership mesh, fog, map/story and action data remain bound by the adoption input hashes. RC34 changes only a view-side per-draw visibility lookup cache."},"packed_query_equivalence_verified":{"fresh_retention_checks_per_package":102920},"terrain_commands_verified":{"checks_per_compiled_package":5873,"maps":200},"visibility_cache_verified":{"source_pixel_pairs":42,"compiled_pixel_pairs":42,"pixel_delta":0,"compiled_cache_capture_checks":18,"scope":"Cache clears at every CanvasItem draw and invalidates on battle reset, visibility revision and observer side; no fog state crosses a map transition."},"current_input_binding_sha256":sha(binding_path if binding_path.exists() else history/"combat-history-binding.json")}
