"""Verify and summarize isolated opening-tier unit purchase exchanges."""
import argparse
import hashlib
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    data = json.loads(args.input.read_text(encoding="utf-8"))
    for key, expected in data["inputs"].items():
        actual = ROOT / "game" / key.removeprefix("res://")
        if hashlib.sha256(actual.read_bytes()).hexdigest() != expected:
            raise ValueError("Changed source: " + key)
    balance = json.loads((ROOT / "game/data/balance-prototype.json").read_text(encoding="utf-8"))
    candidates = {k for k, u in balance["units"].items() if not u.get("economy") and u.get("manual_recruit") and u.get("tier") == 0}
    required = {(k, enemy, side) for k in candidates for enemy in ["unit.yin.axe", "unit.mo.blade"] for side in [0, 1]}
    observed = {(r["id"], r["opponent"], r["candidate_side"]) for r in data["records"]}
    if required != observed or len(data["records"]) != len(required):
        raise ValueError("Incomplete or duplicate opening exchange coverage")
    summary = {}
    for row in data["records"]:
        side = row["candidate_side"]
        if max(row["purchase_costs"]) > 300:
            raise ValueError("Purchase budget exceeded")
        result = "won" if row["survivors"][side] > 0 and row["survivors"][1-side] == 0 else "lost" if row["survivors"][side] == 0 and row["survivors"][1-side] > 0 else "mutual_death" if max(row["survivors"]) == 0 else "unresolved"
        entry = summary.setdefault(row["id"], {"won": 0, "lost": 0, "mutual_death": 0, "unresolved": 0, "observations": []})
        entry[result] += 1
        entry["observations"].append({"opponent": row["opponent"], "side": side, "result": result, "time": row["time"], "candidate_cost": row["purchase_costs"][side], "enemy_cost": row["purchase_costs"][1-side], "candidate_hp": row["hp"][side], "enemy_hp": row["hp"][1-side], "releases": row["attack_releases"][side]})
    report = {"scope": data["scope"], "provenance_verified": True, "complete": True, "records": len(required), "input_sha256": hashlib.sha256(args.input.read_bytes()).hexdigest(), "units": summary}
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"records": len(required), "units": {k: {x: v[x] for x in ["won", "lost", "mutual_death", "unresolved"]} for k, v in summary.items()}}))

if __name__ == "__main__":
    main()
