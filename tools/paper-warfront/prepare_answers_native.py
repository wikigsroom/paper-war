"""Freeze export-selected RC31 resources and native imports for candidate GPU checks."""
from pathlib import Path
import hashlib
import json
import re
import shutil

ROOT=Path(__file__).resolve().parents[2]
QA=ROOT/"output/qa/godot/contact-runtime-rc32"
BASE=QA/"native-baseline-runtime"
CANDIDATE=QA/"native-answers-r1-runtime"
assert not BASE.exists() and not CANDIDATE.exists()
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
# Native tests are deliberately separate from export-selected inputs (UID sidecars remain).
for p in (ROOT/"game/tests").glob("*.gd"):
    dest=BASE/"tests"/p.name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest)
shutil.copytree(BASE,CANDIDATE)
for name in ["battle_sim.gd","battle_visibility.gd"]:
    shutil.copy2(QA/"answers-r1-runtime/scripts"/name,CANDIDATE/"scripts"/name)
for n,d in freeze["public_inputs"].items():assert sha(ROOT/n)==d,n
(QA/"native-preparation.json").write_text(json.dumps({"passed":True,"public_inputs":freeze["public_inputs"],
    "native_imports":imports,"generator_sha256":sha(Path(__file__)),
    "candidate_changed_scripts":{n:sha(CANDIDATE/"scripts"/n) for n in ["battle_sim.gd","battle_visibility.gd"]},
    "scope":"Native source GPU projects: frozen1194 RC31 export-selected raw inputs, corresponding native imported resources and all source tests. Candidate changes exactly2 scripts. Imports are byte copies, no rendering simplification; no formal game edits or exports."
},indent=2)+"\n","utf-8")
print("Prepared native RC31/candidate source projects; imported resources",len(imports))
