"""One native observer for source and previously/currently shipped camera logic."""
import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ap = argparse.ArgumentParser()
ap.add_argument('--output', type=Path, required=True)
ap.add_argument('--pack', type=Path)
ap.add_argument('--allow-observed-failures', action='store_true')
args = ap.parse_args()
qa = args.output.resolve()
qa.mkdir(parents=True, exist_ok=True)
engine = ROOT / '.tools/godot/Godot_v4.7.2-stable_win64_console.exe'
harness = ROOT / 'game/tests/test_observer_camera.gd'
command = [str(engine), '--headless']
command += ['--main-pack', str(args.pack.resolve())] if args.pack else ['--path', str(ROOT / 'game')]
command += ['--script', str(harness)]
result = subprocess.run(command, cwd=ROOT, capture_output=True, encoding='utf-8', errors='replace', timeout=90)
log = result.stdout + result.stderr
(qa / 'runtime.log').write_text(log, encoding='utf-8')
observed = re.search(r'OBSERVER_CAMERA: (\d+) checks; failures=(\[.*\])', log)
if not observed or 'SCRIPT ERROR' in log or 'ERROR:' in log:
    raise RuntimeError(log[-4000:])
failures = json.loads(observed.group(2))
report = {'checks': int(observed.group(1)), 'failures': failures,
          'passed': result.returncode == 0 and not failures,
          'harness_sha256': hashlib.sha256(harness.read_bytes()).hexdigest(),
          'scope': 'Controlled Windows native sight/host-client and local/LAN input checks. No Android hardware, rendering, original-game timing or balance proof.'}
if args.pack:
    report.update(pack=str(args.pack.resolve()), pack_sha256=hashlib.sha256(args.pack.read_bytes()).hexdigest())
else:
    report['inputs'] = {f'game/scripts/{name}.gd': hashlib.sha256((ROOT / f'game/scripts/{name}.gd').read_bytes()).hexdigest()
                        for name in ['battle_sim', 'battle_view', 'local_duel', 'battle_visibility', 'client_battle', 'match_projection', 'map_runtime']}
(qa / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({'checks': report['checks'], 'failed': len(failures), 'passed': report['passed']}), flush=True)
raise SystemExit(0 if report['passed'] or args.allow_observed_failures else 1)
