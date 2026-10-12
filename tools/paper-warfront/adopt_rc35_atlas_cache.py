"""Adopt the reviewed RC35 unit-atlas handle cache into the working Godot source."""
from pathlib import Path
import hashlib
import json
import shutil

ROOT = Path(__file__).resolve().parents[2]
QA = ROOT / "output/qa/godot/render-runtime-rc35"
TRIAL = QA / "atlas-cache-runtime"
TARGET = ROOT / "game/scripts/battle_view.gd"
OUT = QA / "adoption.json"
BINDING = QA / "combat-history-binding-r5.json"
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
read = lambda p: json.loads(p.read_text("utf-8"))

assert not OUT.exists(), "RC35 adoption receipt already exists"
assert not BINDING.exists(), "RC35 binding already exists"
source = read(QA / "atlas-cache-source-gates.json")
assert source["passed"] and source["source_unchanged"]
pixels = read(QA / "atlas-cache-render/report.json")
assert pixels["passed"] and len(pixels["comparisons"]) == 42
assert all(row["max_channel_delta"] == 0 for row in pixels["comparisons"])
mobile = read(QA / "atlas-cache-mobile/compact-16x9/report.json")
assert mobile["passed"]
natural = read(QA / "atlas-cache-natural-observation.json")
assert natural["passed"] and len(natural["cases"]) == 4
baseline = [row for row in natural["cases"] if row["label"] == "baseline"]
candidate = [row for row in natural["cases"] if row["label"] == "candidate"]
assert len(baseline) == len(candidate) == 2
assert max(row["draw_mean_ms"] for row in candidate) < min(row["draw_mean_ms"] for row in baseline)
assert min(row["fps"] for row in candidate) > max(row["fps"] for row in baseline) * 1.02
assert max(row["p95_frame_ms"] for row in candidate) <= max(row["p95_frame_ms"] for row in baseline)

trial = TRIAL / "scripts/battle_view.gd"
assert trial.exists() and sha(TARGET) != sha(trial)
before = sha(TARGET)
backup = QA / "pre-adoption"
assert not backup.exists()
backup.mkdir()
shutil.copy2(TARGET, backup / TARGET.name)
shutil.copy2(trial, TARGET)
after = sha(TARGET)
assert after == sha(trial)

binding = {
    "passed": True,
    "version": "3.0.0-rc35-preview",
    "base_binding_sha256": sha(QA / "../render-runtime-rc34/combat-history-binding-r4d.json"),
    "changed_file": "game/scripts/battle_view.gd",
    "before_sha256": before,
    "after_sha256": after,
    "source_gate_sha256": sha(QA / "atlas-cache-source-gates.json"),
    "pixel_report_sha256": sha(QA / "atlas-cache-render/report.json"),
    "mobile_report_sha256": sha(QA / "atlas-cache-mobile/compact-16x9/report.json"),
    "natural_observation_sha256": sha(QA / "atlas-cache-natural-observation.json"),
    "reason": "Dense battle profiling showed repeated unit atlas handle lookup in draw_frame_unit. The cache is keyed only by atlas path, cleared on battle reset, and does not alter frame selection, geometry, visibility, fog, simulation or UI.",
    "scope": "One rendering script only; map/story/fog rules, simulation, action frames, particles, assets and mobile layout remain unchanged.",
}
BINDING.write_text(json.dumps(binding, ensure_ascii=False, indent=2) + "\n", "utf-8")
receipt = {
    "passed": True,
    "release": "3.0.0-rc35-preview",
    "changed_inputs": {"game/scripts/battle_view.gd": {"before": before, "after": after}},
    "proofs": {
        "atlas-cache-preparation.json": sha(QA / "preparation.json"),
        "atlas-cache-source-gates.json": sha(QA / "atlas-cache-source-gates.json"),
        "atlas-cache-render/report.json": sha(QA / "atlas-cache-render/report.json"),
        "atlas-cache-mobile/compact-16x9/report.json": sha(QA / "atlas-cache-mobile/compact-16x9/report.json"),
        "atlas-cache-natural-observation.json": sha(QA / "atlas-cache-natural-observation.json"),
    },
    "runner_sha256": sha(Path(__file__)),
    "source_groups": source["jobs"][0]["groups"],
    "source_checks": source["jobs"][0]["checks"],
    "source_pixel_pairs": len(pixels["comparisons"]),
    "natural_abba_windows": len(natural["cases"]),
    "generated_raster_assets": False,
    "scope": "RC35 atlas-handle cache adopted only after source, pixel, mobile and natural ABBA evidence. The candidate caches loaded Texture2D handles by atlas path and clears them on reset; it does not cache frame regions or visibility results.",
}
OUT.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", "utf-8")
print(json.dumps({"passed": True, "before": before, "after": after, "binding": BINDING.as_posix()}))
