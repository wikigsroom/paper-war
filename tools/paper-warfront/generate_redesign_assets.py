"""Produce consistent, readable theatre art using the user's specified gateway CLI."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import argparse, json, subprocess, sys

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'output/imagegen/paper-warfront/theatre-v3'
CLI=Path('C:/Users/carzy/.codex/skills/sub2-image-gen/scripts/sub2_image_gen.py')
ROLES={
 'yin':['vanguard','javelin','crusher','artillery'],
 'mo':['raider','poisoner','necromancer','colossus'],
 'deng':['mirror','repeater','assassin','guard'],
 'ji':['vanguard','javelin','engineer','artillery'],
 'yuan':['vanguard','archer','harrier','artillery'],
 'qi':['vanguard','javelin','executioner','siege'],
 'mu':['guard','poisoner','medic','colossus'],
 'shuang':['shield','javelin','warden','mortar'],
 'jin':['berserker','archer','leech','artillery'],
 'bai':['mirror','repeater','oracle','colossus'],
}
IDENTITY={
 'yin':('cinnabar red, warm ivory and brass','stamp-seal helmets, broad square shields, red paper tassels','sunlit terracotta cliffs, red paper pines and ancient stamp gates'),
 'mo':('plum purple, bone cream and moss green','round skull-paper masks, ragged violet cloaks, comically sinister grins','purple reed marsh, crooked paper willows, soft green mist'),
 'deng':('jade turquoise, golden yellow and coral','lantern hats, round mirror shields, luminous paper charms','jade pagoda hills, oversized lanterns and peach clouds'),
 'ji':('copper orange, denim blue and cream','folded brass gears, rivets, engineer goggles and winding cranks','copper paper workshop towers, folded gear wheels and blue mountains'),
 'yuan':('sky blue, navy and ivory','kite wings, feather-shaped helmets and wind ribbons','blue canyon spires, paper kites, distant hanging bridges and fluffy ivory clouds'),
 'qi':('golden yellow, royal blue and ivory','coin-shaped shields, merchant hats and gold tassels','golden paper port, blue sail silhouettes and stepped market roofs'),
 'mu':('leaf green, berry red and warm cream','sprout helmets, folded leaf capes and seed-shaped shields','lush folded-paper grove, broad round leaves and soft sun rays'),
 'shuang':('icy cyan, navy and pale violet','snowflake crests, crystal-paper shields and compact fur collars','pastel ice cliffs, cut-paper firs and pale lavender mountains'),
 'jin':('ember orange, charcoal blue and warm cream','flame-shaped hair, bandaged paper armor and fiery ribbons','amber sunset, charcoal paper ruins and glowing orange hills'),
 'bai':('ivory white, indigo and dusty gold','blank-page masks, neat rectangular hats and gold paper edges','quiet ivory terraces, indigo mountains and pale gold archive towers'),
}
WEAPON={
 'vanguard':'a broad axe or stout short sword and a clear small shield',
 'javelin':'a long throwing spear held horizontally, alert slim stance',
 'crusher':'a chunky mallet raised behind the shoulder, broad sturdy body',
 'artillery':'a cheerful compact paper cannon on two clearly visible round wheels',
 'raider':'two hooked short blades, springy crouched stance',
 'poisoner':'a green-tipped blowpipe, sly eyes and a tiny toxin pouch',
 'necromancer':'a skull-shaped staff with an attached skull, crooked wizard hat',
 'colossus':'a large but friendly square paper golem, huge readable fists and two thick separated feet',
 'mirror':'a round shiny mirror shield and a short saber',
 'repeater':'a compact repeating crossbow with two clear bolts',
 'assassin':'a long folded cloak and two short knives, compact nimble silhouette',
 'guard':'a very broad shield and a heavy blunt sword',
 'engineer':'a chunky wrench, oversized goggles and a paper tool pouch',
 'archer':'a tall simple bow, visible arrow and confident focused eyes',
 'harrier':'a small kite-shaped shield and a light curved blade, wing-like scarf',
 'executioner':'an oversized crescent blade, stocky stern silhouette',
 'siege':'a compact paper bolt launcher on two visible wheels',
 'medic':'a sprout or paper-healing staff, a satchel and gentle determined face',
 'shield':'an oversized snowflake-shaped shield and a short spear',
 'warden':'an ice-paper staff and a bell charm, upright imposing stance',
 'mortar':'a squat upward-pointing paper mortar on two clear wheels',
 'berserker':'two chunky axes, flame-like hair and exaggerated brave eyebrows',
 'leech':'a curved red blade and a dramatic folded vampire-paper collar',
 'oracle':'a round paper divination fan and blank mask with expressive large eyes',
}
STYLE='''Original colorful 2D side-view strategy game, whimsical folded-paper theatre. Clean cartoon illustration with thick dark plum outlines, large simple shapes, expressive faces, broad painted color blocks and only 2-3 shadow tones. Chibi heads approximately one-third of character height. Very light paper grain, a small visible paper edge and a few purposeful fold marks. Crisp readable silhouettes at 100 pixels tall. Charming and humorous, emphatic gestures. NOT realistic, not photoreal, not 3D rendering, not low-contrast watercolor, not intricate origami sculpture, not tiny armor tiles, not grunge. Cohesive warm ivory paper highlights. No text, labels, typography, numbers, logos or interface screenshots.'''

def jobs():
 balance=json.loads((ROOT/'game/data/balance-prototype.json').read_text(encoding='utf-8'))
 factions=json.loads((ROOT/'game/data/factions.json').read_text(encoding='utf-8'))['factions']
 result=[]
 for f in factions:
  key=f['id'];palette,motifs,scene=IDENTITY[key]
  ids=[next(uid for uid in f['combat_units'] if balance['units'][uid]['role']==role) for role in ROLES[key]]
  ids+=['unit.'+key+'.worker','building.'+key+'.base']
  subjects=[WEAPON[r] for r in ROLES[key]]+['a cheerful worker carrying a clearly attached backpack full of gold, short legs and a tiny pickaxe','a squat welcoming fortified paper castle matching this faction, bold roof and a large visible entrance, no characters around it']
  positions=['top left','top middle','top right','bottom left','bottom middle','bottom right']
  sheet='\n'.join(f'{p}: one independent isolated sprite, {s}.' for p,s in zip(positions,subjects))
  prompt=STYLE+f'\nFaction color palette: {palette}. Costume motifs: {motifs}.\nA transparent RGBA sprite sheet, exactly SIX subjects arranged in a strict 3-column 2-row layout. Subjects are fully separated by generous transparent gutters. Every humanoid faces RIGHT in a perfect side-view, two visible separated feet, readable face. All entire weapons, wheels, hats and capes fit inside their own region with generous margins. No shared ground, shadow blobs, backdrops, scenery, checkered background or enclosing panels. No cut-off pieces at any canvas edge. Source layout:\n'+sheet
  result.append(dict(id='army-'+key,category='army',faction=key,assets=ids,cols=3,rows=2,size='1536x1024',prompt=prompt))
  prompt=STYLE+f'\nFaction palette: {palette}; motifs: {motifs}. A transparent RGBA sheet containing exactly FOUR isolated props in a 2-column 2-row layout with generous transparent gutters. Top left: one charming watchtower with a visible big crossbow, chunky side-view construction. Top right: one squat glowing paper lantern shrine that clearly produces magical energy. Bottom left: one characteristic stylized tree or plant from this region. Bottom right: one distinctive ruined paper gate or folded rock formation from this region. No characters, shared ground or backdrop; entire silhouettes fit inside their cells; no cut-off edges. All four objects use clean broad shapes and the same black-plum outline weight.'
  result.append(dict(id='props-'+key,category='props',faction=key,assets=['building.'+key+'.tower','building.'+key+'.mana','prop.'+key+'.terrain','prop.'+key+'.landmark'],cols=2,rows=2,size='1024x1024',prompt=prompt))
  prompt=STYLE+f'\nA wide 2D videogame background panorama for {scene}. Palette built around {palette}, with pale cream and soft complementary sky. Layered cut-paper landscape: calm spacious sky in upper half, distant softened mountain silhouettes, characteristic regional scenery in middle ground. Lower one-third is a quiet pale atmosphere, free of large foreground objects; playable ground will be drawn separately by the engine. Interesting asymmetrical silhouettes near side edges, clear empty middle for readable combat. Background contrast and saturation remain softer than vivid characters. NO ground cross-section, roads, UI, units, buildings to interact with, foreground trees, text or borders. Flat orthographic side view, no isometric viewpoint.'
  result.append(dict(id='background-'+key,category='background',faction=key,assets=['background.'+({'yin':'stamp-plain','mo':'ink-marsh','deng':'lantern-ridge'}.get(key,key))],size='1536x1024',prompt=prompt))
 return result

def run(job):
 dest=OUT/(job['id']+'.png');prompt=OUT/(job['id']+'.prompt.txt');log=OUT/(job['id']+'.log')
 prompt.write_text(job['prompt'],encoding='utf-8')
 if dest.exists():return dict(id=job['id'],status='existing')
 result=subprocess.run([sys.executable,str(CLI),'generate','--model','gpt-image-2.5','--prompt-file',str(prompt),'--size',job['size'],'--quality','high','--background','transparent' if job['category']!='background' else 'opaque','--out',str(dest)],capture_output=True,text=True,encoding='utf-8',errors='replace',cwd=ROOT)
 log.write_text(result.stdout+'\n'+result.stderr,encoding='utf-8')
 return dict(id=job['id'],status='generated' if result.returncode==0 and dest.exists() else 'failed',exit_code=result.returncode)

def main():
 sys.stdout.reconfigure(encoding='utf-8');p=argparse.ArgumentParser();p.add_argument('--first',action='store_true');p.add_argument('--faction');p.add_argument('--all',action='store_true');p.add_argument('--workers',type=int,default=2);a=p.parse_args()
 OUT.mkdir(parents=True,exist_ok=True);batch=jobs();(OUT/'jobs.json').write_text(json.dumps(dict(model='gpt-image-2.5',skill='sub2-image-gen',jobs=batch),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 if a.first:batch=[j for j in batch if j['id'] in ['army-yin','background-yin']]
 elif a.faction:batch=[j for j in batch if j['faction']==a.faction]
 elif not a.all:print('Choose --first, --faction or --all; prompts and jobs prepared.');return
 with ThreadPoolExecutor(max_workers=max(1,min(2,a.workers))) as pool:
  futures=[pool.submit(run,j) for j in batch]
  for future in as_completed(futures):print(json.dumps(future.result(),ensure_ascii=False),flush=True)

if __name__=='__main__':main()
