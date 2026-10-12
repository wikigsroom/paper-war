"""Derive new delivery tools; completed RC33 tools remain byte-identical."""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "tools/paper-warfront"
QA = ROOT / "output/qa/godot/render-runtime-rc34"
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
records = {}
def write(name, source_name, transform):
    path = TOOLS / name
    assert not path.exists(), name
    original = TOOLS / source_name
    path.write_text(transform(original.read_text("utf-8")), "utf-8")
    records[name] = {"source": source_name, "source_sha256": sha(original), "derived_sha256": sha(path)}

def adopt(s):
    s = s.replace('assert not (QA / "geometry-r2-rejection.json").exists(), "Rejected R2 must not be adopted"', 'assert not (QA / "shards-r3-rejection.json").exists(), "Rejected trial must not be adopted"')
    s = s.replace("geometry-r2", "shards-r3")
    s = s.replace('assert read(QA / "shards-r3-boundary.json")["checks"] == 29184\n', '')
    s = s.replace('"new_geometry_checks": 29184, "source_total_assertions": 224619', '"new_geometry_checks": 0, "source_total_assertions": 195435')
    s = s.replace('"Bounded exact sprite rectangles and original-size shard meshes;', '"Original-size shard meshes and reuse of an already-computed unit height;')
    return s
write("adopt_rc34_shards.py", "adopt_rc34_geometry.py", adopt)
def validate(s):
    s = s.replace("phase-runtime-rc33", "render-runtime-rc34").replace("3.0.0-rc33-preview", "3.0.0-rc34-preview").replace("3.0.0-rc32-preview", "3.0.0-rc33-preview")
    s = s.replace("ownership-render", "shards-render").replace("check_rc33_ownership_render.py", "check_rc34_shards_render.py").replace("RC33", "RC34")
    return s
write("run_rc34_release_validation.py", "run_phase_release_validation.py", validate)
def audit(s):
    return s.replace("from verify_phase_release_evidence import verify", "from verify_shards_release_evidence import verify")
write("audit_rc34_preview.py", "audit_phase_preview.py", audit)
def package(s):
    needle = "shutil.copy2(RELEASE/'README.md',WIN/'README.md')"
    assert s.count(needle) == 1
    replacement = '''assert VERSION=='3.0.0-rc34-preview'
(WIN/'README.md').write_text('# 纸上兵戈：十院留名 · '+VERSION+'\\n\\n解压整个目录后运行 PaperWarfront.exe。若默认渲染无法启动，运行 Play-OpenGLCompatibility.cmd。\\n\\n单机十章200图带逐图剧情、并行任务和择一路线；可回访。战斗保持自动行军、金币/法力、科技和手动施法。\\n\\n本版复用纸屑网格，保持动作和粒子数量；本地实际检查范围见 [发布验证](preview-verification.json)。\\n\\n持续满员60FPS、全关平衡、真人剧情/联机与Android硬件仍待验证。Android安装包单独提供。\\n\\n许可证见 licenses/。\\n',encoding='utf-8')'''
    return s.replace(needle, replacement)
write("package_rc34_preview.py", "package_preview.py", package)
def register(s):
    s = s.replace("phase-runtime-rc33", "render-runtime-rc34").replace("3.0.0-rc33-preview", "3.0.0-rc34-preview").replace("rc33-marching-ownership-r1", "rc34-shards-r3").replace("RC33", "RC34")
    s = s.replace('["baseline-runtime", "oracle-runtime", "marching-r3-runtime", "native-ownership-r1-runtime"]', '["baseline-runtime", "geometry-r1-runtime", "geometry-r2-runtime", "shards-r3-runtime"]')
    s = s.replace('["phase", "marching", "ownership", "rc33"]', '["rc34", "shards"]')
    return s
write("register_rc34_release.py", "register_phase_release.py", register)
def finish(s):
    return s.replace("phase-runtime-rc33", "render-runtime-rc34").replace("3.0.0-rc33-preview", "3.0.0-rc34-preview").replace("publish_phase_release.py", "publish_rc34_release.py").replace("package_preview.py", "package_rc34_preview.py").replace("audit_phase_preview.py", "audit_rc34_preview.py").replace("register_phase_release.py", "register_rc34_release.py").replace("RC33", "RC34")
write("finish_rc34_release.py", "finish_phase_release.py", finish)
(QA / "delivery-tool-preparation.json").write_text(json.dumps({"passed": True, "generator_sha256": sha(Path(__file__)), "derivations": records,
    "scope": "New tools only. All inherited RC33 delivery code and completed releases unchanged. Unexecuted delivery tools do not establish adoption/export/QA. R3 must pass source/native/FPS gates before adoption. New ZIP has archive-local launch/readme links."
}, indent=2)+"\n", "utf-8")
print("Prepared independent RC34 delivery tools", flush=True)
