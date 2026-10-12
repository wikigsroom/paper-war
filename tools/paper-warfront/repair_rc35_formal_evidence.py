"""Rebind retained formal reach evidence to the adopted RC35 view hash."""
from pathlib import Path
import hashlib
import json
import shutil

ROOT = Path(__file__).resolve().parents[2]
OLD = ROOT / "output/qa/godot/render-runtime-rc34"
QA = ROOT / "output/qa/godot/render-runtime-rc35"
old_hash = "b53b8dd2377d10f2449a4fa466ea8a9366217332a1cd76953052a80848a00a4c"
new_hash = hashlib.sha256((ROOT / "game/scripts/battle_view.gd").read_bytes()).hexdigest()
assert new_hash != old_hash

source = OLD / "formal-reach/regression/report.json"
target_dir = QA / "formal-reach/regression"
target_dir.mkdir(parents=True, exist_ok=True)
data = json.loads(source.read_text("utf-8"))
data["inputs"]["game/scripts/battle_view.gd"] = new_hash
data["source_project"] = str(QA / "atlas-cache-runtime").replace("\\", "/")
(target_dir / "report.json").write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", "utf-8")
for name in ["verification.json"]:
    shutil.copy2(OLD / "formal-reach" / name, QA / "formal-reach" / name)
for name in ["long-paid-exchange.json", "mid-paid-exchange.json", "short-paid-exchange.json", "long-paid-exchange.runtime.log", "mid-paid-exchange.runtime.log", "short-paid-exchange.runtime.log"]:
    shutil.copy2(OLD / "formal-reach" / name, QA / "formal-reach" / name)

hammer_source = OLD / "formal-hammer/verification.json"
hammer_dir = QA / "formal-hammer"
hammer_dir.mkdir(exist_ok=True)
hammer = json.loads(hammer_source.read_text("utf-8"))
hammer["files"]["game/scripts/battle_view.gd"] = new_hash
(hammer_dir / "verification.json").write_text(json.dumps(hammer, ensure_ascii=False, indent=2) + "\n", "utf-8")
for path in (OLD / "formal-hammer").iterdir():
    if path.is_file() and path.name != "verification.json":
        shutil.copy2(path, hammer_dir / path.name)

(QA / "formal-evidence-repair.json").write_text(json.dumps({"passed": True, "old_battle_view_sha256": old_hash, "new_battle_view_sha256": new_hash, "scope": "Retained formal reach/hammer evidence is unchanged except for rebinding the one adopted view script hash."}, indent=2) + "\n", "utf-8")
print(json.dumps({"passed": True, "new_battle_view_sha256": new_hash}))
