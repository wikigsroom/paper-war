"""Compare actual paid study/deployment cohorts under identical native inputs."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def summarize(data, technology, balance):
    nodes = {n["id"]: n for n in technology["nodes"]}
    births = [event for row in data["records"] for event in row.get("combat_trace", []) if event["kind"] == "spawn"]
    origin_verified = bool(births) and all(event.get("origin") in {"production", "clone", "summon", "scripted"} for event in births)
    rows = []
    totals = dict(completed_unit_studies=0, studies_with_paid_orders=0,
                  studies_with_first_spawns=0, studies_with_first_hits=0,
                  studies_with_first_specials=0, first_cohort_hits=0,
                  first_cohort_healing=0.0, research_gold_without_followup=0,
                  unresolved=0, sides_without_workers_including_queue=0)
    side_totals = [totals.copy(), totals.copy()]
    for record in data["records"]:
        sides = []
        for side, faction in enumerate([record["west"], record["east"]]):
            investments = record.get("investment_trace", [])
            combat = record.get("combat_trace", [])
            studies = []
            for start in investments:
                if start["side"] != side or start["kind"] != "research_start":
                    continue
                node = nodes[start["id"]]
                unit = node["grant"]
                if unit not in balance["units"]:
                    continue
                completed = next((e for e in investments if e["side"] == side
                                  and e["kind"] == "research_done" and e["id"] == unit
                                  and e["time"] >= start["time"]), None)
                if completed is None:
                    continue
                orders = [e for e in investments if e["side"] == side
                          and e["kind"] == "recruit" and e["id"] == unit
                          and e["time"] >= completed["time"]]
                first_order = orders[0] if orders else None
                seconds = balance["units"][unit].get("production_seconds", 2)
                spawn = next((e for e in combat if first_order and e["kind"] == "spawn"
                              and e.get("side") == side and e.get("id") == unit
                              and (not origin_verified or e["origin"] == "production")
                              and e["time"] >= first_order["time"] + seconds - .03), None)
                uid = spawn["uid"] if spawn else None
                hits = [e for e in combat if uid is not None and e["kind"] == "hit"
                        and e.get("source_uid") == uid and e.get("attacker_side") == side]
                heals = [e for e in combat if uid is not None and e["kind"] == "heal"
                         and e.get("source_uid") == uid and e.get("side") == side]
                specials = [e for e in combat if uid is not None and e["kind"] == "unit_special"
                            and e.get("uid") == uid and e.get("side") == side]
                healing = sum(e.get("amount", 0) for e in heals)
                studies.append(dict(tech=node["id"], unit=unit, research_gold=node["gold"],
                                    started=start["time"], completed=completed["time"],
                                    paid_orders=len(orders), first_order=first_order["time"] if first_order else None,
                                    first_spawn=spawn["time"] if spawn else None, first_paid_uid=uid,
                                    production_origin_verified=origin_verified,
                                    first_cohort_hits=len(hits), first_cohort_event_damage=sum(e.get("amount", 0) for e in hits),
                                    first_cohort_healing=healing, first_cohort_specials=len(specials),
                                    first_hit=hits[0]["time"] if hits else None))
                for bucket in [totals, side_totals[side]]:
                    bucket["completed_unit_studies"] += 1
                    bucket["studies_with_paid_orders"] += bool(orders)
                    bucket["studies_with_first_spawns"] += spawn is not None
                    bucket["studies_with_first_hits"] += bool(hits)
                    bucket["studies_with_first_specials"] += bool(specials)
                    bucket["first_cohort_hits"] += len(hits)
                    bucket["first_cohort_healing"] += healing
                    if not orders:
                        bucket["research_gold_without_followup"] += node["gold"]
            state = record["sides"][side]
            totals["sides_without_workers_including_queue"] += state["workers"] == 0
            side_totals[side]["sides_without_workers_including_queue"] += state["workers"] == 0
            sides.append(dict(faction=faction, workers_including_queue=state["workers"],
                              base_hp=state["base_hp"], cash=state["gold"],
                              delivered=state["stats"]["gold_delivered"], studies=studies))
        totals["unresolved"] += record["winner"] == -2
        for bucket in side_totals: bucket["unresolved"] += record["winner"] == -2
        rows.append(dict(index=record["index"], west=record["west"], east=record["east"],
                         winner=record["winner"], end_seconds=record["time"], sides=sides))
    return dict(totals=totals, records=rows, totals_by_side=side_totals, production_origin_verified=origin_verified)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--trial", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--expected-count", type=int, required=True)
    parser.add_argument("--source-archive", type=Path)
    parser.add_argument("--policy", choices=["paid-opening", "budget-planner"], default="paid-opening")
    args = parser.parse_args()
    baseline = json.loads(args.baseline.read_text(encoding="utf-8"))
    trial = json.loads(args.trial.read_text(encoding="utf-8"))
    assert baseline["inputs"] == trial["inputs"], "Mixed revisions cannot be compared"
    for field in ["map", "seed", "duration_seconds", "combat_trace_seconds"]:
        assert baseline[field] == trial[field], "Different conditions: " + field
    assert baseline["combat_trace_seconds"] == baseline["duration_seconds"], "Contribution trace must cover the observation"
    assert {r["index"] for r in baseline["records"]} == {r["index"] for r in trial["records"]}, "Incomplete pairing coverage"
    assert len({r["index"] for r in trial["records"]}) == len(trial["records"]), "Duplicate observations"
    assert len(trial["records"]) == args.expected_count > 0, "Observation batch is incomplete"
    # Import only at CLI entry so summarize remains usable from read-only tools.
    from check_ai_engagement import experimental_policy_fields
    policies = {
        "paid-opening": {"experimental_ai_paid_opening", "experimental_paid_opening_side", "experimental_paid_opening_faction"},
        "budget-planner": {"experimental_ai_budget_planner", "experimental_ai_budget_planner_side"},
    }
    flag = "experimental_ai_paid_opening" if args.policy == "paid-opening" else "experimental_ai_budget_planner"
    assert baseline.get(flag) is False and trial.get(flag) is True, "Comparison must switch the selected policy"
    assert not experimental_policy_fields(baseline), "Baseline must have all experimental policies disabled"
    assert set(experimental_policy_fields(trial)) <= policies[args.policy], "Unrelated active trial treatment"
    for field in set(baseline) | set(trial):
        if field.startswith("experimental_") and field not in policies[args.policy]:
            assert trial.get(field) == baseline.get(field), "Unrelated trial pilot: " + field
    source_root = args.source_archive.resolve() if args.source_archive else ROOT
    verified = {}
    for resource, expected in baseline["inputs"].items():
        relative = "game/" + resource.removeprefix("res://")
        path = source_root / relative
        assert path.is_file() and digest(path) == expected, "Input differs: " + relative
        verified[relative] = expected
    technology = json.loads((source_root / "game/data/technology.json").read_text(encoding="utf-8"))
    balance = json.loads((source_root / "game/data/balance-prototype.json").read_text(encoding="utf-8"))
    summaries = {"baseline": summarize(baseline, technology, balance),
                 "trial": summarize(trial, technology, balance)}
    if args.policy == "budget-planner":
        assert all(summary["production_origin_verified"] for summary in summaries.values()), "Budget comparison requires paid-production birth origins; clone births are not recruitment"
    for data in [baseline, trial]:
        nodes = {node["id"]: node for node in technology["nodes"]}
        for row in data["records"]:
            for event in row.get("investment_trace", []):
                if "gold_spent" not in event:
                    assert args.policy == "paid-opening", "Current budget traces must record actual fee amounts"
                    continue
                expected = (nodes[event["id"]]["gold"] if event["kind"] == "research_start"
                            else balance["units"][event["id"]]["gold"] if event["kind"] == "recruit" else 0)
                assert event["gold_spent"] == expected, "Observation differs from recorded normal prices"
    result = dict(passed=True,
                  policy=args.policy,
                  scope="Same-input native Windows paid AI observations. Birth-origin fields verify paid production when present; older records without origins retain a legacy spawn estimate and explicitly report production_origin_verified=false. Later actors are not added to the selected cohort. Zero workers includes queued orders. Unresolved is an observation limit, not a draw. No human, original-HD, Android or full-balance claim.",
                  conditions={k:baseline[k] for k in ["map", "seed", "duration_seconds"]},
                  coverage=len(trial["records"]), inputs=verified,
                  sources={str(p.resolve()):digest(p) for p in [args.baseline, args.trial]},
                  **summaries)
    selector = "experimental_paid_opening_side" if args.policy == "paid-opening" else "experimental_ai_budget_planner_side"
    selected_side = trial.get(selector, -1)
    if selected_side in [0, 1]:
        result["selected_policy_side"] = selected_side
        result["baseline_policy_side_totals"] = summaries["baseline"]["totals_by_side"][selected_side]
        result["trial_policy_side_totals"] = summaries["trial"]["totals_by_side"][selected_side]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"passed":True,"coverage":result["coverage"],"selected_policy_side":result.get("selected_policy_side"),
                      "baseline":result.get("baseline_policy_side_totals",result["baseline"]["totals"]),
                      "trial":result.get("trial_policy_side_totals",result["trial"]["totals"])}, ensure_ascii=False))


if __name__ == "__main__":
    main()
