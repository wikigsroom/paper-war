"""Deterministic rc7 progression update; stable IDs and source/runtime data stay paired."""
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
def read(name):
    return json.loads((ROOT / "game/data" / name).read_text(encoding="utf-8"))
def save(name, data):
    text=json.dumps(data,ensure_ascii=False,indent=2)+"\n"
    for directory in ["game/data", "assets/paper-warfront"]:
        (ROOT / directory / name).write_text(text,encoding="utf-8")
b=read("balance-prototype.json")
t=read("technology.json")
f=read("factions.json")
faction_defs={entry["id"]:entry for entry in f["factions"]}
heavy={"artillery","mortar","siege","colossus","summoner","illusionist"}
support={"medic","engineer","necromancer","oracle","scribe","banner","caravan"}
for uid,unit in b["units"].items():
    role=unit.get("role","")
    seconds=1.6 if unit.get("economy") else 4.8 if role=="colossus" else 3.8 if role in heavy else 2.8 if role in support else 2.4 if unit["gold"]>=95 else 1.8
    unit["production_seconds"]=seconds
b["version"]="3.0.0-rc7-dev"
b["stage"]="core-alignment-in-progress"
b["simulation"]["production_roster_max"]=6
b["map"]["fog_of_war"]=True
nodes={n["grant"]:n for n in t["nodes"]}
for faction in f["order"]:
    units=faction_defs[faction]["combat_units"]
    basic=[u for u in t["starting_unlocked"][faction] if u.startswith("unit.") and not u.endswith(".worker")]
    intermediate=[u for u in units if u not in basic and b["units"][u].get("role") not in heavy]
    for u in units:
        node=nodes[u]
        if u in basic:continue
        if b["units"][u].get("role") in heavy:
            prerequisite=intermediate[0] if intermediate else basic[0]
            node["requires"]=[nodes[prerequisite]["id"]]
            node["seconds"]=8 if b["units"][u].get("role")!="colossus" else 10
        else:
            prerequisite=basic[1] if b["units"][u].get("role") in support else basic[0]
            node["requires"]=[nodes[prerequisite]["id"]]
            node["seconds"]=5
    advanced=[n for n in t["nodes"] if n["faction"]==faction and n["grant"].startswith("spell.") and n["grant"] not in t["starting_unlocked"][faction]]
    for i,node in enumerate(advanced):
        node["requires"]=[nodes[intermediate[min(i,len(intermediate)-1)] if intermediate else basic[0]]["id"]]
t["schema_version"]=4
t["revision"]="rc7-investment-paths"
save("balance-prototype.json",b)
save("technology.json",t)
print("Updated production profiles and faction investment paths; source/runtime paired.")
