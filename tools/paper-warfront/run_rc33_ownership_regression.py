"""Validate the native mesh trial against all78 source regression groups."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
QA = ROOT / "output/qa/godot/phase-runtime-rc33"
TRIAL = QA / "native-ownership-r1-runtime"
OUT = QA / "ownership-r1-regression"
LOG = QA / "ownership-r1-regression-orchestration.log"
RECEIPT = QA / "ownership-r1-source-gates.json"
assert not any(p.exists() for p in [OUT, LOG, RECEIPT])
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
prep = json.loads((QA / "ownership-r1-preparation.json").read_text("utf-8"))
assert prep["passed"]
assert json.loads((QA / "ownership-r1-render-equivalence/report.json").read_text("utf-8"))["passed"]
before = {str(p.relative_to(TRIAL)): sha(p) for folder in ["scripts", "data", "tests"] for p in (TRIAL / folder).glob("*") if p.is_file()}
print("Starting ownership mesh full78 source regression", flush=True)
with LOG.open("w", encoding="utf-8") as f:
    run = subprocess.run([sys.executable, str(ROOT / "tools/paper-warfront/check_ai_engagement.py"), "--mechanisms-only", "--project", str(TRIAL), "--output", str(OUT)], cwd=ROOT, stdout=f, stderr=subprocess.STDOUT, timeout=1800)
report = OUT / "report.json"
d = json.loads(report.read_text("utf-8"))
unchanged = all(sha(TRIAL / n) == h for n, h in before.items())
same = all(sha(TRIAL / "scripts" / n) == h for n, h in prep["candidate_scripts"].items())
checks = sum(t["checks"] for t in d["tests"])
passed = run.returncode == 0 and d["passed"] and unchanged and same and len(d["tests"]) == 78 and checks == 195435 and "ERROR:" not in LOG.read_text("utf-8")
RECEIPT.write_text(json.dumps({
    "passed": passed, "source_tests": len(d["tests"]), "source_checks": checks,
    "source_unchanged": unchanged, "preparation_closure_matches": same,
    "runner_sha256": sha(Path(__file__)), "report_sha256": sha(report), "log_sha256": sha(LOG),
    "preparation_sha256": sha(QA / "ownership-r1-preparation.json"),
    "pixel_report_sha256": sha(QA / "ownership-r1-render-equivalence/report.json"),
    "source_inputs": before,
    "scope": "Isolated ownership rendering trial: all78 source groups195435 checks with complete assets/imports. Retains earlier R3 simulation exact-state gates; changes one view script from that verified simulation candidate. No formal adoption, export, balance, FPS or Android hardware claim."
}, indent=2) + "\n", "utf-8")
print(json.dumps({"passed": passed, "tests": len(d["tests"]), "checks": checks, "unchanged": unchanged}), flush=True)
assert passed, "Inspect " + str(LOG)
