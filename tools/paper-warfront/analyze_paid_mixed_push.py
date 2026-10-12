"""Verify actual paid research, FIFO production and advancing mixed armies."""
import hashlib,json,math,importlib.util
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];QA=ROOT/"output/qa/godot/core-alignment-rc9"
balance=json.loads((ROOT/"game/data/balance-prototype.json").read_text(encoding="utf-8"))
technology=json.loads((ROOT/"game/data/technology.json").read_text(encoding="utf-8"))
tech={x["id"]:x for x in technology["nodes"]}
spec=importlib.util.spec_from_file_location("guard",ROOT/"tools/paper-warfront/check_ai_engagement.py")
guard=importlib.util.module_from_spec(spec);spec.loader.exec_module(guard)
rows=[]
for faction in ("mu","bai","yuan"):
    arms={}
    for arm in ("legacy","current"):
        stem=f"paid-mixed-push-{faction}-{arm}"
        data=json.loads((QA/(stem+".json")).read_text(encoding="utf-8"))
        assert data["scripted_formation"]==faction
        assert data["experimental_legacy_formation"]==(arm=="legacy")
        assert bool(guard.experimental_policy_fields(data))==(arm=="legacy")
        log=(QA/(stem+".log")).read_text(encoding="utf-8-sig")
        assert "SCRIPT ERROR" not in log and "ERROR:" not in log
        assert "PAID_MIXED_PUSH 6" in log
        for path,digest in data["inputs"].items():
            assert hashlib.sha256((ROOT/"game"/path.removeprefix("res://")).read_bytes()).hexdigest()==digest,path
        assert len(data["records"])==6
        assert {(r["map"],r["side"]) for r in data["records"]}=={(m,s) for m in ("map.01.01","map.01.04","map.01.11") for s in (0,1)}
        for row in data["records"]:
            paid=row["paid"];research=[r for r in paid if r["kind"]=="research"];recruits=[r for r in paid if r["kind"]=="recruit"]
            spent=sum(r["gold"] for r in paid)
            assert math.isclose(row["gold"],300+row["delivered"]-spent,abs_tol=1e-6),"No free gold or unrecorded spending"
            assert row["enemy_orders"]==3
            studied={r["id"] for r in technology["nodes"] if r["faction"]==faction and r["grant"] in technology["starting_unlocked"][faction]}
            complete_at=0
            for r in research:
                node=tech[r["id"]]
                assert r["gold"]==node["gold"] and set(node["requires"]).issubset(studied)
                assert r["time"]+.02>=complete_at
                complete_at=r["time"]+node["seconds"];studied.add(node["id"])
            assert all(r["time"]+.02>=complete_at for r in recruits)
            assert len(row["members"])==len(recruits)
            previous=0
            for order,member in zip(recruits,row["members"]):
                definition=balance["units"][order["id"]]
                assert order["id"]==member["id"] and order["gold"]==definition["gold"]
                assert member["created_at"]+.02>=max(order["time"],previous)+definition["production_seconds"]
                previous=member["created_at"]
        arms[arm]=data
    for before,after in zip(arms["legacy"]["records"],arms["current"]["records"]):
        assert (before["map"],before["side"])==(after["map"],after["side"])
        assert before["paid"]==after["paid"],"Comparison must retain investment and order times"
        rows.append({"faction":faction,"map":after["map"],"side":after["side"],"spent":sum(p["gold"] for p in after["paid"]),"legacy_winner":before["winner"],"current_winner":after["winner"],"legacy_time":before["time"],"current_time":after["time"],"legacy_enemy_base_hp":before["enemy_base_hp"],"current_enemy_base_hp":after["enemy_base_hp"],"legacy_members":before["members"],"current_members":after["members"],"workers":after["workers"],"remaining_orders":after["remaining_orders"],"same_record":before==after})
assert sum(r["faction"]=="mu" and r["current_winner"]==r["side"] and r["legacy_winner"]==-2 for r in rows)==4
assert all(r["same_record"] for r in rows if r["faction"]!="mu")
result={"passed":True,"scope":"18 paired controlled paid investments, 36 runs. Normal 300 gold, real workers/research/production/fog, three opposing axe recruits; scripted wave, no continuing AI reinforcement or human balance proof.","rows":rows,"decision":"Mixed formation repair enables actual mu medical backline contribution during base assault. Other two compositions and long-map completion still require strategic tuning."}
(QA/"paid-mixed-push-summary.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
print("PAID_MIXED_PUSH: 18 paired cases verified; real costs/prerequisites/research and FIFO production; four mu completion improvements")
