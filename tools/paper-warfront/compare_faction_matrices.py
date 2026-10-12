"""Compare complete, provenance-verified paired faction observations."""
import argparse,hashlib,json
from pathlib import Path

def read_verified(path):
    data=json.loads(path.read_text(encoding="utf-8"))
    assert data["complete"] and data["provenance_verified"]
    assert all(sum(row[k] for k in ["wins","losses","unresolved"])==18 for row in data["factions"].values())
    return data

def main():
    p=argparse.ArgumentParser();p.add_argument("before",type=Path);p.add_argument("after",type=Path);p.add_argument("--output",type=Path,required=True);args=p.parse_args()
    before=read_verified(args.before);after=read_verified(args.after)
    assert (before["map"],before["seed"])==(after["map"],after["seed"])
    assert set(before["factions"])==set(after["factions"])
    rows={}
    for faction,old in before["factions"].items():
        new=after["factions"][faction]
        rows[faction]={"before":old,"after":new,"delta":{k:new[k]-old[k] for k in old}}
    report={"scope":"Complete paired 100-combination AI matrices on one formal map/seed. 150s unresolved is not a draw; counts are observations, not human win rates. Before is historical verified baseline, after is separately verified current input.","map":after["map"],"seed":after["seed"],"factions":rows,"inputs":{str(args.before):hashlib.sha256(args.before.read_bytes()).hexdigest(),str(args.after):hashlib.sha256(args.after.read_bytes()).hexdigest()}}
    args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({"factions":{f:r["delta"] for f,r in rows.items()}}))
if __name__=="__main__":main()
