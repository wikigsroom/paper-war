"""Adopt verified native target/fog lookup candidates, preserving RC31 inputs."""
from pathlib import Path
import hashlib
import json
import shutil

ROOT=Path(__file__).resolve().parents[2]
QA=ROOT/"output/qa/godot/contact-runtime-rc32"
VERSION="3.0.0-rc32-preview"
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text("utf-8"))
assert not (QA/"adoption.json").exists()
baseline=read(QA/"baseline-build-manifest.json")
assert baseline["version"]=="3.0.0-rc31-preview"
assert all(sha(ROOT/n)==d for n,d in baseline["source_inputs"].items())
candidate=QA/"native-answers-r1-runtime"
regression=read(QA/"candidate-regression-r1/report.json")
assert regression["passed"] and regression["source_unchanged"] and len(regression["tests"])==78
assert sum(r["checks"] for r in regression["tests"])==195435
proofs={}
for name,expected in [("answers-capacity-r1.json",3600),("answers-paid-r1.json",73103),
    ("answers-phase-r1.json",21607),("answers-lookup-boundary-r1.json",619103)]:
    x=read(QA/name);assert x["passed"] and x["checks"]==expected and not x["failures"]
    if "simulation_sha256" in x:assert x["simulation_sha256"]==sha(candidate/"scripts/battle_sim.gd")
    assert x["baseline_sha256"]==sha(QA/"oracle-runtime/scripts/battle_sim.gd")
    proofs[name]=sha(QA/name)
for name in ["native-baseline-stress-r1","native-answers-stress-r1"]:
    p=QA/name/"receipt.json";assert read(p)["passed"];proofs[name+"/receipt.json"]=sha(p)
proofs["candidate-regression-r1/report.json"]=sha(QA/"candidate-regression-r1/report.json")
backup=QA/"pre-adoption";assert not backup.exists();backup.mkdir()
changed={}
for name in ["scripts/battle_sim.gd","scripts/battle_visibility.gd","project.godot","export_presets.cfg"]:
    before=ROOT/"game"/name;saved=backup/name;saved.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(before,saved)
    if name.startswith("scripts/"):shutil.copy2(candidate/name,before)
    else:
        old=before.read_text("utf-8");new=old.replace(baseline["version"],VERSION)
        if name=="export_presets.cfg":
            assert new.count("version/code=30030")==1;new=new.replace("version/code=30030","version/code=30031")
        assert new!=old;before.write_text(new,"utf-8")
    changed["game/"+name]={"before":sha(saved),"after":sha(before)}
assert all(sha(ROOT/n)==d for n,d in regression["inputs"].items())
shutil.copytree(QA/"candidate-regression-r1",QA/"source-final")
shutil.copytree(QA/"candidate-regression-r1",QA/"formal-reach/regression")
previous=ROOT/"output/qa/godot/pressure-runtime-rc31"
shutil.copy2(previous/"authorship.json",QA/"authorship.json")
font=read(previous/"font-coverage.json")
assert font["passed"] and all(sha(ROOT/r["path"])==r["sha256"] for r in font["records"])
font["retained_from_version"]=font["version"];font["version"]=VERSION
font["retained_report_sha256"]=sha(previous/"font-coverage.json")
font["retention_scope"]="Byte-identical200-map narrative, data and fonts; retained glyph coverage, no new text or glyph generation."
(QA/"font-coverage.json").write_text(json.dumps(font,ensure_ascii=False,indent=2)+"\n","utf-8")
unchanged={n:d for n,d in baseline["source_inputs"].items() if n not in changed}
assert len(unchanged)==1190 and all(sha(ROOT/n)==d for n,d in unchanged.items())
binding={"passed":True,"previous_version":baseline["version"],"current_version":VERSION,
    "changed_inputs":changed,"unchanged_inputs":unchanged,
    "campaign_battle_fields_unchanged":True,"story_progression_unchanged":True,
    "previous_verification_sha256":sha(ROOT/"release/3.0.0-rc31-preview/preview-verification.json"),
    "scope":"Two simulation/query helper changes, exactly1190 unchanged public inputs: all story/maps/AI/price/actions/art/UI/fonts and42 other scripts. New every-step RC31 complete-closure comparisons are fresh; story authoring/font coverage retained by identical data hashes."}
(QA/"combat-history-binding.json").write_text(json.dumps(binding,ensure_ascii=False,indent=2)+"\n","utf-8")
(QA/"adoption.json").write_text(json.dumps({"passed":True,"release":VERSION,"changed_inputs":changed,
    "proofs":proofs,"generated_raster_assets":False,"source_base_checks":195435,
    "new_source_boundary_checks":640710,"source_total_assertions":836145,
    "fresh_capacity_state_steps":3600,"fresh_normal_paid_state_steps":73103,
    "scope":"Bounded answers only during native dense simultaneous unit phase, exact geometry and source parameters, per-phase eligibility, immediate lethal/TTL invalidation. Refresh-local ordered fog actor lookup with scalar-ID fallback. Native frame observations are separate, not a60FPS guarantee; compiled exports remain to validate."
},indent=2)+"\n","utf-8")
print("Adopted verified native query candidates; RC32 compiled exports remain")
