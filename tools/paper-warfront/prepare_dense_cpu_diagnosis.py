"""Prepare nested diagnostic timers; never use them as a performance benchmark."""
from pathlib import Path
import hashlib
import json
import shutil

ROOT = Path(__file__).resolve().parents[2]
QA = ROOT / 'output/qa/godot/dense-runtime-rc30'
TARGET = QA / 'profile-r2-runtime'
assert not TARGET.exists(), 'Do not overwrite completed diagnostic inputs'
shutil.copytree(QA / 'baseline-runtime', TARGET)
profiler = TARGET / 'tests/capacity_cpu_profiler.gd'
source = profiler.read_text('utf-8')
source += '''
func nearest_melee_query(anchor: Dictionary,side: int,priority: bool,reach: float) -> Dictionary:
	var before: int=Time.get_ticks_usec();var result: Dictionary=super.nearest_melee_query(anchor,side,priority,reach);record("melee_query",before);return result
func nearest_ranged_query(origin: Vector2,side: int,priority: bool,reach: float) -> Dictionary:
	var before: int=Time.get_ticks_usec();var result: Dictionary=super.nearest_ranged_query(origin,side,priority,reach);record("ranged_query",before);return result
func prepare_melee_queries():
	var before: int=Time.get_ticks_usec();super.prepare_melee_queries();record("melee_index",before)
func prepare_ranged_queries():
	var before: int=Time.get_ticks_usec();super.prepare_ranged_queries();record("ranged_index",before)
func physical_point(a: Dictionary) -> Vector2:
	var before: int=Time.get_ticks_usec();var result: Vector2=super.physical_point(a);record("physical_point",before);return result
func combat_distance(a: Dictionary,b: Dictionary,def: Dictionary) -> float:
	var before: int=Time.get_ticks_usec();var result: float=super.combat_distance(a,b,def);record("combat_distance",before);return result
func movement_anchor(u: Dictionary) -> Dictionary:
	var before: int=Time.get_ticks_usec();var result: Dictionary=super.movement_anchor(u);record("movement_snapshot",before);return result
func apply_movement_anchor(u: Dictionary,anchor: Dictionary):
	var before: int=Time.get_ticks_usec();super.apply_movement_anchor(u,anchor);record("movement_apply",before)
func release_attack_intents():
	var before: int=Time.get_ticks_usec();super.release_attack_intents();record("attack_release",before)
'''
profiler.write_text(source, 'utf-8')
visibility = TARGET / 'tests/dense_visibility_profiler.gd'
visibility.write_text('''extends "res://scripts/battle_visibility.gd"
var timings: Dictionary={}
func record(label: String,before: int):
	if not timings.has(label):timings[label]={"calls":0,"us":0}
	timings[label].calls+=1;timings[label].us+=Time.get_ticks_usec()-before
func refresh():
	var before: int=Time.get_ticks_usec();super.refresh();record("refresh",before)
func reveal(side: int,a: Dictionary,r: float):
	var before: int=Time.get_ticks_usec();super.reveal(side,a,r);record("reveal",before)
func propagate(side: int):
	var before: int=Time.get_ticks_usec();super.propagate(side);record("propagate",before)
func merge(spans: Array) -> Array:
	var before: int=Time.get_ticks_usec();var result: Array=super.merge(spans);record("merge",before);return result
func point_visible(side: int,a: Dictionary) -> bool:
	var before: int=Time.get_ticks_usec();var result: bool=super.point_visible(side,a);record("point_visible",before);return result
''', 'utf-8')
probe = TARGET / 'tests/probe_capacity_cpu.gd'
source = probe.read_text('utf-8').replace('const Profiler=', 'const MeasuredVisibility=preload("res://tests/dense_visibility_profiler.gd")\nconst Profiler=', 1)
source = source.replace('\ts.visibility.refresh();s.drain_events()', '''	var vision=MeasuredVisibility.new(s)
	for name in ["revision","current","explored","last_seen","visible_uids","enemies","node_budgets","spotted","alert_at","firing_reveals"]:vision.set(name,s.visibility.get(name))
	s.visibility=vision
	s.visibility.refresh();s.drain_events()''', 1)
source = source.replace('\t\ts.timings.clear();', '\t\ts.timings.clear();s.visibility.timings.clear();', 1)
source = source.replace('"timings":s.timings.duplicate(true),', '"timings":s.timings.duplicate(true),"visibility_timings":s.visibility.timings.duplicate(true),', 1)
probe.write_text(source, 'utf-8')
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
(TARGET / 'profile-inputs.json').write_text(json.dumps({
    'inputs': {p.relative_to(TARGET).as_posix(): sha(p) for p in [profiler, visibility, probe]},
    'scope': 'Nested timers on exact frozen rc29 combat. Instrumentation overhead is substantial; timings diagnose call sites, not uninstrumented CPU or FPS.'
}, indent=2), 'utf-8')
print('Prepared extended CPU diagnosis')
