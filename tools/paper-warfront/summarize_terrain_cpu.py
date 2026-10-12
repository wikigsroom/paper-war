"""Bind nearby native ABBA layer timings; do not call mixed frames pure FPS."""
from pathlib import Path
import hashlib
import json
import statistics

ROOT = Path(__file__).resolve().parents[2]
QA = ROOT / "output/qa/godot/pressure-runtime-rc31"
target = QA / "terrain-cpu-summary.json"
assert not target.exists()
raw = QA / "terrain-abba-native-r3/terrain-abba.json"
source = json.loads(raw.read_text("utf-8"))
samples = source["samples"]
pairs = []
for i in range(32, len(samples) - 3, 4):
    rows = samples[i:i + 4]
    assert [r["kind"] for r in rows] == ["optimized", "original", "original", "optimized"]
    if len({r["camera_x"] for r in rows}) != 1 or not all(r["reuse"] for r in rows if r["kind"] == "optimized"):
        continue
    pairs.append({"sample_start": i, "camera_x": rows[0]["camera_x"],
        "original_us": statistics.mean(r["terrain_us"] for r in rows if r["kind"] == "original"),
        "optimized_us": statistics.mean(r["terrain_us"] for r in rows if r["kind"] == "optimized")})
assert pairs
before = statistics.mean(r["original_us"] for r in pairs)
after = statistics.mean(r["optimized_us"] for r in pairs)
target.write_text(json.dumps({"passed": True, "native_samples": len(samples),
    "paired_stable_quartets": len(pairs), "original_layer_us": before, "optimized_layer_us": after,
    "decrease_percent": 100 * (1 - after / before), "pairs": pairs,
    "abba_report_sha256": hashlib.sha256(raw.read_bytes()).hexdigest(),
    "generator_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    "scope": "Native source-trial same-process ABBA in the background/terrain draw layer. First32 draw samples excluded; only complete quartets with an exactly identical camera and both optimized calls actually reusing commands. This layer includes the background. Mixed-stream FPS is not pure optimized FPS, and external user workload was not controlled."
}, indent=2) + "\n", "utf-8")
print("Native stable layer pairs", len(pairs), "mean decrease", round(100 * (1 - after / before), 3), "%")
