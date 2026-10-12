"""Freeze the released gameplay source before diagnosing sustained capacity load."""
from pathlib import Path
import hashlib,json,shutil
ROOT=Path(__file__).resolve().parents[2]
QA=ROOT/'output/qa/godot/capacity-performance-rc27'
dest=QA/'baseline-runtime';assert not dest.exists(), 'Never overwrite frozen source'
dest.mkdir(parents=True)
for part in ['scripts','data']:
 shutil.copytree(ROOT/'game'/part,dest/part)
(dest/'tests').mkdir()
(dest/'project.godot').write_text('config_version=5\n[application]\nconfig/name="Capacity CPU diagnosis"\n[rendering]\nrenderer/rendering_method="gl_compatibility"\n','utf-8')
for name in ['capacity_cpu_profiler.gd','probe_capacity_cpu.gd']:
 shutil.copyfile(ROOT/'tools/paper-warfront'/name,dest/'tests'/name)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
request=json.loads((ROOT/'output/qa/godot/realtime-performance-rc26/release/realtime/stress/report.json').read_text('utf-8'))
(dest/'capacity-config.json').write_text(json.dumps(request['config'],ensure_ascii=False,indent=2),'utf-8')
(dest/'inputs.json').write_text(json.dumps({'scope':'Exact rc26 source scripts/data; native CPU sustained Yin/Mu capacity fixture matches real-time config. No render or paid-play evidence.',
 'pack_sha256':sha(ROOT/'release/3.0.0-rc26-preview/windows/PaperWarfront.exe'),
 'inputs':{p.relative_to(dest).as_posix():sha(p) for p in sorted(dest.rglob('*')) if p.is_file()}},indent=2),'utf-8')
print('Frozen sustained capacity runtime')
