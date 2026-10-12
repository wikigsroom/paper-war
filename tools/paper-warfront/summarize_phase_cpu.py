"""Summarize the already frozen matched-process timings, without rerunning them."""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[2]
QA = ROOT / "output/qa/godot/phase-runtime-rc33"
OUT = QA / "cpu-summary.json"
assert not OUT.exists()
source = QA / "marching-capacity-r3.json"
d = json.loads(source.read_text("utf-8"))
assert d["passed"] and d["checks"] == 3600 and len(d["paired_cpu"]) == 3600
rows = []
for case in d["cases"]:
    samples = [r for r in d["paired_cpu"] if r["map"] == case["map"]]
    assert len(samples) == 1200 and case["equal"]
    baseline = sum(r["baseline_us"] for r in samples) / len(samples)
    candidate = sum(r["candidate_us"] for r in samples) / len(samples)
    rows.append({"map": case["map"], "steps": len(samples), "original_us": baseline, "candidate_us": candidate, "decrease_percent": (baseline-candidate)/baseline*100})
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
OUT.write_text(json.dumps({
    "passed": True, "cases": rows, "input_sha256": sha(source), "tool_sha256": sha(Path(__file__)),
    "scope": "Retained fresh same-process1200-step alternating RC32/R3 timings per map; exact full-state comparisons separate from measured tick interval.124 high-HP actors/AI disabled is capacity CPU evidence, not paid balance or rendered FPS. Ownership view optimization does not run in this headless fixture."
}, indent=2) + "\n", "utf-8")
print(json.dumps(rows), flush=True)
