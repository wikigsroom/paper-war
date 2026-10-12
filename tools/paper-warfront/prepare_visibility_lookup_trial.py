"""Build an isolated RC31 visibility lookup candidate and independent observers."""
from pathlib import Path
import hashlib
import json
import shutil

ROOT = Path(__file__).resolve().parents[2]
QA = ROOT / "output/qa/godot/contact-runtime-rc32"
BASE = QA / "baseline-runtime"
TRIAL = QA / "lookup-r1-runtime"
assert not TRIAL.exists()
shutil.copytree(BASE, TRIAL)
p = TRIAL / "scripts/battle_visibility.gd"
s = p.read_text("utf-8")
original = s
s = s.replace("\tvar battle=sim\n\trevision+=1", '''\tvar battle=sim
\t# Ordered live references are local to this refresh, never retained across ticks.
\tvar actors: Array=battle.units+battle.buildings+battle.bases
\tvar actors_by_uid: Dictionary={}
\tvar indexed: bool=firing_reveals[0].size()+firing_reveals[1].size()+last_seen[0].size()+last_seen[1].size()>=4
\tif indexed:
\t\tfor a in actors:
\t\t\t# Preserve the original scalar comparison for non-integer public fixture IDs.
\t\t\tif typeof(a.uid)!=TYPE_INT:indexed=false;break
\t\t\tif a.hp>0 and not actors_by_uid.has(a.uid):actors_by_uid[a.uid]=a
\trevision+=1''')
s = s.replace("for a in battle.units+battle.buildings+battle.bases:", "for a in actors:")
s = s.replace("var source: Dictionary=battle.actor(int(uid))", "var source: Dictionary=actors_by_uid.get(int(uid),{}) if indexed else battle.actor(int(uid))")
s = s.replace("point_visible(side,remembered) and battle.actor(int(uid)).is_empty()", "point_visible(side,remembered) and (actors_by_uid.get(int(uid),{}) if indexed else battle.actor(int(uid))).is_empty()")
assert s != original and s.count("actors_by_uid.get") == 2 and s.count("for a in actors:") == 3
p.write_text(s, "utf-8")
old = ROOT / "output/qa/godot/dense-runtime-rc30"
for source, target in [("capacity-query-reuse-observer.gd", "lookup-capacity-observer.gd"), ("paid-phase-observer.gd", "lookup-paid-observer.gd")]:
    text = (old / source).read_text("utf-8").replace("frozen complete rc29", "frozen complete rc31")
    (QA / target).write_text(text, "utf-8")
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
(QA / "lookup-r1-manifest.json").write_text(json.dumps({"generator_sha256": sha(Path(__file__)),
    "input_visibility_sha256": sha(BASE / "scripts/battle_visibility.gd"), "candidate_visibility_sha256": sha(p),
    "candidate_inputs": {p.relative_to(TRIAL).as_posix(): sha(p) for p in TRIAL.rglob("*") if p.is_file()},
    "observer_provenance": {n: sha(old / n) for n in ["capacity-query-reuse-observer.gd", "paid-phase-observer.gd"]},
    "scope": "Refresh-scoped actor lookup only; no public source edits or exports. Exact scalar fallback for non-integer actor IDs; ordered first live duplicate preserved."
}, indent=2)+"\n", "utf-8")
print("Prepared isolated visibility lookup R1 and RC31 complete-state observers")
