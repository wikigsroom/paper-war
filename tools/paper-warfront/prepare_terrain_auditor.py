"""Derive a new audit entry point; preserve all already bound historical tools."""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[2]
before = ROOT / "tools/paper-warfront/audit_preview_build.py"
target = ROOT / "tools/paper-warfront/audit_terrain_preview.py"
assert not target.exists()
source = before.read_text("utf-8")
marker = """        if release_number>=30:
            from verify_dense_release_evidence import verify"""
assert source.count(marker) == 1
source = source.replace(marker, """        if release_number>=31:
            from verify_terrain_release_evidence import verify
            result.update(verify(ROOT,qa,args.version,manifest,apk_logic))
        elif release_number>=30:
            from verify_dense_release_evidence import verify""", 1)
target.write_text(source, "utf-8")
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
(ROOT / "output/qa/godot/pressure-runtime-rc31/auditor-generation.json").write_text(json.dumps({
    "original_auditor_sha256": sha(before), "derived_auditor_sha256": sha(target),
    "generator_sha256": sha(Path(__file__)),
    "scope": "Adds only the RC31 evidence branch; all common compiled UI/story/render/native FPS/package requirements stay intact. Historical RC30 auditor remains byte-identical."
}, indent=2) + "\n", "utf-8")
print("Prepared RC31 audit entry point without editing the old auditor")
