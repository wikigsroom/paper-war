"""Bind the adopted RC35 rendering change to a new preview version."""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[2]
QA = ROOT / "output/qa/godot/render-runtime-rc35"
OUT = QA / "version-preparation.json"
assert not OUT.exists()
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()

project = ROOT / "game/project.godot"
presets = ROOT / "game/export_presets.cfg"
project_before = sha(project)
presets_before = sha(presets)
project_text = project.read_text("utf-8")
presets_text = presets.read_text("utf-8")
assert 'config/version="3.0.0-rc34-preview"' in project_text
assert 'version/name="3.0.0-rc34-preview"' in presets_text
assert "version/code=30033" in presets_text
project.write_text(project_text.replace('config/version="3.0.0-rc34-preview"', 'config/version="3.0.0-rc35-preview"'), "utf-8")
presets.write_text(
    presets_text.replace("version/code=30033", "version/code=30034").replace(
        'version/name="3.0.0-rc34-preview"', 'version/name="3.0.0-rc35-preview"'
    ),
    "utf-8",
)
OUT.write_text(json.dumps({
    "passed": True,
    "version": "3.0.0-rc35-preview",
    "changed_inputs": {
        "game/project.godot": {"before": project_before, "after": sha(project)},
        "game/export_presets.cfg": {"before": presets_before, "after": sha(presets)},
    },
    "scope": "Version/code binding only after RC35 atlas cache adoption. No gameplay, map, story, fog, UI, asset or export preset target changes.",
}, ensure_ascii=False, indent=2) + "\n", "utf-8")
print(json.dumps({"passed": True, "project_sha256": sha(project), "presets_sha256": sha(presets)}))
