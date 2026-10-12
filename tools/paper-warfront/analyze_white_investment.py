"""Verify paid white investment trials and read-only spell observations."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
QA=ROOT/"output/qa/godot/core-alignment-rc9"
def load(stem):
    data=json.loads((QA/(stem+".json")).read_text(encoding="utf-8"))
    log=(QA/(stem+".log")).read_text(encoding="utf-8-sig")
    assert "SCRIPT ERROR" not in log and "ERROR:" not in log,stem
    assert len([x for x in log.splitlines() if x.startswith("FACTION_MATCHUP ")])==len(data["records"]),stem
    assert not data.get("experimental_price_overrides") and not data.get("experimental_map_removed_edges"),stem
    for path,digest in data["inputs"].items():
        assert hashlib.sha256((ROOT/"game"/path.removeprefix("res://")).read_bytes()).hexdigest()==digest,(stem,path)
    return data
def white(row):return 0 if row["west"]=="bai" else 1
def stripped(row,fields):return {k:v for k,v in row.items() if k not in fields}
protections=[];opening=[];adaptive=[]
for label in ("short","medium","long"):
    reference=json.loads((QA/f"research-feedback-{label}271.json").read_text(encoding="utf-8"))
    expected={r["index"]:r for r in reference["records"] if r["index"] in (9,90)}
    trace=load(f"white-spell-trace-{label}271")
    assert {r["index"] for r in trace["records"]}=={9,90}
    for row in trace["records"]:
        assert stripped(row,{"white_spell_trace","white_blocked_trace"})==expected[row["index"]]
        for cast in row["white_spell_trace"]:
            if not cast["id"].endswith(".protect"):continue
            blocked=[b for b in row["white_blocked_trace"] if b["target"]==cast["target"] and cast["time"]<=b["time"]<cast["time"]+2.5]
            protections.append({"map":label,"index":row["index"],"time":cast["time"],"hp_at_cast":cast["target_hp"],"mana_at_cast":cast["mana"],"blocked_count":len(blocked),"raw_blocked_amount":sum(b["raw_amount"] for b in blocked)})
    for arm in ("early","early-hold"):
        report=load(f"white-{arm}-{label}271")
        assert report["experimental_white_early_research"] is True
        assert report["experimental_white_hold_clone"]==(arm=="early-hold")
        assert {r["index"] for r in report["records"]}=={9,90}
        for row in report["records"]:
            side=white(row)
            assert row["timeline"][0]["sides"][side]["research"]["id"]=="tech.bai.unit.scribe"
            assert row["timeline"][0]["sides"][side]["research"]["total"]==5
            assert row["timeline"][1]["sides"][side]["stats"]["mana_income"]["research"]==8
            opening.append({"map":label,"arm":arm,"index":row["index"],"winner":row["winner"],"time":row["time"],"workers":row["sides"][side]["workers"],"spells":row["sides"][side]["stats"]["spell_counts"]})
    plan=load(f"white-map-plan-{label}271")
    assert plan["experimental_white_map_plan"] is True
    for row in plan["records"]:
        if label!="long":
            assert not row["plan_trace"]
            assert stripped(row,{"plan_trace"})==expected[row["index"]]
        else:
            assert len(row["plan_trace"])==1
            grant=row["plan_trace"][0]
            assert 50<=grant["road"]<60 and grant["research"]["ok"] and grant["gold_after"]==215
        adaptive.append({"map":label,"index":row["index"],"winner":row["winner"],"time":row["time"],"workers":row["sides"][white(row)]["workers"]})
cross=[]
for suffix,indices in (("cross271",{19,29,69,91,92,96}),("yin137",{9,90})):
    control=load("white-map-plan-control-"+suffix)
    pilot=load("white-map-plan-pilot-"+suffix)
    assert not control["experimental_white_map_plan"] and pilot["experimental_white_map_plan"]
    assert {r["index"] for r in control["records"]}==indices=={r["index"] for r in pilot["records"]}
    for before,after in zip(control["records"],pilot["records"]):
        assert before["index"]==after["index"]
        side=white(before)
        cross.append({"seed":control["seed"],"index":before["index"],"before_winner":before["winner"],"after_winner":after["winner"],"before_seconds":before["time"],"after_seconds":after["time"],"before_workers":before["sides"][side]["workers"],"after_workers":after["sides"][side]["workers"]})
assert len(protections)==8 and all(r["blocked_count"]>0 for r in protections)
result={"passed":True,"scope":"Read-only trace reproduces six baseline timelines. Non-shipping investment trials; never a whole-game balance claim.","protections":protections,"opening_trials":opening,"adaptive_trials":adaptive,"cross_trials":cross,"decision":"Do not adopt a universal opening: some economic outcomes improve but prior wins against mo become unresolved. Keep trials separate from formal evidence."}
(QA/"white-investment-summary.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
print("WHITE_INVESTMENT: 8 protection windows, 12 opening trials, 6 adaptive trials and 8 cross/seed pairs verified")
