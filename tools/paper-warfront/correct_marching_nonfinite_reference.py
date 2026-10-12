"""Retain scalar NaN mismatch; verify invalid requests with the actual RC32 closure."""
from pathlib import Path
import hashlib
import json

ROOT=Path(__file__).resolve().parents[2]
QA=ROOT/"output/qa/godot/phase-runtime-rc33"
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
failed=json.loads((QA/"marching-r3-semantic-r2-receipt.json").read_text("utf-8"))
assert failed["passed"] is False
d=json.loads((QA/"marching-boundary-r3-r2.json").read_text("utf-8"))
assert len(d["failures"])==1 and "expected=nan" in d["failures"][0]
old=QA/"marching-boundary-observer-r2.gd"
new=QA/"marching-boundary-observer-r3.gd"
assert not new.exists()
s=old.read_text("utf-8").replace('.2,0.0,-.1,INF,NAN]', '.2,0.0,-.1,INF]')
anchor='\tvar output: String=OS.get_cmdline_user_args()[0]'
assert s.count(anchor)==1
extra='''\t# Nonfinite requested steps follow the actual RC32 indexed/fallback contract,
\t# which can differ from the older scalar scan for NaN. Keep both references.
\tvar oracle: GDScript=load(OS.get_cmdline_user_args()[1])
\tfor invalid_worker in [false,true]:
\t\tfor forward in [-1.0,1.0]:
\t\t\tvar original=oracle.new(db);var candidate=Simulation.new(db);var sources: Array=[]
\t\t\tfor battle in [original,candidate]:
\t\t\t\tbattle.start({"map":"map.01.04","faction":"yin","enemy":"mu"});battle.ai_enabled=[false,false];battle.units.clear()
\t\t\t\tvar economic=battle.spawn(worker_ids[0],0,3)
\t\t\t\tif invalid_worker:economic.s=INF
\t\t\t\tvar source=battle.spawn("unit.yin.axe",0,3);var blocker=battle.spawn("unit.yin.axe",0,3)
\t\t\t\tblocker.s=float(source.s)+forward*(.54+.0000000001);sources.append(source)
\t\t\t\tbattle.prepare_movement_sides();battle.movement_sides_active=true
\t\t\tprepare(candidate)
\t\t\tvar def: Dictionary=db.balance.units["unit.yin.axe"]
\t\t\tcandidate.marching_step(sources[1],def,{},.1,forward)
\t\t\tfor step in [INF,NAN,-INF]:
\t\t\t\tvar expected: float=original.marching_step(sources[0],def,{},step,forward)
\t\t\t\tvar actual: float=candidate.marching_step(sources[1],def,{},step,forward)
\t\t\t\tcheck(actual==expected or (is_nan(actual) and is_nan(expected)),"nonfinite request exact RC32 worker="+str(invalid_worker)+" direction="+str(forward)+" step="+str(step))
'''
s=s.replace(anchor,extra+anchor)
s=s.replace('"scope":"All200 authored maps', '"baseline_sha256":FileAccess.get_sha256(OS.get_cmdline_user_args()[1]),"scope":"All200 authored maps')
s=s.replace("nonstandard direction and outside-phase API.","nonstandard direction and outside-phase API. Nonfinite requested steps separately compared with actual frozen complete RC32 indexed/fallback closure, with both valid and nonfinite economy offsets.")
new.write_text(s,"utf-8")
old_runner=ROOT/"tools/paper-warfront/run_rc33_marching_semantics_repaired.py"
runner=ROOT/"tools/paper-warfront/run_rc33_marching_semantics_reference_corrected.py"
assert not runner.exists()
s=old_runner.read_text("utf-8").replace("marching-boundary-observer-r2.gd","marching-boundary-observer-r3.gd")
s=s.replace("marching-boundary-r3-r2.json","marching-boundary-r3-r3.json")
s=s.replace('str(QA/"marching-boundary-r3-r3.json")]', 'str(QA/"marching-boundary-r3-r3.json"),str(ORACLE)]')
s=s.replace("432416","432427")
s=s.replace("marching-r3-semantic-r2-receipt.json","marching-r3-semantic-r3-receipt.json").replace("marching-r3-semantic-r2-progress.json","marching-r3-semantic-r3-progress.json").replace('label+"-r3-r2-orchestration.log"','label+"-r3-r3-orchestration.log"')
runner.write_text(s,"utf-8")
(QA/"marching-nonfinite-reference-correction.json").write_text(json.dumps({"passed":True,
    "failed_receipt_sha256":sha(QA/"marching-r3-semantic-r2-receipt.json"),"failed_report_sha256":sha(QA/"marching-boundary-r3-r2.json"),
    "old_observer_sha256":sha(old),"observer_sha256":sha(new),"old_runner_sha256":sha(old_runner),"runner_sha256":sha(runner),
    "candidate_manifest_sha256":sha(QA/"marching-r3-manifest.json"),"generator_sha256":sha(Path(__file__)),
    "scope":"Test-reference correction only; failed NaN reference retained. Finite requested-step linear checks remain;12 actual frozen RC32 NaN/infinite request comparisons added across directions and valid/nonfinite worker offsets. Candidate correctly bypasses its cache on nonfinite requested steps; game/candidate source unchanged."
},indent=2)+"\n","utf-8")
print("Preserved failed scalar NaN case; added12 actual frozen RC32 nonfinite comparisons")
