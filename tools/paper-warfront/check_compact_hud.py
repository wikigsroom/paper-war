"""Native Windows GPU checks for the source HUD, including touch and real fees."""
import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CASES = {
    "desktop": ("1280x720", []),
    "phone": ("1280x720", ["--mobile-ui", "--mobile-density", "2"]),
    "compact": ("1136x640", ["--mobile-ui", "--mobile-density", "2"]),
    "short": ("1136x512", ["--mobile-ui", "--mobile-density", "2"]),
}


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", choices=CASES)
    parser.add_argument("--output", type=Path, default=ROOT / "output/qa/godot/core-alignment-rc15/hud70/runtime")
    args = parser.parse_args()
    startup = subprocess.STARTUPINFO()
    startup.dwFlags = 1
    startup.wShowWindow = 0
    reports = []
    for name, (resolution, flags) in CASES.items():
        if args.case and name != args.case:
            continue
        folder = args.output.resolve() / name
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "report.json").unlink(missing_ok=True)
        result = subprocess.run([
            str(ROOT / ".tools/godot/Godot_v4.7.2-stable_win64_console.exe"),
            "--path", str(ROOT / "game"), "--rendering-method", "gl_compatibility",
            "--resolution", resolution, "--script", "res://tests/recruitment_ui_qa.gd",
            "--", *flags, "--output", str(folder), "--profile-path", str(folder / "profile.json"),
        ], cwd=ROOT, capture_output=True, encoding="utf-8", errors="replace", startupinfo=startup, timeout=120)
        log = result.stdout + result.stderr
        (folder / "runtime.log").write_text(log, encoding="utf-8")
        report = json.loads((folder / "report.json").read_text(encoding="utf-8")) if (folder / "report.json").exists() else {}
        passed = result.returncode == 0 and report.get("passed", False) and "SCRIPT ERROR" not in log and "ERROR:" not in log
        outcome = {"name": name, "passed": passed, "checks": len(report.get("checks", [])),
                   "coverage": [c for c in report.get("checks", []) if "70 percent" in c["name"]],
                   "failures": [c for c in report.get("checks", []) if not c["passed"]]}
        reports.append(outcome)
        print(json.dumps(outcome, ensure_ascii=False), flush=True)
        if not passed:
            print(log[-3500:], flush=True)
    return 0 if reports and all(r["passed"] for r in reports) else 1


if __name__ == "__main__":
    raise SystemExit(main())
