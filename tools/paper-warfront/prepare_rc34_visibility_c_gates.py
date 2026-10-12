"""Prepare gates comparing RC33 ownership candidate against R4c."""
from pathlib import Path
import hashlib
import json

ROOT=Path(__file__).resolve().parents[2]
QA=ROOT/"output/qa/godot/render-runtime-rc34"
TOOLS=ROOT/"tools/paper-warfront"
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
records={}
source=TOOLS/"run_rc34_shards_gates.py"
dst=TOOLS/"run_rc34_visibility_c_gates.py";assert not dst.exists()
s=source.read_text("utf-8").replace("shards-r3","visibility-r4c").replace("shards R3","visibility R4c")
s=s.replace('freeze["trial_scripts"]','{p.name: sha(p) for p in (PROJECT / "scripts").glob("*.gd")}')
dst.write_text(s,"utf-8");records[dst.name]={"source":source.name,"source_sha256":sha(source),"derived_sha256":sha(dst)}
source=TOOLS/"check_rc34_shards_render.py";dst=TOOLS/"check_rc34_visibility_c_render.py";assert not dst.exists()
s=source.read_text("utf-8").replace("shards-render-observer.gd","shards-render-observer.gd")
dst.write_text(s,"utf-8");records[dst.name]={"source":source.name,"source_sha256":sha(source),"derived_sha256":sha(dst)}
source=TOOLS/"observe_rc34_shards.py";dst=TOOLS/"observe_rc34_visibility_c.py";assert not dst.exists()
s=source.read_text("utf-8").replace("shards-r3","visibility-r4c").replace("shard R3","visibility R4c")
s=s.replace('project = QA / ("baseline-runtime" if label == "baseline" else "visibility-r4c-runtime")', 'project = ROOT / ("output/qa/godot/phase-runtime-rc33/native-ownership-r1-runtime" if label == "baseline" else "output/qa/godot/render-runtime-rc34/visibility-r4c-runtime")')
s=s.replace('"shards-r3-source-gates.json"','"visibility-r4c-source-gates.json"').replace('"shards-r3-render/report.json"','"visibility-r4c-render/report.json"')
dst.write_text(s,"utf-8");records[dst.name]={"source":source.name,"source_sha256":sha(source),"derived_sha256":sha(dst)}
(QA/"visibility-r4c-gate-preparation.json").write_text(json.dumps({"passed":True,"generator_sha256":sha(Path(__file__)),"derivations":records,"scope":"R4c-only gates. Baseline is the complete RC33 native ownership candidate; R4c adds one view cache. R3/R4b evidence remains unchanged and non-authoritative for adoption."},indent=2)+"\n","utf-8")
print("Prepared RC33-derived R4c gates",flush=True)
