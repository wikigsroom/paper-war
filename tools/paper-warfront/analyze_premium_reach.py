"""Verify paid executioner price/reach ablations and actual battle contribution."""
import argparse
import hashlib
import json
from pathlib import Path

from analyze_demand_research import unit_investments

ROOT = Path(__file__).resolve().parents[2]
QA = ROOT / "output/qa/godot/core-alignment-rc14/premium-reach"
UNIT = "unit.qi.executioner"
INDICES = {15, 51, 59, 95}
POLICY = {
    "experimental_ai_demand_research": True,
    "experimental_demand_research_faction": "qi",
    "experimental_ai_demand_deployment": True,
    "experimental_demand_deployment_faction": "qi",
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds", type=int, nargs="+", default=[137])
    parser.add_argument("--mid-only", action="store_true")
    parser.add_argument("--source-archive", type=Path, help="Exact pre-change game source directory for historical evidence")
    args = parser.parse_args()
    source_root = args.source_archive or ROOT / "game"
    technology = {n["id"]: n for n in json.loads((source_root / "data/technology.json").read_text(encoding="utf-8"))["nodes"]}
    maps = [("", "map.01.04", ["control", "price", "reach", "both"])]
    if not args.mid_only:
        maps += [("short-", "map.01.01", ["control", "both"]), ("long-", "map.01.11", ["control", "both"])]
    errors, files, records = [], {}, []
    for seed in args.seeds:
        for prefix, map_id, variants in maps:
            reports = {}
            for variant in variants:
                path = QA / f"{prefix}{variant}{seed}.json"
                if not path.exists():
                    errors.append(f"Missing completed observation: {path.name}")
                    continue
                data = json.loads(path.read_text(encoding="utf-8"))
                files[str(path.relative_to(ROOT)).replace("\\", "/")] = sha(path)
                reports[variant] = data
                if len(data["records"]) != len(INDICES) or {r["index"] for r in data["records"]} != INDICES:
                    errors.append(f"{path.name}: incomplete match set")
                for source, expected_hash in data["inputs"].items():
                    current = source_root / source.removeprefix("res://")
                    if not current.exists() or sha(current) != expected_hash:
                        errors.append(f"{path.name}: stale source {source}")
                if [data[k] for k in ["map", "seed", "duration_seconds", "combat_trace_seconds"]] != [map_id, seed, 300, 300]:
                    errors.append(f"{path.name}: different observation conditions")
                if not data["observe_ai_recruitment"]:
                    errors.append(f"{path.name}: missing actual recruitment decisions")
                expected = dict(POLICY)
                if variant in ["price", "both"]:
                    expected["experimental_price_overrides"] = {UNIT: 92}
                if variant in ["reach", "both"]:
                    expected["experimental_executioner_range"] = 1.25
                active = {k: v for k, v in data.items() if k.startswith("experimental_") and v}
                if active != expected:
                    errors.append(f"{path.name}: unexpected experimental settings")
                for row in data["records"]:
                    if row["winner"] == -2 and abs(row["time"] - 300) > .1:
                        errors.append(f"{path.name}/{row['index']}: unfinished observation")
            if set(reports) != set(variants):
                continue
            control = reports["control"]
            for variant, report in reports.items():
                if report["inputs"] != control["inputs"]:
                    errors.append(f"{map_id}/{seed}/{variant}: mismatched sources")
            rows_by_variant = {variant: {row["index"]: row for row in report["records"]} for variant, report in reports.items()}
            for index in sorted(INDICES):
                if any(index not in rows for rows in rows_by_variant.values()):
                    continue
                baseline = rows_by_variant["control"][index]
                side = 0 if baseline["west"] == "qi" else 1
                pair = {"map": map_id, "seed": seed, "index": index, "west": baseline["west"], "east": baseline["east"], "qi_side": side}
                for variant, rows in rows_by_variant.items():
                    row = rows[index]
                    if [row[k] for k in ["west", "east"]] != [baseline[k] for k in ["west", "east"]]:
                        errors.append(f"{map_id}/{seed}/{index}/{variant}: mismatched side assignments")
                    investments = unit_investments(row, side, technology)
                    executioner = [i for i in investments if i["unit"] == UNIT]
                    hits = [e for e in row["combat_trace"] if e["kind"] == "hit" and e.get("source_id") == UNIT and e.get("attacker_side") == side]
                    pair[variant] = {
                        "winner": row["winner"], "end_seconds": row["time"],
                        "workers": row["sides"][side]["workers"], "base_hp": row["sides"][side]["base_hp"],
                        "opponent_workers": row["sides"][1-side]["workers"], "opponent_base_hp": row["sides"][1-side]["base_hp"],
                        "investments": investments, "executioner": executioner,
                        "executioner_orders": sum(len(i["paid_order_seconds"]) for i in executioner),
                        "executioner_spawns": sum(len(i["spawn_seconds"]) for i in executioner),
                        "executioner_hits": len(hits), "executioner_event_damage": sum(e.get("amount", 0) for e in hits),
                        "executioner_victims": sorted({e.get("actor_id", "") for e in hits}),
                        "research_gold_without_followup_order": sum(i["research_gold"] for i in investments if i["completed_seconds"] and not i["paid_order_seconds"]),
                    }
                records.append(pair)
    report = {
        "passed": not errors, "errors": errors, "files": files, "records": records,
        "source_mode": "historical_archives" if args.source_archive else "current",
        "source_archive": str(args.source_archive) if args.source_archive else None,
        "scope": "Exact-input qi-only paid AI price/reach trial at pre-adoption balance. All controls already enable demand research and finite deployment memory; they are not the shipping default. Normal production, fog and mining remain. These experimental observations do not prove any subsequent build, net causal value, whole-game balance or hardware performance.",
    }
    (QA / "comparison.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"passed": report["passed"], "errors": errors, "pairs": len(records), "results": [
        {**{k: row[k] for k in ["map", "seed", "index"]}, **{
            variant: {k: row[variant][k] for k in ["winner", "end_seconds", "workers", "base_hp", "executioner_orders", "executioner_spawns", "executioner_hits", "executioner_event_damage", "executioner_victims"]}
            for variant in ["control", "price", "reach", "both"] if variant in row}}
        for row in records]}, ensure_ascii=False))
    raise SystemExit(0 if report["passed"] else 1)


if __name__ == "__main__":
    main()
