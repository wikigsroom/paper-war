"""Bind the immutable RC35 preview, evidence and delivery tools."""
from pathlib import Path
import hashlib, json

ROOT = Path(__file__).resolve().parents[2]
QA = ROOT / "output/qa/godot/render-runtime-rc35"
VERSION = "3.0.0-rc35-preview"
RELEASE = ROOT / "release" / VERSION
TARGET = ROOT / "assets/paper-warfront/system-revisions/rc35-atlas-cache.json"
assert not TARGET.exists()
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
read = lambda p: json.loads(p.read_text("utf-8"))
assert read(RELEASE / "preview-verification.json")["preview_artifacts_verified"]
assert read(QA / "publication.json")["passed"]
manifest = read(RELEASE / "build-manifest.json")
refs = {}
def bind(path):
    if path.is_file(): refs[path.relative_to(ROOT).as_posix()] = sha(path)
for name, digest in manifest["source_inputs"].items():
    assert sha(ROOT / name) == digest
    bind(ROOT / name)
for name in ["build-manifest.json", "preview-verification.json", "SHA256SUMS.txt", "README.md"]: bind(RELEASE / name)
for row in manifest["builds"] + manifest["archives"]:
    assert sha(ROOT / row["path"]) == row["sha256"]
    bind(ROOT / row["path"])
for path in QA.rglob("*"):
    parts = path.relative_to(QA).parts
    if path.is_file() and not any(part.endswith("-runtime") or part == ".godot" or part == "extracted-runtime" for part in parts): bind(path)
for directory in ["baseline-runtime", "atlas-cache-runtime"]:
    for path in (QA / directory / "scripts").glob("*.gd"): bind(path)
for path in (ROOT / "tools/paper-warfront").glob("*.py"):
    if any(word in path.name for word in ["rc35", "atlas_cache", "atlas"]): bind(path)
for name in ["build_game.py", "package_rc35_preview.py", "check_ai_engagement.py", "check_dense_packaged_logic.py", "check_terrain_packaged_logic.py", "run_realtime_release.py", "check_realtime_battle.py", "probe_realtime_battle.gd", "run_preview_checks.py", "run_query_native_extras.py"]: bind(ROOT / "tools/paper-warfront" / name)
for name, digest in read(QA / "publication.json")["files"].items():
    assert sha(ROOT / name) == digest
    bind(ROOT / name)
report = {
    "id": "system.atlas-cache.rc35", "version": 1, "release": VERSION,
    "parent_revision": "system.visibility-cache.rc34", "formal_script_changes": ["battle_view.gd"],
    "generated_raster_assets": False, "runtime_input_count": 1194, "unchanged_rc34_input_count": 1193, "runtime_asset_count": 455,
    "story_maps": 200, "story_chapters": 10, "local_minimal_route_orders": 552,
    "source_groups": {"base": 78}, "source_assertions": 195435,
    "compiled_groups_each": {"base": 36, "dense": 2, "terrain": 1}, "compiled_assertions_each": 757280,
    "native_source_ABBA_observations": read(QA / "atlas-cache-natural-observation.json"),
    "native_exported_frame_observations": read(QA / "release-final/realtime/report.json"),
    "compiled_native_atlas_pixel_pairs": 42, "compiled_native_atlas_pixel_delta": 0,
    "status": "verified_preview; dense60fps_balance_story_human_android_hardware_pending",
    "remaining": ["sustained_dense60fps", "full_faction_and_campaign_balance", "original_exact_fog_timing", "human_complete_story_experience", "android_physical_device", "human_network_play"],
    "scope": "Fresh RC34-derived atlas-handle cache with source, pixel, mobile and native package evidence. Unit frame selection, map/story graph, fog, simulation, UI and assets remain unchanged. No physical Android claim.",
    "references": dict(sorted(refs.items())),
}
TARGET.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", "utf-8")
assert all(sha(ROOT / name) == digest for name, digest in report["references"].items())
print(json.dumps({"passed": True, "revision": TARGET.relative_to(ROOT).as_posix(), "references": len(refs), "sha256": sha(TARGET)}))
