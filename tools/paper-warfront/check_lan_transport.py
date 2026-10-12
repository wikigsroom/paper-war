"""Native two-process ENet probe; ready files avoid buffered stdout races."""
import json
import pathlib
import subprocess
import tempfile
import time
import argparse
import hashlib

parser=argparse.ArgumentParser()
parser.add_argument("--probe", choices=["commands", "research", "match"], default="commands")
options=parser.parse_args()

ROOT = pathlib.Path(__file__).resolve().parents[2]
QA = ROOT / "output/qa/godot/core-alignment-rc7"
QA.mkdir(parents=True, exist_ok=True)
marker = QA / "lan-ready.flag"
marker.unlink(missing_ok=True)
command = [str(ROOT / ".tools/godot/Godot_v4.7.2-stable_win64_console.exe"),
           "--headless", "--path", str(ROOT / "game"),
           "--script", {"commands":"tests/lan_transport_probe.gd", "research":"tests/lan_research_probe.gd", "match":"tests/lan_full_match_probe.gd"}[options.probe]]
with tempfile.TemporaryFile() as host_log:
    host = subprocess.Popen(command + ["--", "--host", "--ready", str(marker)],
                            stdout=host_log, stderr=subprocess.STDOUT)
    try:
        deadline = time.monotonic() + 30
        while not marker.exists():
            if host.poll() is not None or time.monotonic() > deadline:
                raise RuntimeError("Host did not become ready")
            time.sleep(.05)
        client = subprocess.run(command, capture_output=True, text=True,
                                encoding="utf-8", timeout=75 if options.probe=="match" else 20)
        host.wait(timeout=75 if options.probe=="match" else 20)
        host_log.seek(0)
        report = {"scope": "Native Windows loopback transport, not LAN UI or Android proof",
                  "host_exit": host.returncode, "client_exit": client.returncode,
                  "host_log": host_log.read().decode("utf-8", errors="replace"),
                  "client_log": client.stdout + client.stderr}
        report["probe"]=options.probe
        report["simulation_wall_rate"]=8 if options.probe=="match" else 1
        report["inputs"]={str(path.relative_to(ROOT)):hashlib.sha256(path.read_bytes()).hexdigest()
                          for path in [ROOT/"game/scripts/lan_match.gd",ROOT/"game/scripts/match_projection.gd",ROOT/"game/scripts/client_battle.gd",ROOT/"game/scripts/battle_sim.gd",ROOT/"game"/command[-1]]}
        report["passed"]=not client.returncode and not host.returncode and "LAN_CLIENT_PASS" in client.stdout and "SCRIPT ERROR" not in report["host_log"]+report["client_log"]
        (QA / {"commands":"lan-transport-marker.json", "research":"lan-research.json", "match":"lan-full-match.json"}[options.probe]).write_text(
            json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps(report, ensure_ascii=False))
        if not report["passed"]:
            raise SystemExit(1)
    finally:
        if host.poll() is None:
            host.terminate()
            host.wait(timeout=5)
        marker.unlink(missing_ok=True)
