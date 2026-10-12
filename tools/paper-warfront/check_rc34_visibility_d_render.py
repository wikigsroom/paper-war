"""Freeze and compare actual native-render captures before/after cache changes."""
import argparse,hashlib,json,shutil,subprocess
from pathlib import Path
from PIL import Image,ImageChops,ImageStat
ROOT=Path(__file__).resolve().parents[2]
ap=argparse.ArgumentParser()
ap.add_argument('--before-pack',type=Path,required=True)
after=ap.add_mutually_exclusive_group(required=True)
after.add_argument('--after-pack',type=Path)
after.add_argument('--after-source',type=Path)
ap.add_argument('--output',type=Path,required=True)
args=ap.parse_args();folder=args.output.resolve()
assert not folder.exists(), 'Never overwrite render comparisons'
folder.mkdir(parents=True)
observer=folder/'observer.gd';shutil.copyfile(ROOT/'output/qa/godot/render-runtime-rc34/visibility-c-render-observer-b.gd',observer)
shutil.copyfile(Path(__file__),folder/'runner.py')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
startup=subprocess.STARTUPINFO();startup.dwFlags=1;startup.wShowWindow=0
outputs=[]
for name,resolution,flags,backend in [('desktop','1280x720',[],[]),('phone','1136x640',['--mobile-ui','--mobile-density','2'],['--rendering-method','gl_compatibility'])]:
 for phase in ['before','after']:
  dest=folder/f'{name}-{phase}';dest.mkdir()
  pack=args.before_pack if phase=='before' else args.after_pack
  runtime=['--main-pack',str(pack.resolve())] if pack else ['--path',str(args.after_source.resolve())]
  request={'phase':phase,'pack_sha256':sha(pack) if pack else None,'source_inputs':{p.relative_to(args.after_source).as_posix():sha(p) for p in (args.after_source/'scripts').glob('*.gd')} if not pack else None}
  (dest/'request.json').write_text(json.dumps(request,indent=2),'utf-8')
  cmd=[str(ROOT/'.tools/godot/Godot_v4.7.2-stable_win64_console.exe'),*runtime,*backend,'--resolution',resolution,'--script',str(observer),'--',*flags,'--output',str(dest),'--profile-path',str(dest/'profile.json')]
  run=subprocess.run(cmd,cwd=ROOT,capture_output=True,encoding='utf-8',errors='replace',timeout=90,startupinfo=startup)
  log=run.stdout+run.stderr;(dest/'runtime.log').write_text(log,'utf-8')
  assert run.returncode==0 and 'SCRIPT ERROR' not in log and 'ERROR:' not in log,log[-3500:]
  report=json.loads((dest/'report.json').read_text('utf-8'));assert report['observer_sha256']==sha(observer)
  for shot in report['captures']:assert sha(Path(shot['path']))==shot['sha256']
 for file in sorted((folder/f'{name}-before').glob('*.png')):
  other=folder/f'{name}-after'/file.name
  a=Image.open(file).convert('RGB');b=Image.open(other).convert('RGB');assert a.size==b.size
  delta=ImageChops.difference(a,b);stats=ImageStat.Stat(delta)
  changed=sum(any(ch>2 for ch in pixel) for pixel in delta.get_flattened_data())
  row={'display':name,'image':file.name,'before_sha256':sha(file),'after_sha256':sha(other),'mean_channel_delta':sum(stats.mean)/3,'max_channel_delta':max(x[1] for x in delta.getextrema()),'pixels_over_2':changed,'fraction_over_2':changed/(a.width*a.height)}
  row['passed']=row['mean_channel_delta']<.1 and row['fraction_over_2']<.005
  outputs.append(row);print(json.dumps(row),flush=True)
report={'passed':all(x['passed'] for x in outputs),'comparisons':outputs,'observer_sha256':sha(observer),'runner_sha256':sha(folder/'runner.py'),'scope':'Native fixed-pose comparison; tolerance covers subpixel float/edge rasterization: mean RGB channel error <0.1/255 and pixels differing >2/255 <0.5%. Does not establish real-time FPS or Android hardware.'}
(folder/'report.json').write_text(json.dumps(report,indent=2),'utf-8')
assert report['passed'], 'Cache rendering differs beyond the predeclared tolerance'
