"""Compare complete normal-AI cohorts; preserve both-side and faction scopes."""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path

read = lambda p: json.loads(p.read_text(encoding="utf-8-sig"))
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
ap = argparse.ArgumentParser()
ap.add_argument("--control", type=Path, required=True)
ap.add_argument("--candidate", type=Path, required=True)
ap.add_argument("--output", type=Path, required=True)
args = ap.parse_args()


def verify(path):
    report = read(path)
    runtime = Path(report["runtime"])
    assert report["passed"] and report["candidate_side"] is None
    assert all(sha(runtime / name) == digest for name, digest in report["runtime_inputs"].items())
    selectors = {
        "experimental_paid_opening_side": "experimental_ai_paid_opening",
        "experimental_ai_budget_planner_side": "experimental_ai_budget_planner",
        "experimental_ai_grant_redemption_side": "experimental_ai_grant_redemption",
    }
    rows = {}
    for item in report["batches"]:
        file = path.parent / item["file"]
        assert sha(file) == item["sha256"]
        raw = read(file)
        for key, expected in [("map", report["map"]), ("seed", report["seed"]),
                              ("starting_gold_per_side", report["starting_stock"]), ("duration_seconds", report["duration"])]:
            assert raw[key] == expected
        for key, value in raw.items():
            if key.startswith("experimental_") and value:
                assert key in selectors and not raw.get(selectors[key], False), (key, value)
        for row in raw["records"]:
            assert row["index"] not in rows
            rows[row["index"]] = row
    assert sorted(rows) == [r["index"] for r in report["matches"]]
    return report, rows


control, raw_control = verify(args.control)
candidate, raw_candidate = verify(args.candidate)
assert read(Path(candidate["runtime"]) / "candidate.json")["normal_pipeline_enabled_on_both_sides"]
for key in ["map", "seed", "starting_stock", "duration"]:
    assert control[key] == candidate[key]
assert raw_candidate.keys() <= raw_control.keys()
changed = []
for name, digest in control["runtime_inputs"].items():
    if name.endswith((".gd", ".json", ".godot")) and name not in ["snapshot.json", "candidate.json"]:
        assert name in candidate["runtime_inputs"]
        if candidate["runtime_inputs"][name] != digest:
            changed.append(name)
assert sorted(changed) == ["scripts/tactical_ai.gd", "tests/probe_faction_matchups.gd"], changed


def summarize(row, side):
    own = row["sides"][side]
    studies = [s for s in row["studies"] if s["side"] == side]
    return {
        "win": int(row["winner"] == side), "loss": int(row["winner"] == 1 - side),
        "unresolved": int(row["winner"] not in [0, 1]), "gold_delivered": own["stats"]["gold_delivered"],
        "no_workers_at_endpoint": int(own["workers"] == 0 and not any(x.endswith(".worker") for x in own["queue"])),
        "research_paid": len(studies), "research_completed": sum(s["research_done"] is not None for s in studies),
        "research_with_paid_order": sum(s["paid_order"] is not None for s in studies),
        "research_with_production_spawn": sum(s["production_spawn"] is not None for s in studies),
        "research_with_direct_contribution": sum(s["direct_contribution"] for s in studies),
        "effective_first_unit_healing": sum(s["effective_heal_amount"] for s in studies),
        "completed_without_order_with_30_seconds": sum(s["research_done"] is not None and s["paid_order"] is None and s["remaining_after_completion"] >= 30 for s in studies),
    }


before = {r["index"]: r for r in control["matches"]}
totals = {"control": Counter(), "candidate": Counter()}
outcomes = {"control": Counter(), "candidate": Counter()}
factions = defaultdict(lambda: {"control": Counter(), "candidate": Counter()})
records = []
for row in candidate["matches"]:
    old = before[row["index"]]
    assert old["west"] == row["west"] and old["east"] == row["east"]
    entry = {"index": row["index"], "west": row["west"], "east": row["east"],
             "control_winner": old["winner"], "candidate_winner": row["winner"], "sides": []}
    for label, value in [("control", old), ("candidate", row)]:
        outcomes[label]["west_win" if value["winner"] == 0 else "east_win" if value["winner"] == 1 else "unresolved"] += 1
    for side in [0, 1]:
        stats = {"control": summarize(old, side), "candidate": summarize(row, side)}
        for label, values in stats.items():
            totals[label].update(values)
            factions[row[["west", "east"][side]]][label].update(values)
        entry["sides"].append(stats)
    records.append(entry)
result = {
    "passed": True, "balance_accepted": False, "pairs": len(records), "side_participations": len(records) * 2,
    "scope": "Paid normal AI on both sides, same map/stock/seed/ceiling. Each match counted once in outcomes; faction metrics count its actual side participations. Provenance/measurement acceptance only, not full balance or human-play acceptance.",
    "map": control["map"], "seed": control["seed"], "stock": control["starting_stock"], "duration": control["duration"],
    "inputs": {"control": {"path": str(args.control.resolve()), "sha256": sha(args.control)},
               "candidate": {"path": str(args.candidate.resolve()), "sha256": sha(args.candidate)}},
    "changed_runtime_inputs": changed, "outcomes": outcomes, "totals": totals, "factions": factions, "records": records,
}
args.output.parent.mkdir(parents=True, exist_ok=True)
args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({k: result[k] for k in ["pairs", "outcomes", "totals"]}))
