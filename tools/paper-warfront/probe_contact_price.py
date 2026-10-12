"""Isolate an explicitly experimental Jin starting-front price on both sides."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import copy
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

from analyze_paid_opening import summarize

ROOT = Path(__file__).resolve().parents[2]
ENGINE = ROOT / ".tools/godot/Godot_v4.7.2-stable_win64_console.exe"
UNIT = "unit.jin.berserker"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def fees(data, technology, balance):
    nodes = {node["id"]: node for node in technology["nodes"]}
    for row in data["records"]:
        for event in row["investment_trace"]:
            due = (nodes[event["id"]]["gold"] if event["kind"] == "research_start"
                   else balance["units"][event["id"]]["gold"] if event["kind"] == "recruit" else 0)
            assert event["gold_spent"] == due, (event, due)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--price", type=int, default=75)
    args = parser.parse_args()
    reference = args.reference.resolve()
    output = args.output.resolve()
    assert output.is_relative_to(ROOT) and 1 <= args.price < 125
    report = read(reference / "comparison.json")
    assert report["passed"] and report["source_unchanged"] and 88 in report["indices"]
    output.mkdir(parents=True, exist_ok=True)
    for relative, expected in report["inputs"].items():
        assert sha(ROOT / relative) == expected
        archived = reference / "source" / relative
        assert sha(archived) == expected
        target = output / "source" / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(archived, target)
    technology = read(output / "source/game/data/technology.json")
    balance = read(output / "source/game/data/balance-prototype.json")
    assert balance["units"][UNIT]["gold"] == 125
    trial_balance = copy.deepcopy(balance)
    trial_balance["units"][UNIT]["gold"] = args.price
    override = output / "overrides.json"
    override.write_text(json.dumps({UNIT: args.price}, indent=2), encoding="utf-8")
    tool_copy = output / "source/tools/paper-warfront/probe_contact_price.py"
    tool_copy.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(Path(__file__), tool_copy)
    maps = sorted({row["map"] for row in report["comparisons"]})

    def observe(job):
        map_id, policy = job
        folder = output / map_id
        folder.mkdir(parents=True, exist_ok=True)
        dest = folder / (policy + ".json")
        command = [str(ENGINE), "--headless", "--path", str(ROOT / "game"),
                   "--script", "res://tests/probe_faction_matchups.gd", "--", "--indices", "88",
                   "--map", map_id, "--seed", str(report["seed"]),
                   "--duration-seconds", str(report["duration_seconds"]),
                   "--timeline", "--sample-seconds", "10", "--investment-trace", "--combat-trace",
                   "--combat-trace-seconds", str(report["duration_seconds"]), "--budget-decision-trace",
                   "--price-overrides", str(override), "--output", str(dest)]
        if policy != "baseline":
            command += ["--budget-planner-trial", "--budget-planner-side", "0" if policy == "west" else "1"]
        run = subprocess.run(command, cwd=ROOT, capture_output=True, encoding="utf-8", errors="replace", timeout=180)
        log = run.stdout + run.stderr
        dest.with_suffix(".log").write_text(log, encoding="utf-8")
        assert run.returncode == 0 and "SCRIPT ERROR" not in log and "ERROR:" not in log, log[-2000:]
        trial = read(dest)
        assert len(trial["records"]) == 1 and trial["records"][0]["index"] == 88
        control_path = reference / map_id / (policy + ".json")
        control = read(control_path)
        control["records"] = [r for r in control["records"] if r["index"] == 88]
        assert len(control["records"]) == 1
        # The observer intentionally labels a price pilot as experimental;
        # verify that label explicitly while comparing every mechanical field.
        assert control["scope"].startswith("Paid AI-vs-AI baseline")
        assert trial["scope"].startswith("Experimental paid price pilot")
        assert {k: v for k, v in control.items() if k not in {"records", "scope", "experimental_price_overrides"}} == \
               {k: v for k, v in trial.items() if k not in {"records", "scope", "experimental_price_overrides"}}
        assert not control["experimental_price_overrides"] and trial["experimental_price_overrides"] == {UNIT: args.price}
        for resource, expected in trial["inputs"].items():
            assert report["inputs"]["game/" + resource.removeprefix("res://")] == expected
        summaries = []
        for data, prices in [(control, balance), (trial, trial_balance)]:
            fees(data, technology, prices)
            summary = summarize(data, technology, prices)
            assert summary["production_origin_verified"]
            summaries.append(summary)
        side = 0 if policy == "west" else 1 if policy == "east" else -1
        result = {"map": map_id, "policy": policy, "selected_side": side,
                  "native_exit": run.returncode, "log_sha256": sha(dest.with_suffix(".log")),
                  "control_path": control_path.relative_to(ROOT).as_posix(), "control_sha256": sha(control_path),
                  "trial_path": dest.relative_to(ROOT).as_posix(), "trial_sha256": sha(dest),
                  "before": summaries[0], "after": summaries[1]}
        if side >= 0:
            for branch, data, summary in zip(["before", "after"], [control, trial], summaries):
                own = data["records"][0]["sides"][side]
                result[branch + "_selected"] = {"winner": data["records"][0]["winner"],
                    "time": data["records"][0]["time"], "workers": own["workers"],
                    "cash": own["gold"], "base_hp": own["base_hp"], **summary["totals_by_side"][side]}
        print(map_id, policy, "explicit-price observation verified", flush=True)
        return result

    rows = []
    jobs = [(map_id, policy) for map_id in maps for policy in ["baseline", "west", "east"]]
    with ThreadPoolExecutor(max_workers=2) as pool:
        for future in as_completed([pool.submit(observe, job) for job in jobs]):
            rows.append(future.result())
    assert all(sha(ROOT / relative) == expected for relative, expected in report["inputs"].items())
    result = {"provenance_passed": True, "formal_price_changed": False,
              "scope": "Isolated CPU Jin mirrors. BOTH armies pay the same explicit 75-gold pilot price (or the requested recorded price), not a one-side subsidy. Original 125-gold reference uses the identical runtime and observer. Other unit/research fees, 300-gold starts, fog, mining, production and opponent policy remain unchanged. Not shipped balance, cross-faction or hardware acceptance.",
              "seed": report["seed"], "duration_seconds": report["duration_seconds"],
              "unit": UNIT, "formal_price": 125, "pilot_price": args.price,
              "fresh_observations": len(jobs), "reused_reference_conditions": len(jobs),
              "inputs": report["inputs"], "engine_sha256": sha(ENGINE),
              "override_sha256": sha(override), "tool_sha256": sha(Path(__file__)),
              "analysis_tool_sha256": sha(ROOT / "tools/paper-warfront/analyze_paid_opening.py"),
              "rows": sorted(rows, key=lambda r: (r["map"], r["policy"]))}
    (output / "comparison.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k not in {"inputs", "rows"}}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
