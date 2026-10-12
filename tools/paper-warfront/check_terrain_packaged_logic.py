"""Compare actual compiled terrain helpers with independent frozen RC30 drawing."""
from pathlib import Path
import argparse
import hashlib
import json
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "output/qa/godot/pressure-runtime-rc31"
parser = argparse.ArgumentParser()
runtime = parser.add_mutually_exclusive_group(required=True)
runtime.add_argument("--pack", type=Path)
runtime.add_argument("--apk-runtime", type=Path)
parser.add_argument("--artifact", type=Path, required=True)
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args()
folder = args.output.resolve()
assert not folder.exists()
folder.mkdir(parents=True)
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
observer = folder / "observer.gd"
shutil.copy2(ROOT / "tools/paper-warfront/test_terrain_command_retention.gd", observer)
shutil.copy2(Path(__file__), folder / "runner.py")
frozen = json.loads((BASE / "freeze.json").read_text("utf-8"))
references = {}
for name in ["theatre_ground.gd", "theatre_ground_cache.gd"]:
    source = BASE / "oracle-runtime/scripts" / name
    assert sha(source) == frozen["oracle_scripts"][name]["oracle_sha256"]
    dest = folder / ("original_" + name)
    shutil.copy2(source, dest)
    references[dest.name] = sha(dest)
artifact = args.artifact.resolve()
if args.pack:
    assert args.pack.resolve() == artifact
    flags = ["--main-pack", str(artifact)]
else:
    project = args.apk_runtime.resolve()
    assert not list((project / "scripts").glob("*.gd"))
    for name in ["theatre_ground", "theatre_ground_cache", "map_runtime", "data_store"]:
        assert (project / "scripts" / (name + ".gdc")).is_file()
    flags = ["--path", str(project), "--rendering-method", "gl_compatibility"]
command = [str(ROOT / ".tools/godot/Godot_v4.7.2-stable_win64_console.exe"), *flags,
    "--resolution", "1280x720", "--script", str(observer), "--",
    "--baseline-ground", str(folder / "original_theatre_ground.gd"),
    "--baseline-cache", str(folder / "original_theatre_ground_cache.gd"),
    "--output", str(folder / "native.json")]
startup = subprocess.STARTUPINFO()
startup.dwFlags = 1
startup.wShowWindow = 0
result = subprocess.run(command, cwd=ROOT, startupinfo=startup, capture_output=True,
    encoding="utf-8", errors="replace", timeout=180)
log = result.stdout + result.stderr
(folder / "runtime.log").write_text(log, "utf-8")
assert result.returncode == 0 and "SCRIPT ERROR" not in log and "ERROR:" not in log, log[-4000:]
native = json.loads((folder / "native.json").read_text("utf-8"))
assert native["passed"] and not native["failures"] and native["checks"] == 5873
assert native["maps"] == 200 and native["native_draw_comparisons"] == 2521 and native["mesh_geometry_present"]
assert native["observer_sha256"] == sha(observer)
assert native["reference_ground_sha256"] == references["original_theatre_ground.gd"]
assert native["reference_cache_sha256"] == references["original_theatre_ground_cache.gd"]
if args.apk_runtime:
    assert native["source_sha256"] == sha(project / "scripts/theatre_ground_cache.gdc")
    assert native["ground_sha256"] == sha(project / "scripts/theatre_ground.gdc")
(folder / "report.json").write_text(json.dumps({"passed": True, "artifact": artifact.as_posix(),
    "artifact_sha256": sha(artifact), "runtime_kind": "windows_embedded_pack" if args.pack else "apk_extracted_bytecode_on_windows",
    "checks": native["checks"], "native_report_sha256": sha(folder / "native.json"),
    "runner_sha256": sha(folder / "runner.py"), "observer_sha256": sha(observer), "references": references,
    "compiled_cache_sha256": native["source_sha256"], "compiled_ground_sha256": native["ground_sha256"],
    "scope": "Fresh native drawing-parameter comparison against independent RC30 helpers, actual EXE embedded / APK extracted compiled GDC. Synthetic textures isolate exact commands and resource invalidation; raster captures and natural FPS separately checked. APK on Windows is not Android hardware."
}, indent=2) + "\n", "utf-8")
print("Compiled terrain retention", native["checks"], "checks passed")
