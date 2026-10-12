"""Freeze an instrumented native view to locate unit submission work; no adoption."""
from pathlib import Path
import hashlib
import json
import shutil

ROOT = Path(__file__).resolve().parents[2]
QA = ROOT / "output/qa/godot/phase-runtime-rc33"
SOURCE = QA / "native-marching-r3-runtime"
TRIAL = QA / "native-unit-profile-runtime"
assert json.loads((QA / "source-gates-final.json").read_text("utf-8"))["passed"]
assert not TRIAL.exists()
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
shutil.copytree(SOURCE, TRIAL)
p = TRIAL / "scripts/battle_view.gd"
s = p.read_text("utf-8")
s = s.replace("var layer_cpu_us: Dictionary={}\n", "var layer_cpu_us: Dictionary={}\nvar unit_detail_us: Dictionary={}\n")
old = "\tvar ordered=ordered_units()\n\tfor u in ordered: draw_unit(u)\n"
new = "\tunit_detail_us.clear()\n\tvar order_start: int=Time.get_ticks_usec()\n\tvar ordered=ordered_units()\n\tunit_detail_us[\"ordering\"]=Time.get_ticks_usec()-order_start\n\tfor u in ordered: draw_unit(u)\n\tfor k in unit_detail_us:layer_cpu_us[\"unit_detail.\"+k]=unit_detail_us[k]\n"
assert s.count(old) == 1
s = s.replace(old, new)
start = s.index("func draw_unit(u: Dictionary):")
end = s.index("\nfunc draw_frame_unit", start)
unit = s[start:end]
unit = unit.replace("func draw_unit(u: Dictionary):\n", "func draw_unit(u: Dictionary):\n\tvar unit_mark: int=Time.get_ticks_usec()\n")
markers = [
    ("\tif u.get(\"objective_unit\",false)", "prepare"),
    ("\tdraw_frame_unit(u,pos,meta,modulation)", "shadow_label"),
    ("\tif u.cargo>0:", "frame_pose"),
    ("\t# Ownership is independent", "cargo_work_queue"),
    ("\tif u.hp<u.max_hp", "ownership"),
]
for needle, label in markers:
    assert unit.count(needle) == 1
    unit = unit.replace(needle, f'\tunit_mark=unit_detail_mark("{label}",unit_mark)\n' + needle)
unit += '\tunit_detail_mark("health_status",unit_mark)\n'
helper = '''
func unit_detail_mark(label_value: String,started: int) -> int:
\tvar now: int=Time.get_ticks_usec()
\tunit_detail_us[label_value]=int(unit_detail_us.get(label_value,0))+now-started
\treturn now
'''
s = s[:start] + unit + helper + s[end:]
p.write_text(s, "utf-8")
(QA / "unit-profile-preparation.json").write_text(json.dumps({
    "passed": True, "generator_sha256": sha(Path(__file__)),
    "source_view_sha256": sha(SOURCE / "scripts/battle_view.gd"),
    "instrumented_view_sha256": sha(p),
    "source_gates_sha256": sha(QA / "source-gates-final.json"),
    "scope": "Isolated native source with per-unit CPU markers. Ordering, prepare, shadow, full pose, cargo, ownership and status submission only. Instrumentation overhead included; this project is neither a proposed implementation nor comparable FPS proof. Formal source and frozen R3 untouched."
}, indent=2) + "\n", "utf-8")
print("Prepared isolated per-unit diagnostic view", flush=True)
