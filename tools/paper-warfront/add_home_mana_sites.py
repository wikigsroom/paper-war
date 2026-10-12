"""Keep authored forward sites; add a reachable rear mana investment to each battlefield."""
import json,math,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
p=ROOT/"game/data/maps.json"
data=json.loads(p.read_text(encoding="utf-8"))
for m in data["maps"]:
    for side,base in enumerate(m["bases"]):
        uid=f"site.{side}.home-mana"
        if any(site["id"]==uid for site in m["build_sites"]):continue
        edge=next(e for e in m["edges"] if e["from" if side==0 else "to"]==base["node"])
        lengths=[math.dist(a,b) for a,b in zip(edge["points"],edge["points"][1:])]
        total=sum(lengths);s=min(2.8,total*.7) if side==0 else max(0,total-min(2.8,total*.7))
        remaining=s
        for a,b,length in zip(edge["points"],edge["points"][1:],lengths):
            if remaining<=length:
                t=remaining/length;point=[a[0]+(b[0]-a[0])*t,a[1]+(b[1]-a[1])*t];break
            remaining-=length
        m["build_sites"].append(dict(id=uid,owner=side,label="后营法灯位",types=["mana"],edge=edge["id"],s=round(s,6),x=round(point[0],6),y=round(point[1],6)))
for m in data["maps"]:
    m["geometry_sha256"]=hashlib.sha256(json.dumps({k:m[k] for k in ["length","nodes","edges","mines","build_sites"]},sort_keys=True).encode()).hexdigest()
    m["revision"]="rc7-rear-mana-investment"
data["revision"]="rc7-rear-mana-investment"
text=json.dumps(data,ensure_ascii=False,indent=2)+"\n"
for folder in ["game/data","assets/paper-warfront"]:(ROOT/folder/"maps.json").write_text(text,encoding="utf-8")
print("Updated",len(data["maps"]),"maps without changing roads, mines, existing sites or IDs.")
