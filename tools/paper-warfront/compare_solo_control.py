"""Compare formal spell utility on complete archived paid match inputs."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CHANGED = "game/scripts/tactical_ai.gd"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def summary(record):
    return {"winner": record["winner"], "seconds": record["end_seconds"],
            "sides": [{"faction": s["faction"], "workers": s["workers_including_queue"],
                       "base_hp": s["base_hp"], "cash": s["cash"],
                       "unit_studies": len(s["studies"]),
                       "studies_paid": sum(t["paid_orders"] > 0 for t in s["studies"]),
                       "studies_hit": sum(t["first_cohort_hits"] > 0 for t in s["studies"])}
                      for s in record["sides"]]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--before", type=Path, required=True)
    parser.add_argument("--after", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    folders = [args.before.resolve(), args.after.resolve()]
    reports = [read(f / "comparison.json") for f in folders]
    assert all(r["passed"] and r["source_unchanged"] for r in reports)
    assert reports[0]["seed"] == reports[1]["seed"]
    assert reports[0]["duration_seconds"] == reports[1]["duration_seconds"]
    indices = sorted(set(reports[0]["indices"]) & set(reports[1]["indices"]))
    maps = sorted(set(p["map"] for p in reports[0]["comparisons"]) &
                  set(p["map"] for p in reports[1]["comparisons"]))
    assert indices and maps
    runtime = {k for k in reports[0]["inputs"]
               if k.startswith(("game/scripts/", "game/data/")) or
               k in {"game/project.godot", "game/tests/probe_faction_matchups.gd"}}
    assert runtime <= set(reports[1]["inputs"])
    assert sorted(k for k in runtime if reports[0]["inputs"][k] != reports[1]["inputs"][k]) == [CHANGED]
    for folder, report in zip(folders, reports):
        assert all(sha(folder / "source" / k) == report["inputs"][k] for k in runtime)
    rows = []
    proofs = []
    for map_id in maps:
        for policy in ["baseline", "west", "east"]:
            raw = [read(f / map_id / (policy + ".json")) for f in folders]
            # Both sides' spell utility changes, so legacy controls may also
            # change. Mechanical settings, fees, mining and fog must match.
            settings = [{k: v for k, v in r.items() if k not in {"records", "inputs"}} for r in raw]
            assert settings[0] == settings[1]
            key = "east" if policy == "east" else "west"
            paths = [f / map_id / ("analysis-" + key + ".json") for f in folders]
            data = [read(p) for p in paths]
            assert all(d["passed"] for d in data)
            group = "baseline" if policy == "baseline" else "trial"
            records = [{r["index"]: r for r in d[group]["records"]} for d in data]
            assert set(indices) <= set(records[0]) & set(records[1])
            for index in indices:
                rows.append({"map": map_id, "policy": policy, "index": index,
                             "before": summary(records[0][index]),
                             "after": summary(records[1][index])})
            proofs += [{"path": p.relative_to(ROOT).as_posix(), "sha256": sha(p)} for p in paths]
    report = {"provenance_passed": True, "changed_runtime": [CHANGED],
              "seed": reports[0]["seed"], "duration_seconds": reports[0]["duration_seconds"],
              "matched_observations": len(rows), "rows": rows, "proofs": proofs,
              "tool_sha256": sha(Path(__file__)), "balance_accepted": False,
              "scope": "Formal spell-utility change on both sides, not candidate-planner promotion. Matched CPU conditions with normal fees, production, transport and fog. Default controls may change legitimately. No human, GPU, all-faction or Android hardware acceptance."}
    output = args.output.resolve()
    assert output.is_relative_to(ROOT)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k not in {"proofs", "rows"}}, ensure_ascii=False))


if __name__ == "__main__":
    main()
