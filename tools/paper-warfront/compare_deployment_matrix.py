"""Compare matched paid-AI matrices without treating recruitment as combat benefit."""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[2]
QA = ROOT / 'output/qa/godot/core-alignment-rc13'
control = json.loads((QA/'group-matrix-control/matrix.json').read_text(encoding='utf-8'))
trial = json.loads((QA/'group-matrix-trial/matrix.json').read_text(encoding='utf-8'))
assert control['source_unchanged'] and trial['source_unchanged']
assert not control['experimental_sequential_deployment'] and trial['experimental_sequential_deployment']
assert control['inputs'] == trial['inputs']
assert control['map'] == trial['map'] and control['seed'] == trial['seed']
for path, digest in control['inputs'].items():
    assert hashlib.sha256((ROOT/'game'/path.removeprefix('res://')).read_bytes()).hexdigest() == digest
reviews = [json.loads((QA/name/'review-summary.json').read_text(encoding='utf-8'))
           for name in ('group-matrix-control', 'group-matrix-trial')]
assert all(r['inputs'] == control['inputs'] for r in reviews)
changes = []
for before, after in zip(control['records'], trial['records'], strict=True):
    assert (before['index'], before['west'], before['east']) == (after['index'], after['west'], after['east'])
    if before['winner'] != after['winner']:
        changes.append({'index': before['index'], 'west': before['west'], 'east': before['east'],
                        'control_winner': before['winner'], 'trial_winner': after['winner'],
                        'control_seconds': before['time'], 'trial_seconds': after['time']})
totals = []
for review in reviews:
    totals.append({key: sum(row[key] for row in review['faction_summary'].values())
                   for key in next(iter(review['faction_summary'].values()))})
result = {'scope': '100 paired games; faction totals exclude mirrors (90 games, 180 side observations); one map/seed, 150-second cutoff; both AI policies change, not a single-side causal experiment; recruitment is not production, arrival or combat contribution',
          'inputs': control['inputs'], 'source_unchanged': True,
          'analysis_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
          'control_totals': totals[0], 'trial_totals': totals[1],
          'winner_changes': changes,
          'factions': {f: {'control': reviews[0]['faction_summary'][f], 'trial': reviews[1]['faction_summary'][f]}
                       for f in reviews[0]['faction_summary']}}
(QA/'deployment-matrix-comparison.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
print(json.dumps({'control': totals[0], 'trial': totals[1], 'winner_changes': changes}, indent=2))
