"""Separate renderer investigation on identical compiled RC33; no adoption."""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[2]
QA = ROOT / "output/qa/godot/render-runtime-rc34"
TARGET = ROOT / "tools/paper-warfront/check_rc34_backend_realtime.py"
assert not TARGET.exists()
source = ROOT / "tools/paper-warfront/check_realtime_battle.py"
s = source.read_text("utf-8")
needle = "ap.add_argument('--profile-layers', action='store_true')"
assert s.count(needle)==1
s = s.replace(needle, needle+"\nap.add_argument('--native-backend',choices=['mobile','gl_compatibility'],required=True)")
needle = "if args.case == 'phone':\n    cmd[1:1] = ['--rendering-method', 'gl_compatibility']"
assert s.count(needle)==1
s = s.replace(needle, "cmd[1:1] = ['--rendering-method', args.native_backend]")
TARGET.write_text(s, "utf-8")
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
(QA / "backend-observer-preparation.json").write_text(json.dumps({"passed":True,"generator_sha256":sha(Path(__file__)),
    "inherited_runner_sha256":sha(source),"new_runner_sha256":sha(TARGET),
    "scope":"Same actual compiled RC33 EXE and original natural-time observer. Explicit native renderer override only; stress actors, audio, desktop1280x720, frames, UI, particles, effects and visibility unchanged. No Vulkan/OpenGL outcome, formal settings change, export or hardware claim yet."
},indent=2)+"\n", "utf-8")
print("Prepared explicit native backend comparison",flush=True)
