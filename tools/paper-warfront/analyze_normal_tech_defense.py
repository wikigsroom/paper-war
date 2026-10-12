"""Verify normal-technology controlled defense costs, timing and provenance."""
import argparse
import hashlib
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]

def main():
    ap=argparse.ArgumentParser();ap.add_argument("input",type=Path);ap.add_argument("--output",type=Path,required=True);args=ap.parse_args()
    data=json.loads(args.input.read_text(encoding="utf-8"))
    for key,value in data["inputs"].items():
        assert hashlib.sha256((ROOT/"game"/key.removeprefix("res://")).read_bytes()).hexdigest()==value,key
    balance=json.loads((ROOT/"game/data/balance-prototype.json").read_text(encoding="utf-8"))
    tech=json.loads((ROOT/"game/data/technology.json").read_text(encoding="utf-8"))
    policies={"yin":["recruit_only","spell_and_recruit"],"bai":["recruit_only","spell_and_recruit","early_research_spell_and_recruit","reactive_research_spell_and_recruit"]}
    required={(m,s,f,p) for m in ["map.01.01","map.01.04","map.01.11"] for s in [0,1] for f in policies for p in policies[f]}
    assert len(data["records"])==36 and {(r["map"],r["side"],r["faction"],r["policy"]) for r in data["records"]}==required
    for r in data["records"]:
        assert r["options"]["full_tech"] is False
        assert set(r["initial_unlocked"])==set(tech["starting_unlocked"][r["faction"]])
        assert r["front_result"]["ok"] and r["stats"]["recruited"]==1
        assert len(r["attacker_orders"])==2 and all(c["ok"] for c in r["attacker_orders"])
        assert r["front_order_at"]>=r["first_visible_at"]
        cost=float(balance["units"][r["front"]]["gold"])
        if r["research_order_at"] is not None:
            assert r["research_result"]["ok"]
            node=next(n for n in tech["nodes"] if n["id"]=="tech.bai.unit.scribe")
            cost+=node["gold"]
            assert r["research_done_at"]>=r["research_order_at"]+node["seconds"]-.00001
            assert node["id"] in r["studied"]
            if r["policy"].startswith("early"):assert r["research_order_at"]==0
            else:assert r["research_order_at"]>=r["first_visible_at"]
        assert abs(r["gold"]-(300+r["stats"]["gold_delivered"]-cost))<.001
        spent=balance["spells"][r["spell"]]["mana"] if r["cast_at"] is not None else 0
        assert r["stats"]["mana_spent"]==spent
        assert abs(r["mana"]-(40+sum(r["stats"]["mana_income"].values())-spent))<.001
        if r["cast_at"] is not None:assert r["cast_result"]["ok"] and r["cast_at"]>=r["first_visible_at"]
    summary=[]
    for f,items in policies.items():
        for policy in items:
            rows=[r for r in data["records"] if r["faction"]==f and r["policy"]==policy]
            summary.append({"faction":f,"policy":policy,"cases":6,"both_workers_preserved":sum(r["worker_count"]==2 for r in rows),"one_worker_preserved":sum(r["worker_count"]==1 for r in rows),"no_workers":sum(r["worker_count"]==0 for r in rows)})
    report={"scope":data["scope"],"passed":True,"provenance_verified":True,"input_sha256":hashlib.sha256(args.input.read_bytes()).hexdigest(),"analyzer_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),"summary":summary,"records":data["records"],"inputs":data["inputs"]}
    args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(summary))
if __name__=="__main__":main()
