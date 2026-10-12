"""Bind the verified RC32 runtime and immutable observation artifacts."""
from pathlib import Path
import hashlib
import json

ROOT=Path(__file__).resolve().parents[2]
QA=ROOT/"output/qa/godot/contact-runtime-rc32";VERSION="3.0.0-rc32-preview"
RELEASE=ROOT/"release"/VERSION
TARGET=ROOT/"assets/paper-warfront/system-revisions/rc32-target-answers-r1.json"
assert not TARGET.exists()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text("utf-8"))
proof=read(RELEASE/"preview-verification.json")
assert proof["preview_artifacts_verified"] and read(QA/"publication.json")["passed"]
manifest=read(RELEASE/"build-manifest.json");refs={}
def bind(p):
    if p.is_file():refs[p.relative_to(ROOT).as_posix()]=sha(p)
for n,d in manifest["source_inputs"].items():assert sha(ROOT/n)==d;bind(ROOT/n)
for n in ["build-manifest.json","preview-verification.json","SHA256SUMS.txt","README.md"]:bind(RELEASE/n)
for row in manifest["builds"]+manifest["archives"]:assert sha(ROOT/row["path"])==row["sha256"];bind(ROOT/row["path"])
skip={"baseline-runtime","oracle-runtime","profile-r1-runtime","lookup-r1-runtime","answers-r1-runtime","native-baseline-runtime","native-answers-r1-runtime"}
for p in QA.rglob("*"):
    if p.is_file() and not any(part in skip or part==".godot" for part in p.relative_to(QA).parts):bind(p)
# Bind the actual independent source closures without recording duplicate raster caches.
for directory in ["baseline-runtime","oracle-runtime"]:
    for p in (QA/directory/"scripts").glob("*.gd"):bind(p)
for p in (ROOT/"tools/paper-warfront").glob("*.py"):
    if any(word in p.name for word in ["answers","contact","visibility_lookup"]):bind(p)
for n in ["build_game.py","package_preview.py","check_ai_engagement.py","check_dense_packaged_logic.py","check_terrain_packaged_logic.py",
    "run_realtime_release.py","check_realtime_battle.py","probe_realtime_battle.gd","run_preview_checks.py","run_query_native_extras.py"]:bind(ROOT/"tools/paper-warfront"/n)
for n,d in read(QA/"publication.json")["files"].items():assert sha(ROOT/n)==d;bind(ROOT/n)
report={"id":"system.target-answers.rc32","version":1,"release":VERSION,"parent_revision":"system.terrain-command-cache.rc31",
    "formal_script_changes":["battle_sim.gd","battle_visibility.gd"],"generated_raster_assets":False,
    "runtime_input_count":1194,"unchanged_rc31_input_count":1190,"runtime_asset_count":455,
    "story_maps":200,"story_chapters":10,"local_minimal_route_orders":552,
    "source_groups":{"base":78,"new_query_boundaries":2},"source_assertions":836145,
    "fresh_complete_closure_comparison_steps":{"capacity":3600,"normal_paid":73103},
    "compiled_groups_each":{"base":36,"dense":2,"terrain":1,"new_query_boundaries":2},"compiled_assertions_each":936748,
    "same_process_cpu_observations":read(QA/"cpu-summary.json"),"native_exported_frame_observations":read(QA/"release-final/realtime/report.json"),
    "status":"verified_preview; dense60fps_balance_story_human_android_hardware_pending",
    "remaining":["sustained_dense60fps","full_faction_and_campaign_balance","original_exact_fog_timing","human_complete_story_experience","android_physical_device","human_network_play"],
    "scope":"Fresh exact RC31 closure comparisons, controlled all-roster phase and200-map fog boundaries, actual EXE/APK bytecode and native UI/render/FPS. Existing200-map authoring/font/art preserved by hash, no new image generation or physical Android claim.",
    "references":dict(sorted(refs.items()))}
TARGET.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n","utf-8")
assert all(sha(ROOT/n)==d for n,d in report["references"].items())
print(json.dumps({"passed":True,"revision":TARGET.relative_to(ROOT).as_posix(),"references":len(refs),"sha256":sha(TARGET)}))
