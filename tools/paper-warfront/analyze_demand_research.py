"""Audit demand-research ablations, normal payments and researched-unit contribution."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
QA = ROOT / "output/qa/godot/core-alignment-rc14/demand-research"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def unit_investments(row, side, technology):
    events = [e for e in row["investment_trace"] if e["side"] == side]
    investments = []
    for event in events:
        if event["kind"] != "research_start":
            continue
        node = technology[event["id"]]
        grant = node["grant"]
        if not grant.startswith("unit."):
            continue
        completed = [e["time"] for e in events if e["kind"] == "research_done" and e["id"] == grant and e["time"] >= event["time"]]
        paid = [e["time"] for e in events if e["kind"] == "recruit" and e["id"] == grant and e["time"] >= event["time"]]
        spawned = [e["time"] for e in row["combat_trace"] if e["kind"] == "spawn" and e.get("id") == grant and e.get("side") == side and e["time"] >= event["time"]]
        hits = [e for e in row["combat_trace"] if e["kind"] == "hit" and e.get("source_id") == grant and e.get("attacker_side") == side and e["time"] >= event["time"]]
        investments.append({"tech": node["id"], "unit": grant, "research_gold": node["gold"],
                            "started_seconds": event["time"], "completed_seconds": completed,
                            "paid_order_seconds": paid, "spawn_seconds": spawned,
                            "hit_events": len(hits), "event_damage": sum(e.get("amount", 0) for e in hits)})
    return investments


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds", nargs="+", type=int, default=[137])
    parser.add_argument("--deployment-ablation", action="store_true")
    parser.add_argument("--ai-archive", type=Path)
    parser.add_argument("--probe-archive", type=Path)
    args = parser.parse_args()
    if bool(args.ai_archive) != bool(args.probe_archive):
        parser.error("Historical replay requires both exact AI and probe archives")
    archived = {"res://scripts/tactical_ai.gd": args.ai_archive, "res://tests/probe_faction_matchups.gd": args.probe_archive} if args.ai_archive else {}
    qa = ROOT / "output/qa/godot/core-alignment-rc14/demand-deployment" if args.deployment_ablation else QA
    labels = ["study-only", "study-deploy"] if args.deployment_ablation else ["control", "trial"]
    technology = {n["id"]: n for n in json.loads((ROOT / "game/data/technology.json").read_text(encoding="utf-8"))["nodes"]}
    records, errors, files = [], [], {}
    for seed in args.seeds:
        paths = [qa / f"{label}{seed}.json" for label in labels]
        control, trial = [json.loads(p.read_text(encoding="utf-8")) for p in paths]
        for path in paths:
            files[str(path.relative_to(ROOT)).replace('\\', '/')] = sha(path)
        for label, data in [("control", control), ("trial", trial)]:
            if len(data["records"]) != 4 or {r["index"] for r in data["records"]} != {15, 51, 59, 95}:
                errors.append(f"{seed}/{label}: incomplete pair set")
            for path, expected in data["inputs"].items():
                if sha(archived.get(path, ROOT / "game" / path.removeprefix("res://"))) != expected:
                    errors.append(f"{seed}/{label}: stale source {path}")
            if data["seed"] != seed or data["map"] != "map.01.04" or data["duration_seconds"] != 300 or data["combat_trace_seconds"] != 300:
                errors.append(f"{seed}/{label}: unexpected observation conditions")
        if control["inputs"] != trial["inputs"]:
            errors.append(f"{seed}: mismatched sources")
        active = lambda d: {k: v for k, v in d.items() if k.startswith("experimental_") and v}
        expected_study = {"experimental_ai_demand_research": True, "experimental_demand_research_faction": "qi"}
        expected_trial = expected_study | ({"experimental_ai_demand_deployment": True, "experimental_demand_deployment_faction": "qi"} if args.deployment_ablation else {})
        if active(control) != (expected_study if args.deployment_ablation else {}) or active(trial) != expected_trial:
            errors.append(f"{seed}: unexpected ablation policies")
        for base, candidate in zip(control["records"], trial["records"]):
            if [base[k] for k in ["index", "west", "east"]] != [candidate[k] for k in ["index", "west", "east"]]:
                errors.append(f"{seed}: mismatched pair identity")
            side = 0 if base["west"] == "qi" else 1
            pair = {"seed": seed, "index": base["index"], "west": base["west"], "east": base["east"], "qi_side": side}
            for label, row in [("control", base), ("trial", candidate)]:
                investments = unit_investments(row, side, technology)
                pair[label] = {"winner": row["winner"], "end_seconds": row["time"],
                               "workers": row["sides"][side]["workers"], "base_hp": row["sides"][side]["base_hp"],
                               "investments": investments,
                               "research_gold_without_followup_order": sum(i["research_gold"] for i in investments if i["completed_seconds"] and not i["paid_order_seconds"])}
            records.append(pair)
    report = {"passed": not errors, "errors": errors, "seeds": args.seeds, "files": files, "deployment_ablation": args.deployment_ablation,
              "source_mode": "historical_archives" if archived else "current",
              "source_archives": {key: {"path": str(path), "sha256": sha(path)} for key, path in archived.items()},
              "scope": "Current-source qi-only research-policy ablation, two opponents reversed sides, map.01.04 up to300s, normal gold/research/fog; hit damage is recorded event amount, not net causal benefit or whole-game balance.",
              "records": records}
    (qa / "comparison.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"passed": report["passed"], "errors": errors, "pairs": len(records),
                      "results": [{"seed": r["seed"], "index": r["index"], **{label: {"winner": r[label]["winner"], "end_seconds": r[label]["end_seconds"], "workers": r[label]["workers"], "base_hp": r[label]["base_hp"], "research_without_order_gold": r[label]["research_gold_without_followup_order"], "paid_orders": sum(len(i["paid_order_seconds"]) for i in r[label]["investments"]), "spawns": sum(len(i["spawn_seconds"]) for i in r[label]["investments"]), "hits": sum(i["hit_events"] for i in r[label]["investments"])} for label in ["control", "trial"]}} for r in records]}, ensure_ascii=False))
    raise SystemExit(0 if report["passed"] else 1)


if __name__ == "__main__":
    main()
