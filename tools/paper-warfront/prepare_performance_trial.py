"""Freeze invariant target-query reads and same-side movement scans."""
import difflib
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[2]
QA = ROOT / 'output/qa/godot/realtime-performance-rc26'
baseline = QA / 'baseline-runtime'
target = QA / 'combined-runtime'
assert not target.exists(), 'Never overwrite a started candidate'
shutil.copytree(baseline, target)
source = (baseline / 'scripts/battle_sim.gd').read_text('utf-8')

def replace(old, new):
    global source
    assert source.count(old) == 1, old
    source = source.replace(old, new)

replace('var formation_ranges: Dictionary={}',
        'var formation_ranges: Dictionary={}\nvar movement_side_units: Array=[[],[]]\nvar movement_sides_active: bool=false')
replace('\tformation_ranges.clear()\n\tcollecting_attacks=',
        '\tformation_ranges.clear();movement_side_units=[[],[]];movement_sides_active=false\n\tcollecting_attacks=')
replace('\tnext_uid+=1; units.append(u)',
        '\tnext_uid+=1; units.append(u)\n\tif movement_sides_active:movement_side_units[side].append(u)')
replace('\t\t\t\ttarget.side=side; target.facing=1 if side==0 else -1',
        '\t\t\t\ttarget.side=side; target.facing=1 if side==0 else -1\n\t\t\t\tif movement_sides_active:prepare_movement_sides()')
replace('\tvar movement_intents: Array=[]\n\tcollecting_attacks=true',
        '\tvar movement_intents: Array=[]\n\tprepare_movement_sides();movement_sides_active=true\n\tcollecting_attacks=true')
replace('\tcollecting_attacks=false\n\tcollecting_combat_hits=true',
        '\tcollecting_attacks=false;movement_sides_active=false\n\tcollecting_combat_hits=true')
replace('func movement_anchor(u: Dictionary) -> Dictionary:',
        '''# Used only during the simultaneous unit phase. Keep live actor references:
# movement, death and a just-born summon remain visible to later blockers.
func prepare_movement_sides():
\tmovement_side_units=[[],[]]
\tfor unit in units:movement_side_units[int(unit.side)].append(unit)

func movement_anchor(u: Dictionary) -> Dictionary:''')
replace('\t\tfor ally in units if step>0 else []:',
        '\t\tvar blockers: Array=movement_side_units[int(u.side)] if movement_sides_active else units\n\t\tfor ally in blockers if step>0 else []:')
replace('''\tvar origin: Vector2=Vector2(anchor.x,anchor.y)
\tvar melee: bool=str(def.get("attack","projectile")).begins_with("melee")
\tfor e in visibility.enemies[int(u.side)]:
\t\tif e.side==u.side or e.hp<=0:continue''',
        '''\tvar melee: bool=str(def.get("attack","projectile")).begins_with("melee")
\tvar origin: Vector2=Vector2.ZERO if melee else Vector2(anchor.x,anchor.y)
\tvar edge: String=anchor.edge if melee else ""
\tvar offset: float=float(anchor.s) if melee else 0.0
\tvar priority: bool=bool(def.get("support_priority",false)) and not u.get("building",false)
\tvar reach: float=float(def.range) if priority else 0.0
\tvar side: int=int(u.side)
\tfor e in visibility.enemies[side]:
\t\tif e.side==side or e.hp<=0:continue''')
replace('\t\tif melee and anchor.edge==destination.edge:d=absf(float(anchor.s)-float(destination.s))',
        '\t\tif melee and edge==destination.edge:d=absf(offset-float(destination.s))')
replace('\t\tif def.get("support_priority",false) and not u.get("building",false) and not e.get("building",false) and d<=float(def.range):',
        '\t\tif priority and not e.get("building",false) and d<=reach:')
path = target / 'scripts/battle_sim.gd'
path.write_text(source, 'utf-8')
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
diff = QA / 'combined.diff'
diff.write_text(''.join(difflib.unified_diff((baseline / 'scripts/battle_sim.gd').read_text('utf-8').splitlines(keepends=True),
                                          source.splitlines(keepends=True), fromfile='rc25/battle_sim.gd', tofile='combined/battle_sim.gd')), 'utf-8')
(target / 'candidate-inputs.json').write_text(json.dumps({
    'scope': 'Native headless CPU candidate, not shipping source or rendered FPS. Copied inputs.json is the baseline receipt.',
    'baseline_receipt_sha256': sha(baseline / 'inputs.json'), 'generator_sha256': sha(Path(__file__)),
    'diff_sha256': sha(diff), 'only_gameplay_file_changed': 'scripts/battle_sim.gd',
    'inputs': {p.relative_to(target).as_posix(): sha(p) for p in sorted(target.rglob('*'))
               if p.is_file() and (p.suffix in ['.gd', '.json'] or p.name == 'project.godot')}
}, indent=2), 'utf-8')
print('Frozen combined performance candidate; formal runtime unchanged')
