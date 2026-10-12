"""Check captured, stationary terrain after exact one-pixel camera translation."""
from pathlib import Path
import hashlib,json,subprocess,shutil
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[2]
QA=ROOT/'output/qa/godot/frame-rebuild/pan'
def main():
    paths=sorted((QA/'frames').glob('frame-*.png'));assert len(paths)==48
    # Ground-only ROI, below the authored road and above the fixed HUD. This
    # excludes moving/parallax actors, trees, sky and stationary controls.
    arrays=[np.array(Image.open(p).convert('RGB'),dtype=np.int16)[650:710,100:1500] for p in paths]
    rows=[]
    for a,b in zip(arrays,arrays[1:]):
        delta=np.abs(a[:,1:]-b[:,:-1])
        rows.append({'mean_rgb_error':float(delta.mean()),'p99_rgb_error':float(np.percentile(delta,99)),
                     'fraction_rgb_over_8':float((delta>8).mean())})
    report={'passed':all(r['mean_rgb_error']<.1 and r['fraction_rgb_over_8']<.001 for r in rows),
       'pairs':len(rows),'roi':[100,650,1400,60],'alignment':'Next frame shifted exactly one pixel right to undo measured left pan.',
       'worst_mean_rgb_error':max(r['mean_rgb_error'] for r in rows),'rows':rows,
       'frame_sha256':[hashlib.sha256(p.read_bytes()).hexdigest() for p in paths],
       'scope':'Stationary terrain raster consistency in native Windows GPU capture; not Android FPS or moving scenery.'}
    (QA/'pixel-report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    assert report['passed'],report
    subprocess.run([shutil.which('ffmpeg'),'-y','-loglevel','error','-framerate','30','-i',str(QA/'frames/frame-%04d.png'),'-frames:v','48','-c:v','libx264','-crf','18','-pix_fmt','yuv420p',str(QA/'camera-pan.mp4')],check=True)
    print(json.dumps({k:v for k,v in report.items() if k not in ['rows','frame_sha256']}))
if __name__=='__main__':main()
