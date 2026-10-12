"""Run additional compiled native observers serially, before FPS observations."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
p = argparse.ArgumentParser()
p.add_argument('--version', required=True)
p.add_argument('--qa', type=Path, required=True)
p.add_argument('--before-version', default='3.0.0-rc27-preview')
p.add_argument('--reuse-story-ui', action='store_true', help='Use an already completed story UI proof for this identical compiled pack.')
a = p.parse_args()
qa = a.qa.resolve()
qa.mkdir(parents=True, exist_ok=True)
assert not (qa / 'extras-runner-report.json').exists()
shutil.copyfile(Path(__file__), qa / 'extras-runner.py')
pack = ROOT / f'release/{a.version}/windows/PaperWarfront.exe'
before = ROOT / f'release/{a.before_version}/windows/PaperWarfront.exe'
jobs = [('render-cache', 'check_render_cache_equivalence.py', ['--before-pack', before, '--after-pack', pack]),
        ('story-ui-final', 'check_story_routes_ui.py', ['--pack', pack]),
        ('normal-fielding', 'check_paid_fielding_render.py', ['--pack', pack]),
        ('stalled-front', 'check_stalled_front_render.py', ['--pack', pack])]
rows = []
for label, script, flags in jobs:
    if label=='story-ui-final' and a.reuse_story_ui:
        import hashlib
        proof=json.loads((qa/label/'report.json').read_text('utf-8'))
        digest=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
        assert proof['passed'] and proof['pack_sha256']==digest(pack)
        assert proof['observer_sha256']==digest(ROOT/'tools/paper-warfront/probe_story_routes_ui.gd')
        for case in proof['cases']:assert digest(qa/label/case['name']/'report.json')==case['report_sha256']
        rows.append({'name':label,'passed':True,'reused_identical_pack_proof':True})
        print(label,'completed identical-pack proof retained',flush=True)
        continue
    cmd = [sys.executable, str(ROOT / 'tools/paper-warfront' / script), *map(str, flags), '--output', str(qa / label)]
    with (qa / (label + '-runner.log')).open('w', encoding='utf-8') as log:
        result = subprocess.run(cmd, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, timeout=360)
    assert result.returncode == 0, label
    rows.append({'name': label, 'passed': True})
    print(label, 'compiled native checks passed', flush=True)
folder = qa / 'stalled-front-vulkan/desktop'
assert not folder.exists()
folder.mkdir(parents=True)
cmd = [str(ROOT / '.tools/godot/Godot_v4.7.2-stable_win64_console.exe'), '--main-pack', str(pack),
    '--resolution', '1280x720', '--script', str(ROOT / 'tools/paper-warfront/probe_stalled_front_render.gd'),
    '--', '--output', str(folder), '--profile-path', str(folder / 'profile.json')]
startup = subprocess.STARTUPINFO()
startup.dwFlags = 1
startup.wShowWindow = 0
with (folder / 'runtime.log').open('w', encoding='utf-8') as log:
    result = subprocess.run(cmd, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, timeout=180, startupinfo=startup)
assert result.returncode == 0
report = json.loads((folder / 'report.json').read_text('utf-8'))
assert report['passed'] and len(report['checks']) == 32
rows.append({'name': 'stalled-front-vulkan', 'passed': True})
(qa / 'extras-runner-report.json').write_text(json.dumps({'passed': True, 'version': a.version,
    'jobs': rows, 'scope': 'Serial compiled Windows GPU fixed/synchronized captures; not real-time FPS or Android hardware.'}, indent=2), 'utf-8')
print('All additional compiled native checks passed', flush=True)
