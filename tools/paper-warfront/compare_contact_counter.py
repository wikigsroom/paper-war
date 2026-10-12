"""Pair frozen normal-AI cohorts, retaining outcome and economy regressions."""
import argparse
import collections
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
read = lambda p: json.loads(p.read_text('utf-8-sig'))
ap = argparse.ArgumentParser()
ap.add_argument('--control', type=Path, required=True)
ap.add_argument('--candidate', type=Path, required=True)
ap.add_argument('--output', type=Path, required=True)
args = ap.parse_args()
a, b = read(args.control), read(args.candidate)
assert a['passed'] and b['passed']
for key in ['map', 'seed', 'starting_stock', 'duration', 'observer_sha256']:
    assert a[key] == b[key], key
assert a['candidate_side'] is None and b['candidate_side'] is None
assert a['candidate_policy'] is None and b['candidate_policy'] is None
game_inputs = lambda r: {k: v for k, v in r['runtime_inputs'].items() if k.startswith(('scripts/', 'data/', 'tests/')) or k == 'project.godot'}
ai, bi = game_inputs(a), game_inputs(b)
assert ai.keys() == bi.keys()
changed = [k for k in ai if ai[k] != bi[k]]
assert changed == ['scripts/tactical_ai.gd'], changed
refs = {}
for name, path, report in [('control', args.control, a), ('candidate', args.candidate, b)]:
    runtime = Path(report['runtime'])
    for key, digest in report['runtime_inputs'].items():
        assert sha(runtime / key) == digest, (name, key)
    refs[name + '_report'] = {'path': str(path.resolve()), 'sha256': sha(path)}
    rows = []
    for batch in report['batches']:
        raw = path.parent / batch['file']
        assert sha(raw) == batch['sha256'], raw
        data = read(raw)
        assert data['map'] == report['map'] and data['seed'] == report['seed']
        assert data['starting_gold_per_side'] == report['starting_stock'] and data['duration_seconds'] == report['duration']
        for key, value in data.items():
            if not key.startswith('experimental_') or key.endswith('_side'):
                continue
            assert not value, (key, value)
        for key, digest in data['inputs'].items():
            assert sha(runtime / key.removeprefix('res://')) == digest, key
        rows.extend(data['records'])
        refs[name + '_' + batch['file']] = {'path': str(raw.resolve()), 'sha256': sha(raw)}
    assert [r['index'] for r in sorted(rows, key=lambda x: x['index'])] == [r['index'] for r in report['matches']]
assert [(r['index'], r['west'], r['east']) for r in a['matches']] == [(r['index'], r['west'], r['east']) for r in b['matches']]

def aggregate(rows):
    studies = [s for r in rows for s in r['studies']]
    sides = [s for r in rows for s in r['sides']]
    return {'matches': len(rows), 'west_wins': sum(r['winner'] == 0 for r in rows), 'east_wins': sum(r['winner'] == 1 for r in rows),
            'unresolved': sum(r['winner'] == -2 for r in rows), 'ending_workerless_sides': sum(s['workers'] == 0 for s in sides),
            'gold_delivered': sum(s['stats']['gold_delivered'] for s in sides),
            'research_completed': sum(s['research_done'] is not None for s in studies), 'paid_orders': sum(s['paid_order'] is not None for s in studies),
            'production_spawns': sum(s['production_spawn'] is not None for s in studies), 'direct_contributions': sum(s['direct_contribution'] for s in studies),
            'completed_no_order_30s': sum(s['research_done'] is not None and s['paid_order'] is None and s['remaining_after_completion'] >= 30 for s in studies)}

houses = {}
changes = []
for x, y in zip(a['matches'], b['matches']):
    if x['winner'] != y['winner']:
        changes.append({'index': x['index'], 'west': x['west'], 'east': x['east'], 'control_winner': x['winner'], 'candidate_winner': y['winner'], 'control_time': x['time'], 'candidate_time': y['time']})
    for side, house in enumerate([x['west'], x['east']]):
        out = houses.setdefault(house, {'side_participations': 0, 'control': collections.Counter(), 'candidate': collections.Counter()})
        out['side_participations'] += 1
        for name, row in [('control', x), ('candidate', y)]:
            outcome = 'wins' if row['winner'] == side else ('unresolved' if row['winner'] == -2 else 'losses')
            stats = out[name]
            stats[outcome] += 1
            stats['workerless'] += row['sides'][side]['workers'] == 0
            stats['gold_delivered'] += row['sides'][side]['stats']['gold_delivered']
            stats['completed_studies'] += sum(s['research_done'] is not None for s in row['studies'] if s['side'] == side)
            stats['direct_contributions'] += sum(s['direct_contribution'] for s in row['studies'] if s['side'] == side)
result = {'passed': True, 'scope': 'Provenance and paired comparison passed; this does not mean the candidate is acceptable. Same paid normal-AI CPU conditions; zero warmup. No GPU, human, original equivalence or Android hardware claim.',
          'paired_conditions': len(a['matches']), 'runtime_changed_inputs': changed, 'conditions': {k: a[k] for k in ['map', 'seed', 'starting_stock', 'duration']},
          'control': aggregate(a['matches']), 'candidate': aggregate(b['matches']), 'houses': houses, 'outcome_changes': changes,
          'references': refs, 'comparator_sha256': sha(Path(__file__))}
args.output.parent.mkdir(parents=True, exist_ok=True)
args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), 'utf-8')
print(json.dumps({k: result[k] for k in ['paired_conditions', 'control', 'candidate', 'houses']}))
