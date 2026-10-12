"""Complete the RC34 validation receipt after the formal-hammer retry."""
from pathlib import Path
import hashlib
import json

ROOT=Path(__file__).resolve().parents[2]
QA=ROOT/"output/qa/godot/render-runtime-rc34"
FINAL=QA/"release-final"
VERSION="3.0.0-rc34-preview"
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
progress=json.loads((FINAL/"validation-progress.json").read_text("utf-8"))
rows=progress["jobs"]
assert len(rows)==16 and all(r["passed"] for r in rows[:-1]) and rows[-1]["name"]=="formal-hammer" and not rows[-1]["passed"]
hammer=json.loads((QA/"formal-hammer/verification.json").read_text("utf-8"))
assert hammer["passed"] and not hammer["errors"]
rows[-1]={"name":"formal-hammer","passed":True,"exit_code":0,"retry":"formal-hammer-retry"}
realtime=json.loads((FINAL/"realtime/report.json").read_text("utf-8"))
assert realtime["passed"] and realtime["version"]==VERSION
rows.append({"name":"native-realtime","passed":True,"exit_code":0,"retry":"native-realtime-direct"})
progress={"version":VERSION,"jobs":rows}
(FINAL/"validation-progress.json").write_text(json.dumps(progress,indent=2)+"\n","utf-8")
runner=ROOT/"tools/paper-warfront/run_rc34_release_validation.py"
assert sha(FINAL/"validation-runner.py")==sha(runner)
(FINAL/"validation-report.json").write_text(json.dumps({
    "passed":True,"version":VERSION,"runner_sha256":sha(runner),"jobs":rows,
    "scope":"Fresh RC34 native exports, compiled code, UI/plot/map/render/ownership checks and direct retry of formal hammer plus native realtime after the source binding correction. Natural FPS is observational; dense60FPS, all-faction/campaign balance, human story/network and physical Android remain pending."
},indent=2)+"\n","utf-8")
print(json.dumps({"passed":True,"jobs":len(rows),"runner_sha256":sha(runner)}))
