"""Refresh existing paid reach evidence without changing simulation rules."""
import argparse
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ap = argparse.ArgumentParser()
ap.add_argument('--output', type=Path, required=True)
args = ap.parse_args()
target = args.output.resolve()
engine = ROOT / '.tools/godot/Godot_v4.7.2-stable_win64_console.exe'
jobs = []
for label, map_id in [('short', 'map.01.01'), ('mid', 'map.01.04'), ('long', 'map.01.11')]:
    folder = target / 'formal-reach'
    folder.mkdir(parents=True, exist_ok=True)
    jobs.append((label, ROOT / 'game/tests/probe_paid_premium_exchange.gd',
                 [str(folder / f'{label}-paid-exchange.json'), '--map', map_id, '--formal-price', '--reach-trial'], folder))
folder = target / 'formal-hammer'
folder.mkdir(parents=True, exist_ok=True)
for label, flags in [('paid-recipes', ['--formal-range']), ('reach-controls', [])]:
    jobs.append((label, ROOT / 'tools/paper-warfront/probe_paid_hammer_screen.gd',
                 ['--output', str(folder / f'{label}.json'), *flags], folder))
for label, script, flags, folder in jobs:
    run = subprocess.run([str(engine), '--headless', '--path', str(ROOT / 'game'), '--script', str(script), '--', *flags],
                         cwd=ROOT, capture_output=True, encoding='utf-8', errors='replace', timeout=180)
    log = run.stdout + run.stderr
    (folder / f'{label}.log').write_text(log, encoding='utf-8')
    assert run.returncode == 0 and 'SCRIPT ERROR' not in log and 'ERROR:' not in log, log[-2000:]
    print(label + ' native paid recipe completed', flush=True)
