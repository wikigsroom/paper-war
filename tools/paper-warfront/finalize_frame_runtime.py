"""Remove the legacy joint fallback only after complete current frame publication."""
from pathlib import Path
import json,re
ROOT=Path(__file__).resolve().parents[2]
def main():
 data=ROOT/'game/data';profiles=json.loads((data/'unit-frames.json').read_text(encoding='utf-8'))['profiles'];units=json.loads((data/'balance-prototype.json').read_text(encoding='utf-8'))['units']
 assert len(profiles)==len(units)==72 and all(p['source'].startswith('output/imagegen/paper-warfront/frame-rebuild/v2/') for p in profiles.values())
 path=ROOT/'game/scripts/battle_view.gd';text=path.read_text(encoding='utf-8')
 text=text.replace('const UnitMotion = preload("res://scripts/unit_motion.gd")\n','').replace('const WorkerMotion = preload("res://scripts/worker_motion.gd")\n','')
 text=re.sub(r'func draw_part\(.*?(?=func draw_unit\()', '',text,flags=re.S)
 text=text.replace('\tvar anim=meta.animation\n','')
 text=re.sub(r'\tif db.unit_frames.has\(u.id\):\n\t\tdraw_frame_unit\(u,pos,meta,modulation\)\n\telif .*?\n\t\tdraw_action_puppet\(u,pos,meta,modulation\)\n\telse:\n\t\tdraw_worker_puppet\(u,pos,meta,modulation\)', '\tdraw_frame_unit(u,pos,meta,modulation)',text,flags=re.S)
 text=re.sub(r'func draw_worker_puppet\(.*?(?=func draw_missile\()', '''func action_tip(u: Dictionary) -> Vector2:
\tvar meta: Dictionary=db.assets[u.id]
\tvar p: Dictionary=db.unit_frames[u.id]
\tvar sf: float=float(meta.world_height)*PX*PUPPET_SCALE/float(p.source_height)
\treturn unit_position(u)+Vector2((float(p.release_origin[0])-float(p.anchor[0]))*float(u.facing)*sf,(float(p.release_origin[1])-float(p.anchor[1]))*sf)

''',text,flags=re.S)
 text=re.sub(r'\t\t\telif data.has\("puppet"\) and db.balance.units\[data.id\].get\("economy",false\):.*?(?=\n\t\t"dash":)', '',text,flags=re.S)
 assert 'draw_action_puppet' not in text and 'draw_worker_puppet' not in text and 'UnitMotion.pose' not in text and 'func draw_unit' in text and 'func draw_effect' in text
 path.write_text(text,encoding='utf-8')
 old=ROOT/'game/scripts/unit_motion.gd';selector=old.read_text(encoding='utf-8').partition('static func projectile(')[2]
 target=ROOT/'game/scripts/unit_projectile.gd';target.write_text('extends RefCounted\n# Equipment only; character poses are complete drawn frames.\nstatic func projectile('+selector,encoding='utf-8')
 path=ROOT/'game/scripts/battle_sim.gd';text=path.read_text(encoding='utf-8').replace('const UnitMotion=preload("res://scripts/unit_motion.gd")','const UnitProjectile=preload("res://scripts/unit_projectile.gd")').replace('UnitMotion.projectile(','UnitProjectile.projectile(');path.write_text(text,encoding='utf-8')
 path=ROOT/'game/export_presets.cfg';text=path.read_text(encoding='utf-8');text=text.replace('data/library-definition.json"','data/library-definition.json,assets/characters/cutouts/*,assets/characters/portraits/unit-*.png,assets/animation/actions-rc4/*,assets/animation/rc2/*,assets/animation/unit-*.png,scripts/unit_motion.gd,scripts/worker_motion.gd"');path.write_text(text,encoding='utf-8')
 print('72 new identities bound; legacy joint renderer removed; old unit rasters excluded from export')
if __name__=='__main__':main()
