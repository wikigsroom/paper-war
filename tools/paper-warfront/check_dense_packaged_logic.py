"""Exercise retention/invalidations against actual compiled pack script bytes."""
from pathlib import Path
import argparse
import hashlib
import json
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[2]
ap = argparse.ArgumentParser()
runtime = ap.add_mutually_exclusive_group(required=True)
runtime.add_argument('--pack', type=Path)
runtime.add_argument('--apk-runtime', type=Path)
ap.add_argument('--artifact', type=Path, required=True)
ap.add_argument('--output', type=Path, required=True)
args = ap.parse_args()
folder = args.output.resolve()
assert not folder.exists(), 'Never overwrite a completed/started compiled observation'
folder.mkdir(parents=True)
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
for name in ['test_exact_query_retention.gd','test_stationary_projection.gd',
             'dense_reference_target_search.gd','dense_reference_map_runtime.gd']:
    shutil.copy2(ROOT/'tools/paper-warfront'/name,folder/name)
shutil.copy2(Path(__file__),folder/'runner.py')
artifact = args.artifact.resolve()
if args.pack:
    assert args.pack.resolve()==artifact
    flags=['--main-pack',str(artifact)]
else:
    project=args.apk_runtime.resolve()
    assert not list((project/'scripts').glob('*.gd'))
    for name in ['battle_sim','map_runtime','battle_visibility']:
        assert (project/'scripts'/(name+'.gdc')).is_file()
    flags=['--path',str(project)]
reports=[]
for name,expected in [('test_exact_query_retention',25600),('test_stationary_projection',77320)]:
    path=folder/(name+'.json')
    cmd=[str(ROOT/'.tools/godot/Godot_v4.7.2-stable_win64_console.exe'),'--headless',*flags,
         '--script',str(folder/(name+'.gd')),'--','--output',str(path)]
    result=subprocess.run(cmd,cwd=ROOT,capture_output=True,encoding='utf-8',errors='replace',timeout=120)
    log=result.stdout+result.stderr
    (folder/(name+'.log')).write_text(log,'utf-8')
    assert result.returncode==0 and 'SCRIPT ERROR' not in log and 'ERROR:' not in log,log[-3500:]
    row=json.loads(path.read_text('utf-8'))
    assert row['passed'] and not row['failures'] and row['checks']==expected
    assert row['observer_sha256']==sha(folder/(name+'.gd'))
    if name=='test_exact_query_retention':assert row['reference_sha256']==sha(folder/'dense_reference_target_search.gd')
    else:assert row['baseline_sha256']==sha(folder/'dense_reference_map_runtime.gd')
    if not args.pack:
        compiled='battle_sim' if name=='test_exact_query_retention' else 'map_runtime'
        assert row['source_sha256']==sha(project/'scripts'/(compiled+'.gdc'))
    reports.append({'name':name,'checks':expected,'report_sha256':sha(path),'compiled_script_sha256':row['source_sha256']})
    print(name,'actual bytecode',expected,'passed',flush=True)
(folder/'report.json').write_text(json.dumps({'passed':True,'artifact':artifact.as_posix(),
    'artifact_sha256':sha(artifact),'runtime_kind':'windows_embedded_pack' if args.pack else 'apk_extracted_bytecode_on_windows',
    'checks':sum(r['checks'] for r in reports),'tests':reports,
    'observer_inputs':{p.name:sha(p) for p in folder.glob('*.gd')},
    'scope':'Actual compiled target/geometry code with independent raw prior references, every200 map and both directions, replacement/death/conversion/floating-point/geometry edits and bounded memory. APK bytecode on Windows is not Android hardware.'},indent=2)+'\n','utf-8')
