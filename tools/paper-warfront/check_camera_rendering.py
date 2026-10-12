"""Native GPU camera and input observations, with actual pack provenance."""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ap = argparse.ArgumentParser()
ap.add_argument('--output', type=Path, required=True)
ap.add_argument('--pack', type=Path)
ap.add_argument('--allow-observed-failures', action='store_true')
args = ap.parse_args()
startup = subprocess.STARTUPINFO()
startup.dwFlags = 1
startup.wShowWindow = 0
cases = []
for name, resolution, flags in [('desktop', '1280x720', []), ('phone', '1136x640', ['--mobile-ui', '--mobile-density', '2'])]:
    folder = args.output.resolve() / name
    folder.mkdir(parents=True, exist_ok=True)
    cmd = [str(ROOT / '.tools/godot/Godot_v4.7.2-stable_win64_console.exe')]
    cmd += ['--main-pack', str(args.pack.resolve())] if args.pack else ['--path', str(ROOT / 'game')]
    cmd += ['--rendering-method', 'gl_compatibility', '--resolution', resolution, '--script', str(ROOT / 'tools/paper-warfront/probe_camera_rendering.gd'), '--', *flags, '--output', str(folder), '--profile-path', str(folder / 'profile.json')]
    run = subprocess.run(cmd, cwd=ROOT, capture_output=True, encoding='utf-8', errors='replace', timeout=90, startupinfo=startup)
    log = run.stdout + run.stderr
    (folder / 'runtime.log').write_text(log, encoding='utf-8')
    report = json.loads((folder / 'report.json').read_text(encoding='utf-8')) if (folder / 'report.json').is_file() else None
    if not report or 'SCRIPT ERROR' in log or 'ERROR:' in log:
        raise RuntimeError(log[-4000:])
    cases.append({'name': name, 'passed': report['passed'] and run.returncode == 0, 'checks': len(report['checks']), 'failed': [c for c in report['checks'] if not c['passed']]})
    print(json.dumps(cases[-1]), flush=True)
summary = {'passed': all(c['passed'] for c in cases), 'cases': cases,
           'observer_sha256': hashlib.sha256((ROOT / 'tools/paper-warfront/probe_camera_rendering.gd').read_bytes()).hexdigest()}
if args.pack:
    summary.update(pack=str(args.pack.resolve()), pack_sha256=hashlib.sha256(args.pack.read_bytes()).hexdigest())
(args.output / 'report.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
raise SystemExit(0 if summary['passed'] or args.allow_observed_failures else 1)
