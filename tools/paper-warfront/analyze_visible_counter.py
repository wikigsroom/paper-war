"""Verify paid visible-counter pairs and distinguish research, order and contribution."""
import hashlib
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
QA = ROOT / "output/qa/godot/core-alignment-rc14"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    paths = [QA / "visible-counter-control.json", QA / "visible-counter-trial.json"]
    control, trial = [json.loads(p.read_text(encoding="utf-8")) for p in paths]
    errors, records = [], []
    for label, data in [("control", control), ("trial", trial)]:
        if len(data["records"]) != 4 or {r["index"] for r in data["records"]} != {15, 51, 59, 95}:
            errors.append(f"{label}: incomplete four-match observation")
        for name, expected in data["inputs"].items():
            if sha(ROOT / "game" / name.removeprefix("res://")) != expected:
                errors.append(f"{label}: stale source {name}")
        if not data.get("observe_ai_recruitment"):
            errors.append(f"{label}: actual recruitment decisions not captured")
    if control["inputs"] != trial["inputs"]:
        errors.append("Different source inputs")
    for key in ["map", "seed", "duration_seconds", "combat_trace_seconds", "observe_ai_recruitment"]:
        if control[key] != trial[key]:
            errors.append(f"Different conditions: {key}")
    active = lambda d: {k: v for k, v in d.items() if k.startswith("experimental_") and v}
    if active(control):
        errors.append("Control has active experimental policies")
    if active(trial) != {"experimental_ai_visible_counter_deployment": True, "experimental_visible_counter_faction": "qi"}:
        errors.append("Unexpected trial policy or scope")
    for base, candidate in zip(control["records"], trial["records"]):
        if [base[k] for k in ["index", "west", "east"]] != [candidate[k] for k in ["index", "west", "east"]]:
            errors.append("Pair identity mismatch")
        side = 0 if base["west"] == "qi" else 1
        pair = {"index": base["index"], "west": base["west"], "east": base["east"], "records_identical": base == candidate}
        for label, row in [("control", base), ("trial", candidate)]:
            decisions = [d for d in row["recruitment_decisions"] if d["side"] == side and "unit.qi.sniper" in d["unlocked"]]
            events = [e for e in row["investment_trace"] if e["side"] == side]
            eligible = [d for d in decisions if d.get("counter_eligible")]
            pair[label] = {
                "winner": row["winner"], "end_seconds": row["time"],
                "workers": row["sides"][side]["workers"], "base_hp": row["sides"][side]["base_hp"],
                "after_unlock_decisions": len(decisions),
                "maximum_observed_cash_after_unlock": max((d["gold_before"] for d in decisions), default=0),
                "selected_choices": dict(Counter(d["selected"] for d in decisions)),
                "saving_next_research_decisions": sum(bool(d["research_target"]) for d in decisions),
                "candidate_eligible_after_request": len(eligible),
                "eligible_but_emergency_decisions": sum(d["front_broken"] or d["threatened"] for d in eligible),
                "activated_deployment_decisions": sum(bool(d["deployment_target"]) for d in decisions),
                "research_completed_seconds": [e["time"] for e in events if e["kind"] == "research_done" and e["id"] == "unit.qi.sniper"],
                "paid_sniper_orders": sum(e["kind"] == "recruit" and e["id"] == "unit.qi.sniper" for e in events),
                "sniper_spawns": sum(e["kind"] == "spawn" and e.get("id") == "unit.qi.sniper" and e.get("side") == side for e in row["combat_trace"]),
                "sniper_hit_events": sum(e["kind"] == "hit" and e.get("source_id") == "unit.qi.sniper" and e.get("attacker_side") == side for e in row["combat_trace"]),
                "visible_enemy_patterns": [{"ids": list(ids), "decisions": count} for ids, count in Counter(tuple(d["visible_enemy_ids"]) for d in decisions).most_common(5)],
            }
        records.append(pair)
    report = {"passed": not errors, "errors": errors,
              "scope": "Four paired paid AI matches, two opponents with reversed sides, map.01.04 seed137 up to300s; not all-map, human, Android hardware or exported-binary proof.",
              "input_files": {str(p.relative_to(ROOT)).replace('\\', '/'): sha(p) for p in paths},
              "inputs": control["inputs"], "records": records}
    (QA / "visible-counter-comparison.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"passed": report["passed"], "errors": errors, "records": records}, ensure_ascii=False))
    raise SystemExit(0 if report["passed"] else 1)


if __name__ == "__main__":
    main()
