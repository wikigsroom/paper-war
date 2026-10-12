"""Matched native paid-AI observations for default-disabled investment pilots."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--seeds', default='137,419')
parser.add_argument('--map', default='map.01.01')
parser.add_argument('--seconds', type=int, default=600)
parser.add_argument('--output', type=Path, default=ROOT/'output/qa/godot/core-alignment-rc13/wave-seeds')
args = parser.parse_args()
assert 60 <= args.seconds <= 900
seeds = list(dict.fromkeys(int(x) for x in args.seeds.split(',')))
qa = args.output.resolve()
qa.mkdir(parents=True, exist_ok=True)

def observe(job):
    seed, policy = job
    dest = qa/f'{seed}-{policy}.json'
    command = [str(ROOT/'.tools/godot/Godot_v4.7.2-stable_win64_console.exe'), '--headless', '--path', str(ROOT/'game'),
               '--script', 'res://tests/probe_faction_matchups.gd', '--', '--indices', '6,60', '--map', args.map,
               '--seed', str(seed), '--duration-seconds', str(args.seconds), '--timeline', '--sample-seconds', '15',
               '--investment-trace', '--research-screen-budget-trial', '--trial-faction', 'mu', '--output', str(dest)]
    if policy == 'wave':
        command.append('--deployment-commitment-trial')
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=240)
    log = result.stdout + result.stderr
    dest.with_suffix('.log').write_text(log, encoding='utf-8')
    assert result.returncode == 0 and 'ERROR:' not in log and 'SCRIPT ERROR' not in log, log
    data = json.loads(dest.read_text(encoding='utf-8'))
    assert len(data['records']) == 2 and data['seed'] == seed and data['duration_seconds'] == args.seconds
    assert data['experimental_ai_research_screen_budget'] and data['experimental_policy_faction'] == 'mu'
    assert data['experimental_ai_deployment_commitment'] == (policy == 'wave')
    for path, digest in data['inputs'].items():
        assert hashlib.sha256((ROOT/'game'/path.removeprefix('res://')).read_bytes()).hexdigest() == digest
    print(seed, policy, 'verified', flush=True)
    return seed, policy, data

with ThreadPoolExecutor(max_workers=2) as pool:
    observations = list(pool.map(observe, [(seed, policy) for seed in seeds for policy in ['saving', 'wave']]))
inputs = observations[0][2]['inputs']
rows = []
for seed, policy, data in observations:
    assert data['inputs'] == inputs
    for row in data['records']:
        side = 0 if row['west'] == 'mu' else 1
        own = row['sides'][side]
        rows.append({'seed': seed, 'policy': policy, 'index': row['index'], 'winner': row['winner'], 'wood_won': row['winner'] == side,
                     'time': row['time'], 'wood_base': own['base_hp'], 'wood_workers_including_orders': own['workers'], 'healed': own['stats']['healed'],
                     'advanced_events': [{key: e[key] for key in ['kind', 'time', 'id']} for e in row['investment_trace']
                                         if e['side'] == side and ('medic' in e['id'] or 'warden' in e['id'])]})
for path, digest in inputs.items():
    assert hashlib.sha256((ROOT/'game'/path.removeprefix('res://')).read_bytes()).hexdigest() == digest
(qa/'comparison.json').write_text(json.dumps({'scope': 'Normal paid full AI, saving-only vs fully funded deployment on wood; both default-disabled pilots; not human or whole-faction balance acceptance',
                                            'map': args.map, 'duration_seconds': args.seconds, 'inputs': inputs, 'source_unchanged': True, 'records': rows}, indent=2), encoding='utf-8')
print(json.dumps(rows), flush=True)
