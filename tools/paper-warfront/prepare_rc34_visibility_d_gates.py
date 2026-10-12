"""Derive R4d source, pixel and natural observers from R4c gates."""
from pathlib import Path
import hashlib
import json

ROOT=Path(__file__).resolve().parents[2]
QA=ROOT/"output/qa/godot/render-runtime-rc34"
TOOLS=ROOT/"tools/paper-warfront"
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
records={}
def derive(name,source,repl):
    dst=TOOLS/name;assert not dst.exists();s=(TOOLS/source).read_text("utf-8")
    for a,b in repl:s=s.replace(a,b)
    dst.write_text(s,"utf-8");records[name]={"source":source,"source_sha256":sha(TOOLS/source),"derived_sha256":sha(dst)}
derive("run_rc34_visibility_d_gates.py","run_rc34_visibility_c_gates.py",[("r4c","r4d"),("R4c","R4d")])
derive("check_rc34_visibility_d_render.py","check_rc34_visibility_c_render.py",[("r4c","r4d"),("R4c","R4d")])
derive("observe_rc34_visibility_d.py","observe_rc34_visibility_c.py",[("r4c","r4d"),("R4c","R4d")])
(QA/"visibility-r4d-gate-preparation.json").write_text(json.dumps({"passed":True,"generator_sha256":sha(Path(__file__)),"derivations":records,"scope":"R4d gate tools only. R4d is RC33-derived R4c plus revision-safe invalidation; R4c and R4b evidence are retained separately."
},indent=2)+"\n","utf-8")
print("Prepared R4d gates",flush=True)
