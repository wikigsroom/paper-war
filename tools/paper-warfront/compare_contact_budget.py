"""Check matched R8/R9 paid observations without mixing balance and provenance."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CHANGED = "game/scripts/ai_budget_planner.gd"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--before", type=Path, required=True)
    parser.add_argument("--after", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    folders = [args.before.resolve(), args.after.resolve()]
    reports = [read(folder / "comparison.json") for folder in folders]
    assert all(r["passed"] and r["source_unchanged"] for r in reports)
    assert reports[0]["seed"] == reports[1]["seed"]
    assert reports[0]["duration_seconds"] == reports[1]["duration_seconds"]
    indices = sorted(set(reports[0]["indices"]) & set(reports[1]["indices"]))
    maps = sorted(set(p["map"] for p in reports[0]["comparisons"]) &
                  set(p["map"] for p in reports[1]["comparisons"]))
    assert indices and maps
    # The complete archived runtime includes pure command guards and modules
    # absent from older observer dependency lists. All must remain identical
    # except the declared recruitment policy revision.
    runtime = {key for key in reports[0]["inputs"]
               if key.startswith(("game/scripts/", "game/data/")) or
               key in {"game/project.godot", "game/tests/probe_faction_matchups.gd"}}
    assert runtime <= set(reports[1]["inputs"])
    changed = sorted(key for key in runtime
                     if reports[0]["inputs"][key] != reports[1]["inputs"][key])
    assert changed == [CHANGED], changed
    for folder, report in zip(folders, reports):
        for key in runtime:
            assert sha(folder / "source" / key) == report["inputs"][key]
    rows = []
    equal_controls = 0
    raw_files = []
    for map_id in maps:
        controls = []
        for folder in folders:
            path = folder / map_id / "baseline.json"
            data = read(path)
            controls.append({r["index"]: r for r in data["records"]})
            raw_files.append({"path": path.relative_to(ROOT).as_posix(), "sha256": sha(path)})
        for index in indices:
            assert controls[0][index] == controls[1][index], (map_id, index, "control changed")
            equal_controls += 1
        for policy, side in [("west", 0), ("east", 1)]:
            data = []
            proof = []
            for folder in folders:
                raw_path = folder / map_id / (policy + ".json")
                analysis_path = folder / map_id / ("analysis-" + policy + ".json")
                data.append(read(raw_path))
                proof.append(read(analysis_path))
                assert proof[-1]["passed"] and proof[-1]["selected_policy_side"] == side
                for path in [raw_path, analysis_path]:
                    raw_files.append({"path": path.relative_to(ROOT).as_posix(), "sha256": sha(path)})
            assert {k: v for k, v in data[0].items() if k not in {"records", "inputs"}} == \
                   {k: v for k, v in data[1].items() if k not in {"records", "inputs"}}
            lookup = [{r["index"]: r for r in p["trial"]["records"]} for p in proof]
            for index in indices:
                outcomes = []
                for records in lookup:
                    record = records[index]
                    own = record["sides"][side]
                    studies = [s for s in own["studies"] if s["completed"] is not None]
                    outcomes.append({
                        "winner": record["winner"], "end_seconds": record["end_seconds"],
                        "workers_including_queue": own["workers_including_queue"],
                        "cash": own["cash"], "base_hp": own["base_hp"],
                        "studies_completed": len(studies),
                        "studies_with_paid_orders": sum(s["paid_orders"] > 0 for s in studies),
                        "studies_with_first_hits": sum(s["first_cohort_hits"] > 0 for s in studies),
                        "first_cohort_hits": sum(s["first_cohort_hits"] for s in studies),
                        "research_gold_without_followup": sum(s["research_gold"] for s in studies if not s["paid_orders"]),
                    })
                rows.append({"map": map_id, "index": index, "side": side,
                             "faction": lookup[0][index]["sides"][side]["faction"],
                             "before": outcomes[0], "after": outcomes[1]})
    totals = {}
    for revision in ["before", "after"]:
        totals[revision] = {"wins": sum(r[revision]["winner"] == r["side"] for r in rows),
                            "losses": sum(r[revision]["winner"] == 1-r["side"] for r in rows),
                            "unresolved": sum(r[revision]["winner"] == -2 for r in rows),
                            "draws": sum(r[revision]["winner"] == -1 for r in rows)}
        for key in ["studies_completed", "studies_with_paid_orders", "studies_with_first_hits", "first_cohort_hits", "research_gold_without_followup"]:
            totals[revision][key] = sum(r[revision][key] for r in rows)
        totals[revision]["sides_without_workers_including_queue"] = sum(r[revision]["workers_including_queue"] == 0 for r in rows)
    out = args.output.resolve()
    assert out.is_relative_to(ROOT)
    out.parent.mkdir(parents=True, exist_ok=True)
    report = {"provenance_passed": True, "balance_accepted": False,
              "scope": "Same seed, fees, formal fog, observer and runtime except the one declared candidate planner. Matched CPU observations at their actual ceiling; no default-policy promotion, cross-faction, human, GPU or Android hardware acceptance.",
              "seed": reports[0]["seed"], "duration_seconds": reports[0]["duration_seconds"],
              "paired_trials": len(rows), "identical_control_conditions": equal_controls,
              "changed_runtime": changed, "fresh_after_observations": reports[1]["observation_count"],
              "totals": totals, "rows": rows, "sources": raw_files,
              "tool_sha256": sha(Path(__file__))}
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k not in {"rows", "sources", "tool_sha256"}}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
