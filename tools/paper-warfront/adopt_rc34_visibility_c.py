"""Adopt RC33-derived R4c after exact pixels and repeated native source benefit."""
from pathlib import Path
import hashlib
import json
import shutil

ROOT=Path(__file__).resolve().parents[2]
QA=ROOT/"output/qa/godot/render-runtime-rc34"
HISTORY=ROOT/"output/qa/godot/phase-runtime-rc33"
VERSION="3.0.0-rc34-preview"
TRIAL=QA/"visibility-r4c-runtime"
SOURCE=HISTORY/"native-ownership-r1-runtime"
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text("utf-8"))
assert not (QA/"adoption.json").exists()
baseline=read(QA/"baseline-build-manifest.json");assert baseline["version"]=="3.0.0-rc33-preview"
assert all(sha(ROOT/n)==h for n,h in baseline["source_inputs"].items())
for n in ["visibility-r4c-preparation.json","visibility-r4c-source-gates.json","visibility-r4c-render/report.json","visibility-r4c-natural-observation.json"]:assert read(QA/n)["passed"]
gate=read(QA/"visibility-r4c-source-gates.json");assert gate["jobs"][0]["groups"]==78 and gate["jobs"][0]["checks"]==195435
pixels=read(QA/"visibility-r4c-render/report.json");assert pixels["passed"] and len(pixels["comparisons"])==42 and all(r["max_channel_delta"]==0 for r in pixels["comparisons"])
cases=read(QA/"visibility-r4c-natural-observation.json")["cases"];base=[r for r in cases if r["label"]=="baseline"];trial=[r for r in cases if r["label"]=="candidate"];assert len(base)==len(trial)==2
assert max(r["draw_mean_ms"] for r in trial)<min(r["draw_mean_ms"] for r in base)
assert max(r["particles_snapshot_mean_ms"] for r in trial)<min(r["particles_snapshot_mean_ms"] for r in base)
# Confirm current RC33 code is the exact candidate used as the R4c baseline.
for n in ["battle_sim.gd","battle_visibility.gd","theatre_fog.gd","unit_frame_player.gd"]:assert sha(ROOT/"game/scripts"/n)==sha(SOURCE/"scripts"/n),n
assert sha(ROOT/"game/scripts/battle_view.gd")==sha(SOURCE/"scripts/battle_view.gd")
changed=[]
for n in ["battle_view.gd","battle_sim.gd","battle_visibility.gd","unit_frame_player.gd"]:
    if sha(TRIAL/"scripts"/n)!=sha(SOURCE/"scripts"/n):changed.append(n)
assert changed==["battle_view.gd"],changed
backup=QA/"pre-adoption";assert not backup.exists();changed_inputs={}
for n in ["scripts/battle_view.gd","project.godot","export_presets.cfg"]:
    path=ROOT/"game"/n;old=backup/n;old.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,old)
    if n.startswith("scripts/"):shutil.copy2(TRIAL/n,path)
    else:
        s=path.read_text("utf-8").replace(baseline["version"],VERSION)
        if n=="export_presets.cfg":assert s.count("version/code=30032")==1;s=s.replace("version/code=30032","version/code=30033")
        path.write_text(s,"utf-8")
    changed_inputs["game/"+n]={"before":sha(old),"after":sha(path)}
unchanged={n:h for n,h in baseline["source_inputs"].items() if n not in changed_inputs};assert len(unchanged)==1191 and all(sha(ROOT/n)==h for n,h in unchanged.items())
for dest in [QA/"source-final",QA/"formal-reach/regression"]:shutil.copytree(QA/"visibility-r4c-regression",dest)
previous=ROOT/"output/qa/godot/phase-runtime-rc33";shutil.copy2(previous/"authorship.json",QA/"authorship.json")
font=read(previous/"font-coverage.json");assert font["passed"] and all(sha(ROOT/r["path"])==r["sha256"] for r in font["records"])
font["retained_report_sha256"]=sha(previous/"font-coverage.json");font["retained_from_version"]=font["version"];font["version"]=VERSION;font["retention_scope"]="Byte-identical200-map story/data and fonts; one view-only visibility cache."
(QA/"font-coverage.json").write_text(json.dumps(font,ensure_ascii=False,indent=2)+"\n","utf-8")
(QA/"combat-history-binding.json").write_text(json.dumps({"passed":True,"previous_version":baseline["version"],"current_version":VERSION,"changed_inputs":changed_inputs,"unchanged_inputs":unchanged,"campaign_battle_fields_unchanged":True,"story_progression_unchanged":True,"previous_verification_sha256":sha(ROOT/"release/3.0.0-rc33-preview/preview-verification.json"),"scope":"One battle_view cache change and version fields;1191 public inputs identical. All200 story maps/branches, AI, prices, actions, art/UI/fonts, RC33 marching and ownership logic retained."},indent=2)+"\n","utf-8")
(QA/"adoption.json").write_text(json.dumps({"passed":True,"release":VERSION,"changed_inputs":changed_inputs,"proofs":{n:sha(QA/n) for n in ["visibility-r4c-preparation.json","visibility-r4c-source-gates.json","visibility-r4c-render/report.json","visibility-r4c-natural-observation.json"]},"runner_sha256":sha(Path(__file__)),"source_groups":78,"source_checks":195435,"source_pixel_pairs":42,"natural_abba_windows":4,"generated_raster_assets":False,"scope":"R4c is derived from complete RC33 ownership/marching candidate. Per-draw location visibility cache clears each draw and uses exact Vector2 keys; original fog/observer state remains live. It reduces repeated view-side map projection queries without changing the simulation, particle count, animation, status effects, map/story or UI."},indent=2)+"\n","utf-8")
print("Adopted RC33-derived visibility cache R4c; RC34 exports pending",flush=True)
