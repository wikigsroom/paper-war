"""Bind a full-closure, uninstrumented, alternating native capacity comparison."""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[2]
QA = ROOT / 'output/qa/godot/dense-runtime-rc30'
target = QA / 'capacity-query-reuse-observer.gd'
assert not target.exists()
old = ROOT / 'output/qa/godot/packed-query-rc28/capacity-observer-parse-r2.gd'
source = old.read_text('utf-8')
source = source.replace('var loaded_source_matches: bool=Simulation.get_source_code()', 'var simulation_script: GDScript=Simulation\n\tvar loaded_source_matches: bool=simulation_script.get_source_code()', 1)
source = source.replace('"ai_rng":[s.ai_rng[0].state,s.ai_rng[1].state]}', '"ai_rng":[s.ai_rng[0].state,s.ai_rng[1].state],"visibility_uids":s.visibility.visible_uids,"visible_enemy_order":[s.visibility.enemies[0].map(func(a):return a.uid),s.visibility.enemies[1].map(func(a):return a.uid)],"spotted":s.visibility.spotted,"alert_at":s.visibility.alert_at,"firing_reveals":s.visibility.firing_reveals,"result_reason":s.result_reason,"intercept_crossed":s.intercept_crossed}')
source = source.replace('"units":b.units.size()}', '"units":b.units.size(),"snapshot_reuses":b.target_snapshot_reuses,"snapshot_rebuilds":b.target_snapshot_rebuilds}')
source = source.replace('against frozen rc27', 'against the frozen complete rc29 script closure')
target.write_text(source, 'utf-8')
(QA / 'initial-observer-parse-failure.json').write_text(json.dumps({
    'process_exit_code': 1,
    'observer': old.relative_to(ROOT).as_posix(),
    'observer_sha256': hashlib.sha256(old.read_bytes()).hexdigest(),
    'diagnosis': 'An old observation calls get_source_code on an inferred preload class. Adding a class with a matches method made Godot resolve this as a class call. The new observer explicitly types the resource as GDScript; candidate inputs stay unchanged.',
    'exact_error': 'Parse Error: Cannot call non-static function "get_source_code()" on the class "res://scripts/battle_sim.gd" directly. Make an instance instead.',
    'scope': 'Observer parse failure before any simulated comparison; never counted as gameplay evidence.'
}, indent=2), 'utf-8')
print('Prepared explicit-script full-state observer')
