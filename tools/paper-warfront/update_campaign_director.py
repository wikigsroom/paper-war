"""Author campaign intentions without granting resources or spawning unpaid armies."""
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
path = ROOT / "game/data/campaign.json"
campaign = json.loads(path.read_text(encoding="utf-8"))
factions = json.loads((ROOT / "game/data/factions.json").read_text(encoding="utf-8"))
units = {f["id"]: f["combat_units"] for f in factions["factions"]}
for level in campaign["levels"]:
    roster = units[level["enemy"]]
    local = level["index"] % 20
    opening = float(level.get("ai_warmup", 4))
    objective = level.get("win", "destroy_base")
    middle_style = "counter" if objective in {"escort", "intercept"} else "economy"
    late_style = "rush" if objective in {"protect", "survive", "collect_gold"} else "counter"
    level["ai_phases"] = [
        {"id": level["id"] + ".probe", "at": opening, "style": "rush", "workers": 3, "prefer_units": roster[:2]},
        {"id": level["id"] + ".investment", "at": 24 + local * 1.5, "style": middle_style, "workers": 4 if local < 5 else 5, "prefer_units": roster[2:4]},
        {"id": level["id"] + ".breakthrough", "at": 65 + local * 2, "style": late_style, "workers": 4, "prefer_units": roster[4:]},
    ]
campaign["director_revision"] = "rc7-paid-phase-intentions"
text = json.dumps(campaign, ensure_ascii=False, indent=2) + "\n"
path.write_text(text, encoding="utf-8")
(ROOT / "assets/paper-warfront/campaign.json").write_text(text, encoding="utf-8")
print("Authored three paid-intent phases for", len(campaign["levels"]), "levels")
