"""New observers; retain the completed RC33 tools and evidence unchanged."""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[2]
QA = ROOT / "output/qa/godot/render-runtime-rc34"
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
boundary = QA / "geometry-boundary-observer.gd"
pixel = QA / "geometry-render-observer.gd"
runner = ROOT / "tools/paper-warfront/check_rc34_geometry_render.py"
assert all(not p.exists() for p in [boundary, pixel, runner])
boundary.write_text('''extends SceneTree
const Data=preload("res://scripts/data_store.gd")
const View=preload("res://scripts/battle_view.gd")
const Frames=preload("res://scripts/unit_frame_player.gd")
var checks: int=0
var failures: Array=[]
func check(value: bool,label_value: String):
\tchecks+=1
\tif not value:failures.append(label_value)
func _initialize():call_deferred("run")
func run():
\tvar db=Data.new();var view=View.new();view.db=db
\tfor id in db.unit_frames:
\t\tvar profile: Dictionary=db.unit_frames[id].duplicate(true)
\t\tvar geometry=view.frame_geometry(id,profile)
\t\tcheck(geometry.destination==Rect2(-Vector2(profile.anchor[0],profile.anchor[1]),Vector2(profile.frame_size[0],profile.frame_size[1])),id+" destination")
\t\tfor frame in range(36):
\t\t\tcheck(geometry.region(frame)==Frames.region(profile,frame),id+" frame "+str(frame))
\t\t\tcheck(is_same(geometry,view.frame_geometry(id,profile)),id+" warm identity")
\t\tfor frame in [-17,-1,36,37,71,135,4097]:
\t\t\tcheck(geometry.region(frame)==Frames.region(profile,frame),id+" out of ordinary atlas range")
\t\tfor change in ["anchor","frame_size","columns"]:
\t\t\tvar previous=geometry
\t\t\tif change=="columns":profile.columns=7
\t\t\telse:profile[change][0]=float(profile[change][0])+.237;profile[change][1]=float(profile[change][1])+3.17
\t\t\tgeometry=view.frame_geometry(id,profile)
\t\t\tcheck(not is_same(previous,geometry),id+" edited "+change+" invalidates")
\t\t\tcheck(geometry.destination==Rect2(-Vector2(profile.anchor[0],profile.anchor[1]),Vector2(profile.frame_size[0],profile.frame_size[1])),id+" edited destination")
\t\t\tfor frame in range(36):check(geometry.region(frame)==Frames.region(profile,frame),id+" edited "+change+" frame")
\t\t# Equal replacement arrays can reuse exact geometry; field changes cannot.
\t\tprofile.anchor=profile.anchor.duplicate();profile.frame_size=profile.frame_size.duplicate()
\t\tcheck(is_same(geometry,view.frame_geometry(id,profile)),id+" equal replacement")
\t\tprofile.source_height=float(profile.source_height)+17;profile.atlas="different-live-texture"
\t\tcheck(is_same(geometry,view.frame_geometry(id,profile)),id+" live scale/atlas not retained")
\t\tfor frame in range(200):check(geometry.region(frame)==Frames.region(profile,frame),id+" bounded frame "+str(frame))
\t\tcheck(geometry.regions.size()<=64,id+" bounded regions")
\tfor i in range(300):
\t\tvar profile: Dictionary=db.unit_frames.values()[i%db.unit_frames.size()].duplicate(true)
\t\tvar value=view.frame_geometry("fixture."+str(i),profile)
\t\tcheck(value.region(33)==Frames.region(profile,33),"profile eviction keeps coordinates")
\t\tcheck(view.frame_geometry_cache.size()<=128,"bounded profiles")
\tvar inputs: Dictionary={}
\tfor n in ["scripts/battle_view","scripts/unit_frame_player","scripts/data_store"]:
\t\tvar p: String="res://"+n+(".gd" if FileAccess.file_exists("res://"+n+".gd") else ".gdc")
\t\tinputs[p]=FileAccess.get_sha256(p)
\tvar args=OS.get_cmdline_user_args();var out: String=args[args.find("--report")+1]
\tFileAccess.open(out,FileAccess.WRITE).store_string(JSON.stringify({"passed":failures.is_empty(),"checks":checks,"failures":failures,"units":db.unit_frames.size(),"inputs":inputs,"observer_sha256":FileAccess.get_sha256(get_script().resource_path),"scope":"72 actual profiles; exact original FramePlayer.region and destination formula, subpixel metadata changes, equal replacements, live atlas/height changes and bounded region/profile eviction. Shard rendering and natural FPS require separate native observations."},"  "))
\tview.free();print("GEOMETRY_BOUNDARY ",checks," failures ",failures.size());quit(0 if failures.is_empty() else 1)
''', "utf-8")
source = ROOT / "output/qa/godot/phase-runtime-rc33/ownership-render-observer.gd"
s = source.read_text("utf-8")
needle = '\tvar inputs: Dictionary={}\n'
assert s.count(needle) == 1
extra = '''
\t\t# Exercise warm shard meshes with all native sizes, alpha, rotation,
\t\t# subpixel locations and >32 deliberately varied fixture sizes.
\t\tapp.sim.config.fog=false;app.sim.visibility.refresh()
\t\tfor phase in range(3):
\t\t\tapp.view.particles.clear()
\t\t\tapp.view.camera_x=app.sim.map.length*.5+.237+float(phase)*.313
\t\t\tfor i in range(40):
\t\t\t\tvar x: float=app.view.camera_x-4.5+float(i%10)*.95
\t\t\t\tvar y: float=app.sim.map.ground_y_at(x)-float(i/10)*.8
\t\t\t\tapp.view.particles.append({"pos":Vector2(x*app.view.PX+.237,y*app.view.PY-95),"v":Vector2.ZERO,"life":.09+float(i%5)*.21,"total":1.0,"color":[Color("c65c42"),Color("4c8a91"),Color("fff8e9")][i%3],"angle":-.713+float(i)*.431,"spin":0.0,"size":3.0+float(i%4) if phase!=1 else 2.123+float(i)*.131})
\t\t\tapp.view.visual_time=3.271+float(phase)*.43
\t\t\tapp.view.shake=4.5 if phase!=2 else 0.0
\t\t\tawait render(map_id+"-shards-"+str(phase))
'''
s = s.replace(needle, extra + needle)
pixel.write_text(s, "utf-8")
original_runner = ROOT / "tools/paper-warfront/check_render_cache_equivalence.py"
s = original_runner.read_text("utf-8")
s = s.replace("shutil.copyfile(ROOT/'tools/paper-warfront/probe_render_cache_equivalence.gd',observer)", "shutil.copyfile(ROOT/'output/qa/godot/render-runtime-rc34/geometry-render-observer.gd',observer)")
s = s.replace("delta.getdata()", "delta.get_flattened_data()")
runner.write_text(s, "utf-8")
(QA / "observer-preparation.json").write_text(json.dumps({
    "passed": True, "generator_sha256": sha(Path(__file__)), "boundary_sha256": sha(boundary),
    "pixel_sha256": sha(pixel), "pixel_runner_sha256": sha(runner),
    "inherited_observer_sha256": sha(source), "inherited_runner_sha256": sha(original_runner),
    "scope": "New evidence only; inherited fixed native sprite/status/terrain/observer poses plus nine shard size/color/rotation/fade/eviction poses per display. Original RC33 tools and evidence unchanged."
}, indent=2) + "\n", "utf-8")
print("Prepared new geometry boundary and expanded pixel observers", flush=True)
