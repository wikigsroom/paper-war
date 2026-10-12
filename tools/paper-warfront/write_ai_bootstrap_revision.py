"""Bind the rc23 economy change to its frozen observations and verified binaries."""
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[2]
QA = ROOT / "output/qa/godot/ai-redemption-rc23"
RELEASE = ROOT / "release/3.0.0-rc23-preview"


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


proof = read(RELEASE / "preview-verification.json")
manifest = read(RELEASE / "build-manifest.json")
prior = read(ROOT / "release/3.0.0-rc22-preview/build-manifest.json")
assert manifest["version"] == proof["version"] == "3.0.0-rc23-preview"
assert proof["preview_artifacts_verified"] and proof["source_inputs_verified"]
assert not proof["android_hardware_verified"] and not proof["full_balance_verified"]
assert manifest["source_inputs"].keys() == prior["source_inputs"].keys()
changed = sorted(k for k, v in manifest["source_inputs"].items() if prior["source_inputs"][k] != v)
assert changed == ["game/export_presets.cfg", "game/project.godot", "game/scripts/tactical_ai.gd"]
assert all(sha(ROOT / k) == v for k, v in manifest["source_inputs"].items())

equivalence = read(QA / "formal-source/equivalence.json")
assert equivalence["candidate_active_branch_equals_formal_source"]
assert equivalence["formal_ai_sha256"] == sha(ROOT / "game/scripts/tactical_ai.gd")
assert sorted(equivalence["changed_public_inputs"]) == changed

regression = read(QA / "formal-reach/regression/report.json")
assert regression["passed"] and regression["source_unchanged"]
assert len(regression["tests"]) == 68
assert sum(t["checks"] for t in regression["tests"]) == 15436
package_checks = {}
for package in ("windows", "apk"):
    report = read(QA / f"release-final/{package}-logic/report.json")
    assert report["passed"] and len(report["tests"]) == 24
    assert sum(t["checks"] for t in report["tests"]) == 2546
    package_checks[package] = {"groups": 24, "checks": 2546}

compiled = read(QA / "release-final/apk-logic/report.json")["extracted_inputs"]
prior_compiled = read(ROOT / "output/qa/godot/observer-camera-rc22/release/apk-logic/report.json")["extracted_inputs"]
assert compiled.keys() == prior_compiled.keys()
compiled_changes = sorted(k for k in compiled if compiled[k] != prior_compiled[k])
assert compiled_changes == [".godot/uid_cache.bin", "assets.sparsepck", "project.binary", "scripts/tactical_ai.gdc"]

comparisons = {}
for name in ("compare-r8-west-matrix.json", "compare-r8-short-east.json", "compare-r8-long-east.json"):
    data = read(QA / name)
    assert data["passed"] and not data["balance_accepted"]
    assert data["stock"] == 160 and data["duration"] == 240
    comparisons[name] = {k: data[k] for k in (
        "pairs", "candidate_side", "map", "seed", "stock", "duration",
        "identical_disabled_records", "totals",
    )}
    comparisons[name]["win_to_loss_indices"] = [r["index"] for r in data["records"]
        if r["control_winner"] == data["candidate_side"] and r["candidate_winner"] == 1 - data["candidate_side"]]
    comparisons[name]["win_to_unresolved_indices"] = [r["index"] for r in data["records"]
        if r["control_winner"] == data["candidate_side"] and r["candidate_winner"] < 0]
assert sum(c["pairs"] for c in comparisons.values()) == 104

observer = ROOT / "tools/paper-warfront/observe_ai_redemption.py"
assert sha(observer) == read(QA / "economy-r8-west-matrix/report.json")["observer_sha256"]
snapshot = QA / "observer-v2.py"
if snapshot.exists():
    assert sha(snapshot) == sha(observer)
else:
    snapshot.write_bytes(observer.read_bytes())

for artifact in manifest["builds"] + manifest["archives"]:
    path = ROOT / artifact["path"]
    assert path.stat().st_size == artifact["bytes"] and sha(path) == artifact["sha256"]
with zipfile.ZipFile(ROOT / manifest["archives"][0]["path"]) as archive:
    receipts = [n for n in archive.namelist() if n.endswith("/preview-verification.json") or n == "preview-verification.json"]
    assert len(receipts) == 1 and json.loads(archive.read(receipts[0])) == proof

