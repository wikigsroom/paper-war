"""Verify mixed formation repair, current GPU evidence and paid-match boundaries."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];QA=ROOT/"output/qa/godot/core-alignment-rc9"
def read(name):return json.loads((QA/name).read_text(encoding="utf-8"))
def current(data):
    for p,h in data["inputs"].items():
        path=ROOT/"game"/p.removeprefix("res://") if p.startswith("res://") else ROOT/p
        assert hashlib.sha256(path.read_bytes()).hexdigest()==h,p
before=read("mixed-formation-before.json");after=read("mixed-formation-current.json")
current(after)
identity=lambda r:(r["faction"],r["side"],r["reverse"],tuple(u["id"] for u in r["members"]))
assert len(before["records"])==32==len(after["records"])
assert len({identity(r) for r in before["records"]})==32
assert {identity(r) for r in before["records"]}=={identity(r) for r in after["records"]}
blocked=sum(any(u["releases"]==0 for u in r["members"]) for r in before["records"])
assert blocked==16
assert all(not r["illegal"] and not r["crossed"] and all(u["releases"]>=3 and u["hits"]>0 for u in r["members"]) for r in after["records"])
assert "failures=[]" in (QA/"mixed-formation-current.log").read_text(encoding="utf-8-sig")
paid=[]
for label in ("short","medium","long"):
    old=read(f"research-feedback-{label}271.json");new=read(f"mixed-paid-{label}271.json")
    current(new)
    assert {r["index"] for r in new["records"]}=={6,9,60,90}
    assert old["records"]==new["records"],"Do not claim these paid outcomes improved"
    log=(QA/f"mixed-paid-{label}271.log").read_text(encoding="utf-8-sig")
    assert "SCRIPT ERROR" not in log and "ERROR:" not in log
    paid.append({"map":new["map"],"records":len(new["records"]),"unchanged_timelines":True})
for name in ("desktop","phone"):
    gpu=read(f"mixed-formation-ui/{name}/report.json");current(gpu)
    assert gpu["passed"] and gpu["runtime_log_verified"]
regression=read("mixed-formation-regression/report.json");current(regression)
assert regression["passed"] and regression["source_unchanged"]
assert sum(r["checks"] for r in regression["tests"])==12542
cpu=read("mixed-formation-cpu.json");current(cpu)
result={"passed":True,"scope":"32 controlled mixed pairs; actual firing, hits, screen spacing and range. Current source GPU and 12 normal paid matches. Not full balance, exported binaries or Android hardware.","before_zero_fire_cases":blocked,"after_zero_fire_cases":0,"minimum_releases":min(u["releases"] for r in after["records"] for u in r["members"]),"minimum_hits":min(u["hits"] for r in after["records"] for u in r["members"]),"regression_checks":12542,"paid_observations":paid,"cpu_ms":{k:cpu[k+"_us"]/1000 for k in ("mean","p95","max")}}
(QA/"mixed-formation-summary.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
print("MIXED_FORMATION: verified 32 repaired pairs, 12542 checks, 12 unchanged paid timelines and two native GPU captures")
