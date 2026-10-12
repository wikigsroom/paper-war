"""Immutable rc30 revision index after final ZIP/pack verification."""
from pathlib import Path
import hashlib
import json
import zipfile

ROOT = Path(__file__).resolve().parents[2]
QA = ROOT / "output/qa/godot/dense-runtime-rc30"
RELEASE = ROOT / "release/3.0.0-rc30-preview"
TARGET = ROOT / "assets/paper-warfront/system-revisions/rc30-dense-phase-caches-r1.json"
read = lambda p: json.loads(p.read_text(encoding="utf-8"))


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


assert not TARGET.exists(), "Completed system revision indexes remain immutable"
manifest = read(RELEASE / "build-manifest.json")
verification = read(RELEASE / "preview-verification.json")
assert verification["preview_artifacts_verified"] and verification["source_inputs_verified"]
assert verification["version"] == manifest["version"] == "3.0.0-rc30-preview"
assert verification["dense_retention_checks_on_windows"] == {"windows": 102920, "apk": 102920}
assert verification["packaged_logic_checks_on_windows"] == {"apk": 187249, "windows": 187249}
with zipfile.ZipFile(RELEASE / "PaperWarfront-Windows-3.0.0-rc30-preview.zip") as bundle:
    assert json.loads(bundle.read("PaperWarfront/preview-verification.json")) == verification
    assert bundle.testzip() is None
for name in ["campaign.json", "campaign-flow.json", "campaign-narrative.json", "balance-prototype.json", "style-tokens.json"]:
    assert (ROOT / "assets/paper-warfront" / name).read_bytes() == (ROOT / "game/data" / name).read_bytes(), name
publication = read(QA / "publication-inputs.json")
review = read(QA / "publication-review.json")
assert review["passed"] and review["actual_packaged_json_count"] == len(verification["apk_packaged_json_files_verified"]) == 22
for name, digest in publication["files"].items():
    if name in review["changed"]:
        assert digest == review["changed"][name]["before"]
        digest = review["changed"][name]["after"]
    assert sha(ROOT / name) == digest, name
for name, row in review["changed"].items():
    assert sha(QA / "pre-final-review" / Path(name).name) == row["before"]
    assert sha(ROOT / name) == row["after"]
for name, digest in publication["observations"].items():
    assert sha(QA / "release-final" / name) == digest, name
references = dict(manifest["source_inputs"])


def bind(path):
    assert path.is_file(), path
    name = path.relative_to(ROOT).as_posix()
    digest = sha(path)
    if name in references:
        assert references[name] == digest, name
    references[name] = digest


for name in manifest["source_inputs"]:
    assert sha(ROOT / name) == references[name], name
for row in manifest["builds"] + manifest["archives"]:
    assert sha(ROOT / row["path"]) == row["sha256"]
for path in RELEASE.rglob("*"):
    if path.is_file():
        bind(path)
for path in [ROOT / "README.md", ROOT / "docs/paper-warfront/README.md",
             ROOT / "docs/paper-warfront/139-密集交战缓存与运行复核.md",
             ROOT / "docs/paper-warfront/138-二百图剧情与非线性战役.md",
             ROOT / "assets/paper-warfront/system-revisions/rc29-story-atlas-r1.json"]:
    bind(path)
for path in (ROOT / "docs/paper-warfront/world").rglob("*.md"):
    bind(path)
for name in ["campaign.json", "campaign-flow.json", "campaign-narrative.json", "balance-prototype.json", "style-tokens.json"]:
    bind(ROOT / "assets/paper-warfront" / name)
for path in QA.iterdir():
    if path.is_file():
        bind(path)
for folder in ["source-final", "candidate-regression-r2", "formal-reach", "formal-hammer",
               "native-phase-r2-pixel-comparison", "pre-adoption", "pre-publication", "pre-final-review",
               "initial-proofless-package", "build"]:
    for path in (QA / folder).rglob("*"):
        if path.is_file():
            bind(path)
for path in (QA / "release-final").rglob("*"):
    if path.is_file() and "extracted-runtime" not in path.relative_to(QA / "release-final").parts:
        bind(path)
for path in (QA / "oracle-runtime/scripts").glob("*.gd"):
    bind(path)
for path in (QA / "baseline-runtime/scripts").glob("*.gd"):
    bind(path)
for name in ["prepare_dense_runtime.py", "prepare_dense_cpu_diagnosis.py", "prepare_dense_query_reuse.py",
             "prepare_dense_equivalence_probe.py", "prepare_dense_phase_trial.py", "prepare_dense_native_play.py",
             "adopt_dense_phase_caches.py", "bind_dense_phase_history.py", "check_dense_packaged_logic.py",
             "verify_dense_release_evidence.py", "audit_preview_build.py", "check_ai_engagement.py",
             "test_exact_query_retention.gd", "test_stationary_projection.gd", "dense_reference_target_search.gd",
             "dense_reference_map_runtime.gd", "publish_dense_phase_release.py", "register_dense_phase_release.py",
             "run_query_native_extras.py", "run_realtime_release.py", "check_realtime_battle.py",
             "probe_realtime_battle.gd", "run_paid_release_recipes.py", "run_preview_checks.py", "package_preview.py"]:
    bind(ROOT / "tools/paper-warfront" / name)
frames = read(QA / "release-final/realtime/report.json")
report = {
    "id": "system.dense-phase-caches.rc30", "version": 1, "release": manifest["version"],
    "status": "native_windows_source_and_compiled_packages_verified; dense60fps_android_hardware_balance_human_story_pending",
    "parent_revision": "system.story-atlas.rc29", "stable_maps": 200, "chapters": 10,
    "local_minimal_route_orders": 552, "generated_raster_assets": False,
    "formal_script_changes": ["battle_sim.gd", "map_runtime.gd", "battle_visibility.gd"],
    "source_groups": {"base": 78, "new_exact_retention": 2},
    "source_checks": {"base": 195435, "new_exact_retention": 102920, "total": 298355},
    "package_groups_each": {"base": 36, "new_exact_retention": 2},
    "package_checks_each": {"base": 187249, "new_exact_retention": 102920, "total": 290169},
    "complete_original_closure_scripts": 44, "capacity_steps": 3600, "normal_paid_steps": 73103,
    "compiled_native_story_ui_checks": 474, "runtime_asset_count": 455,
    "runtime_input_count": 1194, "stationary_projection_entry_bound": 256,
    "realtime_observations": frames,
    "scope": "Fresh exact target/coordinate cache comparisons against full frozen rc29 helper closure and actual EXE/APK bytecode on Windows, selected pixel comparisons and native natural frame observations. Existing story/font/art input evidence retained explicitly; no new raster generation, repeated source run or Android hardware claim.",
    "remaining": ["sustained_dense60fps", "full_faction_and_campaign_balance", "original_exact_fog_timing",
                  "human_complete_story_experience", "android_physical_device", "human_network_play"],
    "references": dict(sorted(references.items()))
}
TARGET.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
assert all(sha(ROOT / name) == digest for name, digest in report["references"].items())
print(json.dumps({"revision": TARGET.relative_to(ROOT).as_posix(), "passed": True,
                  "references": len(references), "sha256": sha(TARGET)}))
