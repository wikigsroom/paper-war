"""Compare paid context-research observations with strict current-source provenance."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
QA = ROOT / "output/qa/godot/core-alignment-rc14"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    control_path, trial_path = QA / "context-control.json", QA / "context-trial.json"
    control = json.loads(control_path.read_text(encoding="utf-8"))
    trial = json.loads(trial_path.read_text(encoding="utf-8"))
    errors = []
    for name, data in [("control", control), ("trial", trial)]:
        for path, expected in data["inputs"].items():
            if sha(ROOT / "game" / path.removeprefix("res://")) != expected:
                errors.append(f"{name}: stale {path}")
        if not {"res://scripts/tactical_ai.gd", "res://scripts/battle_sim.gd",
                "res://tests/probe_faction_matchups.gd", "res://data/technology.json"}.issubset(data["inputs"]):
            errors.append(f"{name}: missing critical source inputs")
        if {r["index"] for r in data["records"]} != {59, 95} or len(data["records"]) != 2:
            errors.append(f"{name}: incomplete side-mirrored observations")
    if control["inputs"] != trial["inputs"]:
        errors.append("Control and trial did not use identical source inputs")
    for key in ["map", "seed", "duration_seconds", "combat_trace_seconds",
                "sample_seconds", "experimental_price_overrides", "experimental_map_removed_edges"]:
        if control[key] != trial[key]:
            errors.append(f"Mismatched conditions: {key}")
    active_control = {k: v for k, v in control.items() if k.startswith("experimental_") and v}
    active_trial = {k: v for k, v in trial.items() if k.startswith("experimental_") and v}
    if active_control:
        errors.append("Control contains an active experimental policy")
    if active_trial != {"experimental_ai_context_research": True,
                        "experimental_context_research_faction": "qi"}:
        errors.append("Trial contains unexpected policy changes")
    records = []
    for base, candidate in zip(control["records"], trial["records"]):
        if (base["index"], base["west"], base["east"]) != (candidate["index"], candidate["west"], candidate["east"]):
            errors.append("Pair identity mismatch")
        side = 0 if base["west"] == "qi" else 1
        pair = {"index": base["index"], "west": base["west"], "east": base["east"],
                "records_identical": base == candidate, "qi_side": side}
        for label, row in [("control", base), ("trial", candidate)]:
            investments = row["investment_trace"]
            pair[label] = {
                "winner": row["winner"], "end_seconds": row["time"],
                "qi_workers": row["sides"][side]["workers"],
                "qi_base_hp": row["sides"][side]["base_hp"],
                "sniper_research_started": [e["time"] for e in investments if e["side"] == side and e["kind"] == "research_start" and e["id"] == "tech.qi.unit.sniper"],
                "sniper_research_completed": [e["time"] for e in investments if e["side"] == side and e["kind"] == "research_done" and e["id"] == "unit.qi.sniper"],
                "paid_sniper_orders": sum(e["kind"] == "recruit" and e["id"] == "unit.qi.sniper" and e["side"] == side for e in investments),
                "sniper_spawns": sum(e["kind"] == "spawn" and e.get("id") == "unit.qi.sniper" and e.get("side") == side for e in row["combat_trace"]),
                "sniper_hit_events": sum(e["kind"] == "hit" and e.get("source_id") == "unit.qi.sniper" and e.get("attacker_side") == side for e in row["combat_trace"]),
            }
        records.append(pair)
    report = {"passed": not errors, "errors": errors,
              "scope": "Two side-mirrored pairs on map.01.04, seed 137, up to 300s, normal paid research/production and fog. Source mechanism evidence only; not human/full-map balance or exported binaries.",
              "source_files": {str(p.relative_to(ROOT)).replace('\\', '/'): sha(p) for p in [control_path, trial_path]},
              "inputs": control["inputs"], "records": records}
    (QA / "context-comparison.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"passed": report["passed"], "errors": errors, "records": records}, ensure_ascii=False))
    raise SystemExit(0 if report["passed"] else 1)


if __name__ == "__main__":
    main()
