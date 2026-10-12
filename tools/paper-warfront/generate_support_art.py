"""Ten faction utility sheets and seven region panoramas, selected gateway only."""
from pathlib import Path
import argparse,json,subprocess,sys,os,time
from generate_world_art import SKILL
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'output/imagegen/paper-warfront/world-support'

def plan():
    world=json.loads((ROOT/'game/data/factions.json').read_text(encoding='utf-8'))
    (OUT/'prompts').mkdir(parents=True,exist_ok=True)
    jobs=[]
    for f in world['factions']:
        ids=[f'portrait.{f["id"]}.commander',f'unit.{f["id"]}.worker']+[f'building.{f["id"]}.{tail}' for tail in ['base','tower','mana']]+[f'prop.{f["id"]}.{tail}' for tail in ['terrain','banner','cargo']]
        prompt=f'''TRANSPARENT BACKGROUND PNG. Eight isolated opaque cut-paper game assets in a clean FOUR COLUMNS TWO ROWS contact sheet. No canvas surface, no beige background, no gradients, no cast shadows. Transparent empty pixels everywhere except the isolated objects. Canvas 1536x1024. Each asset fully visible with generous 24px margins on all sides of its cell. Exactly eight different objects read left to right top to bottom. No lettering, labels, numbers, UI, borders, logos or real-world brands.
Original Paper Warfront faction: {f['name']}. Art motifs: {f['motif']}. Accent #{f['color']}, ivory rag paper, charcoal contour, muted tan, thick layered folded cardboard and tiny paper fibers. Expressive large-head stylized paper puppets, consistent friendly humorous martial character design. Same angle as side-view cut-paper strategy units: facing right, slight 3/4 angle, flat even light, broad clear silhouettes. The paper texture is ONLY inside the sprites, not a background.
Cell 1: full-body imposing commander {f['hero']}, {f['title']}, distinctive headwear and ceremonial weapon; upright still pose, clearly separated two feet. Cell 2: small humble cargo-carrying worker in faction costume, big gold-paper basket on back, two separated feet. Cell 3: wide layered-paper fortress, distinctive faction motifs, gate, roof and ramparts, no characters, ground-aligned. Cell 4: slim paper watchtower with a ranged paper-weapon perch, no characters, ground-aligned. Cell 5: distinctive standing mana-generating paper lamp shrine, faction motifs and visible colored center, no characters, ground-aligned. Cell 6: one folded tree or tall plant emblematic of {f['region']}, no ground surface. Cell 7: one narrow faction flag on a pole, emblem expressed as an abstract cut-paper shape, absolutely no letters. Cell 8: one compact cargo crate and folded evidence scroll bundle, no letters. All eight objects isolated and visibly separated. Do not copy existing game assets.''' 
        name=f['id']+'-utility';path=OUT/'prompts'/f'{name}.txt';path.write_text(prompt,encoding='utf-8')
        jobs.append(dict(id=name,faction=f['id'],kind='utility',assets=ids,prompt=str(path.relative_to(ROOT)).replace('\\','/'),source=str((OUT/f'{name}.png').relative_to(ROOT)).replace('\\','/'),background='transparent'))
        if f['id'] not in ['yin','mo','deng']:
            prompt=f'''Original 2D side-view strategy game background panorama, 1536x1024, cut-paper layered diorama and delicate ink wash on ivory rag paper. Region {f['region']} of the faction {f['name']}. Motifs: {f['motif']}. Distinct visual place, muted accent #{f['color']}, pale ivory and restrained charcoal. Distant architecture and folded landscapes occupy upper 55 percent. Bottom 45 percent is a quiet empty pale-paper stage with NO ground path, no platforms, no troops, no UI, no text or decorative clutter; the game will draw paths and actors there. Very low contrast behind gameplay, distant hazy layers, tactile paper fibers, flat soft lighting, broad silhouettes, horizontal camera-friendly composition. No real-world buildings, logos or existing game imitation. Opaque background.''' 
            name=f['id']+'-background';path=OUT/'prompts'/f'{name}.txt';path.write_text(prompt,encoding='utf-8')
            jobs.append(dict(id=name,faction=f['id'],kind='background',assets=['background.'+f['id']],prompt=str(path.relative_to(ROOT)).replace('\\','/'),source=str((OUT/f'{name}.png').relative_to(ROOT)).replace('\\','/'),background='opaque'))
    (OUT/'jobs.json').write_text(json.dumps(dict(model='gpt-image-2.5',jobs=jobs),ensure_ascii=False,indent=2),encoding='utf-8')
    return jobs

def main():
    sys.stdout.reconfigure(encoding='utf-8')
    parser=argparse.ArgumentParser();parser.add_argument('--plan-only',action='store_true');parser.add_argument('--job',action='append');args=parser.parse_args()
    jobs=plan()
    if args.plan_only:print('Planned 10 utility sheets and 7 original region panoramas.');return
    for job in jobs:
        if args.job and job['id'] not in args.job:continue
        if (ROOT/job['source']).exists():continue
        print('Generating '+job['id'],flush=True)
        command=[sys.executable,str(SKILL),'generate','--prompt-file',str(ROOT/job['prompt']),'--model','gpt-image-2.5','--quality','high','--size','1536x1024','--output-format','png','--background',job['background'],'--out',str(ROOT/job['source'])]
        for attempt in range(3):
            result=subprocess.run(command,capture_output=True,text=True,encoding='utf-8',errors='replace',env={**os.environ,'PYTHONIOENCODING':'utf-8'})
            if result.returncode==0:break
            if not any(code in result.stderr for code in ['429','502','503']) or attempt==2:break
            time.sleep(8*(attempt+1))
        if result.returncode:print('Selected gateway failed. No fallback used.');raise SystemExit(result.returncode)
        print(job['id']+' generated; review pending',flush=True)
if __name__=='__main__':main()
