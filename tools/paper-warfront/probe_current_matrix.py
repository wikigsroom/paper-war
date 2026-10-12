"""Matched native paid-AI matrix, default or explicit sequential deployment pilot."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output', type=Path, default=ROOT/'output/qa/godot/core-alignment-rc13/current-matrix')
parser.add_argument('--map', default='map.01.04')
parser.add_argument('--seed', type=int, default=137)
parser.add_argument('--sequential', action='store_true', help='Enable sequential deployment on both AI sides; other pilots stay disabled.')
args = parser.parse_args()
qa = args.output.resolve()
qa.mkdir(parents=True, exist_ok=True)

def batch(start):
    dest = qa/f'{start:02d}.json'
    command = [str(ROOT/'.tools/godot/Godot_v4.7.2-stable_win64_console.exe'), '--headless', '--path', str(ROOT/'game'),
               '--script', 'res://tests/probe_faction_matchups.gd', '--', '--start', str(start), '--count', '10',
               '--map', args.map, '--seed', str(args.seed), '--investment-trace', '--output', str(dest)]
    if args.sequential:
        command.append('--sequential-deployment-trial')
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=300)
    log = result.stdout + result.stderr
    dest.with_suffix('.log').write_text(log, encoding='utf-8')
    assert result.returncode == 0 and 'ERROR:' not in log and 'SCRIPT ERROR' not in log, log
    data = json.loads(dest.read_text(encoding='utf-8'))
    assert len(data['records']) == 10 and [r['index'] for r in data['records']] == list(range(start, start+10))
    assert data['duration_seconds'] == 150 and data['seed'] == args.seed and data['map'] == args.map
    for key, value in data.items():
        if key.startswith('experimental_'):
            expected = True if key == 'experimental_ai_sequential_deployment' and args.sequential else 'both' if key == 'experimental_policy_faction' and args.sequential else None
            assert value == expected if expected is not None else not value, (key, value)
    for path, digest in data['inputs'].items():
        assert hashlib.sha256((ROOT/'game'/path.removeprefix('res://')).read_bytes()).hexdigest() == digest
    print(f'Completed {start:02d}..{start+9:02d}', flush=True)
    return data

with ThreadPoolExecutor(max_workers=2) as pool:
    batches = list(pool.map(batch, range(0, 100, 10)))
inputs = batches[0]['inputs']
assert all(b['inputs'] == inputs for b in batches)
records = [r for b in batches for r in b['records']]
assert [r['index'] for r in records] == list(range(100))
for path, digest in inputs.items():
    assert hashlib.sha256((ROOT/'game'/path.removeprefix('res://')).read_bytes()).hexdigest() == digest
summary = {}
for r in records:
    for side, faction in enumerate([r['west'], r['east']]):
        own = r['sides'][side]
        item = summary.setdefault(faction, {'observations': 0, 'wins': 0, 'losses': 0, 'unresolved': 0,
                                           'no_workers_including_orders': 0, 'paid_research_starts': 0, 'healed': 0})
        item['observations'] += 1
        item['wins' if r['winner'] == side else 'losses' if r['winner'] == 1-side else 'unresolved'] += 1
        item['no_workers_including_orders'] += own['workers'] == 0
        item['paid_research_starts'] += sum(e['kind'] == 'research_start' and e['side'] == side for e in r['investment_trace'])
        item['healed'] += own['stats']['healed']
(qa/'matrix.json').write_text(json.dumps({'scope': '100 directed normal paid full-AI combinations, one map/seed, 150s ceiling; mirrors counted as two side observations; not human or all-map balance acceptance',
                                        'experimental_sequential_deployment': args.sequential,
                                        'map': args.map, 'seed': args.seed, 'inputs': inputs, 'source_unchanged': True,
                                        'records': records, 'faction_summary': summary}, indent=2), encoding='utf-8')
print(json.dumps(summary), flush=True)
