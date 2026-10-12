"""A same-process alternating terrain comparison, including actual cache hits."""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[2]
QA = ROOT / "output/qa/godot/pressure-runtime-rc31"
target = QA / "terrain-abba-observer-r1.gd"
assert not target.exists()
original = ROOT / "tools/paper-warfront/probe_realtime_battle.gd"
source = original.read_text("utf-8")
marker = 'const App = preload("res://scripts/main.gd")\n'
addition = '''class SwitchingTerrainCache:
	extends "res://scripts/theatre_ground_cache.gd"
	var optimized: bool=true
	func draw_terrain(view,sim):
		if optimized:super.draw_terrain(view,sim)
		else:
			Terrain.ground(view,sim)
			Terrain.decorations(view,sim)
'''
source = source.replace(marker, marker + addition, 1)
source = source.replace('\tvar observation_draw_us: int=0\n', '\tvar observation_draw_us: int=0\n\tvar terrain_draw_samples: Array=[]\n\tvar terrain_draw_index: int=0\n', 1)
source = source.replace('''		var before: int=Time.get_ticks_usec()
		super._draw()
		observation_draw_us=Time.get_ticks_usec()-before''', '''		var before: int=Time.get_ticks_usec()
		if not menu and sim!=null:
			if not ground_mesh_cache is SwitchingTerrainCache:ground_mesh_cache=SwitchingTerrainCache.new()
			ground_mesh_cache.optimized=terrain_draw_index%4 in [0,3]
			terrain_draw_index+=1
			var reuse_before: int=ground_mesh_cache.terrain_reuses
			var rebuild_before: int=ground_mesh_cache.terrain_rebuilds
			super._draw()
			terrain_draw_samples.append({"kind":"optimized" if ground_mesh_cache.optimized else "original","terrain_us":layer_cpu_us.background_ground,"total_us":Time.get_ticks_usec()-before,"camera_x":camera_x,"reuse":ground_mesh_cache.terrain_reuses>reuse_before,"rebuilt":ground_mesh_cache.terrain_rebuilds>rebuild_before})
		else:super._draw()
		observation_draw_us=Time.get_ticks_usec()-before''', 1)
source = source.replace('\tprint("REALTIME_BATTLE ",', '''	FileAccess.open(folder+"/terrain-abba.json",FileAccess.WRITE).store_string(JSON.stringify({"samples":app.view.terrain_draw_samples,"source_sha256":FileAccess.get_sha256("res://scripts/theatre_ground_cache.gd"),"observer_sha256":FileAccess.get_sha256(get_script().resource_path),"scope":"Actual one-process ABBA original/candidate terrain calls under the same App battle, view and renderer, with hit/rebuild and camera samples. Mixed stream FPS is not pure candidate FPS; source trial, not shipped packages or Android hardware."},"  "))
	print("REALTIME_BATTLE ",''', 1)
assert "terrain_draw_samples.append" in source and "terrain-abba.json" in source
target.write_text(source, "utf-8")
(QA / "terrain-abba-observer-inputs.json").write_text(json.dumps({"original_observer": original.relative_to(ROOT).as_posix(),
    "original_sha256": hashlib.sha256(original.read_bytes()).hexdigest(), "observer_sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
    "scope": "Derived telemetry observer; actual superclass rendering and simulation unchanged. ABBA switch applies only to the static terrain method."}, indent=2) + "\n", "utf-8")
print("Prepared native same-process ABBA terrain probe")
