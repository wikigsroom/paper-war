"""Derive R4b gate runners from completed R3 runners; preserve earlier evidence."""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[2]
QA = ROOT / "output/qa/godot/render-runtime-rc34"
TOOLS = ROOT / "tools/paper-warfront"
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
records = {}
def derive(name, source, replacements):
    dst = TOOLS / name
    assert not dst.exists()
    text = (TOOLS / source).read_text("utf-8")
    for a,b in replacements:text=text.replace(a,b)
    dst.write_text(text,"utf-8")
    records[name]={"source":source,"source_sha256":sha(TOOLS/source),"derived_sha256":sha(dst)}
derive("run_rc34_visibility_gates.py","run_rc34_shards_gates.py",[("shards-r3","visibility-r4b"),("shards R3","visibility R4b"),("shards-r3-preparation.json","visibility-r4b-preparation.json")])
derive("check_rc34_visibility_render.py","check_rc34_shards_render.py",[("shards-render-observer.gd","shards-render-observer.gd")])
derive("observe_rc34_visibility.py","observe_rc34_shards.py",[("shards-r3","visibility-r4b"),("shard R3","visibility R4b")])
(QA/"visibility-gate-preparation.json").write_text(json.dumps({"passed":True,"generator_sha256":sha(Path(__file__)),"derivations":records,
    "scope":"New runners only. R4b changes battle_view location visibility calls and uses inherited 42-pose observer; all source/render/natural evidence is independent and new. R3 artifacts remain immutable."
},indent=2)+"\n","utf-8")
print("Prepared R4b visibility gates",flush=True)
