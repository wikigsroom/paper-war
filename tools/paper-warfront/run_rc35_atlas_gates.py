"""Serial complete source tests and new geometry boundary, on an isolated trial."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
QA = ROOT / "output/qa/godot/render-runtime-rc35"
PROJECT = QA / "atlas-cache-runtime"
OUT = QA / "atlas-cache-source-gates.json"
assert not OUT.exists()
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
freeze = json.loads((QA / "preparation.json").read_text("utf-8"))
before = {p.relative_to(PROJECT).as_posix(): sha(p) for part in ["scripts", "data", "tests"] for p in (PROJECT / part).rglob("*") if p.is_file()}
jobs = []
commands = [
    ("regression", [sys.executable, str(ROOT / "tools/paper-warfront/check_ai_engagement.py"), "--mechanisms-only", "--project", str(PROJECT), "--output", str(QA / "atlas-cache-regression")], QA / "atlas-cache-regression/report.json", 1800),

]
for name, cmd, report, timeout in commands:
    log = QA / ("atlas-cache-" + name + "-runner.log")
    assert not report.exists() and not log.exists()
    print("Starting " + name, flush=True)
    with log.open("w", encoding="utf-8") as f:
        run = subprocess.run(cmd, cwd=ROOT, stdout=f, stderr=subprocess.STDOUT, timeout=timeout)
    d = json.loads(report.read_text("utf-8")) if report.exists() else {}
    text = log.read_text("utf-8")
    passed = run.returncode == 0 and d.get("passed", False) and "SCRIPT ERROR" not in text and "ERROR:" not in text
    checks = sum(r["checks"] for r in d["tests"]) if name == "regression" and "tests" in d else d.get("checks", 0)
    row = {"job": name, "passed": passed, "checks": checks, "groups": len(d.get("tests", [])), "report_sha256": sha(report) if report.exists() else None, "log_sha256": sha(log)}
    jobs.append(row)
    print(json.dumps(row), flush=True)
    if not passed: break
unchanged = all(sha(PROJECT / n) == h for n, h in before.items())
passed = len(jobs) == 1 and all(r["passed"] for r in jobs) and unchanged
OUT.write_text(json.dumps({"passed": passed, "jobs": jobs, "source_unchanged": unchanged,
    "runner_sha256": sha(Path(__file__)), "preparation_sha256": sha(QA / "preparation.json"), "freeze_sha256": None, "observer_preparation_sha256": None,
    "trial_scripts": {p.name: sha(p) for p in (PROJECT / "scripts").glob("*.gd")}, "scope": "Fresh complete78 source regression. Native shard reference/eviction checks are in the separate42-pose render gate; the retired sprite-cache boundary is not counted. One rendering script changed; all43 other raw helpers and all gameplay/story data remain identical RC33. Not pixel, natural FPS, compiled release or physical Android validation."
}, indent=2) + "\n", "utf-8")
assert passed, "Inspect retained gate logs"
