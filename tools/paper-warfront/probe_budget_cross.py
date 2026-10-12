"""Observe all directed faction pairings with default and both-side budget AI."""
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


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--map", default="map.01.04")
    ap.add_argument("--seed", type=int, default=271)
    ap.add_argument("--seconds", type=int, default=300)
    ap.add_argument("--indices", help="Explicit directed pair indices; default all 100, including ten mirrors.")
    args = ap.parse_args()
    indices = sorted(set(map(int, args.indices.split(",")))) if args.indices else list(range(100))
    assert indices and all(0 <= i < 100 for i in indices) and 60 <= args.seconds <= 900
    output = args.output.resolve()
    assert output.is_relative_to(ROOT)
    output.mkdir(parents=True, exist_ok=True)
    sources = [*sorted((ROOT / "game/scripts").glob("*.gd")),
               *sorted((ROOT / "game/data").glob("*.json")),
               ROOT / "game/project.godot", ROOT / "game/tests/probe_faction_matchups.gd",
               Path(__file__), ROOT / "tools/paper-warfront/analyze_paid_opening.py",
               ROOT / "tools/paper-warfront/check_ai_engagement.py"]
    inputs = {}
    for source in sources:
        relative = source.relative_to(ROOT).as_posix()
        target = output / "source" / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        inputs[relative] = sha(source)
    (output / "source/snapshot.json").write_text(json.dumps({"inputs": inputs}, indent=2), encoding="utf-8")
    groups = [indices[start:start+10] for start in range(0, len(indices), 10)]

    def observe(job):
        policy, group = job
        folder = output / "chunks" / policy
        folder.mkdir(parents=True, exist_ok=True)
        dest = folder / (str(group[0]).zfill(2) + ".json")
        command = [str(ENGINE), "--headless", "--path", str(ROOT / "game"),
                   "--script", "res://tests/probe_faction_matchups.gd", "--",
                   "--indices", ",".join(map(str, group)), "--map", args.map,
                   "--seed", str(args.seed), "--duration-seconds", str(args.seconds),
                   "--timeline", "--sample-seconds", "10", "--investment-trace", "--combat-trace",
                   "--combat-trace-seconds", str(args.seconds), "--budget-decision-trace", "--output", str(dest)]
        if policy == "trial":
            command += ["--budget-planner-trial"]
        run = subprocess.run(command, cwd=ROOT, capture_output=True, encoding="utf-8", errors="replace", timeout=600)
        log = run.stdout + run.stderr
        dest.with_suffix(".log").write_text(log, encoding="utf-8")
        assert run.returncode == 0 and "SCRIPT ERROR" not in log and "ERROR:" not in log, log[-2000:]
        data = read(dest)
        assert {r["index"] for r in data["records"]} == set(group) and len(data["records"]) == len(group)
        assert data["experimental_ai_budget_planner"] == (policy == "trial")
        assert data["experimental_ai_budget_planner_side"] == -1
        for resource, expected in data["inputs"].items():
            assert inputs["game/" + resource.removeprefix("res://")] == expected
        return policy, dest, len(group)

    completed = {"baseline": 0, "trial": 0}
    paths = {"baseline": [], "trial": []}
    jobs = [(policy, group) for policy in ["baseline", "trial"] for group in groups]
    with ThreadPoolExecutor(max_workers=2) as pool:
        for future in as_completed([pool.submit(observe, job) for job in jobs]):
            policy, path, size = future.result()
            paths[policy].append(path)
            completed[policy] += size
            if completed[policy] % 20 == 0 or completed[policy] == len(indices):
                print(policy, completed[policy], "/", len(indices), "paid directed pairings recorded", flush=True)
    combined = {}
    for policy, files in paths.items():
        data = None
        rows = []
        for path in sorted(files):
            chunk = read(path)
            if data is None:
                data = {k: v for k, v in chunk.items() if k != "records"}
            else:
                assert data == {k: v for k, v in chunk.items() if k != "records"}
            rows += chunk["records"]
        assert len(rows) == len(indices) and {r["index"] for r in rows} == set(indices)
        data["records"] = sorted(rows, key=lambda r: r["index"])
        dest = output / (policy + ".json")
        dest.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        combined[policy] = dest
    analysis_path = output / "analysis.json"
    run = subprocess.run([sys.executable, str(ROOT / "tools/paper-warfront/analyze_paid_opening.py"),
                          "--baseline", str(combined["baseline"]), "--trial", str(combined["trial"]),
                          "--output", str(analysis_path), "--expected-count", str(len(indices)),
                          "--policy", "budget-planner", "--source-archive", str(output / "source")],
                         cwd=ROOT, capture_output=True, encoding="utf-8", errors="replace", timeout=180)
    (output / "analysis.log").write_text(run.stdout+run.stderr, encoding="utf-8")
    assert run.returncode == 0, run.stderr[-2000:]
    proof = read(analysis_path)
    assert proof["passed"] and all(sha(ROOT / relative) == expected for relative, expected in inputs.items())
    totals = {}
    for policy in ["baseline", "trial"]:
        rows = proof[policy]["records"]
        totals[policy] = {"west_wins": sum(r["winner"] == 0 for r in rows),
                          "east_wins": sum(r["winner"] == 1 for r in rows),
                          "draws": sum(r["winner"] == -1 for r in rows),
                          "unresolved": sum(r["winner"] == -2 for r in rows)}
        assert sum(totals[policy].values()) == len(indices)
        totals[policy].update({k: v for k, v in proof[policy]["totals"].items() if k != "unresolved"})
    report = {"provenance_passed": True, "default_policy_changed": False,
              "scope": "Native Windows CPU directed pairings at recorded map/seed/ceiling. Default AI on both sides versus opt-in budget AI on BOTH sides. Normal fees, research, mining, production, endpoint health and fog; no price pilot. Cohorts are actual paid births. Not human balance, GPU, campaign-wide or Android hardware acceptance.",
              "map": args.map, "seed": args.seed, "duration_seconds": args.seconds,
              "indices": indices, "fresh_observations": len(indices)*2, "totals": totals,
              "inputs": inputs, "analysis_sha256": sha(analysis_path),
              "chunks": [{"path": path.relative_to(ROOT).as_posix(), "sha256": sha(path)}
                         for files in paths.values() for path in sorted(files)]}
    (output / "comparison.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k not in {"inputs", "chunks", "indices"}}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
