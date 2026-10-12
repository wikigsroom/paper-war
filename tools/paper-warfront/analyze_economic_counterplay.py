"""Verify the controlled paid economic-defense observations, not overall balance."""
import argparse
import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
POLICIES = {
    "passive": [], "recruit_on_sight": ["unit.yin.axe"],
    "lightning_on_sight": [],
    "formation_on_sight": ["unit.yin.axe"] * 2 + ["unit.yin.spear"] * 2,
    "early_formation": ["unit.yin.axe"] * 2 + ["unit.yin.spear"] * 2,
    "lightning_then_recruit": ["unit.yin.axe"],
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input", type=Path)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    data = json.loads(args.input.read_text(encoding="utf-8"))
    for key, digest in data["inputs"].items():
        assert hashlib.sha256((ROOT / "game" / key.removeprefix("res://")).read_bytes()).hexdigest() == digest, key
    expected = {(m, side, policy) for m in ["map.01.01", "map.01.04", "map.01.11"]
                for side in [0, 1] for policy in POLICIES}
    assert len(data["records"]) == 36
    assert {(r["map"], r["defender_side"], r["policy"]) for r in data["records"]} == expected
    balance = json.loads((ROOT / "game/data/balance-prototype.json").read_text(encoding="utf-8"))
    flat = []
    for row in data["records"]:
        policy = row["policy"]
        assert len(row["attacker_orders"]) == 2 and all(c["ok"] for c in row["attacker_orders"])
        if policy != "passive":
            assert row["response"]["ok"]
            if policy != "early_formation":
                assert row["response_at"] >= row["first_visible_at"]
            else:
                assert row["response_at"] == 0
        if "orders" in row["response"]:
            assert len(row["response"]["orders"]) == 4 and all(c["ok"] for c in row["response"]["orders"])
        if policy == "lightning_then_recruit":
            assert row["response"]["recruit"]["ok"]
        cost = sum(balance["units"][unit]["gold"] for unit in POLICIES[policy])
        assert row["stats"]["recruited"] == len(POLICIES[policy])
        assert abs(row["gold"] - (300 + row["gold_delivered"] - cost)) < .001
        spell_cost = balance["spells"]["spell.yin.lightning"]["mana"] if policy.startswith("lightning") else 0
        assert row["stats"]["mana_spent"] == spell_cost
        assert row["stats"]["casts"] == (1 if spell_cost else 0)
        for key in ["first_worker_hit_at", "first_worker_release_at", "first_worker_lost_at", "last_worker_lost_at"]:
            assert row[key] is None or 0 <= row[key] <= row["time"]
        flat.append({key: row[key] for key in ["map", "defender_side", "policy", "first_visible_at",
                    "first_worker_release_at", "first_worker_hit_at", "response_at", "response_unit_spawn_at",
                    "response_unit_attack_at", "first_worker_lost_at", "last_worker_lost_at", "worker_count",
                    "gold_delivered"]} | {"response_gold": cost, "response_mana": spell_cost})
    report = {"scope": data["scope"], "provenance_verified": True,
              "input_sha256": hashlib.sha256(args.input.read_bytes()).hexdigest(), "inputs": data["inputs"],
              "analyzer_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), "records": flat}
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    with args.output.with_suffix(".csv").open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(flat[0]))
        writer.writeheader()
        writer.writerows(flat)
    print(json.dumps({"verified_cases": len(flat), "all_workers_preserved": sum(r["worker_count"] == 2 for r in flat)}))


if __name__ == "__main__":
    main()
