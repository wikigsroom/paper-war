"""Prepare new cast seeds only AFTER the corresponding boards were inspected."""
from pathlib import Path
import argparse,json,hashlib
from PIL import Image
from prepare_frame_pilots import BASE
from paper_alpha import defringe
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'output/imagegen/paper-warfront/frame-rebuild/v2'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser();p.add_argument('--factions',nargs='+',required=True);args=p.parse_args()
    file=ROOT/'assets/paper-warfront/frame-rebuild/unit-briefs.json';doc=json.loads(file.read_text(encoding='utf-8'));records=[]
    for faction in args.factions:
        cast=OUT/(faction+'-cast.png');im=Image.open(cast).convert('RGBA');w,h=im.size
        rows=[row for row in doc['units'] if row['faction']==faction]
        for i,row in enumerate(rows):
            col=i%4;r=i//4;cell=im.crop((round(col*w/4),round(r*h/2),round((col+1)*w/4),round((r+1)*h/2)))
            # Generated boards occasionally draw 1-pixel cell guides. Crop guides
            # from the reference cells; they are never part of a runtime sprite.
            cell=cell.copy();alpha=cell.getchannel('A')
            from PIL import ImageDraw
            pen=ImageDraw.Draw(alpha);pen.rectangle((0,0,cell.width-1,2),fill=0);pen.rectangle((0,cell.height-3,cell.width-1,cell.height-1),fill=0);pen.rectangle((0,0,2,cell.height-1),fill=0);pen.rectangle((cell.width-3,0,cell.width-1,cell.height-1),fill=0)
            cell.putalpha(alpha);cell=defringe(cell)
            if cell.getbbox() is None:raise ValueError('Missing actual new seed '+row['id'])
            stem=row['id'].replace('.','-');seed=OUT/(stem+'-seed.png');cell.save(seed)
            row['legacy_source']=row.get('legacy_source',row['source']);row['source']=seed.relative_to(ROOT).as_posix();row['raw']=(OUT/(stem+'-raw.png')).relative_to(ROOT).as_posix();row['prompt']=(OUT/(stem+'.prompt.txt')).relative_to(ROOT).as_posix();row['identity_version']=2
            special='Perform the actual equipment action described by this kit: '+row['hint']+'. Clearly handle the new equipment, then recover. Do not change equipment or turn into another character.'
            if row['gesture'] in ['crossbow','ballista']:special='Open the empty bolt rail or spring magazine, insert new bolt(s), crank or tension the actual mechanism with BOTH hands or moving machine arms, shut it, re-aim and return to ready. This is the real reload clip.'
            if row['gesture']=='mine':special='Crouch and unload the gold/ore container: open it, pour out folded gold pieces, close it, lift it back and return to ready. Keep the worker distinct and correctly grip its own mining implement.'
            action=row['attack_description']
            if row['gesture']=='mine':action='MINING cycle: planted feet, raise the actual pick/shovel with both hands, lift fully in frame 3, strike into the ground to the right in frame 4, lift from ground and recover. No walking during mining.'
            body=BASE.replace('DESIGN_DESCRIPTION',row['design']).replace('ATTACK_DESCRIPTION',action).replace('SPECIAL_DESCRIPTION',special)
            body=body.replace('Image 1 is the character identity and paper illustration style reference.','Image 1 is the NEW approved character silhouette and paper illustration style. Preserve it exactly: same species/anatomy, face, equipment, costume and proportions in all frames. Do not revert to a generic human soldier, ordinary sword or cannon.')
            if row['gesture'] in ['ballista','ram','mortar','stamp_machine','kite_launcher','bomb']:
                body=body.replace('knees buckle, kneel, fall sideways','axles or mechanical supports buckle, chassis pitches down, equipment comes loose, fall sideways').replace('lie completely still with body horizontal and weapon fallen beside body','lie completely still as a collapsed wreck on the ground')
            (ROOT/row['prompt']).write_text(body,encoding='utf-8')
            records.append({'id':row['id'],'source':row['source'],'sha256':sha(seed),'cast':cast.relative_to(ROOT).as_posix(),'cast_sha256':sha(cast),'cell':i,'status':'cast-inspected-seed-ready'})
    file.write_text(json.dumps(doc,ensure_ascii=False,indent=2),encoding='utf-8')
    dest=OUT/'seed-provenance.json';old=json.loads(dest.read_text(encoding='utf-8')) if dest.exists() else []
    ids={r['id'] for r in records};old=[r for r in old if r['id'] not in ids]+records;dest.write_text(json.dumps(old,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Prepared inspected new seeds',len(records))
if __name__=='__main__':main()
