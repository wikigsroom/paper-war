"""Freeze observed control-lock responses; never edit the shipping runtime."""
import argparse
import difflib
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[2]
QA = ROOT / 'output/qa/godot/fielding-contact-rc25'
ap = argparse.ArgumentParser()
ap.add_argument('--dedup', action='store_true')
args = ap.parse_args()
name = 'ranged-r5' if args.dedup else 'ranged-r4'
baseline = QA / 'rc24-runtime'
prior = QA / 'ranged-r3-runtime/scripts/tactical_ai.gd'
target = QA / (name + '-runtime')
assert not target.exists(), 'Never overwrite frozen candidates'
source = prior.read_text('utf-8')
old = '\t\tvar fighting: bool=own.any(func(u):return sim.combat_distance(enemy,u,weapon)<=float(weapon.range)+.3)\n\t\tif not fighting and not economic_attack(sim,side,enemy):continue\n'
new = '''\t\tvar fighting: bool=own.any(func(u):
\t\t\tvar def: Dictionary=sim.db.balance.units[u.id]
\t\t\tif not is_frontline(def) or sim.combat_distance(enemy,u,weapon)>float(weapon.range)+.3:return false
\t\t\tfor status in ["bind","stun","root","cold"]:
\t\t\t\tif not u.statuses.has(status) or int(u.statuses[status].get("source",-1))!=int(enemy.side):continue
\t\t\t\tif status in ["bind","stun"] or sim.combat_distance(u,enemy,def)>float(def.range)+.3:return true
\t\t\treturn false)
\t\tif not fighting:continue
'''
assert source.count(old) == 1
source = source.replace(old, new)
if args.dedup:
    old_coverage = ' and sim.combat_distance(u,enemy,sim.db.balance.units[u.id])<=float(sim.db.balance.units[u.id].range)+.3'
    assert source.count(old_coverage) == 1
    source = source.replace(old_coverage, '')
# The affordable-only variants do not execute the unused delivery forecast.
start = source.index('# Only actual carried cargo already coming home')
end = source.index('static func unbuilt_facility_reserve', start)
source = source[:start] + source[end:]
old_purchase = '''\t\tif counter!="" and (float(sim.db.balance.units[counter].gold)<=p.gold or false):
\t\t\tvar affordable: bool=float(sim.db.balance.units[counter].gold)<=p.gold
\t\t\tif affordable or contact_counter_delivery_due(sim,side,counter,enemies):
\t\t\t\tbest=counter;p.ai_research="";p.ai_build_reserve=0.0
'''
assert source.count(old_purchase) == 1
source = source.replace(old_purchase, '\t\tif counter!="" and float(sim.db.balance.units[counter].gold)<=p.gold:\n\t\t\tbest=counter;p.ai_research="";p.ai_build_reserve=0.0\n')
shutil.copytree(baseline, target, ignore=shutil.ignore_patterns('.godot'))
path = target / 'scripts/tactical_ai.gd'
path.write_text(source, 'utf-8')
diff = QA / (name + '.diff')
diff.write_text(''.join(difflib.unified_diff((baseline / 'scripts/tactical_ai.gd').read_text('utf-8').splitlines(keepends=True), source.splitlines(keepends=True), fromfile='rc24/tactical_ai.gd', tofile=name + '/tactical_ai.gd')), 'utf-8')
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
(target / 'candidate.json').write_text(json.dumps({'policy': name, 'baseline': '3.0.0-rc24-preview',
    'shipping_source_changed': False, 'observed_control_lock_only': True, 'deduplicate_living_adequate_weapon': args.dedup,
    'prices_times_roads_fog_unchanged': True, 'baseline_ai_sha256': sha(baseline / 'scripts/tactical_ai.gd'),
    'ai_sha256': sha(path), 'prior_r3_ai_sha256': sha(prior), 'diff_sha256': sha(diff), 'generator_sha256': sha(Path(__file__))}, indent=2), 'utf-8')
print('Frozen control-lock response prepared:', name)
