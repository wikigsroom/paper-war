"""Generate original 400-unit atlas sources using the user-selected local skill.

Only writes imagegen outputs. Runtime publication follows review and normalization.
The skill owns credentials; this process never reads or copies gateway secrets.
"""
from pathlib import Path
import argparse,json,os,subprocess,sys,time

ROOT=Path(__file__).resolve().parents[2]
SKILL=Path('C:/Users/carzy/.codex/skills/sub2-image-gen/scripts/sub2_image_gen.py')
OUT=ROOT/'output/imagegen/paper-warfront/world-v2'

WEAPONS={
 'vanguard':'broad short sword and square shoulder pads','pike':'long upright folded-paper pike',
 'guard':'large rectangular pack shield and cargo-protection apron','cleaver':'wide notched axe',
 'duelist':'two thin paper rapiers, nimble silhouette','lancer':'folded spear and spring-shaped boots',
 'assassin':'two small curved knives and short scarf','shield':'large layered shield, stout silhouette',
 'crusher':'large rectangular stamping hammer','harrier':'hooked pole and binding paper cord',
 'banner':'large faction banner on a pole','drummer':'small barrel drum and two sticks',
 'medic':'repair-patch satchel and a folded-paper healing fan','engineer':'tool belt, wrench and small blueprint',
 'mirror':'round mirror shield and straight sword','scribe':'long brush and sealed scroll',
 'poisoner':'dart tube, pointed paper darts and ink bottles','burner':'orange paper fire brands',
 'archer':'large folded-paper bow','javelin':'several paper javelins held behind the shoulder',
 'sniper':'long angular paper crossbow and sighting hood','repeater':'three folded rocket tubes',
 'artillery':'compact two-wheel scroll cannon cart, no human legs','siege':'compact armored two-wheel battering cart, no human legs',
 'mortar':'two-wheel paper mortar with an upward barrel, no human legs',
 'chain':'connected ink-orb paper charms and a forked staff','executioner':'oversized chopping blade and hood',
 'leech':'curved siphon blade and stitched cape','raider':'small axe and stolen-gold pouch',
 'demolisher':'demolition axe and rolled fuse','summoner':'paper guardian figurine and summoning fan',
 'necromancer':'paper-bone staff, old-page skull charm','illusionist':'two small overlapping mirror frames',
 'saboteur':'hooded sneaking figure with lamp-snuffing tool','warden':'large nail-shaped spear and bound scroll',
 'berserker':'torn shoulder armor and two heavy axes','colossus':'huge thick-paper armored humanoid, giant hammer, thick separated legs',
 'caravan':'cargo-protection flag and ledger bag','oracle':'folded mask and three small floating ink signs',
 'phoenix':'heavy armor with burnt-paper orange edges and a flame-shaped crest'}

def write_json(path,value):
    temporary=path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    temporary.replace(path)

