"""Read-only map design audit. Writes research evidence, never game data."""
from __future__ import annotations

import collections
import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'docs/research/swords-and-soldiers-map/recheck-20261008'


def read(name):
    return json.loads((ROOT / 'game/data' / name).read_text(encoding='utf-8'))


def digest(path):
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def edge_length(edge):
    return sum(math.dist(a, b) for a, b in zip(edge['points'], edge['points'][1:]))


def range_summary(values):
    return {'min': round(min(values), 4), 'max': round(max(values), 4),
            'mean': round(sum(values) / len(values), 4)}


def audit(output_path=None):
    maps = read('maps.json')['maps']
    balance = read('balance-prototype.json')
    rows = []
    topology = collections.Counter()
    arrangements = collections.Counter()
    worker = balance['units']['unit.yin.worker']
    tower = balance['buildings']['building.yin.tower']
    for m in maps:
        edges = {e['id']: e for e in m['edges']}
        lengths = {key: edge_length(e) for key, e in edges.items()}
        ground = m['presentation']['ground_edges']
        base_distance = sum(lengths[e] for e in ground)
        # Structural signature excludes coordinates, theme, faction and names.
        signature = json.dumps([(e['from'], e['to']) for e in m['edges']])
        topology[signature] += 1
        arrangement = json.dumps({
            'mines': [(p['owner'], p['edge'], round(p['s']/lengths[p['edge']], 3))
                      for p in m['mines']],
            'sites': [(p['owner'], p['edge'], round(p['s']/lengths[p['edge']], 3))
                      for p in m['build_sites']]
        }, sort_keys=True)
        arrangements[arrangement] += 1
        bridge = next((e for e in m['edges'] if e.get('route_role') == 'bridge'), None)
        extra_distance = 0.0
        route_seconds = 0.0
        if bridge:
            parallel = next(e for e in m['edges'] if e['id'] != bridge['id']
                            and e['from'] == bridge['from'] and e['to'] == bridge['to'])
            extra_distance = lengths[bridge['id']] - lengths[parallel['id']]
            route_seconds = extra_distance / balance['units']['unit.yin.axe']['speed']
        mines = []
        for side in (0, 1):
            near_edge = ground[0 if side == 0 else -1]
            before_outer = lengths[near_edge]
            for mine in [p for p in m['mines'] if p['owner'] == side]:
                remaining = mine['s'] if side == 0 else lengths[mine['edge']]-mine['s']
                distance = remaining if mine['edge'] == near_edge else before_outer + remaining
                cycle = 2*distance / worker['speed'] + mine['mine_seconds'] + 1.0
                cargo = worker['cargo'] + mine['cargo_bonus']
                mines.append({'id': mine['id'], 'side': side, 'distance': round(distance, 4),
                              'capacity': mine['capacity'], 'cargo': cargo,
                              'ideal_cycle_seconds': round(cycle, 4),
                              'ideal_gold_per_second': round(cargo/cycle, 4)})
        near, outer = mines[:2]
        rows.append({'id': m['id'], 'name': m['name'], 'world_length': m['length'],
                     'base_path_length': round(base_distance, 4),
                     'fork_count': m['presentation']['forks'],
                     'bridge_extra_distance': round(extra_distance, 4),
                     'bridge_delay_yin_axe_seconds': round(route_seconds, 4),
                     'mine_count': len(m['mines']), 'site_count': len(m['build_sites']),
                     'branch_mines': sum(p['edge']=='bridge' for p in m['mines']),
                     'branch_sites': sum(p['edge']=='bridge' for p in m['build_sites']),
                     'mines': mines,
                     'outer_to_near_ideal_worker_income_ratio': round(
                         outer['ideal_gold_per_second']/near['ideal_gold_per_second'], 4)})
    forks = [r for r in rows if r['fork_count']]
    files = ['game/data/maps.json', 'game/data/campaign.json',
             'game/data/balance-prototype.json', 'game/scripts/map_runtime.gd',
             'game/scripts/battle_view.gd', 'game/scripts/battle_sim.gd',
             'tools/paper-warfront/prepare_theatre_rules.py']
    report = {
        'date': '2026-10-08', 'scope': 'Current working tree, not delivered 2.0 and not the original game',
        'data_version': balance['version'], 'source_sha256': {p: digest(p) for p in files},
        'summary': {
            'map_entries': len(maps), 'unique_geometry_hashes': len({m['geometry_sha256'] for m in maps}),
            'topology_families': len(topology), 'topology_family_sizes': sorted(topology.values()),
            'anchor_arrangement_families': len(arrangements),
            'anchor_arrangement_family_sizes': sorted(arrangements.values()),
            'unique_decision_texts': len({m.get('decision', '') for m in maps}),
            'unique_alternative_texts': len({m.get('alternative', '') for m in maps}),
            'single_line_entries': len(rows)-len(forks), 'fork_entries': len(forks),
            'maps_with_any_branch_mine': sum(r['branch_mines']>0 for r in rows),
            'maps_with_any_branch_site': sum(r['branch_sites']>0 for r in rows),
            'maps_with_finite_mine': sum(any(p['resource']>=0 for p in m['mines']) for m in maps),
            'maps_with_neutral_mine': sum(any(p['owner'] not in [0, 1] for p in m['mines']) for m in maps),
            'world_length': range_summary([r['world_length'] for r in rows]),
            'bridge_delay_yin_axe_seconds': range_summary([r['bridge_delay_yin_axe_seconds'] for r in forks]),
            'outer_to_near_ideal_worker_income_ratio': range_summary(
                [r['outer_to_near_ideal_worker_income_ratio'] for r in rows]),
            'campaign_objectives': dict(collections.Counter(l['win'] for l in read('campaign.json')['levels'])),
        },
        'measurement_model': {
            'worker': 'unit.yin.worker', 'worker_speed': worker['speed'],
            'tower_range': tower['range'],
            'income': 'one worker, round trip along path, no combat, no queue, no faction trait; analytical estimate',
            'route_delay': 'extra arc length / unit.yin.axe.speed; not an original-game measurement',
            'limitations': 'Equal topology does not imply identical play. Different hashes do not prove different decisions. Native probes are reported separately.'
        }, 'maps': rows
    }
    destination = Path(output_path).resolve() if output_path else OUT/'current-map-audit.json'
    destination.relative_to(ROOT)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(report['summary'], ensure_ascii=False))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(description='Read-only current map audit. Output must stay in this workspace.')
    parser.add_argument('--output', help='Optional new report path; use for reruns without replacing the baseline.')
    audit(parser.parse_args().output)
