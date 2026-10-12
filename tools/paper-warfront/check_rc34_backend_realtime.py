"""Collect real wall-clock frames from the exported native Windows App."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import time

ROOT = Path(__file__).resolve().parents[2]
ap = argparse.ArgumentParser()
runtime = ap.add_mutually_exclusive_group(required=True)
runtime.add_argument('--pack', type=Path)
runtime.add_argument('--source-project', type=Path)
ap.add_argument('--output', type=Path, required=True)
ap.add_argument('--case', choices=['bridge', 'long', 'phone', 'stress'], required=True)
ap.add_argument('--duration', type=float, default=160)
ap.add_argument('--fps-cap', type=int, choices=[30,60], default=60)
ap.add_argument('--profile-layers', action='store_true')
ap.add_argument('--native-backend',choices=['mobile','gl_compatibility'],required=True)
args = ap.parse_args()
folder = args.output.resolve()
assert not (folder / 'report.json').exists(), 'Completed real-time observations are immutable'
folder.mkdir(parents=True, exist_ok=True)
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
observer = ROOT / 'tools/paper-warfront/probe_realtime_battle.gd'
frozen = folder / 'observer.gd'
assert not frozen.exists(), 'Do not reuse a started observation directory'
shutil.copyfile(observer, frozen)
shutil.copyfile(Path(__file__), folder / 'runner.py')
pack = args.pack.resolve() if args.pack else None
settings = {
    'bridge': ('1280x720', 'map.01.04', []),
    'long': ('1280x720', 'map.01.11', []),
    'phone': ('1136x640', 'map.01.04', ['--mobile-ui', '--mobile-density', '2']),
    'stress': ('1280x720', 'map.01.04', ['--stress-120']),
}
resolution, map_id, flags = settings[args.case]
if args.profile_layers:flags = [*flags, '--qa-profile-layers']
runtime_args = ['--main-pack', str(pack)] if pack else ['--path', str(args.source_project.resolve())]
cmd = [str(ROOT / '.tools/godot/Godot_v4.7.2-stable_win64_console.exe'), *runtime_args, '--resolution', resolution,
       '--script', str(frozen), '--', *flags, '--output', str(folder),
       '--map', map_id, '--duration', str(args.duration), '--fps-cap', str(args.fps_cap),
       '--profile-path', str(folder / 'profile.json')]
cmd[1:1] = ['--rendering-method', args.native_backend]
manifest = pack.parent.parent / 'build-manifest.json' if pack else None
if manifest and manifest.exists():
    shutil.copyfile(manifest, folder / 'input-build-manifest.json')
source_inputs = {}
if not pack:
    project = args.source_project.resolve()
    source_inputs = {p.relative_to(project).as_posix(): sha(p)
                     for part in ['scripts', 'data'] for p in sorted((project / part).rglob('*')) if p.is_file()}
    (folder / 'source-inputs.json').write_text(json.dumps(source_inputs, indent=2), 'utf-8')
request = {'case': args.case, 'command': cmd, 'pack_sha256': sha(pack) if pack else None,
           'runtime_kind': 'exported_compiled_pack' if pack else 'native_source_candidate',
           'source_inputs': source_inputs,
           'observer_sha256': sha(frozen), 'runner_sha256': sha(Path(__file__)),
           'scope': 'Sequential native Windows GPU observation; natural App processing, real wall clock. Not Android hardware.'}
(folder / 'request.json').write_text(json.dumps(request, indent=2), 'utf-8')
startup = subprocess.STARTUPINFO()
startup.dwFlags = subprocess.STARTF_USESHOWWINDOW
startup.wShowWindow = 0
started = time.monotonic()
run = subprocess.run(cmd, cwd=ROOT, capture_output=True, encoding='utf-8', errors='replace',
                     timeout=args.duration + 90, startupinfo=startup)
log = run.stdout + run.stderr
(folder / 'runtime.log').write_text(log, 'utf-8')
report_path = folder / 'report.json'
assert report_path.exists() and 'SCRIPT ERROR' not in log and 'ERROR:' not in log, log[-4500:]
report = json.loads(report_path.read_text('utf-8'))
assert all(path.endswith('.gdc' if pack else '.gd') for path in report['inputs']), 'Verify the recorded runtime kind'
assert report['observer_sha256'] == sha(frozen)
assert report['frames_sha256'] == sha(folder / 'frames.csv')
for shot in report['captures']:
    assert sha(Path(shot['path'])) == shot['sha256']
receipt = {'passed': report['passed'] and run.returncode == 0, 'request': request,
           'report_sha256': sha(report_path), 'process_elapsed_seconds': time.monotonic()-started,
           'runtime_log_sha256': sha(folder / 'runtime.log'),
           'intervals_steady': report['intervals_steady'], 'app_process_steady': report['app_process_steady'],
           'draw_callback_steady': report['draw_callback_steady'], 'visual_event_steady': report['visual_event_steady'],
           'wall_seconds': report['wall_seconds'], 'simulation_seconds': report['simulation_seconds'],
           'max_units': max(s['units'] for s in report['snapshots']),
           'max_particles': max(s['particles'] for s in report['snapshots']),
           'max_texture_bytes': max(s['texture_bytes'] for s in report['snapshots'])}
(folder / 'receipt.json').write_text(json.dumps(receipt, indent=2), 'utf-8')
print(json.dumps({k: v for k, v in receipt.items() if k != 'request'}, indent=2), flush=True)
assert receipt['passed'], log[-4500:]
