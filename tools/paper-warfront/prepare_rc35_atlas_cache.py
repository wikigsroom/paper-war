"""Prepare an isolated RC35 candidate that caches loaded unit atlas handles."""
from pathlib import Path
import hashlib
import json
import shutil

ROOT=Path(__file__).resolve().parents[2]
QA=ROOT/"output/qa/godot/render-runtime-rc35"
SOURCE=ROOT/"output/qa/godot/render-runtime-rc34/visibility-r4d-runtime"
TRIAL=QA/"atlas-cache-runtime"
assert not QA.exists() and SOURCE.exists()
QA.mkdir(parents=True)
shutil.copytree(SOURCE,TRIAL)
path=TRIAL/"scripts/battle_view.gd"
text=path.read_text("utf-8")
needle="var draw_visibility_cache: Dictionary={}\n"
assert text.count(needle)==1
text=text.replace(needle,needle+"var unit_atlas_cache: Dictionary={}\n")
needle="\tdraw_visibility_cache.clear();draw_visibility_revision=-1;draw_visibility_side=-1\n"
assert text.count(needle)==1
text=text.replace(needle,needle+"\tunit_atlas_cache.clear()\n")
needle="\tdraw_texture_rect_region(db.texture(profile.atlas),Rect2(-anchor,Vector2(profile.frame_size[0],profile.frame_size[1])),FramePlayer.region(profile,selected.frame),modulation)\n"
assert text.count(needle)==1
replacement="\tvar atlas_path: String=str(profile.atlas)\n\tvar atlas: Texture2D=unit_atlas_cache.get(atlas_path)\n\tif atlas==null:\n\t\tatlas=db.texture(atlas_path);unit_atlas_cache[atlas_path]=atlas\n\tdraw_texture_rect_region(atlas,Rect2(-anchor,Vector2(profile.frame_size[0],profile.frame_size[1])),FramePlayer.region(profile,selected.frame),modulation)\n"
text=text.replace(needle,replacement)
path.write_text(text,"utf-8")
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
(QA/"preparation.json").write_text(json.dumps({"passed":True,"source":"output/qa/godot/render-runtime-rc34/visibility-r4d-runtime","source_view_sha256":sha(SOURCE/"scripts/battle_view.gd"),"trial_view_sha256":sha(path),"scope":"View-only candidate caches Texture2D handles for already loaded unit atlas paths. It leaves frame selection, physical dimensions, ordering, visibility, effects, particles, fog, map/story and simulation unchanged; the cache is cleared on battle reset."},ensure_ascii=False,indent=2)+"\n","utf-8")
print("Prepared RC35 unit atlas handle cache candidate",flush=True)
