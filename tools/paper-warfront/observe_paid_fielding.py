"""Frozen current-release AI cohorts and research-to-field evidence."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[2]
ENGINE = ROOT / '.tools/godot/Godot_v4.7.2-stable_win64_console.exe'
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
read = lambda path: json.loads(path.read_text(encoding='utf-8-sig'))
ap = argparse.ArgumentParser()
ap.add_argument('--runtime', type=Path, required=True)
ap.add_argument('--output', type=Path, required=True)
ap.add_argument('--snapshot', action='store_true')
ap.add_argument('--shipping-version', default='3.0.0-rc23-preview')
ap.add_argument('--map', default='map.01.04')
ap.add_argument('--seed', type=int, default=137)
ap.add_argument('--duration', type=int, default=240)
ap.add_argument('--stock', type=int, default=160)
ap.add_argument('--indices', default='all')
policy = ap.add_mutually_exclusive_group()
policy.add_argument('--redemption-side', type=int, choices=[0, 1])
policy.add_argument('--economy-side', type=int, choices=[0, 1])
args = ap.parse_args()
runtime = args.runtime.resolve()
qa = args.output.resolve()
qa.mkdir(parents=True, exist_ok=True)
if args.snapshot:
    assert not runtime.exists(), 'Never overwrite an existing frozen runtime'
    runtime.mkdir(parents=True)
    shipping = read(ROOT / 'release' / args.shipping_version / 'build-manifest.json')
    for folder, pattern in [('scripts', '*.gd'), ('data', '*.json')]:
        (runtime / folder).mkdir()
        for path in sorted((ROOT / 'game' / folder).glob(pattern)):
            assert sha(path) == shipping['source_inputs'][path.relative_to(ROOT).as_posix()], path
            shutil.copy2(path, runtime / folder / path.name)
    (runtime / 'tests').mkdir()
    shutil.copy2(ROOT / 'game/tests/probe_faction_matchups.gd', runtime / 'tests/probe_faction_matchups.gd')
    (runtime / 'project.godot').write_text(f'config_version=5\n[application]\nconfig/name="Paid AI observation"\nconfig/version="{args.shipping_version}"\n[rendering]\nrenderer/rendering_method="gl_compatibility"\n', encoding='utf-8')
    (runtime / 'snapshot.json').write_text(json.dumps({'verified_shipping_version': shipping['version'],
        'scope': 'Gameplay scripts/data verified against the shipping source manifest; no artwork copied and no rendering claim.',
        'inputs': {path.relative_to(runtime).as_posix(): sha(path) for path in sorted(runtime.rglob('*')) if path.is_file()}}, indent=2), encoding='utf-8')
inputs = {path.relative_to(runtime).as_posix(): sha(path) for path in sorted(runtime.rglob('*'))
          if path.is_file() and path.suffix in ['.gd', '.json', '.godot'] and '.godot' not in path.relative_to(runtime).parts}
indices = list(range(100)) if args.indices == 'all' else sorted({int(i) for i in args.indices.split(',')})
assert indices and all(0 <= i < 100 for i in indices)
technology = {node['id']: node for node in read(runtime / 'data/technology.json')['nodes']}
balance = read(runtime / 'data/balance-prototype.json')['units']

def analyze(row):
    investments = row['investment_trace']
    field = row['combat_trace']
    studies = []
    for event in investments:
        if event['kind'] != 'research_start' or not technology[event['id']]['grant'].startswith('unit.'):
            continue
        node = technology[event['id']]
        grant, side = node['grant'], event['side']
        completed = next((e for e in investments if e['kind'] == 'research_done' and e['side'] == side and e['id'] == grant and e['time'] >= event['time']), None)
        order = next((e for e in investments if completed and e['kind'] == 'recruit' and e['side'] == side and e['id'] == grant and e['time'] >= completed['time']), None)
        born = next((e for e in field if order and e['kind'] == 'spawn' and e.get('side') == side and e.get('id') == grant and e.get('origin') == 'production' and e['time'] >= order['time']), None)
        hits = [e for e in field if born and e['kind'] == 'hit' and e.get('source_uid') == born['uid'] and e.get('attacker_side') == side and e.get('amount', 0) > 0]
        heals = [e for e in field if born and e['kind'] == 'heal' and e.get('source_uid') == born['uid'] and e.get('side') == side and e.get('amount', 0) > 0]
        summons = [e for e in field if born and e['kind'] == 'unit_special' and e.get('uid') == born['uid'] and e.get('side') == side and e.get('fx') in ['summon', 'soul'] and e.get('target_uid', 0) > 0]
        decisions = [d for d in row.get('recruitment_decisions', []) if completed and d['side'] == side and d['time'] >= completed['time']]
        studies.append({'side': side, 'tech': node['id'], 'grant': grant, 'research_price': event['gold_spent'], 'unit_price': balance[grant]['gold'],
                        'research_started': event['time'], 'research_done': completed['time'] if completed else None,
                        'paid_order': order['time'] if order else None, 'production_spawn': born['time'] if born else None,
                        'production_uid': born['uid'] if born else None, 'remaining_after_completion': row['time'] - completed['time'] if completed else None,
                        'first_damage': hits[0]['time'] if hits else None, 'damage_events': len(hits), 'damage_amount': sum(e['amount'] for e in hits),
                        'effective_heal_events': len(heals), 'effective_heal_amount': sum(e['amount'] for e in heals), 'summon_events': len(summons),
                        'direct_contribution': bool(hits or heals or summons),
                        'affordable_decisions_after_completion': sum(d['gold_before'] >= balance[grant]['gold'] for d in decisions),
                        'selected_decisions_after_completion': sum(d['selected'] == grant for d in decisions)})
    return {'index': row['index'], 'west': row['west'], 'east': row['east'], 'winner': row['winner'], 'time': row['time'],
            'sides': row['sides'], 'studies': studies}

groups = [indices[start:start + 5] for start in range(0, len(indices), 5)]
def batch(selection):
    path = qa / f"batch-{selection[0]:02d}.json"
    flags = ['--start', str(selection[0]), '--count', str(selection[-1] - selection[0] + 1), '--indices', ','.join(map(str, selection)),
             '--map', args.map, '--seed', str(args.seed), '--starting-gold', str(args.stock), '--duration-seconds', str(args.duration),
             '--combat-trace', '--combat-trace-seconds', str(args.duration), '--investment-trace', '--recruitment-decision-trace',
             '--timeline', '--sample-seconds', '15', '--output', str(path)]
    if args.redemption_side is not None:
        flags += ['--grant-redemption-side', str(args.redemption_side)]
    if args.economy_side is not None:
        flags += ['--economy-side', str(args.economy_side)]
    run = subprocess.run([str(ENGINE), '--headless', '--path', str(runtime), '--script', 'res://tests/probe_faction_matchups.gd', '--', *flags],
                         cwd=ROOT, capture_output=True, encoding='utf-8', errors='replace', timeout=300)
    log = run.stdout + run.stderr
    path.with_suffix('.log').write_text(log, encoding='utf-8')
    assert run.returncode == 0 and 'ERROR:' not in log and 'SCRIPT ERROR' not in log, log[-2500:]
    report = read(path)
    assert [r['index'] for r in report['records']] == selection
    assert report['map'] == args.map and report['seed'] == args.seed and report['duration_seconds'] == args.duration
    assert report['starting_gold_per_side'] == args.stock
    for name, digest in report['inputs'].items():
        assert sha(runtime / name.removeprefix('res://')) == digest, name
    assert bool(report.get('experimental_ai_grant_redemption', False)) == (args.redemption_side is not None)
    assert bool(report.get('experimental_ai_economy_bootstrap', False)) == (args.economy_side is not None)
    if args.redemption_side is not None:
        assert report['experimental_ai_grant_redemption_side'] == args.redemption_side
    if args.economy_side is not None:
        assert report['experimental_ai_economy_bootstrap_side'] == args.economy_side
    inactive_selectors = {'experimental_ai_budget_planner_side': 'experimental_ai_budget_planner',
                          'experimental_paid_opening_side': 'experimental_ai_paid_opening',
                          'experimental_ai_grant_redemption_side': 'experimental_ai_grant_redemption',
                          'experimental_ai_economy_bootstrap_side': 'experimental_ai_economy_bootstrap'}
    for name, value in report.items():
        if name in inactive_selectors and not report.get(inactive_selectors[name], False):
            continue
        if name.startswith('experimental_') and value:
            allowed = []
            if args.redemption_side is not None:
                allowed += ['experimental_ai_grant_redemption', 'experimental_ai_grant_redemption_side']
            if args.economy_side is not None:
                allowed += ['experimental_ai_economy_bootstrap', 'experimental_ai_economy_bootstrap_side']
            assert name in allowed, (name, value)
    print('Completed native paid records: ' + ','.join(map(str, selection)), flush=True)
    return {'file': path.relative_to(qa).as_posix(), 'sha256': sha(path), 'records': [analyze(r) for r in report['records']]}

with ThreadPoolExecutor(max_workers=2) as pool:
    batches = list(pool.map(batch, groups))
assert all(sha(runtime / name) == digest for name, digest in inputs.items()), 'Frozen runtime changed'
matches = sorted((row for b in batches for row in b['records']), key=lambda row: row['index'])
assert [r['index'] for r in matches] == indices
studies = [s for r in matches for s in r['studies']]
summary = {'matches': len(matches), 'completed_matches': sum(r['winner'] >= -1 for r in matches),
           'unit_research_paid': len(studies), 'unit_research_completed': sum(s['research_done'] is not None for s in studies),
           'unit_research_with_paid_order': sum(s['paid_order'] is not None for s in studies),
           'unit_research_with_production_spawn': sum(s['production_spawn'] is not None for s in studies),
           'unit_research_with_direct_contribution': sum(s['direct_contribution'] for s in studies),
           'completed_without_order_with_30_seconds': sum(s['research_done'] is not None and s['paid_order'] is None and s['remaining_after_completion'] >= 30 for s in studies)}
result = {'passed': True, 'scope': 'Windows native paid complete-AI observations in a frozen gameplay runtime. Same stock, rules and fog; zero warmup on both AI sides for comparison. No human, original-game, Android hardware or full-balance acceptance. Direct contribution counts damage, effective healing and successful summons, not all aura effects.',
          'runtime': str(runtime), 'runtime_inputs': inputs, 'map': args.map, 'seed': args.seed, 'starting_stock': args.stock, 'duration': args.duration,
          'candidate_side': args.redemption_side if args.redemption_side is not None else args.economy_side,
          'candidate_policy': 'paid-grant' if args.redemption_side is not None else ('economy-bootstrap' if args.economy_side is not None else None),
          'batches': [{k: v for k, v in b.items() if k != 'records'} for b in batches],
          'observer_sha256': sha(Path(__file__)), 'summary': summary, 'matches': matches}
(qa / 'report.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(summary), flush=True)
