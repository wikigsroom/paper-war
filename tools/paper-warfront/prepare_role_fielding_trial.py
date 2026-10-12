"""Freeze an ability-based formation variation of the paid early-fielding trial."""
import difflib
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[2]
QA = ROOT / "output/qa/godot/paid-fielding-rc24"
parent = QA / "early-r2-runtime"
target = QA / "roles-r3-runtime"
assert not target.exists(), "Never overwrite a frozen trial"
for folder, pattern in [("scripts", "*.gd"), ("data", "*.json"), ("tests", "*.gd")]:
    (target / folder).mkdir(parents=True)
    for path in sorted((parent / folder).glob(pattern)):
        shutil.copy2(path, target / folder / path.name)
for name in ["project.godot", "snapshot.json"]:
    shutil.copy2(parent / name, target / name)
path = target / "scripts/tactical_ai.gd"
source = path.read_text(encoding="utf-8")
old = '\tif is_frontline(def):return allies.size()>=1\n\tif allies.size()<2:return false\n\treturn allies.any(func(u):return is_frontline(sim.db.balance.units[u.id]))\n'
new = '\tif is_frontline(def):return true\n'
new += '\t# Offensive ranged roles need a screen; ally-dependent abilities also\n'
new += '\t# need a second living fighter. No paper-worker or queued body counts.\n'
new += '\tvar ally_dependent: bool=def.has("heal_amount") or def.has("repair_building") or def.has("auto_clone_seconds") or (def.has("summons") and def.has("corpse_range"))\n'
new += '\tif ally_dependent and allies.size()<2:return false\n'
new += '\treturn allies.any(func(u):return is_frontline(sim.db.balance.units[u.id]))\n'
assert source.count(old) == 1
path.write_text(source.replace(old, new), encoding="utf-8")
diff = QA / "roles-r3.diff"
baseline = QA / "rc23-control-runtime/scripts/tactical_ai.gd"
diff.write_text(''.join(difflib.unified_diff(baseline.read_text(encoding="utf-8").splitlines(keepends=True),
    path.read_text(encoding="utf-8").splitlines(keepends=True), fromfile="rc23/tactical_ai.gd", tofile="roles-r3/tactical_ai.gd")), encoding="utf-8")
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
(target / "candidate.json").write_text(json.dumps({
    "policy": "roles-r3", "parent": "early-r2", "shipping_source_changed": False,
    "prices_times_roads_fog_unchanged": True, "generation_tool_sha256": sha(Path(__file__)),
    "diff_sha256": sha(diff), "parent_ai_sha256": sha(parent / "scripts/tactical_ai.gd"),
}, indent=2), encoding="utf-8")
print("Frozen role-based fielding trial prepared")
