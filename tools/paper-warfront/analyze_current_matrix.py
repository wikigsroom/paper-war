"""Audit matrix provenance and count paid unit research that reached recruitment."""
from pathlib import Path
import hashlib
import json
import statistics
import argparse

ROOT = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--input', type=Path, default=ROOT/'output/qa/godot/core-alignment-rc13/current-matrix')
args = parser.parse_args()
QA = args.input.resolve()
data = json.loads((QA/'matrix.json').read_text(encoding='utf-8'))
assert data['source_unchanged'] and len(data['records']) == 100
for path, digest in data['inputs'].items():
    assert hashlib.sha256((ROOT/'game'/path.removeprefix('res://')).read_bytes()).hexdigest() == digest
technology = {n['id']: n for n in json.loads((ROOT/'game/data/technology.json').read_text(encoding='utf-8'))['nodes']}
factions = json.loads((ROOT/'game/data/factions.json').read_text(encoding='utf-8'))
names = {f['id']: f['name'] for f in factions['factions']}
completion_windows = []
summary = {f: {'observations': 0, 'wins': 0, 'losses': 0, 'draws': 0, 'unresolved': 0,
               'unresolved_without_workers_including_orders': 0, 'unit_research_paid': 0,
               'unit_research_completed': 0, 'unit_research_recruited': 0} for f in factions['order']}
for row in data['records']:
    if row['west'] == row['east']:
        continue
    for side, faction in enumerate([row['west'], row['east']]):
        own = row['sides'][side]
        item = summary[faction]
        item['observations'] += 1
        outcome = 'wins' if row['winner'] == side else 'losses' if row['winner'] == 1-side else 'draws' if row['winner'] == -1 else 'unresolved'
        item[outcome] += 1
        item['unresolved_without_workers_including_orders'] += row['winner'] == -2 and own['workers'] == 0
        events = [e for e in row['investment_trace'] if e['side'] == side]
        for event in events:
            if event['kind'] != 'research_start':
                continue
            node = technology[event['id']]
            grant = node['grant']
            if not grant.startswith('unit.'):
                continue
            item['unit_research_paid'] += 1
            finished = [e['time'] for e in events if e['kind'] == 'research_done' and e['id'] == grant and e['time'] >= event['time']]
            if not finished:
                continue
            item['unit_research_completed'] += 1
            completion_windows.append(row['time'] - min(finished))
            item['unit_research_recruited'] += any(e['kind'] == 'recruit' and e['id'] == grant and e['time'] >= min(finished) for e in events)
assert all(s['observations'] == 18 for s in summary.values())
(QA/'review-summary.json').write_text(json.dumps({'scope': '90 directed cross-faction games; 18 side observations per faction; excludes 10 mirror games; completed research with later paid recruitment is not proof of production or combat benefit',
                                                'inputs': data['inputs'], 'analysis_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                                                'factions_sha256': hashlib.sha256((ROOT/'game/data/factions.json').read_bytes()).hexdigest(),
                                                'completion_windows': {'completed': len(completion_windows),
                                                                       'at_least_30_seconds_remaining': sum(t >= 30 for t in completion_windows),
                                                                       'median_seconds_remaining': statistics.median(completion_windows) if completion_windows else None,
                                                                       'scope': 'Remaining time before actual match end or observation cutoff; not a battle benefit forecast'},
                                                'faction_summary': summary}, indent=2), encoding='utf-8')
for faction, s in summary.items():
    print(names[faction], f"{s['wins']}/{s['losses']}/{s['unresolved']}", 'no-worker unresolved', s['unresolved_without_workers_including_orders'],
          'paid/completed/recruited', s['unit_research_paid'], s['unit_research_completed'], s['unit_research_recruited'])
