"""Prepare an isolated RC36 candidate that reuses battle tick snapshot buffers.

The candidate starts from the current working-tree source and is intentionally
kept outside ``game/`` until the equivalence and realtime gates pass.
"""
from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "output/qa/godot/render-runtime-rc36"
CANDIDATE = OUT / "candidate-source-r2"


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one match, got {count}")
    return text.replace(old, new, 1)


def main() -> None:
    if CANDIDATE.exists():
        shutil.rmtree(CANDIDATE)
    CANDIDATE.mkdir(parents=True, exist_ok=True)
    for name in ["project.godot", "main.tscn", "--map"]:
        shutil.copy2(ROOT / "game" / name, CANDIDATE / name)
    for name in ["scripts", "data"]:
        shutil.copytree(ROOT / "game" / name, CANDIDATE / name)
    # The source candidate uses a directory junction for immutable art. This
    # avoids duplicating nearly 1 GB of approved assets for a logic-only trial.
    junction = CANDIDATE / "assets"
    ps = (
        "$p = '" + str(junction).replace("'", "''") + "'; "
        "$t = '" + str(ROOT / 'game/assets').replace("'", "''") + "'; "
        "New-Item -ItemType Junction -Path $p -Target $t -Force | Out-Null"
    )
    import subprocess
    subprocess.run(["powershell", "-NoProfile", "-Command", ps], check=True)
    target = CANDIDATE / "scripts/battle_sim.gd"
    source_before = target.read_text("utf-8")
    text = source_before

    text = replace_once(
        text,
        "var scheduled: Array = []\nvar spell_areas: Array = []\nvar events: Array = []",
        """var scheduled: Array=[]
var spell_areas: Array=[]
var events: Array=[]

# Tick snapshots and survivor buffers are reused across frames. They preserve
# the old duplicate/filter phase boundaries while avoiding per-tick Array churn.
var tick_units_snapshot: Array=[]
var tick_projectiles_snapshot: Array=[]
var tick_scheduled_snapshot: Array=[]
var tick_corpses_snapshot: Array=[]
var alive_units_buffer: Array=[]
var alive_buildings_buffer: Array=[]""",
        "snapshot buffer declarations",
    )

    text = replace_once(
        text,
        "projectiles.clear(); scheduled.clear(); spell_areas.clear(); events.clear(); stats.clear()",
        """projectiles.clear(); scheduled.clear(); spell_areas.clear(); events.clear(); stats.clear()
	tick_units_snapshot.clear(); tick_projectiles_snapshot.clear(); tick_scheduled_snapshot.clear(); tick_corpses_snapshot.clear()
	alive_units_buffer.clear(); alive_buildings_buffer.clear()""",
        "start buffer reset",
    )

    text = replace_once(
        text,
        "\tfor u in units.duplicate():\n",
        """\ttick_units_snapshot.clear()
	tick_units_snapshot.append_array(units)
	for u in tick_units_snapshot:
""",
        "unit snapshot loop",
    )
    text = replace_once(
        text,
        "\tfor p in projectiles.duplicate():\n",
        """\ttick_projectiles_snapshot.clear()
	tick_projectiles_snapshot.append_array(projectiles)
	for p in tick_projectiles_snapshot:
""",
        "projectile snapshot loop",
    )
    text = replace_once(
        text,
        "\tfor action in scheduled.duplicate():\n",
        """\ttick_scheduled_snapshot.clear()
	tick_scheduled_snapshot.append_array(scheduled)
	for action in tick_scheduled_snapshot:
""",
        "scheduled snapshot loop",
    )
    text = replace_once(
        text,
        "\tfor c in corpses.duplicate():\n",
        """\ttick_corpses_snapshot.clear()
	tick_corpses_snapshot.append_array(corpses)
	for c in tick_corpses_snapshot:
""",
        "corpse snapshot loop",
    )
    text = replace_once(
        text,
        "\tunits=units.filter(func(u):return u.hp>0)\n\tbuildings=buildings.filter(func(b):return b.hp>0)",
        """\talive_units_buffer.clear()
	for u in units:
		if u.hp>0:alive_units_buffer.append(u)
	var previous_units: Array=units
	units=alive_units_buffer
	alive_units_buffer=previous_units
	alive_buildings_buffer.clear()
	for b in buildings:
		if b.hp>0:alive_buildings_buffer.append(b)
	var previous_buildings: Array=buildings
	buildings=alive_buildings_buffer
	alive_buildings_buffer=previous_buildings""",
        "survivor buffers",
    )

    target.write_text(text, "utf-8")
    inputs = {}
    for part in ["scripts", "data"]:
        for path in sorted((CANDIDATE / part).rglob("*")):
            if path.is_file():
                inputs[path.relative_to(CANDIDATE).as_posix()] = sha(path)
    OUT.mkdir(parents=True, exist_ok=True)
    receipt = {
        "candidate": "rc36-sim-buffers",
        "base_project": str(ROOT / "game"),
        "candidate_project": str(CANDIDATE),
        "base_battle_sim_sha256": sha(ROOT / "game/scripts/battle_sim.gd"),
        "candidate_battle_sim_sha256": sha(target),
        "source_inputs": inputs,
        "changes": [
            "reuse unit/projectile/scheduled/corpse tick snapshots",
            "reuse unit/building survivor arrays instead of filter allocations",
            "preserve duplicate/filter phase semantics and actor references",
        ],
    }
    (OUT / "candidate-preparation.json").write_text(json.dumps(receipt, indent=2), "utf-8")
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
