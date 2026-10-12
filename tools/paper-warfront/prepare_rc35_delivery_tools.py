"""Create immutable RC35 delivery/audit tools from the completed RC34 workflow."""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "tools/paper-warfront"
QA = ROOT / "output/qa/godot/render-runtime-rc35"
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
records = {}

def write(name: str, source_name: str, transform):
    target = TOOLS / name
    assert not target.exists(), name
    source = TOOLS / source_name
    text = transform(source.read_text("utf-8"))
    target.write_text(text, "utf-8")
    records[name] = {"source": source_name, "source_sha256": sha(source), "derived_sha256": sha(target)}

def rc35(s: str) -> str:
    return (s.replace("run_rc34_release_validation.py", "run_rc35_release_validation.py")
             .replace("check_rc34_visibility_d_render.py", "check_rc35_atlas_render.py")
             .replace("visibility-render", "atlas-render")
             .replace("render-runtime-rc34", "render-runtime-rc35")
             .replace("3.0.0-rc34-preview", "3.0.0-rc35-preview")
             .replace("3.0.0-rc33-preview", "3.0.0-rc34-preview")
             .replace("RC34", "RC35")
             .replace("rc34", "rc35"))

write("run_rc35_release_validation.py", "run_rc34_release_validation.py", rc35)
write("package_rc35_preview.py", "package_rc34_preview.py", rc35)
write("audit_rc35_preview.py", "audit_rc34_preview.py", lambda s: rc35(s).replace("verify_visibility_c_release_evidence", "verify_rc35_atlas_release_evidence"))
write("finish_rc35_release.py", "finish_rc34_release.py", rc35)

verifier = '''"""Verify RC35 atlas-cache package evidence and retain combat/story continuity."""
from pathlib import Path
import hashlib
import json

def verify(root, qa, version, manifest, apk_logic):
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    read = lambda p: json.loads(p.read_text("utf-8"))
    history = qa.parent
    assert version == "3.0.0-rc35-preview"
    binding_path = history / "combat-history-binding-r5.json"
    binding = read(binding_path)
    assert binding["passed"] and binding["version"] == version
    assert binding["changed_file"] == "game/scripts/battle_view.gd"
    assert sha(root / binding["changed_file"]) == binding["after_sha256"]
    gate = read(history / "atlas-cache-source-gates.json")
    assert gate["passed"] and gate["source_unchanged"]
    assert gate["jobs"][0]["groups"] == 78 and gate["jobs"][0]["checks"] == 195435
    pixels = read(history / "atlas-cache-render/report.json")
    assert pixels["passed"] and len(pixels["comparisons"]) == 42
    assert all(row["max_channel_delta"] == 0 for row in pixels["comparisons"])
    mobile = read(history / "atlas-cache-mobile/compact-16x9/report.json")
    assert mobile["passed"]
    natural = read(history / "atlas-cache-natural-observation.json")
    assert natural["passed"] and len(natural["cases"]) == 4
    base = [row for row in natural["cases"] if row["label"] == "baseline"]
    trial = [row for row in natural["cases"] if row["label"] == "candidate"]
    assert len(base) == len(trial) == 2
    assert max(row["draw_mean_ms"] for row in trial) < min(row["draw_mean_ms"] for row in base)
    assert min(row["fps"] for row in trial) > max(row["fps"] for row in base) * 1.02
    compiled = read(qa / "atlas-render/report.json")
    assert compiled["passed"] and len(compiled["comparisons"]) == 42
    assert all(row["max_channel_delta"] == 0 for row in compiled["comparisons"])
    for display in ["desktop", "phone"]:
        native = read(qa / "atlas-render" / (display + "-after/report.json"))
        assert len(native.get("visibility_checks", [])) == 9
        assert all(row["passed"] and 0 <= row["entries"] <= 1000 for row in native["visibility_checks"])
        assert all(sha(Path(row["path"])) == row["sha256"] for row in native["captures"])
    for platform, artifact in [("windows", manifest["builds"][0]), ("apk", manifest["builds"][1])]:
        kind = "windows_embedded_pack" if platform == "windows" else "apk_extracted_bytecode_on_windows"
        for name, checks in [("dense", 102920), ("terrain", 5873), ("phase", 461238)]:
            report = read(qa / (name + "-" + platform + "/report.json"))
            assert report["passed"] and report["checks"] == checks
            assert report["artifact_sha256"] == artifact["sha256"] and report["runtime_kind"] == kind
    validation = read(qa / "validation-report.json")
    assert validation["passed"] and validation["version"] == version
    assert all(row["passed"] for row in validation["jobs"])
    runner = root / "tools/paper-warfront/run_rc35_release_validation.py"
    assert validation["runner_sha256"] == sha(runner) == sha(qa / "release-final/validation-runner.py")
    prior = root / "output/qa/godot/phase-runtime-rc33"
    retained = {}
    for name, count in [("marching-capacity-r3.json", 3600), ("marching-paid-r3.json", 73103), ("marching-boundary-r3-r3.json", 432427), ("marching-phase-r3.json", 28811)]:
        record = read(prior / name)
        assert record["passed"] and not record["failures"] and record["checks"] == count
        assert record["simulation_sha256"] == sha(root / "game/scripts/battle_sim.gd")
        retained[name] = sha(prior / name)
    return {
        "retained_rc33_simulation_equivalence": {"capacity_steps": 3600, "normal_paid_steps": 73103, "source_boundary_checks": 432427, "mixed_phase_checks": 28811, "records": retained, "scope": "RC33 simulation, fog, map/story, actions and UI remain bound by unchanged input hashes; RC35 changes only a view-side unit-atlas handle cache."},
        "packed_query_equivalence_verified": {"fresh_retention_checks_per_package": 102920},
        "terrain_commands_verified": {"checks_per_compiled_package": 5873, "maps": 200},
        "atlas_handle_cache_verified": {"source_pixel_pairs": 42, "compiled_pixel_pairs": 42, "pixel_delta": 0, "mobile_cases": 1, "scope": "Texture2D handles are reused by atlas path and cleared on battle reset; frame regions, animation, fog, route hit-tests and simulation remain live."},
        "current_input_binding_sha256": sha(binding_path),
    }
'''
(TOOLS / "verify_rc35_atlas_release_evidence.py").write_text(verifier, "utf-8")
records["verify_rc35_atlas_release_evidence.py"] = {"source": "custom", "derived_sha256": sha(TOOLS / "verify_rc35_atlas_release_evidence.py")}

