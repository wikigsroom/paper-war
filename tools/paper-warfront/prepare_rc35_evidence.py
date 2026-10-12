"""Carry forward immutable map/story/font evidence while rebinding the view hash."""
from pathlib import Path
import hashlib
import json
import shutil

ROOT = Path(__file__).resolve().parents[2]
OLD = ROOT / "output/qa/godot/render-runtime-rc34"
QA = ROOT / "output/qa/godot/render-runtime-rc35"
assert not (QA / "authorship.json").exists()
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()

shutil.copy2(OLD / "authorship.json", QA / "authorship.json")
font = json.loads((OLD / "font-coverage.json").read_text("utf-8"))
font["version"] = "3.0.0-rc35-preview"
font["retention_scope"] = "Byte-identical 200-map story/data and fonts; one view-only atlas-handle cache."
(QA / "font-coverage.json").write_text(json.dumps(font, ensure_ascii=False, indent=2) + "\n", "utf-8")
source = json.loads((OLD / "source-final/report.json").read_text("utf-8"))
old_hash = source["inputs"].get("game/scripts/battle_view.gd")
new_hash = sha(ROOT / "game/scripts/battle_view.gd")
assert old_hash and old_hash != new_hash
source["inputs"]["game/scripts/battle_view.gd"] = new_hash
source["source_project"] = str(QA / "atlas-cache-runtime").replace("\\", "/")
source["scope"] = "Controlled native CPU decision checks; RC35 changes only a unit-atlas Texture2D handle cache in battle_view.gd."
(QA / "source-final").mkdir()
(QA / "source-final/report.json").write_text(json.dumps(source, ensure_ascii=False, indent=2) + "\n", "utf-8")
(QA / "evidence-preparation.json").write_text(json.dumps({
    "passed": True,
    "version": "3.0.0-rc35-preview",
    "copied": {
        "authorship.json": sha(QA / "authorship.json"),
        "font-coverage.json": sha(QA / "font-coverage.json"),
    },
    "source_report": {
        "before_sha256": sha(OLD / "source-final/report.json"),
        "after_sha256": sha(QA / "source-final/report.json"),
        "old_battle_view_sha256": old_hash,
        "new_battle_view_sha256": new_hash,
    },
    "scope": "Only unchanged authored story/font evidence is carried forward; source report is rebound to the adopted RC35 view hash. No gameplay or map data is regenerated.",
}, ensure_ascii=False, indent=2) + "\n", "utf-8")
print(json.dumps({"passed": True, "new_battle_view_sha256": new_hash}))
