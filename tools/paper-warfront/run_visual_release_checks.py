"""Run native visual release checks sequentially; no browser or emulator."""
import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ap = argparse.ArgumentParser()
ap.add_argument('--version', required=True)
ap.add_argument('--qa', type=Path, required=True)
args = ap.parse_args()
qa = args.qa.resolve()
exe = ROOT / 'release' / args.version / 'windows/PaperWarfront.exe'
environment = {**os.environ, 'PAPER_RELEASE_VERSION': args.version, 'PAPER_QA_DIR': str(qa)}
jobs = [
    ('check_fog_rendering.py', ['--output', str(qa / 'fog-render'), '--pack', str(exe)]),
    ('check_stage_proportions.py', ['--output', str(qa / 'stage-proportions'), '--pack', str(exe)]),
    ('check_ui_modal_navigation.py', ['--output', str(qa / 'modal-navigation'), '--pack', str(exe)]),
    ('check_live_battle_sheets.py', ['--output', str(qa / 'live-battle-sheets'), '--pack', str(exe)]),
    ('check_paper_ui.py', ['--output', str(qa / 'paper-ui'), '--pack', str(exe)]),
    ('smoke_mobile_exports.py', []),
]
if int(re.search(r'-rc(\d+)', args.version).group(1)) >= 22:
    jobs.insert(0, ('check_camera_rendering.py', ['--output', str(qa / 'camera-render'), '--pack', str(exe)]))
for name, flags in jobs:
    print('Starting ' + name, flush=True)
    run = subprocess.run([sys.executable, str(ROOT / 'tools/paper-warfront' / name), *flags], cwd=ROOT, env=environment)
    if run.returncode:
        raise SystemExit(run.returncode)
print('All native visual release checks passed', flush=True)
