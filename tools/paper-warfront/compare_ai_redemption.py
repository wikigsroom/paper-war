"""Compare frozen paid cohorts without treating observation success as balance acceptance."""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path

read = lambda p: json.loads(p.read_text(encoding='utf-8-sig'))
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
ap = argparse.ArgumentParser()
ap.add_argument('--control', type=Path, required=True)
ap.add_argument('--candidate', type=Path, required=True)
ap.add_argument('--output', type=Path, required=True)
ap.add_argument('--disabled-control', type=Path)
args = ap.parse_args()

def verify(path):
    report = read(path)
    assert report['passed'] is True
    folder, runtime = path.parent, Path(report['runtime'])
    assert all(sha(runtime / name) == digest for name, digest in report['runtime_inputs'].items())
    rows = {}
    for item in report['batches']:
        raw_path = folder / item['file']
        assert sha(raw_path) == item['sha256']
        raw = read(raw_path)
        for key, expected in [('map', report['map']), ('seed', report['seed']),
                              ('starting_gold_per_side', report['starting_stock']), ('duration_seconds', report['duration'])]:
            assert raw[key] == expected
        for row in raw['records']:
            assert row['index'] not in rows
            rows[row['index']] = row
    assert sorted(rows) == [r['index'] for r in report['matches']]
    return report, rows

control, raw_control = verify(args.control)
candidate, raw_candidate = verify(args.candidate)
for key in ['map', 'seed', 'starting_stock', 'duration']:
    assert control[key] == candidate[key], key
assert candidate['candidate_side'] in [0, 1]
assert control['candidate_side'] is None
side = candidate['candidate_side']
assert raw_candidate.keys() <= raw_control.keys()
changed = []
for name, digest in control['runtime_inputs'].items():
    if name.endswith(('.gd', '.json', '.godot')) and name not in ['snapshot.json', 'candidate.json']:
        assert name in candidate['runtime_inputs']
        if candidate['runtime_inputs'][name] != digest:
            changed.append(name)
assert sorted(changed) == ['scripts/tactical_ai.gd', 'tests/probe_faction_matchups.gd'], changed
disabled_checks = []
if args.disabled_control:
    disabled, raw_disabled = verify(args.disabled_control)
    assert disabled['candidate_side'] is None
    assert disabled['runtime_inputs'] == candidate['runtime_inputs']
    for index, row in raw_disabled.items():
        assert index in raw_control and row == raw_control[index], index
        disabled_checks.append(index)

control_rows = {r['index']: r for r in control['matches']}
totals = {'control': Counter(), 'candidate': Counter()}
factions = defaultdict(lambda: {'control': Counter(), 'candidate': Counter()})
pairs = []

def summarize(row, player_side):
    own = row['sides'][player_side]
    studies = [s for s in row['studies'] if s['side'] == player_side]
    return {
        'win': int(row['winner'] == player_side),
        'loss': int(row['winner'] == 1 - player_side),
        'unresolved': int(row['winner'] not in [0, 1]),
        'workers_at_endpoint': own['workers'],
        'no_workers_at_endpoint': int(own['workers'] == 0 and not any(id.endswith('.worker') for id in own['queue'])),
        'gold_delivered': own['stats']['gold_delivered'],
        'research_paid': len(studies),
        'research_completed': sum(s['research_done'] is not None for s in studies),
        'research_with_paid_order': sum(s['paid_order'] is not None for s in studies),
        'research_with_production_spawn': sum(s['production_spawn'] is not None for s in studies),
        'research_with_direct_contribution': sum(s['direct_contribution'] for s in studies),
        'research_unredeemed_with_30s': sum(s['research_done'] is not None and s['paid_order'] is None and s['remaining_after_completion'] >= 30 for s in studies),
    }

for row in candidate['matches']:
    before = control_rows[row['index']]
    assert row['west'] == before['west'] and row['east'] == before['east']
    faction = row[['west', 'east'][side]]
    stats = {'control': summarize(before, side), 'candidate': summarize(row, side)}
    for label, values in stats.items():
        totals[label].update(values)
        factions[faction][label].update(values)
    pairs.append({'index': row['index'], 'west': row['west'], 'east': row['east'],
                  'control_winner': before['winner'], 'candidate_winner': row['winner'],
                  'control_time': before['time'], 'candidate_time': row['time'],
                  'candidate_side': side, 'metrics': stats})
result = {
    'passed': True,
    'scope': 'Paired Windows-native paid AI observations; metrics refer only to the policy side. A passed comparison verifies provenance and pairing, not balance or default adoption.',
    'candidate_policy': candidate.get('candidate_policy', 'paid-grant'), 'candidate_side': side,
    'balance_accepted': False, 'pairs': len(pairs),
    'map': control['map'], 'seed': control['seed'], 'stock': control['starting_stock'], 'duration': control['duration'],
    'inputs': {'control': {'path': str(args.control.resolve()), 'sha256': sha(args.control)},
               'candidate': {'path': str(args.candidate.resolve()), 'sha256': sha(args.candidate)}},
    'changed_runtime_inputs': changed, 'identical_disabled_records': disabled_checks,
    'totals': totals, 'factions': factions, 'records': pairs,
}
if args.disabled_control:
    result['inputs']['disabled_control'] = {'path': str(args.disabled_control.resolve()), 'sha256': sha(args.disabled_control)}
args.output.parent.mkdir(parents=True, exist_ok=True)
args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({'pairs': len(pairs), 'totals': totals}, ensure_ascii=False))