ui = read(ROOT / "assets/paper-warfront/ui/paper-ui.json")
style = read(ROOT / "assets/paper-warfront/style-tokens.json")
assert len(ui["assets"]) == 38 and ui["model"] == "gpt-image-2.5"
references = [
    "tools/paper-warfront/write_ai_bootstrap_revision.py",
    "tools/paper-warfront/observe_ai_redemption.py",
    "tools/paper-warfront/compare_ai_redemption.py",
    "game/tests/test_ai_economy_bootstrap.gd",
    "game/tests/test_ai_bootstrap_investments.gd",
    "game/tests/test_ai_route_defense.gd",
    "docs/paper-warfront/132-正常开局资金优先级与科技兑现复核及rc23交付.md",
    "docs/paper-warfront/11-Godot架构与数据契约.md",
    "docs/paper-warfront/16-玩家手册.md",
    "assets/paper-warfront/presentation-revisions/rc21-fog-stage-r1.json",
    "assets/paper-warfront/presentation-revisions/rc22-observer-camera-r1.json",
    "assets/paper-warfront/style-tokens.json",
    "assets/paper-warfront/ui/paper-ui.json",
    "release/3.0.0-rc23-preview/README.md",
    "release/3.0.0-rc23-preview/build-manifest.json",
    "release/3.0.0-rc23-preview/preview-verification.json",
]
qa_references = [
    "formal-source/equivalence.json", "formal-source/tactical-ai.diff", "observer-v2.py",
    "formal-reach/regression/report.json", "formal-reach/verification.json", "formal-hammer/verification.json",
    "control-matrix-r1/report.json", "economy-r8-west-matrix/report.json",
    "economy-r8-disabled-control/report.json", "short-r8-east-271/report.json", "long-r8-east-419/report.json",
    "compare-r8-west-matrix.json", "compare-r8-short-east.json", "compare-r8-long-east.json",
    "compare-grant-r6-matrix.json", "formal-reach/regression-r5-failed/report.json",
    "r5-export-not-deliverable/status.json", "release-final/windows-logic/report.json",
    "release-final/apk-logic/report.json", "release-final/camera-render/report.json",
    "release-final/fog-render/report.json", "release-final/stage-proportions/report.json",
    "release-final/duel-stage/report.json", "release-final/mobile/mobile-matrix.json",
    "release-final/paper-ui-assets.json",
]
references.extend("output/qa/godot/ai-redemption-rc23/" + name for name in qa_references)
record = {
    "revision": "rc23-ai-economy-bootstrap-r1", "rule_id": "ai.common.economy.bootstrap",
    "version": manifest["version"], "status": "verified-preview",
    "implementation": "native Godot tactical AI; actual worker, facility and authored research budgets",
    "source": "game/scripts/tactical_ai.gd", "source_sha256": equivalence["formal_ai_sha256"],
    "changed_public_inputs_since_rc22": changed,
    "r8_active_branch_equals_formal_source": True,
    "unchanged_extracted_apk_inputs_since_rc22": len(compiled) - len(compiled_changes),
    "changed_extracted_apk_inputs_since_rc22": compiled_changes,
    "new_raster_generation": False, "style_tokens_version": style["version"],
    "reused_presentation_revisions": ["rc21-fog-stage-r1", "rc22-observer-camera-r1"],
    "reused_ui_asset_version": ui["version"], "reused_ui_assets": len(ui["assets"]),
    "reused_ui_generation_model": ui["model"],
    "source_mechanism_checks": {"groups": 68, "checks": 15436},
    "packaged_logic_checks_on_windows": package_checks,
    "paired_single_side_observations": comparisons,
    "paired_scope": "104 pairs, 160 starting gold, 240-second ceiling; one changed AI side, zero AI warmup. Shipping uses the fix on both sides. These are not human-play or complete balance measurements.",
    "advanced_first_deployment_candidate_shipped": False,
    "advanced_first_deployment_gap_remaining": True,
    "android_hardware_verified": False, "full_balance_verified": False,
    "original_game_numeric_equivalence_verified": False,
    "files": {name: sha(ROOT / name) for name in references},
    "builds_and_archives": manifest["builds"] + manifest["archives"],
}
target = ROOT / "assets/paper-warfront/system-revisions/rc23-ai-economy-bootstrap-r1.json"
target.parent.mkdir(parents=True, exist_ok=True)
target.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
assert all(sha(ROOT / name) == digest for name, digest in record["files"].items())
print(f"AI bootstrap revision verified: {len(references)} references; 104 observation pairs; {len(compiled)-len(compiled_changes)} unchanged APK inputs.")
