"""Bounded image repairs through the authorized skill CLI; no credentials copied."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import subprocess
import json
import sys
from generate_redesign_assets import STYLE

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'output/imagegen/paper-warfront/theatre-v3/repairs'
CLI=Path('C:/Users/carzy/.codex/skills/sub2-image-gen/scripts/sub2_image_gen.py')

def run(job):
    source=OUT/(job['id']+'.png');prompt=OUT/(job['id']+'.prompt.txt')
    prompt.write_text(job['prompt'],encoding='utf-8')
    if source.exists():return dict(id=job['id'],status='existing')
    result=subprocess.run([sys.executable,str(CLI),'generate','--model','gpt-image-2.5','--prompt-file',str(prompt),'--size','1024x1024','--quality','high','--background','transparent','--out',str(source)],cwd=ROOT,capture_output=True,text=True,encoding='utf-8',errors='replace')
    (OUT/(job['id']+'.log')).write_text(result.stdout+'\n'+result.stderr,encoding='utf-8')
    return dict(id=job['id'],status='generated' if result.returncode==0 and source.exists() else 'failed',exit_code=result.returncode)

def main():
    sys.stdout.reconfigure(encoding='utf-8');OUT.mkdir(parents=True,exist_ok=True)
    jobs=[dict(id='props-yin',prompt=STYLE+'''\nA transparent RGBA sprite sheet of EXACTLY FOUR original red-and-ivory paper props, each isolated inside its own cell of a strict 2 by 2 grid. Each object is small in its cell and occupies at most 65 percent of its cell width and height. At least 70 pixels clear transparent outer margin on every canvas edge, and broad transparent gutters. Top left: a squat red paper crossbow watchtower, entirely visible, including its small flag, arrow and foundations. Top right: a squat cinnabar lantern shrine with a large round golden paper light, entirely visible. Bottom left: a chunky simple red folded-paper pine, entirely visible. Bottom right: a small red paper gate with ivory pillars, entirely visible. Broad dark-plum outlines and 2-3 cartoon shadow tones, warm ivory highlights. All gold details are large readable shapes. No crops, text, scenery, ground line, paper sheet background or cut-off stones. Keep EVERY pixel of EVERY complete object comfortably away from the canvas boundary. No detached ornaments.'''),
          dict(id='common-mine',prompt=STYLE+'''\nOne isolated original gold-mine prop for a side-view 2D paper strategy game, transparent RGBA background. A friendly chunky cave entrance shaped from folded ivory and ochre paper rocks, a small wooden arch and three oversized bright golden paper ingots visible in the dark mouth. The mine is low and broad, visually readable at 100 pixels wide. Thick dark-plum cartoon outlines, only 2-3 flat shadow tones, a little visible cream paper thickness. Entire cave and ALL rocks visible, ample 15 percent empty margin on all canvas sides, no cropped parts, no people, no ground plane, no landscape, no labels, no letters, no numbers, no detached particles. Perfect orthographic side-view. A clear foot/base line for placing on a game ground surface.''')]
    (OUT/'jobs.json').write_text(json.dumps(dict(model='gpt-image-2.5',skill='sub2-image-gen',jobs=jobs),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    with ThreadPoolExecutor(max_workers=2) as pool:
        for future in as_completed([pool.submit(run,j) for j in jobs]):print(json.dumps(future.result()),flush=True)

if __name__=='__main__':main()
