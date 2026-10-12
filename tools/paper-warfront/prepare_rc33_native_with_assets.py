"""Repair the incomplete QA environment without editing frozen candidate sources."""
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
partial=QA/"marching-r3-semantic-r3-receipt.json"
d=json.loads(partial.read_text("utf-8"))
assert not d["passed"] and [x["job"] for x in d["jobs"] if x["passed"]]==["boundary","phase","paid"]
reg=json.loads((QA/"candidate-regression-r3/report.json").read_text("utf-8"))
assert reg["source_unchanged"] and {x["script"] for x in reg["tests"] if not x["passed"]}=={"test_economy_alarm.gd","test_observer_camera.gd","test_worker_actions.gd","test_frame_contracts.gd"}
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
# Keep complete source semantics for this QA project. These two old helpers
# remain excluded from the formal42-script export contract.
support={}
for n in ["unit_motion.gd","worker_motion.gd"]:
    p=QA/"baseline-runtime/scripts"/n
    shutil.copy2(p,BASE/"scripts"/n);support[n]=sha(p)
for p in (ROOT/"game/tests").glob("*.gd"):
    dest=BASE/"tests"/p.name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest)
shutil.copytree(BASE,CANDIDATE)
shutil.copy2(QA/"marching-r3-runtime/scripts/battle_sim.gd",CANDIDATE/"scripts/battle_sim.gd")
for n,d in freeze["public_inputs"].items():assert sha(ROOT/n)==d,n
(QA/"native-preparation.json").write_text(json.dumps({"passed":True,"public_inputs":freeze["public_inputs"],
    "native_imports":imports,"generator_sha256":sha(Path(__file__)),"partial_semantic_receipt_sha256":sha(partial),
    "failed_minimal_regression_sha256":sha(QA/"candidate-regression-r3/report.json"),"additional_source_only_helpers":support,
    "candidate_changed_scripts":{"battle_sim.gd":sha(CANDIDATE/"scripts/battle_sim.gd")},
    "scope":"QA resource preparation only, not a passed complete regression yet. Frozen1194 RC32 export-selected raw inputs and455 native imports, plus two excluded legacy source helpers and source tests for full44-script source closure. Candidate changes exactly1 simulation script. Earlier CPU behavior gates passed; missing-resource regression retained. Formal source/export/art untouched."
},indent=2)+"\n","utf-8")
print("Prepared complete native RC32/R3 source QA projects; imports",len(imports))
