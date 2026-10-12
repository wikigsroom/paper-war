"""Prepare RC35 source, pixel and natural observers from the proven R4d gates."""
from pathlib import Path
import hashlib
import json

ROOT=Path(__file__).resolve().parents[2]
QA=ROOT/"output/qa/godot/render-runtime-rc35"
TOOLS=ROOT/"tools/paper-warfront"
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
records={}
def derive(name,source,replacements):
    dst=TOOLS/name;assert not dst.exists()
    text=(TOOLS/source).read_text("utf-8")
    for old,new in replacements:text=text.replace(old,new)
    dst.write_text(text,"utf-8")
    records[name]={"source":source,"source_sha256":sha(TOOLS/source),"derived_sha256":sha(dst)}
derive("run_rc35_atlas_gates.py","run_rc34_visibility_d_gates.py",[("rc34","rc35"),("R4d","RC35 atlas") ,("visibility-r4d","atlas-cache")])
derive("check_rc35_atlas_render.py","check_rc34_visibility_d_render.py",[("rc34","rc35"),("R4d","RC35 atlas"),("visibility-r4d","atlas-cache")])
derive("observe_rc35_atlas.py","observe_rc34_visibility_d.py",[("rc34","rc35"),("R4d","RC35 atlas"),("visibility-r4d","atlas-cache")])
(QA/"gate-preparation.json").write_text(json.dumps({"passed":True,"generator_sha256":sha(Path(__file__)),"derivations":records,"scope":"RC35 atlas-handle cache gates derived from the revision-safe R4d source/pixel/natural observers; failed candidates remain isolated until all evidence is complete."},ensure_ascii=False,indent=2)+"\n","utf-8")
print("Prepared RC35 atlas cache gates",flush=True)
