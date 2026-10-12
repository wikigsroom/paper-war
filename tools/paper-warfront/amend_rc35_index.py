"""Correct the release index pointers after RC35 registration."""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[2]
QA = ROOT / "output/qa/godot/render-runtime-rc35"
AMENDMENT = ROOT / "assets/paper-warfront/system-revisions/rc35-atlas-cache-index-amendment.json"
assert not AMENDMENT.exists()
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
paths = [ROOT / "README.md", ROOT / "docs/paper-warfront/README.md"]
before = {str(p.relative_to(ROOT)).replace("\\", "/"): sha(p) for p in paths}
for path in paths:
    text = path.read_text("utf-8")
    text = text.replace("# 纸上兵戈：十院留名 · rc34-preview", "# 纸上兵戈：十院留名 · rc35-preview")
    text = text.replace("最新下载与验收范围以143为准。以下保留历史阶段记录。", "最新下载与验收范围以145为准。以下保留历史阶段记录。")
    text = text.replace("最新下载与验收范围以143为准。以下保留各历史阶段记录。", "最新下载与验收范围以145为准。以下保留各历史阶段记录。")
    path.write_text(text, "utf-8")
after = {str(p.relative_to(ROOT)).replace("\\", "/"): sha(p) for p in paths}
publication = QA / "publication.json"
data = json.loads(publication.read_text("utf-8"))
for name, digest in after.items():
    data["files"][name] = digest
publication.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", "utf-8")
AMENDMENT.write_text(json.dumps({
    "passed": True,
    "base_revision": "assets/paper-warfront/system-revisions/rc35-atlas-cache.json",
    "publication": "output/qa/godot/render-runtime-rc35/publication.json",
    "changed_files": {name: {"before": before[name], "after": after[name]} for name in after},
    "reason": "The RC35 document was already published; this amendment makes the two navigation indexes point to the current 145 release entry and current rc35 header.",
    "scope": "Documentation index only. Game source, binaries, APK, ZIP, story data and runtime behavior unchanged.",
}, ensure_ascii=False, indent=2) + "\n", "utf-8")
print(json.dumps({"passed": True, "amendment": AMENDMENT.relative_to(ROOT).as_posix(), "publication_sha256": sha(publication)}))
