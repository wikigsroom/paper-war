"""Verify native stage geometry and paid battle images, optionally using EXE pack."""
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
ap.add_argument('--case', choices=['desktop', 'phone', 'short'])
args = ap.parse_args()
startup = subprocess.STARTUPINFO()
startup.dwFlags = 1
startup.wShowWindow = 0
cases = []
selected = [('desktop', '1280x720', []), ('phone', '1136x640', ['--mobile-ui', '--mobile-density', '2'])]
if args.case == 'short':
    selected = [('short', '1136x568', ['--mobile-ui', '--mobile-density', '2'])]
elif args.case:
    selected = [row for row in selected if row[0] == args.case]
for name, resolution, flags in selected:
    folder = args.output.resolve() / name
    folder.mkdir(parents=True, exist_ok=True)
    command = [str(ROOT / '.tools/godot/Godot_v4.7.2-stable_win64_console.exe')]
    command += ['--main-pack', str(args.pack.resolve())] if args.pack else ['--path', str(ROOT / 'game')]
    command += ['--rendering-method', 'gl_compatibility', '--resolution', resolution, '--script', str(ROOT / 'tools/paper-warfront/probe_stage_proportions.gd'), '--', *flags, '--output', str(folder), '--profile-path', str(folder / 'profile.json')]
    run = subprocess.run(command, cwd=ROOT, capture_output=True, encoding='utf-8', errors='replace', timeout=180, startupinfo=startup)
    log = run.stdout + run.stderr
    (folder / 'runtime.log').write_text(log, encoding='utf-8')
    report = json.loads((folder / 'report.json').read_text(encoding='utf-8')) if (folder / 'report.json').exists() else {}
    passed = run.returncode == 0 and report.get('passed') and 'SCRIPT ERROR' not in log and 'ERROR:' not in log
    failures = [c for c in report.get('checks', []) if not c['passed']]
    cases.append({'name': name, 'passed': bool(passed), 'checks': len(report.get('checks', [])), 'failures': failures})
    print(json.dumps({**cases[-1], 'failures': failures[:6]}), flush=True)
    if 'SCRIPT ERROR' in log or 'ERROR:' in log or not report:
        raise RuntimeError(log[-2500:])
    if not passed and not args.allow_observed_failures:
        print(log[-2500:], flush=True)
        break
summary = {'passed': len(cases) == len(selected) and all(c['passed'] for c in cases), 'cases': cases, 'observer_sha256': hashlib.sha256((ROOT / 'tools/paper-warfront/probe_stage_proportions.gd').read_bytes()).hexdigest(), 'pack_sha256': hashlib.sha256(args.pack.read_bytes()).hexdigest() if args.pack else None}
(args.output / 'report.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
raise SystemExit(0 if summary['passed'] or args.allow_observed_failures else 1)
