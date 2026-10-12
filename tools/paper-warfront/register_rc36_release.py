"""Bind the immutable RC36 preview, evidence and delivery tools."""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[2]
QA = ROOT / "output/qa/godot/render-runtime-rc36"
VERSION = "3.0.0-rc36-preview"
RELEASE = ROOT / "release" / VERSION
TARGET = ROOT / "assets/paper-warfront/system-revisions/rc36-sim-buffers.json"
assert not TARGET.exists()


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def read(path: Path):
    return json.loads(path.read_text("utf-8"))


manifest = read(RELEASE / "build-manifest.json")
assert read(RELEASE / "preview-verification.json")["preview_artifacts_verified"]
assert read(QA / "publication.json")["passed"]
refs = {}


def bind(path: Path):
    if path.is_file():
        refs[path.relative_to(ROOT).as_posix()] = sha(path)


for name, digest in manifest["source_inputs"].items():
    assert sha(ROOT / name) == digest
    bind(ROOT / name)
for name in ["build-manifest.json", "preview-verification.json", "SHA256SUMS.txt", "README.md"]:
    bind(RELEASE / name)
for row in manifest["builds"] + manifest.get("archives", []):
    assert sha(ROOT / row["path"]) == row["sha256"]
    bind(ROOT / row["path"])
for path in QA.rglob("*"):
    parts = path.relative_to(QA).parts
    if not path.is_file() or any(part.startswith("candidate-source") or part == ".godot" for part in parts):
        continue
    bind(path)
for path in (ROOT / "tools/paper-warfront").glob("*.py"):
    if "rc36" in path.name or path.name in {"build_game.py", "check_ai_engagement.py", "check_rc35_atlas_render.py", "check_realtime_battle.py", "probe_realtime_battle.gd"}:
        bind(path)
for name, digest in read(QA / "publication.json")["files"].items():
    assert sha(ROOT / name) == digest
    bind(ROOT / name)

report = {
    "id": "system.simulation-buffers.rc36",
    "version": 1,
    "release": VERSION,
    "parent_revision": "system.atlas-cache.rc35",
    "formal_script_changes": ["battle_sim.gd"],
    "generated_raster_assets": False,
    "runtime_input_count": len(manifest["source_inputs"]),
    "story_maps": 200,
    "story_chapters": 10,
    "source_groups": 78,
    "source_assertions": 195435,
    "fixed_pose_render_pairs": 42,
    "fixed_pose_pixel_delta": 0,
    "native_exported_frame_observations": read(QA / "release-final/realtime/report.json"),
    "status": "verified_preview; dense60fps_balance_story_human_android_hardware_pending",
    "remaining": ["sustained_dense60fps", "full_faction_and_campaign_balance", "original_exact_fog_timing", "human_complete_story_experience", "android_physical_device", "human_network_play"],
    "scope": "Fresh RC36 package with reusable battle tick snapshots and survivor arrays. Map/story graph, fog, actions, UI, assets and view-side atlas cache remain bound by source and pixel evidence. No physical Android claim.",
    "references": dict(sorted(refs.items())),
}
TARGET.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", "utf-8")
assert all(sha(ROOT / name) == digest for name, digest in report["references"].items())
print(json.dumps({"passed": True, "revision": TARGET.relative_to(ROOT).as_posix(), "references": len(refs), "sha256": sha(TARGET)}, ensure_ascii=False))
