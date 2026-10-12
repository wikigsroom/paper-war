"""Correct the observer preparation assertion; preserve the failed attempt."""
from pathlib import Path
import hashlib
import json

ROOT=Path(__file__).resolve().parents[2]
QA=ROOT/"output/qa/godot/render-runtime-rc34"
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
src=QA/"shards-render-observer.gd";dst=QA/"visibility-c-render-observer-b.gd";assert not dst.exists()
s=src.read_text("utf-8")
s=s.replace("var mesh_checks: Array=[]\n","var mesh_checks: Array=[]\nvar visibility_checks: Array=[]\n")
needle='\t\t\tif app.view.get_property_list().any(func(info):return str(info.name)=="retained_shard_meshes"): '
needle=needle.rstrip()
assert s.count(needle)==1
extra='''\t\t\tif app.view.get_property_list().any(func(info):return str(info.name)=="draw_visibility_cache"):
\t\t\t\tvar entries: int=app.view.draw_visibility_cache.size()
\t\t\t\tvisibility_checks.append({"pose":map_id+"-"+str(phase),"entries":entries,"passed":entries>=0 and entries<=1000})
\t\t\t\tif not visibility_checks[-1].passed:print("VISIBILITY_CACHE_FAILURE ",visibility_checks[-1]);quit(1);return
'''
s=s.replace(needle,extra+needle)
s=s.replace('"mesh_checks":mesh_checks}', '"mesh_checks":mesh_checks,"visibility_checks":visibility_checks}')
dst.write_text(s,"utf-8")
runner=ROOT/"tools/paper-warfront/check_rc34_visibility_c_render.py";assert runner.exists()
old=runner.read_text("utf-8");old=old.replace("shards-render-observer.gd","visibility-c-render-observer-b.gd");runner.write_text(old,"utf-8")
(QA/"visibility-c-render-preparation-b.json").write_text(json.dumps({"passed":True,"generator_sha256":sha(Path(__file__)),"source_observer_sha256":sha(src),"observer_sha256":sha(dst),"runner_sha256":sha(runner),"failed_preparation_sha256":sha(Path(__file__).with_name("prepare_rc34_visibility_c_render.py")),"scope":"Compiled R4c observer adds per-capture visibility cache metadata while retaining inherited42 image poses. Previous preparation failed only because its exact source line included a trailing-space mismatch; no runtime was launched by that failed preparation."},indent=2)+"\n","utf-8")
print("Prepared corrected R4c compiled visibility observer",flush=True)
