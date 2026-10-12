"""Validate three-wave paid observations without pretending they are full AI matches."""
import hashlib,json,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];QA=ROOT/"output/qa/godot/core-alignment-rc10"
rows=[]
for policy in ("investment_only","replace_front","replace_front_spells","screen_first_spells"):
    stem="sustained-opening-"+policy
    data=json.loads((QA/(stem+".json")).read_text(encoding="utf-8"))
    log=(QA/(stem+".log")).read_text(encoding="utf-8-sig")
    assert data["scripted_policy"]==policy and not data["experimental_legacy_formation"]
    assert "SCRIPT ERROR" not in log and "ERROR:" not in log and "SUSTAINED_OPENING_ORDER 6" in log
    for path,digest in data["inputs"].items():assert hashlib.sha256((ROOT/"game"/path.removeprefix("res://")).read_bytes()).hexdigest()==digest,path
    assert len(data["records"])==6
    assert {(r["map"],r["side"]) for r in data["records"]}=={(m,s) for m in ("map.01.01","map.01.04","map.01.11") for s in (0,1)}
    for record in data["records"]:
        assert data["wave_protocol"]=="fixed_18_43_68" and record["wave_at"]==18
        spent=sum(r["gold"] for r in record["paid"])
        enemy_spent=sum(r["gold"] for r in record["enemy_paid"])
        assert math.isclose(record["gold"],300+record["delivered"]-spent,abs_tol=1e-6)
        assert math.isclose(record["enemy_gold"],300+record["enemy_delivered"]-enemy_spent,abs_tol=1e-6)
        assert record["enemy_orders"]==len(record["enemy_paid"])<=9
        for i,order in enumerate(record["enemy_paid"]):
            assert order["time"]+1e-6>=record["wave_at"]+25*(i//3)
            assert order["id"]=="unit.yin.axe" and order["gold"]==45
        assert record["stats"]["casts"]==len(record["spells"])
        if policy not in ("replace_front_spells","screen_first_spells"):assert not record["spells"] and record["stats"]["mana_spent"]==0
        rows.append({"policy":policy,"map":record["map"],"side":record["side"],"winner":record["winner"],"time":record["time"],"spent":spent,"replacements":sum(bool(r.get("replacement")) for r in record["paid"]),"enemy_recruits":record["enemy_orders"],"remaining_initial_orders":record["remaining_orders"],"workers":record["workers"],"enemy_base_hp":record["enemy_base_hp"],"casts":record["spells"],"healed":record["stats"]["healed"]})
result={"passed":True,"scope":"24 controlled normal-budget fixed-time three-wave observations. Spell threat detection matches formal TacticalAI; screen-first investment changes purchase order, not costs. Requests wait for income; legal visible enemies feed existing spell AI only in the explicit spell arm. No full TacticalAI, human or all-faction balance claim.","rows":rows}
(QA/"sustained-opening-summary.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
for policy in ("investment_only","replace_front","replace_front_spells","screen_first_spells"):
    selected=[r for r in rows if r["policy"]==policy]
    print(policy,"wins",sum(r["winner"]==r["side"] for r in selected),"losses",sum(r["winner"]==1-r["side"] for r in selected),"unresolved",sum(r["winner"]==-2 for r in selected),"worker_survival",[r["workers"] for r in selected])
print("SUSTAINED_OPENING_ORDER: 24 paid cases, both gold ledgers and wave timing verified")
