"""Apply the revision-safe cache correction before RC34 packaging."""
from pathlib import Path
import hashlib
import json
import shutil

ROOT=Path(__file__).resolve().parents[2]
QA=ROOT/"output/qa/godot/render-runtime-rc34"
TRIAL=QA/"visibility-r4d-runtime"
OUT=QA/"visibility-r4d-correction.json"
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert not OUT.exists()
assert json.loads((QA/"visibility-r4d-source-gates.json").read_text("utf-8"))["passed"]
pixels=json.loads((QA/"visibility-r4d-render/report.json").read_text("utf-8"))
assert pixels["passed"] and len(pixels["comparisons"])==42 and all(r["max_channel_delta"]==0 for r in pixels["comparisons"])
mobile=QA/"visibility-r4d-mobile/compact-16x9/report.json"
assert json.loads(mobile.read_text("utf-8"))["passed"]
target=ROOT/"game/scripts/battle_view.gd";before=sha(target);trial=TRIAL/"scripts/battle_view.gd";assert before!=sha(trial)
backup=QA/"pre-r4d-correction";assert not backup.exists();backup.mkdir();shutil.copy2(target,backup/target.name);shutil.copy2(trial,target)
after=sha(target);assert after==sha(trial)
(QA/"combat-history-binding-r4d.json").write_text(json.dumps({"passed":True,"version":"3.0.0-rc34-preview","base_binding_sha256":sha(QA/"combat-history-binding.json"),"changed_file":"game/scripts/battle_view.gd","before_sha256":before,"after_sha256":after,"source_gate_sha256":sha(QA/"visibility-r4d-source-gates.json"),"pixel_report_sha256":sha(QA/"visibility-r4d-render/report.json"),"mobile_report_sha256":sha(mobile),"reason":"R4c cache was valid during _draw but could retain a coordinate between map/fog transitions when route_sign_rect was queried from input. R4d invalidates on reset, visibility.revision and observer side; the compact native mobile route/fork matrix passes again.","scope":"One corrective view script only; simulation, map/story, fog model, actions, assets and UI unchanged."},indent=2)+"\n","utf-8")
OUT.write_text(json.dumps({"passed":True,"version":"3.0.0-rc34-preview","before_sha256":before,"after_sha256":after,"source_groups":78,"source_checks":195435,"pixel_pairs":42,"mobile_cases":1,"base_adoption_sha256":sha(QA/"adoption.json"),"scope":"Corrective amendment to the not-yet-packaged RC34 source. R4c adoption evidence remains immutable; R4d fixes cache invalidation before package export. No release artifact has been claimed yet."},indent=2)+"\n","utf-8")
print("Applied R4d revision-safe invalidation correction",flush=True)
