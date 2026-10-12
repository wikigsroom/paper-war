"""Complete the shared forty-role silhouette library through the authorized gateway."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import argparse
import json
import subprocess
import sys
from generate_redesign_assets import STYLE

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'output/imagegen/paper-warfront/theatre-v3/role-families'
CLI=Path('C:/Users/carzy/.codex/skills/sub2-image-gen/scripts/sub2_image_gen.py')
EQUIPMENT={
 'pike':'a long upright pike, small helmet, both feet visible',
 'cleaver':'a broad square cleaver sword, sturdy armored torso',
 'duelist':'a slender rapier, jaunty cap, confident fencing stance',
 'lancer':'a long tilted lance and a small round buckler, standing on foot',
 'banner':'a large attached rectangular battle banner, compact armored body',
 'drummer':'a large waist-mounted round drum and two visible drumsticks',
 'scribe':'a giant writing brush and a scroll strapped to the back, neat scholar hat',
 'burner':'a large attached flame-shaped paper torch and a small scroll pouch',
 'sniper':'a long simple scoped paper rifle, serious focused eyes',
 'chain':'a short chained flail with its spiked paper ball entirely visible',
 'demolisher':'a large round paper bomb carried in both hands, goggles, oversized eyebrows',
 'summoner':'a staff with an attached small paper-star charm, broad wizard hood',
 'illusionist':'a large fan of folded paper cards and a theatrical pointed cap',
 'saboteur':'a short dagger and a compact tool satchel, small hood, sneaky smile',
 'caravan':'a walking merchant carrying a large pack of scrolls, sturdy walking staff, two feet; no cart',
 'phoenix':'a friendly chunky folded-paper phoenix bird facing right, two ground-contact feet, large simple folded wings and a short curved beak',
}

def make_jobs():
    balance=json.loads((ROOT/'game/data/balance-prototype.json').read_text(encoding='utf-8'))
    factions=json.loads((ROOT/'game/data/factions.json').read_text(encoding='utf-8'))['factions']
    existing=json.loads((ROOT/'output/imagegen/paper-warfront/theatre-v3/jobs.json').read_text(encoding='utf-8'))['jobs']
    supplied={balance['units'][uid]['role'] for job in existing if job['category']=='army' for uid in job['assets'] if uid.startswith('unit.') and 'role' in balance['units'][uid]}
    wanted=sorted({balance['units'][uid]['role'] for f in factions for uid in f['combat_units']}-supplied)
    positions=['top left','top middle','top right','bottom left','bottom middle','bottom right']
    jobs=[]
    for page in range((len(wanted)+5)//6):
        roles=wanted[page*6:page*6+6]
        descriptions='\n'.join(f'{p}: one isolated {r}, {EQUIPMENT[r]}.' for p,r in zip(positions,roles))
        prompt=STYLE+f'''\nShared original troop silhouettes for the paper strategy game's army library. Neutral ivory clothing with clear rich indigo-blue uniform panels, dark-plum outlines and warm natural face color; the indigo panels will be recolored per faction. Exactly {len(roles)} independent subjects in a strict 3-column, 2-row transparent RGBA grid; unused cells are completely empty. Generous transparent gutters and at least 60 pixels transparent outer margin. Every entire weapon, hat, wing, staff, bag, foot and banner must remain inside its own cell. Side view facing RIGHT, expressive chibi faces, feet separated. Make each role immediately distinct by its large equipment silhouette. No background, text, scenery, shared floor, shadows outside the subject, checkerboard or panels. No detached objects or crop at any edge. Source cells:\n'''+descriptions
        jobs.append(dict(id=f'roles-{page:02d}',roles=roles,cols=3,rows=2,size='1536x1024',prompt=prompt))
    return jobs

def run(job):
    prompt=OUT/(job['id']+'.prompt.txt');destination=OUT/(job['id']+'.png');prompt.write_text(job['prompt'],encoding='utf-8')
    if destination.exists():return dict(id=job['id'],status='existing')
    result=subprocess.run([sys.executable,str(CLI),'generate','--model','gpt-image-2.5','--prompt-file',str(prompt),'--size',job['size'],'--quality','high','--background','transparent','--out',str(destination)],cwd=ROOT,capture_output=True,text=True,encoding='utf-8',errors='replace')
    (OUT/(job['id']+'.log')).write_text(result.stdout+'\n'+result.stderr,encoding='utf-8')
    return dict(id=job['id'],status='generated' if result.returncode==0 and destination.exists() else 'failed',exit_code=result.returncode)

def main():
    sys.stdout.reconfigure(encoding='utf-8');parser=argparse.ArgumentParser();parser.add_argument('--generate',action='store_true');args=parser.parse_args();OUT.mkdir(parents=True,exist_ok=True)
    batch=make_jobs();(OUT/'jobs.json').write_text(json.dumps(dict(model='gpt-image-2.5',skill='sub2-image-gen',jobs=batch),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(jobs=len(batch),roles=[r for j in batch for r in j['roles']])),flush=True)
    if args.generate:
        with ThreadPoolExecutor(max_workers=2) as pool:
            for future in as_completed([pool.submit(run,j) for j in batch]):print(json.dumps(future.result()),flush=True)

if __name__=='__main__':main()
