"""Run RC33 marching boundaries and full-state phases on actual EXE/APK code."""
from pathlib import Path
import argparse
import hashlib
import json
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "output/qa/godot/phase-runtime-rc33"
ap = argparse.ArgumentParser()
runtime = ap.add_mutually_exclusive_group(required=True)
runtime.add_argument("--pack", type=Path)
runtime.add_argument("--apk-runtime", type=Path)
ap.add_argument("--artifact", type=Path, required=True)
ap.add_argument("--output", type=Path, required=True)
args = ap.parse_args()
folder = args.output.resolve()
assert not folder.exists()
folder.mkdir(parents=True)
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
shutil.copy2(Path(__file__), folder / "runner.py")
freeze = json.loads((BASE / "freeze.json").read_text("utf-8"))
for n, r in freeze["oracle_scripts"].items():
    assert sha(BASE / "oracle-runtime/scripts" / n) == r["oracle_sha256"]
artifact = args.artifact.resolve()
if args.pack:
    assert args.pack.resolve() == artifact
    flags = ["--main-pack", str(artifact)]
else:
    project = args.apk_runtime.resolve()
    assert not list((project / "scripts").glob("*.gd"))
    flags = ["--path", str(project)]
rows = []
for name, source_name, checks in [("marching-boundary", "marching-boundary-observer-r3.gd", 432427), ("marching-phase", "marching-phase-observer-r2.gd", 28811)]:
    original = BASE / source_name
    source = original.read_text("utf-8")
    needle = 'FileAccess.get_sha256("res://scripts/battle_sim.gd")'
    assert source.count(needle) == 1
    source = source.replace(needle, 'FileAccess.get_sha256("res://scripts/battle_sim.gdc")')
    observer = folder / (name + "-observer.gd")
    observer.write_text(source, "utf-8")
    report = folder / (name + ".json")
    oracle = BASE / "oracle-runtime/scripts/battle_sim.gd"
    arguments = [str(report), str(oracle)] if name == "marching-boundary" else ["--baseline", str(oracle), "--output", str(report)]
    command = [str(ROOT / ".tools/godot/Godot_v4.7.2-stable_win64_console.exe"), "--headless", *flags, "--script", str(observer), "--", *arguments]
    run = subprocess.run(command, cwd=ROOT, capture_output=True, encoding="utf-8", errors="replace", timeout=600)
    log = run.stdout + run.stderr
    (folder / (name + ".log")).write_text(log, "utf-8")
    assert run.returncode == 0 and "SCRIPT ERROR" not in log and "ERROR:" not in log, log[-2500:]
    native = json.loads(report.read_text("utf-8"))
    assert native["passed"] and native["checks"] == checks and not native["failures"]
    assert native["observer_sha256"] == sha(observer) and native["baseline_sha256"] == sha(oracle)
    assert native["simulation_sha256"]
    if args.apk_runtime:
        assert native["simulation_sha256"] == sha(project / "scripts/battle_sim.gdc")
    rows.append({"name": name, "checks": checks, "report_sha256": sha(report), "observer_sha256": sha(observer), "original_observer_sha256": sha(original), "compiled_simulation_sha256": native["simulation_sha256"]})
    print(name, "actual bytecode", checks, "passed", flush=True)
(folder / "report.json").write_text(json.dumps({
    "passed": True, "artifact_sha256": sha(artifact),
    "runtime_kind": "windows_embedded_pack" if args.pack else "apk_extracted_bytecode_on_windows",
    "checks": sum(r["checks"] for r in rows), "tests": rows, "runner_sha256": sha(Path(__file__)),
    "oracle_closure": freeze["oracle_scripts"],
    "scope": "Independent full44-helper RC32 source closure against actual compiled simulation.200 maps/directions marching precision and fallback,30 all-faction mixed-worker phase cases with full state/RNG/fog and lethal/TTL/ownership/reorder changes, bounded cache/restart. Only report hash suffix changed for bytecode. APK code loaded on Windows is not Android hardware."
}, indent=2) + "\n", "utf-8")
