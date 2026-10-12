"""Native GPU fog checks, optionally against the actual exported EXE pack."""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser()
parser.add_argument('--output', type=Path, required=True)
parser.add_argument('--pack', type=Path)
parser.add_argument('--allow-observed-failures', action='store_true')
args = parser.parse_args()
startup = subprocess.STARTUPINFO()
startup.dwFlags = 1
startup.wShowWindow = 0
results = []
for name, resolution, flags in [('desktop', '1280x720', []), ('phone', '1136x640', ['--mobile-ui', '--mobile-density', '2'])]:
    folder = args.output.resolve() / name
    folder.mkdir(parents=True, exist_ok=True)
    command = [str(ROOT / '.tools/godot/Godot_v4.7.2-stable_win64_console.exe')]
    command += ['--main-pack', str(args.pack.resolve())] if args.pack else ['--path', str(ROOT / 'game')]
    command += ['--rendering-method', 'gl_compatibility', '--resolution', resolution, '--script', str(ROOT / 'tools/paper-warfront/probe_fog_rendering.gd'), '--', *flags, '--output', str(folder), '--profile-path', str(folder / 'profile.json')]
    run = subprocess.run(command, cwd=ROOT, capture_output=True, encoding='utf-8', errors='replace', timeout=90, startupinfo=startup)
    log = run.stdout + run.stderr
    (folder / 'runtime.log').write_text(log, encoding='utf-8')
    report = json.loads((folder / 'report.json').read_text(encoding='utf-8')) if (folder / 'report.json').exists() else {}
    if 'SCRIPT ERROR' in log or 'ERROR:' in log or not report:
        raise RuntimeError(log[-4000:])
    results.append({'name': name, 'exit_code': run.returncode, 'passed': report['passed'], 'failed': [c for c in report['checks'] if not c['passed']]})
    print(json.dumps(results[-1]), flush=True)
summary = {'passed': all(r['passed'] for r in results), 'cases': results, 'observer_sha256': hashlib.sha256((ROOT / 'tools/paper-warfront/probe_fog_rendering.gd').read_bytes()).hexdigest(), 'pack': str(args.pack) if args.pack else None}
if args.pack:
    summary['pack_sha256'] = hashlib.sha256(args.pack.read_bytes()).hexdigest()
(args.output / 'report.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
raise SystemExit(0 if summary['passed'] or args.allow_observed_failures else 1)
