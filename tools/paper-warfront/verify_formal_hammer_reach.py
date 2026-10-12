"""Bind hammer definitions to current native paid recipes and GPU captures."""
import argparse, csv, hashlib, json
from pathlib import Path
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parents[2]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--qa', type=Path, required=True)
    ap.add_argument('--regression', type=Path, help='Use an existing identical source mechanism report; does not rerun or double-count its checks.')
    options = ap.parse_args()
    qa = options.qa.resolve()
    files = {}

    def read(path):
        path = path.resolve()
        files[path.relative_to(ROOT).as_posix()] = sha(path)
        return json.loads(path.read_text(encoding='utf-8'))

    def current_inputs(proof):
        for resource, expected in proof['inputs'].items():
            path = ROOT / 'game' / resource.removeprefix('res://')
            assert sha(path) == expected, resource
            files[path.relative_to(ROOT).as_posix()] = expected

    balance = read(ROOT / 'game/data/balance-prototype.json')
    formal = balance['units']['unit.yin.hammer']
    assert (formal['range'], formal['gold'], formal['production_seconds']) == (1.25, 95, 2.4)
    canonical = ROOT / 'assets/paper-warfront/balance-prototype.json'
    assert canonical.read_bytes() == (ROOT / 'game/data/balance-prototype.json').read_bytes()
    files[canonical.relative_to(ROOT).as_posix()] = sha(canonical)
    brief = next(u for u in read(ROOT / 'assets/paper-warfront/frame-rebuild/unit-briefs.json')['units'] if u['id'] == 'unit.yin.hammer')
    csv_path = ROOT / 'assets/paper-warfront/frame-rebuild/roster.csv'
    with csv_path.open(encoding='utf-8-sig', newline='') as stream:
        row = next(u for u in csv.DictReader(stream) if u['id'] == 'unit.yin.hammer')
    files[csv_path.relative_to(ROOT).as_posix()] = sha(csv_path)
    assert brief['mechanics']['range'] == json.loads(row['mechanics'])['range'] == formal['range']
    assert brief['hint'] == row['rule'] == formal['hint']
    for font_path in sorted((ROOT / 'game/assets/fonts').glob('*.ttf')):
        font = TTFont(font_path)
        assert all(ord(c) in font.getBestCmap() for c in formal['hint']), font_path.name
        font.close()
        files[font_path.relative_to(ROOT).as_posix()] = sha(font_path)

    paid = read(qa / 'paid-recipes.json')
    controls = read(qa / 'reach-controls.json')
    for proof in [paid, controls]:
        assert proof['passed'] and not proof['failures']
        current_inputs(proof)
        assert proof['observer_sha256'] == sha(ROOT / 'tools/paper-warfront/probe_paid_hammer_screen.gd')
    assert paid['formal_default'] and len(paid['records']) == 12
    assert not controls['formal_default'] and len(controls['records']) == 24
    pairs = {(r['map'], r['side'], r['mode'], r['effective_range']): r for r in controls['records']}
    records = []
    for r in paid['records']:
        assert r['range_override'] is None and r['effective_range'] == 1.25
        assert r['ledger_ok'] and r['friend_ok'] and r['paid_uid'] > 0 and r['hits'] > 0
        assert r['research_completed'] >= 4.98 and r['ordered_at'] >= r['research_completed']
        assert r['born'] >= r['ordered_at'] + 2.38
        assert sum(e['gold_spent'] for e in r['paid'] if e['side'] == r['side']) == 206
        key = (r['map'], r['side'], r['mode'])
        legacy, selected = pairs[(*key, .82)], pairs[(*key, 1.25)]
        assert r['hits'] == selected['hits'] > legacy['hits']
        assert abs(r['event_damage'] - selected['event_damage']) < .001
        records.append({'map': r['map'], 'side': r['side'], 'mode': r['mode'], 'legacy_hits': legacy['hits'], 'formal_hits': r['hits'], 'formal_event_damage': r['event_damage'], 'paid_uid': r['paid_uid']})

    for name in ['desktop', 'phone']:
        folder = qa / 'gpu' / name
        capture = read(folder / 'report.json')
        assert capture['passed'] and capture['hit_events'] == 26 and len(capture['captures']) >= 12
        assert {'windup', 'attack'} <= set(capture['states'])
        current_inputs(capture)
        for frame in capture['captures']:
            path = folder / frame['path']
            assert path.stat().st_size > 1000
            files[path.relative_to(ROOT).as_posix()] = sha(path)
        assert 'SCRIPT ERROR' not in (folder / 'runtime.log').read_text(encoding='utf-8')
    regression = read(options.regression if options.regression else qa / 'regression/report.json')
    assert regression['passed'] and regression['source_unchanged']
    for relative, expected in regression['inputs'].items():
        assert sha(ROOT / relative) == expected, relative
    report = {'passed': True, 'errors': [], 'records': records, 'files': files,
              'source_mechanism_checks': sum(t['checks'] for t in regression['tests']),
              'scope': 'Current formal hammer definitions, original-fee native CPU and GPU recipes, real research/production, friendly event sides, both bundled fonts and source regression. Stationary base fixtures extend HP; six-front and GPU recipes use ordinary endpoints. No default AI, faction balance, real-time performance or Android hardware acceptance.'}
    (qa / 'verification.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'passed': True, 'recipe_pairs': len(records), 'source_mechanism_checks': report['source_mechanism_checks']}))


if __name__ == '__main__':
    main()