def plan():
    world=json.loads((ROOT/'game/data/factions.json').read_text(encoding='utf-8'))
    balance=json.loads((ROOT/'game/data/balance-prototype.json').read_text(encoding='utf-8'))
    jobs=[]
    (OUT/'prompts').mkdir(parents=True,exist_ok=True)
    for faction in world['factions']:
        for page in range(5):
            units=faction['combat_units'][page*8:(page+1)*8]
            descriptions=[]
            for cell,uid in enumerate(units):
                role=balance['units'][uid]['role']
                descriptions.append(f'Cell {cell+1}, row {cell//4+1} column {cell%4+1}: {WEAPONS[role]}. Clearly distinct tactical silhouette.')
            prompt=f'''TRANSPARENT BACKGROUND PNG GAME ASSET. Eight isolated cutout sprites, absolutely no background surface, no beige paper canvas, no gradient, no scene, no vignette. The only opaque pixels are the eight soldiers or carts. Create a production-ready game sprite contact sheet for an ORIGINAL cut-paper side-view strategy game called Paper Warfront. Exactly eight separate full-body game sprites in a strictly aligned FOUR COLUMNS by TWO ROWS grid, read left to right then top to bottom. Canvas 1536 by 1024. Each cell 384 by 512, a single centered character, common feet baseline at 455 pixels within each cell, generous margins, nothing crosses cell boundaries. Each character faces RIGHT in a readable side/three-quarter profile, neutral ready pose. Human figures have TWO clearly separated visible legs and feet for later paper-puppet animation. Carts have exactly two visible wheels. No shadows outside the sprite silhouette.

Faction: {faction['name']}. Visual motifs: {faction['motif']}. Main faction accent #{faction['color']}, ivory rag paper, dark charcoal outlines, secondary muted tan paper. Original humorous stylized paper soldiers, big expressive head, bold readable weapons, layered cardstock edges, slight paper fibers, tiny cut-paper thickness, clean shapes, broad opaque silhouettes, flat even studio lighting. Alpha-transparent contact sheet with isolated opaque characters. No scenery, no UI, no labels, no lettering, no frame, no cell borders, no cast-shadow on the background. All eight sprites must be drawn completely, heads/weapons/feet/wheels inside their own cells. Keep faction identity consistent while making every role unmistakably different. Do not imitate or include any existing game characters. The paper texture belongs ONLY inside each sprite silhouette; nothing is painted outside the sprites.

{chr(10).join(descriptions)}'''
            name=f'{faction["id"]}-{page+1:02}'
            prompt_path=OUT/'prompts'/f'{name}.txt';prompt_path.write_text(prompt,encoding='utf-8')
            jobs.append(dict(id=name,faction=faction['id'],page=page,units=units,prompt=str(prompt_path.relative_to(ROOT)).replace('\\','/'),source=str((OUT/f'{name}.png').relative_to(ROOT)).replace('\\','/')))
    write_json(OUT/'jobs.json',dict(model='gpt-image-2.5',quality='high',size='1536x1024',jobs=jobs,status='planned; source generation is not art acceptance'))
    return jobs

def main():
    sys.stdout.reconfigure(encoding='utf-8');sys.stderr.reconfigure(encoding='utf-8')
    parser=argparse.ArgumentParser();parser.add_argument('--job',action='append');parser.add_argument('--plan-only',action='store_true')
    args=parser.parse_args();jobs=plan()
    if args.plan_only:print('Planned 50 sheets / 400 original combat sprites.');return
    progress=dict(model='gpt-image-2.5',jobs=[])
    for job in jobs:
        if args.job and job['id'] not in args.job:continue
        source=ROOT/job['source']
        if source.exists():
            progress['jobs'].append(dict(id=job['id'],status='source-exists-needs-review'));continue
        command=[sys.executable,str(SKILL),'generate','--prompt-file',str(ROOT/job['prompt']),'--model','gpt-image-2.5','--quality','high','--size','1536x1024','--output-format','png','--background','transparent','--out',str(source)]
        print(f'Generating {job["id"]}: {len(job["units"])} units',flush=True)
        for attempt in range(3):
            result=subprocess.run(command,capture_output=True,text=True,encoding='utf-8',errors='replace',env={**os.environ,'PYTHONIOENCODING':'utf-8'})
            message=result.stdout+result.stderr
            if result.returncode==0:break
            transient=any(code in message for code in ['429','502','503'])
            if not transient or attempt==2:break
            time.sleep(8*(attempt+1))
        status='source-generated-needs-review' if result.returncode==0 and source.exists() else 'gateway-failed'
        progress['jobs'].append(dict(id=job['id'],status=status,returncode=result.returncode))
        write_json(OUT/'generation-progress.json',progress)
        print(f'{job["id"]}: {status}',flush=True)
        if result.returncode:
            # Do not emit unfiltered gateway output or risk revealing credentials.
            codes=[code for code in ['400','401','403','429','500','502','503'] if code in message]
            print('Gateway request failed; observed status codes: '+','.join(codes),flush=True)
            raise SystemExit(result.returncode)
    write_json(OUT/'generation-progress.json',progress)

if __name__=='__main__':main()
