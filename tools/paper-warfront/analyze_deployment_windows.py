"""Verify native deployment snapshots and classify overlapping sampled conditions."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
QA = ROOT/'output/qa/godot/core-alignment-rc13'
data = json.loads((QA/'deployment-window-observation.json').read_text(encoding='utf-8'))
matrix = json.loads((QA/'group-matrix-trial/matrix.json').read_text(encoding='utf-8'))
assert data['source_unchanged']
for path, digest in data['inputs'].items():
    assert hashlib.sha256((ROOT/'game'/path.removeprefix('res://')).read_bytes()).hexdigest() == digest
rows = []
for record in data['records']:
    original = matrix['records'][record['index']]
    assert record['winner'] == original['winner'] and abs(record['time']-original['time']) < 1e-6
    for side, faction in enumerate([record['west'], record['east']]):
        samples = [s for s in record['samples'] if s['side'] == side and s['unlocked']]
        if not samples:
            continue
        ready = [s for s in samples if s['affordable'] and s['group']['members']]
        rows.append({'index': record['index'], 'faction': faction, 'side': side,
                     'unlocked_pending_samples': len(samples),
                     'affordable_samples': sum(s['affordable'] for s in samples),
                     'formation_samples': sum(bool(s['group']['members']) for s in samples),
                     'affordable_formation_samples': len(ready),
                     'ready_with_front_broken': sum(s['front_broken'] for s in ready),
                     'ready_with_threatened': sum(s['threatened'] for s in ready),
                     'ready_without_either_warning': sum(not s['front_broken'] and not s['threatened'] for s in ready),
                     'ready_blocked_by_build_reserve': sum(s['remaining_after_target'] < float(s['build_reserve']) for s in ready),
                     'no_front_samples': sum(s['group']['front_count'] == 0 for s in samples),
                     'max_cash': max(s['gold'] for s in samples)})
result = {'scope': data['scope'], 'source_unchanged': True, 'inputs': data['inputs'],
          'analysis_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
          'matches_reproduce_matrix_outcomes': True, 'rows': rows}
(QA/'deployment-window-summary.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
print(json.dumps(rows, indent=2))
