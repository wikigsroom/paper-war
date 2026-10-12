"""Bind the failed RC32-based visibility trial as non-adoptable evidence."""
from pathlib import Path
import hashlib
import json

ROOT=Path(__file__).resolve().parents[2]
QA=ROOT/"output/qa/godot/render-runtime-rc34"
OUT=QA/"visibility-r4b-rejection.json"
assert not OUT.exists()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert not (QA/"adoption.json").exists()
OUT.write_text(json.dumps({"passed":False,"rejected":True,"preparation_sha256":sha(QA/"visibility-r4b-preparation.json"),"source_gate_sha256":sha(QA/"visibility-r4b-source-gates.json"),"render_report_sha256":sha(QA/"visibility-r4b-render/report.json"),"natural_report_sha256":sha(QA/"visibility-r4b-natural-observation.json"),"reason":"R4b was correctly tested from the frozen RC32 baseline-runtime. Its pixels and performance evidence are valid for that baseline but it does not include RC33's formal marching and ownership changes, so it cannot be adopted over current game sources. No game files were changed."},indent=2)+"\n","utf-8")
print("Rejected RC32-derived R4b for adoption; evidence retained",flush=True)
