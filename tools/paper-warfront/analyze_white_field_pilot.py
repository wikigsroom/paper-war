"""Verify an explicitly non-shipping AI policy comparison against paid baselines."""
import hashlib, json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
QA = ROOT / "output/qa/godot/core-alignment-rc9"
rows = []
for label in ("short", "medium", "long"):
    reports = {}
    for arm in ("baseline", "hold"):
        report = json.loads((QA / f"white-{arm}-{label}271.json").read_text(encoding="utf-8"))
        assert report["experimental_white_hold_clone"] == (arm == "hold")
        assert not report["experimental_price_overrides"]
        assert not report["experimental_map_removed_edges"]
        assert [r["index"] for r in report["records"]] == [9, 90]
        for path, digest in report["inputs"].items():
            assert hashlib.sha256((ROOT / "game" / path.removeprefix("res://")).read_bytes()).hexdigest() == digest, path
        reports[arm] = report
    reference = json.loads((QA / f"research-feedback-{label}271.json").read_text(encoding="utf-8"))
    expected = [r for r in reference["records"] if r["index"] in (9, 90)]
    assert reports["baseline"]["records"] == expected, "Baseline must reproduce current paid match timelines"
    for before, after in zip(reports["baseline"]["records"], reports["hold"]["records"]):
        side = 0 if before["west"] == "bai" else 1
        assert after["sides"][side]["stats"].get("spell_counts", {}).get("spell.bai.clone", 0) == 0
        rows.append({"map": label, "index": before["index"], "baseline_winner": before["winner"], "pilot_winner": after["winner"], "baseline_seconds": before["time"], "pilot_seconds": after["time"], "pilot_spells": after["sides"][side]["stats"].get("spell_counts", {}), "baseline_workers": before["sides"][side]["workers"], "pilot_workers": after["sides"][side]["workers"]})
result = {"passed": True, "scope": "Six mirrored paid matches; baseline exactly reproduces current timeline. Clone withholding is test-only and rejected, not formal balance or human play evidence.", "rows": rows}
(QA / "white-field-pilot-summary271.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
print("WHITE_FIELD_PILOT: verified 6 paired matches, current hashes and exact baseline timelines")
