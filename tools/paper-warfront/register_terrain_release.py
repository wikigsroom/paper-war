"""Register immutable RC31 inputs, failed trials, native proofs and downloads."""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[2]
QA = ROOT / "output/qa/godot/pressure-runtime-rc31"
VERSION = "3.0.0-rc31-preview"
RELEASE = ROOT / "release" / VERSION
TARGET = ROOT / "assets/paper-warfront/system-revisions/rc31-terrain-command-cache-r1.json"
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
read = lambda p: json.loads(p.read_text("utf-8"))
assert not TARGET.exists()
manifest = read(RELEASE / "build-manifest.json")
proof = read(RELEASE / "preview-verification.json")
assert proof["version"] == VERSION and proof["preview_artifacts_verified"]
assert proof["terrain_commands_verified"]["checks_per_compiled_package"] == 5873
assert all(sha(ROOT / n) == d for n, d in manifest["source_inputs"].items())
references = dict(manifest["source_inputs"])


def bind(path):
    assert path.is_file(), path
    name = path.relative_to(ROOT).as_posix()
    digest = sha(path)
    if name in references:assert references[name] == digest
    references[name] = digest


for path in RELEASE.rglob("*"):
    if path.is_file():bind(path)
for path in [ROOT / "README.md", ROOT / "docs/paper-warfront/README.md",
    ROOT / "docs/paper-warfront/140-地形绘制缓存与镜头移动复核.md",
    ROOT / "docs/paper-warfront/138-二百图剧情与非线性战役.md",
    ROOT / "assets/paper-warfront/system-revisions/rc30-dense-phase-caches-r1.json"]:
    bind(path)
for path in (ROOT / "docs/paper-warfront/world").rglob("*.md"):bind(path)
for name in ["campaign.json", "campaign-flow.json", "campaign-narrative.json", "balance-prototype.json", "style-tokens.json"]:
    bind(ROOT / "assets/paper-warfront" / name)
for path in QA.iterdir():
    if path.is_file():bind(path)
for folder in ["pre-adoption", "pre-publication", "source-final", "candidate-regression-final", "formal-reach", "formal-hammer",
    "terrain-command-pixels-r1", "terrain-command-pixels-r3", "terrain-abba-native-r1", "terrain-abba-native-r2", "terrain-abba-native-r3",
    "native-baseline-layers-r1", "terrain-commands-native-r1", "initial-proofless-package"]:
    for path in (QA / folder).rglob("*"):
        if path.is_file():bind(path)
for path in (QA / "release-final").rglob("*"):
    if path.is_file() and "extracted-runtime" not in path.relative_to(QA / "release-final").parts:bind(path)
for folder in ["baseline-runtime", "oracle-runtime", "terrain-commands-r1-runtime", "terrain-commands-r2-runtime", "terrain-commands-r3-runtime", "terrain-commands-final-runtime"]:
    for path in (QA / folder / "scripts").glob("*.gd"):bind(path)
for name in ["prepare_pressure_runtime.py", "prepare_terrain_commands_trial.py", "prepare_terrain_commands_r2.py", "prepare_terrain_commands_r3.py",
    "prepare_terrain_abba_probe.py", "prepare_terrain_final_validation.py", "test_terrain_command_retention.gd", "check_terrain_packaged_logic.py",
    "adopt_terrain_commands.py", "prepare_terrain_auditor.py", "audit_terrain_preview.py", "verify_terrain_release_evidence.py",
    "run_terrain_release_validation.py", "summarize_terrain_cpu.py", "publish_terrain_release.py", "register_terrain_release.py",
    "resume_terrain_native_validation.py", "finish_terrain_release.py",
    "check_render_cache_equivalence.py", "probe_render_cache_equivalence.gd", "check_realtime_battle.py", "probe_realtime_battle.gd",
    "run_realtime_release.py", "run_preview_checks.py", "run_query_native_extras.py", "package_preview.py", "build_game.py"]:
    bind(ROOT / "tools/paper-warfront" / name)
publication = read(QA / "publication.json")
assert publication["passed"] and all(sha(ROOT / n) == d for n, d in publication["files"].items())
report = {"id": "system.terrain-command-cache.rc31", "version": 1, "release": VERSION,
    "parent_revision": "system.dense-phase-caches.rc30", "generated_raster_assets": False,
    "formal_script_changes": ["battle_view.gd", "theatre_ground_cache.gd"],
    "stable_maps": 200, "chapters": 10, "local_minimal_route_orders": 552,
    "source_groups": {"base": 78, "terrain": 1}, "source_checks": {"base": 195435, "terrain": 5873, "total": 201308},
    "package_groups_each": {"base": 36, "dense_retention": 2, "terrain": 1},
    "package_checks_each": {"base": 187249, "dense_retention": 102920, "terrain": 5873, "total": 296042},
    "native_draw_parameter_comparisons_per_runtime": 2521, "compiled_native_story_ui_checks": 474,
    "runtime_asset_count": 455, "runtime_input_count": 1194, "unchanged_rc30_input_count": 1190,
    "native_source_layer_timings": read(QA / "terrain-cpu-summary.json"),
    "realtime_observations": read(QA / "release-final/realtime/report.json"),
    "status": "verified_preview; dense60fps_global_balance_human_story_android_hardware_pending",
    "remaining": ["sustained_dense60fps", "full_faction_and_campaign_balance", "original_exact_fog_timing", "human_complete_story_experience", "android_physical_device", "human_network_play"],
    "scope": "Fresh render-only source, real compiled EXE/APK bytecode, original-command invalidation and raster equivalence. Natural FPS separated from paired background-layer timing. Identical RC30 simulation and story/font/art evidence retained explicitly. Failed trials/setup retained. No physical Android/emulator or completed balance claim.",
    "references": dict(sorted(references.items()))}
TARGET.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", "utf-8")
assert all(sha(ROOT / n) == d for n, d in report["references"].items())
print(json.dumps({"passed": True, "revision": TARGET.relative_to(ROOT).as_posix(), "references": len(references), "sha256": sha(TARGET)}))
