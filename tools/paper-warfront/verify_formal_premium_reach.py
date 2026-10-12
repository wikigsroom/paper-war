"""Audit the formal scythe reach fix against paid native events and GPU captures."""
import argparse
import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
QA = ROOT / "output/qa/godot/core-alignment-rc14/formal-reach"
UNIT = "unit.qi.executioner"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    global QA
    parser=argparse.ArgumentParser()
    parser.add_argument("--qa",type=Path,default=QA)
    QA=parser.parse_args().qa.resolve()
    errors, files, records = [], {}, []
    balance_path = ROOT / "game/data/balance-prototype.json"
    balance = json.loads(balance_path.read_text(encoding="utf-8"))
    formal = balance["units"][UNIT]
    if (formal["range"], formal["gold"]) != (1.25, 127):
        errors.append("Formal reach/price changed from reviewed selection")
    if balance_path.read_bytes() != (ROOT / "assets/paper-warfront/balance-prototype.json").read_bytes():
        errors.append("Runtime and canonical balance differ")
    brief = next(u for u in json.loads((ROOT / "assets/paper-warfront/frame-rebuild/unit-briefs.json").read_text(encoding="utf-8"))["units"] if u["id"] == UNIT)
    with (ROOT / "assets/paper-warfront/frame-rebuild/roster.csv").open(encoding="utf-8", newline="") as stream:
        row = next(u for u in csv.DictReader(stream) if u["id"] == UNIT)
    if brief["mechanics"].get("range") != formal["range"] or json.loads(row["mechanics"]).get("range") != formal["range"] or brief["hint"] != formal["hint"] or row["rule"] != formal["hint"]:
        errors.append("Scythe design/rule definitions differ from runtime")
    technology = json.loads((ROOT / "game/data/technology.json").read_text(encoding="utf-8"))["nodes"]
    study = next(n for n in technology if n["grant"] == UNIT)
    for name, map_id in [("short", "map.01.01"), ("mid", "map.01.04"), ("long", "map.01.11")]:
        path = QA / f"{name}-paid-exchange.json"
        report = json.loads(path.read_text(encoding="utf-8"))
        files[str(path.relative_to(ROOT)).replace("\\", "/")] = sha(path)
        if report["map"] != map_id or not report["formal_price_only"] or not report["reach_control"] or len(report["records"]) != 4:
            errors.append(f"{name}: incomplete or unexpected exchange configuration")
        for source, digest in report["inputs"].items():
            if sha(ROOT / "game" / source.removeprefix("res://")) != digest:
                errors.append(f"{name}: stale input {source}")
        recipes = {(r["premium_side"], r["reach"]): r for r in report["records"]}
        if set(recipes) != {(side, reach) for side in [0, 1] for reach in [.85, formal["range"]]}:
            errors.append(f"{name}: missing opposite-side price-constant controls")
            continue
        for side in [0, 1]:
            pair = {"map": map_id, "premium_side": side}
            for label, reach in [("legacy", .85), ("formal", formal["range"])]:
                recipe = recipes[side, reach]
                paid = [p for p in recipe["paid"] if p["side"] == side]
                completed = [e for e in recipe["events"] if e["kind"] == "research_done" and e.get("side") == side and e.get("id") == UNIT]
                orders = [p for p in paid if p["id"] == UNIT]
                spawned = [e for e in recipe["events"] if e["kind"] == "spawn" and e.get("side") == side and e.get("id") == UNIT]
                if recipe["errors"] or recipe["price"] != formal["gold"] or recipe["escorts"] != 1 or sum(p["gold"] for p in paid) != study["gold"] + formal["gold"] + balance["units"]["unit.qi.vanguard"]["gold"]:
                    errors.append(f"{name}/{side}/{label}: different or invalid actual investment")
                if len(completed) != 1 or len(orders) != 1 or len(spawned) != 1:
                    errors.append(f"{name}/{side}/{label}: missing actual research/order/spawn chain")
                    continue
                if completed[0]["time"] < study["seconds"] - .02 or orders[0]["time"] < completed[0]["time"] or spawned[0]["time"] < orders[0]["time"] + formal["production_seconds"] - .02:
                    errors.append(f"{name}/{side}/{label}: research/production timing bypassed")
                hits = [e for e in recipe["events"] if e["kind"] == "hit" and e.get("source_uid") == spawned[0]["uid"]]
                if len(hits) != recipe["premium_hit_events"] or not hits:
                    errors.append(f"{name}/{side}/{label}: premium hit trace mismatch")
                pair[label] = {"hit_events": len(hits), "event_damage": recipe["premium_event_damage"], "first_hit_seconds": hits[0]["time"] if hits else None,
                               "opponent_survivors": recipe["survivors"][1-side], "opponent_hp": recipe["hp"][1-side], "army_exchange_end_seconds": recipe["time"]}
            records.append(pair)
    for name in ["desktop", "phone"]:
        path = QA / "gpu" / name / "report.json"
        proof = json.loads(path.read_text(encoding="utf-8"))
        log = (path.parent / "runtime.log").read_text(encoding="utf-8")
        if not proof["passed"] or "SCRIPT ERROR" in log or "ERROR:" in log:
            errors.append(f"{name}: native GPU capture failed")
        for source, digest in proof["inputs"].items():
            if sha(ROOT / "game" / source.removeprefix("res://")) != digest:
                errors.append(f"{name}: stale GPU input {source}")
        files[str(path.relative_to(ROOT)).replace("\\", "/")] = sha(path)
        for capture in proof["captures"]:
            image = path.parent / capture["path"]
            if not image.exists() or image.stat().st_size < 1000:
                errors.append(f"{name}: missing actual capture {capture['path']}")
            else:
                files[str(image.relative_to(ROOT)).replace("\\", "/")] = sha(image)
    result = {"passed": not errors, "errors": errors, "files": files, "records": records,
              "scope": "Formal source reach at original price; 12 ordinary paid scripted recipes on three roads, exact investment/production/spawn/hit chains and two native GPU excerpts. Does not prove default AI improvement, exported builds, all-faction balance, realtime FPS, human play or Android hardware."}
    (QA / "verification.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"passed": result["passed"], "errors": errors, "pairs": len(records), "results": records}, ensure_ascii=False))
    raise SystemExit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()