publish = '''"""Publish RC35 atlas-cache and non-linear single-player story notes."""
from pathlib import Path
import hashlib, json, shutil

ROOT = Path(__file__).resolve().parents[2]
QA = ROOT / "output/qa/godot/render-runtime-rc35"
FINAL = QA / "release-final"
VERSION = "3.0.0-rc35-preview"
RELEASE = ROOT / "release" / VERSION
DOC = ROOT / "docs/paper-warfront/145-单位图集缓存与非线性剧情地图及rc35预览交付.md"
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
read = lambda p: json.loads(p.read_text("utf-8"))
assert not DOC.exists() and not (RELEASE / "README.md").exists()
validation = read(FINAL / "validation-report.json")
assert validation["passed"] and validation["version"] == VERSION
manifest = read(RELEASE / "build-manifest.json")
assert manifest["version"] == VERSION and len(manifest["source_inputs"]) == 1194
assert all(sha(ROOT / name) == digest for name, digest in manifest["source_inputs"].items())
for platform in ["windows", "apk"]:
    primary = read(FINAL / (platform + "-logic/report.json"))
    assert primary["passed"] and sum(row["checks"] for row in primary["tests"]) == 187249
    for prefix, count in [("dense", 102920), ("terrain", 5873), ("phase", 461238)]:
        report = read(FINAL / (prefix + "-" + platform + "/report.json"))
        assert report["passed"] and report["checks"] == count
pixels = read(FINAL / "atlas-render/report.json")
assert pixels["passed"] and len(pixels["comparisons"]) == 42 and all(row["max_channel_delta"] == 0 for row in pixels["comparisons"])
frames = read(FINAL / "realtime/report.json")
assert frames["passed"] and frames["version"] == VERSION
natural = read(QA / "atlas-cache-natural-observation.json")
assert natural["passed"] and len(natural["cases"]) == 4
base = [row for row in natural["cases"] if row["label"] == "baseline"]
candidate = [row for row in natural["cases"] if row["label"] == "candidate"]
assert max(row["draw_mean_ms"] for row in candidate) < min(row["draw_mean_ms"] for row in base)
assert min(row["fps"] for row in candidate) > max(row["fps"] for row in base) * 1.02
story = read(QA / "authorship.json")
assert story["passed"] and story["authored_maps"] == 200
exe_hash, apk_hash = (row["sha256"] for row in manifest["builds"])
fps_table = "\\n".join(f"| {row['case']} | {row['max_units']} | {row['fps_from_mean_interval']:.2f} | {row['p95_frame_ms']:.3f} |" for row in frames["cases"])
candidate_table = "\\n".join(f"| {row['order']} | {row['label']} | {row['fps']:.2f} | {row['draw_mean_ms']:.3f} | {row['p95_frame_ms']:.3f} |" for row in natural["cases"])
text = f"""# 单位图集句柄缓存、非线性剧情地图与rc35预览交付

RC35 在战斗视图中按图集路径复用已加载的 Texture2D 句柄，并在重开战斗时清空。它没有缓存帧区域、单位位置、战争迷雾或路线命中结果，因此不改变动作帧、单位大小、迷雾边界和地图交互，只减少密集单位绘制时的重复资源查找。

## 单机地图与剧情

单机地图继续遵守“地图即叙事场所”的合同：十章200张地图逐图绑定战前冲突、地点动机、真实目标、战后结果和证据旗。`campaign.json`负责对战字段，`campaign-flow.json`负责可达路线，`campaign-narrative.json`负责叙事与道路/目标绑定，`story.json`负责展示文本。

路线不被强制成一条直线。地图按冲突选择单路压迫、分岔择一、并行调查后汇流、条件汇合或可回访支线；战役推进图与一场战斗内部的道路图分开。桥口、矿点、道路长度、护送对象和未知区域必须实际改变自动行军、运金风险、视野或目标窗口。剧情文本不越过战争迷雾泄露实时敌情，未走支线不会自动获得其证据；失败不推进，回访保留已取得记录和最高星级。

## RC35 验证

| 项目 | 结果 |
|---|---:|
| 源码回归 | 78 组 / 195435 项，通过 |
| 固定姿态画面对照 | 42 组，像素差 0 |
| 移动端紧凑路线/分岔矩阵 | 通过，战场可视比例 ≥70% |
| Windows/APK 基础逻辑 | 各 36 组 / 187249 项，通过 |
| 密集、地形、阶段编译检查 | 各 102920、5873、461238 项，通过 |
| 单机剧情作者记录 | 200 张地图，通过 |

自然压力窗口（124 个单位、20 秒，仅比较渲染开销）：

| 顺序 | 输入 | 平均 FPS | 绘制 CPU 均值 | P95 帧间隔 |
|---:|---|---:|---:|---:|
{candidate_table}

实际导出程序帧率：

| 场景 | 峰值单位 | 平均 FPS | P95 帧间隔 |
|---|---:|---:|---:|
{fps_table}

持续满员 60FPS、全阵营/全关人工平衡、原作精确迷雾时序、真人完整剧情体验、Android 实体设备和真人联机仍待验证。当前 Android 结果是 Windows 原生 Godot 对 APK 的资源/字节码检查，没有使用模拟器。

## 下载

- [Windows ZIP](../../release/{VERSION}/PaperWarfront-Windows-{VERSION}.zip)
- [Windows EXE](../../release/{VERSION}/windows/PaperWarfront.exe)
- [Android APK](../../release/{VERSION}/android/PaperWarfront-{VERSION}.apk)
- [发布验证](../../release/{VERSION}/preview-verification.json)
- [SHA256 清单](../../release/{VERSION}/SHA256SUMS.txt)

EXE SHA256：`{exe_hash}`  
APK SHA256：`{apk_hash}`
"""
DOC.write_text(text, "utf-8")
(RELEASE / "README.md").write_text(text, "utf-8")
backup = QA / "pre-publication"
assert not backup.exists()
for name in ["README.md", "docs/paper-warfront/README.md"]:
    source = ROOT / name
    destination = backup / name
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    old = source.read_text("utf-8")
    entry = "[145-单位图集缓存、非线性剧情地图与rc35交付](145-单位图集缓存与非线性剧情地图及rc35预览交付.md)：按图集路径复用Texture2D句柄；200张单机地图逐图绑定剧情，支持分岔、并行、汇流和回访。"
    if name == "docs/paper-warfront/README.md":
        lines = old.splitlines()
        source.write_text(lines[0] + "\\n\\n" + entry + "\\n\\n" + "\\n".join(lines[1:]) + "\\n", "utf-8")
    else:
        source.write_text("# 纸上兵戈：十院留名 · rc35-preview\\n\\n" + entry.replace("](145-", "](docs/paper-warfront/145-") + "\\n\\n" + old.lstrip("# 纸上兵戈：十院留名 · rc34-preview\\n"), "utf-8")
files = [DOC, RELEASE / "README.md", ROOT / "README.md", ROOT / "docs/paper-warfront/README.md"]
(QA / "publication.json").write_text(json.dumps({"passed": True, "version": VERSION, "files": {path.relative_to(ROOT).as_posix(): sha(path) for path in files}, "scope": "Published after RC35 atlas source/pixel/mobile and fresh native package validation. The 200-map single-player story and non-linear route contract remain active."}, ensure_ascii=False, indent=2) + "\\n", "utf-8")
print(json.dumps({"passed": True, "doc": DOC.relative_to(ROOT).as_posix(), "exe_sha256": exe_hash, "apk_sha256": apk_hash}))
'''
(TOOLS / "publish_rc35_release.py").write_text(publish, "utf-8")
records["publish_rc35_release.py"] = {"source": "custom", "derived_sha256": sha(TOOLS / "publish_rc35_release.py")}

register = '''"""Bind the immutable RC35 preview, evidence and delivery tools."""
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
TARGET.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\\n", "utf-8")
assert all(sha(ROOT / name) == digest for name, digest in report["references"].items())
print(json.dumps({"passed": True, "revision": TARGET.relative_to(ROOT).as_posix(), "references": len(refs), "sha256": sha(TARGET)}))
'''
(TOOLS / "register_rc35_release.py").write_text(register, "utf-8")
records["register_rc35_release.py"] = {"source": "custom", "derived_sha256": sha(TOOLS / "register_rc35_release.py")}

(QA / "delivery-tool-preparation.json").write_text(json.dumps({"passed": True, "generator_sha256": sha(Path(__file__)), "derivations": records, "scope": "New RC35 delivery tools only. RC34 tools and releases remain immutable."}, ensure_ascii=False, indent=2) + "\n", "utf-8")
print(json.dumps({"passed": True, "tools": sorted(records)}))
