"""Verify full defender AI against paid fixed waves, without generalizing balance."""
import hashlib
import argparse
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
QA = ROOT / "output/qa/godot/core-alignment-rc10"
parser = argparse.ArgumentParser()
parser.add_argument("--input", default="sustained-full-ai-waves.json")
args = parser.parse_args()
data = json.loads((QA / args.input).read_text(encoding="utf-8"))
assert data["defender_full_tactical_ai"] and data["scripted_policy"] == "full_ai"
assert not data["experimental_legacy_formation"]
for path, digest in data["inputs"].items():
    assert hashlib.sha256((ROOT / "game" / path.removeprefix("res://")).read_bytes()).hexdigest() == digest, path
assert {(r["map"], r["side"]) for r in data["records"]} == {(m, s) for m in ("map.01.01", "map.01.04", "map.01.11") for s in (0, 1)}
rows = []
for r in data["records"]:
    if data.get("symmetric_start"):
        assert r["paid"] and abs(r["paid"][0]["time"] - 1 / 60) < 1e-6
    assert r["enemy_orders"] == len(r["enemy_paid"]) == 9
    for i, order in enumerate(r["enemy_paid"]):
        assert order["time"] + 1e-6 >= 18 + 25 * (i // 3)
        assert order["id"] == "unit.yin.axe" and order["gold"] == 45
    assert math.isclose(r["enemy_gold"], 300 + r["enemy_delivered"] - 405, abs_tol=1e-6)
    spent = sum(order["gold"] for order in r["paid"])
    assert math.isclose(r["gold"], 300 + r["delivered"] - spent, abs_tol=1e-6)
    assert r["stats"]["casts"] == len(r["spells"])
    assert r["stats"]["recruited"] == sum(order["kind"] == "recruit" for order in r["paid"])
    if "medic_trace" in r:
        assert data["medic_trace_sampling_seconds"] == 1
        balance = json.loads((ROOT / "game/data/balance-prototype.json").read_text(encoding="utf-8"))
        radius = balance["units"]["unit.mu.medic"]["heal_radius"]
        previous = {}
        for sample in r["medic_trace"]:
            uid = sample["uid"]
            if uid in previous:assert math.isclose(sample["time"] - previous[uid], 1, abs_tol=1e-6)
            previous[uid] = sample["time"]
            assert sample["hp"] > 0 and sample["eligible"] <= sample["hurt_allies"]
            if sample["eligible"]:assert 0 <= sample["nearest_hurt_distance"] <= radius
            if sample["nearest_hurt_distance"] > radius:assert sample["eligible"] == 0
    rows.append({key: r[key] for key in ("map", "side", "winner", "time", "workers", "enemy_base_hp", "paid", "spells")})
result = {"passed": True, "symmetric_start": data.get("symmetric_start", False), "experimental_ai_research_deployment": data.get("experimental_ai_research_deployment", False), "scope": "Six normal-budget full defender TacticalAI observations against scripted fixed paid axe waves. Explicit trial policy is not formal default AI evidence. Not full opponent AI, human or all-faction balance proof.", "rows": rows}
result["experimental_ai_support_arrival"] = data.get("experimental_ai_support_arrival", False)
if data.get("medic_trace_sampling_seconds"):
    result["medic_diagnostics"] = [{
        "map": r["map"], "side": r["side"], "purchase_context": r["medic_purchase_context"],
        "samples": len(r["medic_trace"]), "eligible_samples": sum(t["eligible"] > 0 for t in r["medic_trace"]),
        "hurt_samples": sum(t["hurt_allies"] > 0 for t in r["medic_trace"]),
        "nearest_sampled_hurt_distance": min([t["nearest_hurt_distance"] for t in r["medic_trace"] if t["nearest_hurt_distance"] >= 0] or [-1]),
        "healed": r["stats"]["healed"],
    } for r in data["records"]]
summary_name = "sustained-full-ai-symmetric-summary.json" if data.get("symmetric_start") else "sustained-full-ai-summary.json"
if args.input not in ("sustained-full-ai-waves.json", "sustained-full-ai-symmetric.json"):summary_name=Path(args.input).stem+"-summary.json"
(QA / summary_name).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
for r in rows:
    print(r["map"], r["side"], "winner", r["winner"], "workers", r["workers"], "enemy_base", r["enemy_base_hp"], "research", [o["id"] for o in r["paid"] if o["kind"] == "research"])
print("SUSTAINED_FULL_AI: six paid cases; both ledgers and wave timing verified")
