"""Validate map identity and legal-sighting timing before comparing warnings."""
import argparse,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def main():
    ap=argparse.ArgumentParser();ap.add_argument("input",type=Path);ap.add_argument("--output",type=Path,required=True);args=ap.parse_args()
    data=json.loads(args.input.read_text(encoding="utf-8"))
    for key,value in data["inputs"].items():assert hashlib.sha256((ROOT/"game"/key.removeprefix("res://")).read_bytes()).hexdigest()==value,key
    required={(m,a,b) for m in ["map.01.01","map.01.04","map.01.11"] for a,b in [("yin","mu"),("mu","yin"),("yin","bai"),("bai","yin")]}
    assert len(data["records"])==12 and {(r["map"],r["west"],r["east"]) for r in data["records"]}==required
    rows=[]
    for r in data["records"]:
        for c in r["contacts"]:
            if c["seen_at"] is not None:assert c["warning_seconds"]>=0 and abs(c["warning_seconds"]-(c["release_at"]-c["seen_at"]))<1e-8
        first=[]
        for side in [0,1]:
            c=next((c for c in r["contacts"] if c["observer_side"]==side and c["kind"]=="first_release"),None)
            assert c is not None
            first.append(c)
        rows.append({"map":r["map"],"shortest_road":r["shortest_road"],"west":r["west"],"east":r["east"],"first_contacts":first,"unseen_release_events":sum(c["seen_at"] is None for c in r["contacts"])})
    report={"scope":data["scope"],"provenance_verified":True,"records":rows,"inputs":data["inputs"],"input_sha256":hashlib.sha256(args.input.read_bytes()).hexdigest()}
    args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({"cases":len(rows),"unseen_release_events":sum(r["unseen_release_events"] for r in rows)}))
if __name__=="__main__":main()
