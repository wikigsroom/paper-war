"""Generate genuinely new faction silhouettes before animating any of them."""
from pathlib import Path
import argparse,concurrent.futures,json,subprocess,sys,time
from PIL import Image
ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'output/imagegen/paper-warfront/frame-rebuild/v2'
SKILL=Path('C:/Users/carzy/.codex/skills/sub2-image-gen/scripts/sub2_image_gen.py')

def prompt(faction,rows):
    items='\n'.join(f'Cell {i+1} ({"top" if i<4 else "bottom"} row, column {i%4+1}): '+row['design'] for i,row in enumerate(rows))
    if len(rows)==7:items+='\nCell 8: completely empty transparent cell.'
    return f'''New original production game character cast for the {faction} faction of Paper Warfront. Create the actual redesigned character silhouettes described below. Do NOT use a standard swordsman or a common base body recolored. Humanoid, mechanical, insect, tree and beast anatomy must follow EACH requested design exactly. Seven or eight individual full-body characters, NOT seven costume variants of one person.

Art direction: 2D layered cut-paper illustration, confident dark ink outlines, thick folded paper edges, matte paper, warm cream highlights, restrained local colors, broad readable shapes, small details only on equipment. Distinct face ages and body proportions according to each role. Humanoids about three-heads tall; machines and nonhuman creatures have their own anatomy. NOT pixel art, NOT photorealism, NOT glossy 3D plastic. Coherent illustration style with readable individual silhouettes.

Transparent 1536x768 canvas. Exactly FOUR equal columns and TWO rows, eight 384x384 cells. No labels, text, cell borders, scenery or ground shadows. One full character in every occupied cell, centered x=192 in its cell, ground y=350, main height about 255 pixels. All face RIGHT in a side-three-quarter game view. Show ALL feet, held equipment, wheels, appendages and horns inside the cell with generous transparent margins. Vehicle barrels, shields and tails must not cross cells. Actors are ready to walk/fight with correctly grasped equipment. No flying projectiles.

{items}

Critical: silhouette variety is mandatory. Every specified automaton must look like an actual spring/gear machine rather than a human with gears painted on armor. A specified tree/stump or moth must be visibly nonhuman. Faceless white-paper creatures must not have the same friendly human soldier face as other factions. Equipment must match the exact character description, not a substitute generic sword or cannon.
'''

def generate(item):
    faction,rows=item;raw=BASE/(faction+'-cast.png');pf=BASE/(faction+'-cast.prompt.txt')
    pf.write_text(prompt(faction,rows),encoding='utf-8')
    if raw.exists():return {'faction':faction,'status':'existing-candidate'}
    for attempt in range(1,5):
        log=BASE/(faction+f'-cast-attempt-{attempt}.log')
        with log.open('w',encoding='utf-8') as out:
            result=subprocess.run([sys.executable,str(SKILL),'generate','--prompt-file',str(pf),'--model','gpt-image-2.5','--size','1536x768','--quality','high','--background','transparent','--out',str(raw)],cwd=ROOT,stdout=out,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
        if result.returncode==0 and raw.exists():return {'faction':faction,'status':'new-cast-candidate','bytes':raw.stat().st_size}
        text=log.read_text(encoding='utf-8',errors='replace')
        if 'gateway_concurrency_limit' not in text:return {'faction':faction,'status':'failed','attempt':attempt}
        time.sleep(20)
    return {'faction':faction,'status':'limited','attempt':4}

def main():
    sys.stdout.reconfigure(encoding='utf-8');p=argparse.ArgumentParser();p.add_argument('--factions',nargs='*');p.add_argument('--workers',type=int,default=2);args=p.parse_args();BASE.mkdir(parents=True,exist_ok=True)
    rows=json.loads((ROOT/'assets/paper-warfront/frame-rebuild/unit-briefs.json').read_text(encoding='utf-8'))['units'];groups={}
    for row in rows:groups.setdefault(row['faction'],[]).append(row)
    if args.factions:groups={f:r for f,r in groups.items() if f in args.factions}
    results=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(2,max(1,args.workers))) as pool:
        for result in pool.map(generate,groups.items()):
            results.append(result);print(json.dumps(result,ensure_ascii=False),flush=True)
            (BASE/'cast-generation-progress.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
    if any(r['status'] in ['failed','limited'] for r in results):raise SystemExit(1)
if __name__=='__main__':main()
