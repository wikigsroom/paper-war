"""Preserve historical audits; generate a new RC33 branch using all common gates."""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[2]
source = ROOT / "tools/paper-warfront/audit_answers_preview.py"
target = ROOT / "tools/paper-warfront/audit_phase_preview.py"
assert not target.exists()
s = source.read_text("utf-8")
needle = "        if release_number>=32:\n            from verify_answers_release_evidence import verify\n"
assert s.count(needle) == 1
s = s.replace(needle, "        if release_number>=33:\n            from verify_phase_release_evidence import verify\n            result.update(verify(ROOT,qa,args.version,manifest,apk_logic))\n        elif release_number>=32:\n            from verify_answers_release_evidence import verify\n")
target.write_text(s, "utf-8")
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
(ROOT / "output/qa/godot/phase-runtime-rc33/audit-generation.json").write_text(json.dumps({
    "generator_sha256": sha(Path(__file__)), "original_audit_sha256": sha(source), "new_audit_sha256": sha(target),
    "evidence_branch_sha256": sha(ROOT / "tools/paper-warfront/verify_phase_release_evidence.py"),
    "scope": "NewRC33 audit keeps all established asset/signing/compiled/UI/story/map/FPS/common gates; replaces only the RC33 version-specific evidence branch. Historical audit bytes unchanged."
}, indent=2) + "\n", "utf-8")
print("Prepared RC33 audit with common gates retained")
