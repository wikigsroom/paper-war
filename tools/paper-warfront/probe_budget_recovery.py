"""Compare real-fee budget AI on both sides of three road lengths, natively."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
ENGINE = ROOT / ".tools/godot/Godot_v4.7.2-stable_win64_console.exe"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--seed", type=int, default=271)
    ap.add_argument("--seconds", type=int, default=300)
    ap.add_argument("--maps", default="map.01.01,map.01.04,map.01.11")
    ap.add_argument("--indices", help="Comma-separated same-faction mirror indices for a focused regression; default all ten mirrors.")
    ap.add_argument("--runtime", type=Path, default=ROOT/"game", help="Native source project to observe, including a complete archived runtime for a matched control.")
    args = ap.parse_args()
    assert 60 <= args.seconds <= 900
    qa = args.output.resolve()
    qa.mkdir(parents=True, exist_ok=True)
    runtime = args.runtime.resolve()
    assert runtime.is_relative_to(ROOT) and (runtime/"project.godot").is_file()
    def source_for(relative):
        return runtime/relative.removeprefix("game/") if relative.startswith("game/") else ROOT/relative
    maps = list(dict.fromkeys(args.maps.split(",")))
    indices = list(range(0,100,11)) if not args.indices else sorted(set(map(int,args.indices.split(","))))
    assert indices and all(0<=i<100 and i//10==i%10 for i in indices),"Select authored same-faction mirror indices"
    # The probe records these authored sources; cache the exact input revision
    # before any observations so later work cannot rewrite their meaning.
    # Snapshot the complete runtime script/data inputs, including new shared
    # command gates. An old report's dependency list cannot cover new modules.
    resources = ["res://"+p.relative_to(runtime).as_posix()
                 for p in [*sorted((runtime/"scripts").glob("*.gd")),
                           *sorted((runtime/"data").glob("*.json")),
                           runtime/"tests/probe_faction_matchups.gd",runtime/"project.godot"]]
    inputs = {}
    for resource in resources:
        relative = "game/" + resource.removeprefix("res://")
        source = source_for(relative).resolve()
        assert source.is_relative_to(runtime)
        target = qa / "source" / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        inputs[relative] = sha(source)
    for relative in ["game/tests/test_ai_budget_recovery.gd", "game/tests/test_ai_budget_planner.gd", "game/tests/test_ai_contact_funding.gd", "game/tests/test_ai_income_staging.gd",
                     "tools/paper-warfront/probe_budget_recovery.py", "tools/paper-warfront/analyze_paid_opening.py",
                     "tools/paper-warfront/check_ai_engagement.py"]:
        source = source_for(relative)
        if not source.is_file():
            assert relative=="game/tests/test_ai_income_staging.gd", "Missing archived evidence source: "+relative
            continue
        target = qa / "source" / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        inputs[relative] = sha(source)
    (qa / "source/snapshot.json").write_text(json.dumps({"inputs": inputs}, indent=2), encoding="utf-8")

    def observe(job):
        map_id, policy = job
        folder = qa / map_id
        folder.mkdir(parents=True, exist_ok=True)
        dest = folder / (policy + ".json")
        command = [str(ENGINE), "--headless", "--path", str(runtime),
                   "--script", "res://tests/probe_faction_matchups.gd", "--", "--mirrors",
                   "--indices", ",".join(map(str,indices)),
                   "--map", map_id, "--seed", str(args.seed), "--duration-seconds", str(args.seconds),
                   "--timeline", "--sample-seconds", "10", "--investment-trace", "--combat-trace",
                   "--combat-trace-seconds", str(args.seconds), "--budget-decision-trace", "--output", str(dest)]
        if policy != "baseline":
            command += ["--budget-planner-trial", "--budget-planner-side", "0" if policy == "west" else "1"]
        result = subprocess.run(command, cwd=ROOT, capture_output=True, encoding="utf-8", errors="replace", timeout=600)
        log = result.stdout + result.stderr
        dest.with_suffix(".log").write_text(log, encoding="utf-8")
        assert result.returncode == 0 and "SCRIPT ERROR" not in log and "ERROR:" not in log, log[-2000:]
        data = json.loads(dest.read_text(encoding="utf-8"))
        assert len(data["records"]) == len(indices) and {r["index"] for r in data["records"]} == set(indices)
        assert data["map"] == map_id and data["seed"] == args.seed and data["duration_seconds"] == args.seconds
        for resource, expected in data["inputs"].items():
            assert inputs["game/" + resource.removeprefix("res://")] == expected
        print(map_id, policy, str(len(indices))+" paid observations verified", flush=True)
        return map_id, policy, dest

    jobs = [(map_id, policy) for map_id in maps for policy in ["baseline", "west", "east"]]
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(observe, job) for job in jobs]
        for future in as_completed(futures):
            future.result()
    pairs = []
    for map_id in maps:
        folder = qa / map_id
        for policy, side in [("west", 0), ("east", 1)]:
            analysis = folder / ("analysis-" + policy + ".json")
            result = subprocess.run([sys.executable, str(ROOT / "tools/paper-warfront/analyze_paid_opening.py"),
                                     "--baseline", str(folder / "baseline.json"), "--trial", str(folder / (policy + ".json")),
                                     "--output", str(analysis), "--expected-count", str(len(indices)), "--policy", "budget-planner",
                                     "--source-archive", str(qa / "source")], cwd=ROOT, capture_output=True,
                                    encoding="utf-8", errors="replace", timeout=90)
            analysis.with_suffix(".log").write_text(result.stdout + result.stderr, encoding="utf-8")
            assert result.returncode == 0, result.stderr[-2000:]
            proof = json.loads(analysis.read_text(encoding="utf-8"))
            assert proof["passed"] and proof["selected_policy_side"] == side
            counts = {}
            for key in ["baseline", "trial"]:
                records = proof[key]["records"]
                counts[key] = {"wins": sum(r["winner"] == side for r in records),
                               "losses": sum(r["winner"] == 1 - side for r in records),
                               "draws": sum(r["winner"] == -1 for r in records),
                               "unresolved": sum(r["winner"] == -2 for r in records)}
                assert sum(counts[key].values()) == len(records), "An outcome was omitted or counted twice"
                counts[key].update(proof[key + "_policy_side_totals"])
            pairs.append({"map": map_id, "side": side, "analysis": analysis.relative_to(ROOT).as_posix(),
                          "analysis_sha256": sha(analysis), **counts})
    assert all(sha(source_for(relative)) == expected for relative, expected in inputs.items())
    report = {"passed": True, "source_unchanged": True, "seed": args.seed, "duration_seconds": args.seconds,
              "indices":indices,"runtime_origin":runtime.relative_to(ROOT).as_posix(),"observation_count": len(jobs) * len(indices), "comparisons": pairs, "inputs": inputs,
              "scope": "Native Windows CPU normal-fee AI mirrors; default control versus one-side opt-in budget policy, explicitly recorded faction indices/maps. Real mining/research/production, formal fog, first paid actor contributions. Not cross-faction balance, human usability, rendering or Android hardware acceptance."}
    (qa / "comparison.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"passed": True, "observation_count": report["observation_count"], "comparisons": pairs}), flush=True)


if __name__ == "__main__":
    main()
