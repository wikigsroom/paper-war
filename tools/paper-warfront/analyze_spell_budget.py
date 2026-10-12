"""Keep official-cost observations separate from explicit runtime price pilots."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
QA = ROOT / "output/qa/godot/core-alignment-rc7"
SIX = {6, 8, 9, 60, 80, 90}
OTHER = {16, 18, 19, 26, 28, 29, 61, 62, 81, 82, 91, 92}
FILES = [
    ("faction-budget-middle137.json", SIX, None),
    ("faction-budget-short271.json", SIX, None),
    ("faction-budget-long271.json", SIX, None),
    ("faction-budget-other137.json", OTHER, None),
    ("faction-price-pilot-a137.json", SIX, "price-pilot-a.json"),
    ("faction-price-pilot-b137.json", SIX, "price-pilot-b.json"),
    ("faction-price-pilot-b-other137.json", OTHER, "price-pilot-b.json"),
]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    report = {"scope": "30 official-cost AI observations and 24 explicit price pilots; pilot outcomes are not shipping balance. Observation-limit outcomes are unresolved, not draws.",
              "files": [], "official": [], "price_pilots": []}
    for filename, expected, profile in FILES:
        path = QA / filename
        data = json.loads(path.read_text(encoding="utf-8"))
        assert len(data["records"]) == len(expected)
        assert {r["index"] for r in data["records"]} == expected
        for resource, digest in data["inputs"].items():
            assert sha(ROOT / "game" / resource.removeprefix("res://")) == digest, (filename, resource)
        overrides = data.get("experimental_price_overrides", {})
        expected_prices = json.loads((QA / profile).read_text(encoding="utf-8")) if profile else {}
        assert overrides == expected_prices
        target = report["price_pilots"] if profile else report["official"]
        for row in data["records"]:
            target.append({"file": filename, "map": data["map"], "seed": data["seed"],
                           "profile": profile, "index": row["index"], "west": row["west"],
                           "east": row["east"], "winner": row["winner"], "time": row["time"],
                           "sides": row["sides"]})
        report["files"].append({"file": filename, "sha256": sha(path), "records": len(data["records"]),
                                "runtime_price_overrides": overrides,
                                "profile_sha256": sha(QA / profile) if profile else None})
    summary = {}
    for label in ["official", "price_pilots"]:
        summary[label] = {}
        for faction in ["mu", "jin", "bai"]:
            rows = [r for r in report[label] if faction in [r["west"], r["east"]]]
            wins = sum(r["winner"] in [0, 1] and [r["west"], r["east"]][r["winner"]] == faction for r in rows)
            losses = sum(r["winner"] in [0, 1] and [r["west"], r["east"]][r["winner"]] != faction for r in rows)
            summary[label][faction] = {"observations": len(rows), "wins": wins,
                                       "losses": losses, "unresolved": len(rows) - wins - losses}
    report["summary"] = summary
    report["provenance_verified"] = True
    (QA / "spell-budget-observation-summary.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
