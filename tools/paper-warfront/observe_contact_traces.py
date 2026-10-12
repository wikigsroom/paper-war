"""Run native normal-paid engagement traces with an immutable observer copy."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
ENGINE = ROOT / '.tools/godot/Godot_v4.7.2-stable_win64_console.exe'
HARNESS = ROOT / 'tools/paper-warfront/probe_fielding_contact.gd'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
read = lambda p: json.loads(p.read_text('utf-8-sig'))
ap = argparse.ArgumentParser()
ap.add_argument('--runtime', type=Path, required=True)
ap.add_argument('--output', type=Path, required=True)
ap.add_argument('--cases', choices=['menu', 'regressions', 'short-long'], default='menu')
ap.add_argument('--side', type=int, choices=[0, 1, 2])
args = ap.parse_args()
runtime, qa = args.runtime.resolve(), args.output.resolve()
assert not qa.exists(), 'Never overwrite completed or in-flight observations'
qa.mkdir(parents=True)
observer = qa / 'observer.gd'
observer.write_bytes(HARNESS.read_bytes())
cases = [('menu-yin-mu', 'yin', 'mu', 'map.01.04', 137, 4)]
if args.cases == 'regressions':
    cases = [(west + '-' + east, west, east, 'map.01.04', 137, 0) for west, east in [
        ('yin', 'bai'), ('ji', 'qi'), ('ji', 'jin'), ('mu', 'bai'), ('jin', 'yin'), ('bai', 'jin'), ('yin', 'mu'), ('mu', 'yin')]]
elif args.cases == 'short-long':
    cases = [(name + '-' + west + '-' + east, west, east, mid, seed, 4) for name, mid, seed in [
        ('short', 'map.01.01', 271), ('long', 'map.01.20', 419)] for west, east in [('yin', 'mu'), ('mu', 'yin')]]

def run(case):
    label, west, east, mid, seed, warmup = case
    folder = qa / label
    folder.mkdir()
    flags = ['--output', str(folder), '--west', west, '--east', east, '--map', mid, '--seed', str(seed), '--warmup', str(warmup)]
    if args.side is not None:
        flags += ['--counter-side', str(args.side)]
    proc = subprocess.run([str(ENGINE), '--headless', '--path', str(runtime), '--script', str(observer), '--', *flags], cwd=ROOT,
                          capture_output=True, encoding='utf-8', errors='replace', timeout=180)
    log = proc.stdout + proc.stderr
    (folder / 'runtime.log').write_text(log, 'utf-8')
    assert proc.returncode == 0 and 'ERROR:' not in log and 'SCRIPT ERROR' not in log, log[-2000:]
    path = folder / 'report.json'
    report = read(path)
    assert report['observer_sha256'] == sha(observer)
    assert report['config']['map'] == mid and report['config']['seed'] == seed and report['config']['ai_warmup'] == warmup
    assert report['config']['starting_gold'] == 300 and report['config']['enemy_starting_gold'] == 300
    for name, digest in report['inputs'].items():
        assert sha(runtime / name) == digest
    summary = {'case': label, 'winner': report['winner'], 'time': report['time'],
               'first': [{k: v for k, v in item.items() if k != 'direct_hits'} | {'hits': len(item['direct_hits'])} for item in report['first']],
               'last_sample_workers': [s['workers'] for s in report['samples'][-1]['sides']], 'report': str(path), 'sha256': sha(path)}
    print(json.dumps(summary), flush=True)
    return summary

with ThreadPoolExecutor(max_workers=2) as pool:
    results = list(pool.map(run, cases))
(qa / 'report.json').write_text(json.dumps({'passed': True, 'runtime': str(runtime), 'cases': results,
    'observer_sha256': sha(observer), 'runner_sha256': sha(Path(__file__)),
    'scope': 'Windows native CPU, both normal AI and paid commands. Last sample is not necessarily the precise terminal tick. Not GPU, exported application entry, Android hardware or full balance.'}, indent=2), 'utf-8')
