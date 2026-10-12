"""Prepare actual whole-sheet edits via the user-selected Sub2 gateway CLI."""
from pathlib import Path
import shutil,json

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'output/imagegen/paper-warfront/frame-rebuild'
REFERENCE=Path('C:/Users/carzy/AppData/Local/Temp/codex-clipboard-4c834b2e-2c68-4ccd-bd1b-2c264ed0cb16.png')
BASE='''Create a production 2D game animation spritesheet, not concept art. Image 1 is the character identity and paper illustration style reference. Image 2 is ONLY an example of animation sheet organization and pose progression; DO NOT copy its armored knight or pixel rendering. Use the original game's warm layered cut paper, confident dark ink outlines, thick folded paper edges, readable face and flat restrained color areas. Re-draw the full character for every frame: torso twist, knees bend, hands grasp correctly, cloth and attachments deform with each action. Never turn one rigid cutout around a pivot to simulate an action.

OUTPUT: exactly 6 columns by 6 rows, 36 equal square cells, on a 1536x1536 transparent canvas. Each cell is 256x256. No labels, words, grid lines, scenery, borders, shadows on the ground, additional people or particles. Exactly one instance of the SAME character in every cell. Facing right consistently. Same costume details, same head size, same weapon length and same body scale in all 36 cells. Main standing character height about 160 pixels, grounded soles at cell y=230 and body center x=128. Leave generous whitespace so all weapons stay inside each cell. Do not individually resize the poses. Death poses keep the SAME ground line and body scale, becoming naturally lower as they collapse. Maintain exact identity and anatomy across the sheet.

ROW 1, six frames: idle, subtle breathing and cloth settling, standing weight shift, hands correctly holding the weapon. Frame 1 is the reference ready stance; frame 6 returns to it.
ROW 2, six frames: full walking cycle, left contact, lowering, passing, right contact, lowering, passing; real knees/hips and alternating feet, cloth and equipment trail behind. Keep soles on the same ground line.
ROW 3, six frames: a complete attack. Frame 1 prepare; frame 2 visibly tense and raise/aim; frame 3 maximal anticipation; frame 4 EXACT release/impact silhouette; frame 5 strong follow-through and recoil; frame 6 recovering towards ready. Detailed action: ATTACK_DESCRIPTION
ROW 4, six frames: receive a hit, recoil in the torso and head, stagger with bent knees, retain control of equipment, brace, recover, return to ready. Do not rotate the whole sprite as one object.
ROW 5, six frames: actual death sequence, struck/lose balance, knees buckle, kneel, fall sideways, hit ground, lie completely still with body horizontal and weapon fallen beside body. Every frame is new drawing; last pose stays on the ground. Not just leaning while standing.
ROW 6, six frames: character's faction-specific secondary action, prepared, engaged, strongest action, completion, settle, ready. Detailed secondary action: SPECIAL_DESCRIPTION

CHARACTER DESIGN: DESIGN_DESCRIPTION
'''

PILOTS=[
 ('unit.yin.axe','A stocky imperial seal-guard with RED square lacquer paper lamellar, a rectangular folded seal shield on left arm, thick wooden-cut guillotine axe in right hand, a short folded red pennant. Disciplined heavy soldier, broad square silhouette; NOT a thin generic swordsman. Preserve the reference face and hand-made paper appearance.',
  'Plant left foot and shield, pull the heavy axe up and back with BOTH torso and bent right elbow, chop decisively forward and down in frame 4, shield remains in front. Axe is visible and changes its orientation and position. Frame 5 leans through the stroke, frame 6 recovers. No flying axe.',
  'Defensive seal brace: lower stance, lift rectangular shield to cover head and torso, brace at full height, counterstep and reset. The heavy square shield and grounded stance define this faction.'),
 ('unit.mo.priest','A hunched old-paper necromancer with an oversized skull-like folded paper hood, worn violet ink-stained ragged robe, a crooked bone-paper staff and bundle of torn scrolls. Skeletal hand shapes, asymmetrical triangular silhouette. NOT the red soldier recolored violet. Preserve the distinctive reference character identity.',
  'Open ragged robe and extend staff with a curled skeletal hand; bend spine and lower knees; frame 4 sweeps the crooked staff forward to release a soul spell, then recoils and folds back. There is no sword, bow or cannon.',
  'Collect a torn paper remnant, kneel and unfold it between both hands into a small paper skeleton shape held at the feet, raise staff then return to standing. A ritual resurrection pose, clearly different from attacking.')
]

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    if not (OUT/'animation-layout-reference.png').exists():shutil.copy2(REFERENCE,OUT/'animation-layout-reference.png')
    records=[]
    for uid,design,attack,special in PILOTS:
        name=uid.replace('.','-')
        prompt=BASE.replace('ATTACK_DESCRIPTION',attack).replace('SPECIAL_DESCRIPTION',special).replace('DESIGN_DESCRIPTION',design)
        (OUT/(name+'.prompt.txt')).write_text(prompt,encoding='utf-8')
        records.append({'id':uid,'model':'gpt-image-2.5','source':f'game/assets/characters/cutouts/{name}.png','prompt':str((OUT/(name+'.prompt.txt')).relative_to(ROOT)).replace('\\','/'),'out':str((OUT/(name+'-raw.png')).relative_to(ROOT)).replace('\\','/'),'status':'candidate-unreviewed','layout':[6,6]})
    (OUT/'pilot-manifest.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Two whole-sheet pilot prompts ready; not approved assets.')

if __name__=='__main__':main()
