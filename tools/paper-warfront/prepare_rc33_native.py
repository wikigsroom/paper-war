"""Prepare frozen RC32 and proven R3 source GPU projects without formal adoption."""
from pathlib import Path
import hashlib
import json
import re
import shutil

ROOT=Path(__file__).resolve().parents[2]
QA=ROOT/"output/qa/godot/phase-runtime-rc33"
BASE=QA/"native-baseline-runtime"
CANDIDATE=QA/"native-marching-r3-runtime"
assert not BASE.exists() and not CANDIDATE.exists()
semantic=QA/"marching-r3-semantic-r3-receipt.json"
assert json.loads(semantic.read_text("utf-8"))["passed"]
freeze=json.loads((QA/"freeze.json").read_text("utf-8"))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
imports={}
for name,digest in freeze["public_inputs"].items():
    p=ROOT/name
    assert sha(p)==digest,name
    dest=BASE/Path(name).relative_to("game")
    dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest)
    if p.suffix==".import":
        for resource in re.findall(r'res://(\.godot/imported/[^"\s]+)',p.read_text("utf-8")):
            source=ROOT/"game"/resource
            assert source.is_file(),resource
            target=BASE/resource;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
            imports[resource]=sha(target)
for p in (ROOT/"game/tests").glob("*.gd"):
    dest=BASE/"tests"/p.name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest)
shutil.copytree(BASE,CANDIDATE)
shutil.copy2(QA/"marching-r3-runtime/scripts/battle_sim.gd",CANDIDATE/"scripts/battle_sim.gd")
for n,d in freeze["public_inputs"].items():assert sha(ROOT/n)==d,n
(QA/"native-preparation.json").write_text(json.dumps({"passed":True,"public_inputs":freeze["public_inputs"],
    "native_imports":imports,"generator_sha256":sha(Path(__file__)),"semantic_receipt_sha256":sha(semantic),
    "candidate_changed_scripts":{"battle_sim.gd":sha(CANDIDATE/"scripts/battle_sim.gd")},
    "scope":"Native source GPU projects only: frozen1194 RC32 export-selected raw inputs, corresponding455 native imported resources and source tests. Candidate changes exactly1 simulation script; no art/render/UI/plot/AI changes or formal adoption/export. Natural frames only after all preparation and other QA is terminal."
},indent=2)+"\n","utf-8")
print("Prepared native RC32/R3 projects; imported resources",len(imports))
