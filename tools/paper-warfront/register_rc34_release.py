"""Bind immutable RC34 evidence and native artifacts after final ZIP verification."""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[2]
QA = ROOT / "output/qa/godot/render-runtime-rc34"
VERSION = "3.0.0-rc34-preview"
RELEASE = ROOT / "release" / VERSION
TARGET = ROOT / "assets/paper-warfront/system-revisions/rc34-visibility-r4d.json"
assert not TARGET.exists()
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
read = lambda p: json.loads(p.read_text("utf-8"))
assert read(RELEASE / "preview-verification.json")["preview_artifacts_verified"]
assert read(QA / "publication.json")["passed"]
manifest = read(RELEASE / "build-manifest.json")
refs = {}

def bind(path):
    if path.is_file():
        refs[path.relative_to(ROOT).as_posix()] = sha(path)

for name, digest in manifest["source_inputs"].items():
    assert sha(ROOT / name) == digest
    bind(ROOT / name)
for name in ["build-manifest.json", "preview-verification.json", "SHA256SUMS.txt", "README.md"]:
    bind(RELEASE / name)
for row in manifest["builds"] + manifest["archives"]:
    assert sha(ROOT / row["path"]) == row["sha256"]
    bind(ROOT / row["path"])
for p in QA.rglob("*"):
    parts = p.relative_to(QA).parts
    # Bind real observations/failures but skip duplicate raster/import caches.
    if p.is_file() and not any(part.endswith("-runtime") or part == ".godot" or part == "extracted-runtime" for part in parts):
        bind(p)
for directory in ["baseline-runtime", "geometry-r1-runtime", "geometry-r2-runtime", "shards-r3-runtime", "visibility-r4d-runtime"]:
    for p in (QA / directory / "scripts").glob("*.gd"):
        bind(p)
for p in (ROOT / "tools/paper-warfront").glob("*.py"):
    if any(word in p.name for word in ["rc34", "shards"]):
        bind(p)
for name in ["build_game.py", "package_preview.py", "check_ai_engagement.py", "check_dense_packaged_logic.py", "check_terrain_packaged_logic.py", "run_realtime_release.py", "check_realtime_battle.py", "probe_realtime_battle.gd", "run_preview_checks.py", "run_query_native_extras.py"]:
    bind(ROOT / "tools/paper-warfront" / name)
for name, digest in read(QA / "publication.json")["files"].items():
    assert sha(ROOT / name) == digest
    bind(ROOT / name)
report = {
    "id": "system.visibility-cache.rc34", "version": 1, "release": VERSION,
    "parent_revision": "system.marching-ownership.rc33", "formal_script_changes": ["battle_view.gd"],
    "generated_raster_assets": False, "runtime_input_count": 1194, "unchanged_rc32_input_count": 1190, "runtime_asset_count": 455,
    "story_maps": 200, "story_chapters": 10, "local_minimal_route_orders": 552,
    "source_groups": {"base": 78}, "source_assertions": 195435,
    "fresh_complete_closure_comparison_steps": {"capacity": 3600, "normal_paid": 73103},
    "compiled_groups_each": {"base": 36, "dense": 2, "terrain": 1}, "compiled_assertions_each": 757280,
    "same_process_cpu_observations": read(QA / "visibility-r4d-natural-observation.json"),
    "native_source_ABBA_observations": read(QA / "visibility-r4d-natural-observation.json"),
    "native_exported_frame_observations": read(QA / "release-final/realtime/report.json"),
    "compiled_native_visibility_pixel_pairs": 42, "compiled_native_visibility_pixel_delta": 0,
    "status": "verified_preview; dense60fps_balance_story_human_android_hardware_pending",
    "remaining": ["sustained_dense60fps", "full_faction_and_campaign_balance", "original_exact_fog_timing", "human_complete_story_experience", "android_physical_device", "human_network_play"],
    "scope": "Fresh RC33-derived view-side visibility cache correction with revision-safe invalidation, independent200-map story bindings and actual EXE/APK code plus native UI/plot/render/FPS. Rejected geometry/shard/cache candidates and failed package attempts retained. RC33 simulation closure is retained by release verification; no physical Android claim.",
    "references": dict(sorted(refs.items()))
}
TARGET.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", "utf-8")
assert all(sha(ROOT / name) == digest for name, digest in report["references"].items())
print(json.dumps({"passed": True, "revision": TARGET.relative_to(ROOT).as_posix(), "references": len(refs), "sha256": sha(TARGET)}), flush=True)
