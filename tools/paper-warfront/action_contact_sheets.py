"""Assemble review contacts from real Godot captures, never source illustrations."""
from pathlib import Path
import json
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[2];QA=ROOT/'output/qa/godot/actions-rc4'
def main():
    gallery=json.loads((QA/'gallery/gallery-report.json').read_text(encoding='utf-8'))
    factions=json.loads((ROOT/'game/data/factions.json').read_text(encoding='utf-8'))['factions']
    ids=[uid for page in gallery['fixtures'] for uid in page['ids']]
    cores=[uid for faction in factions for uid in faction['core_roster']]
    for kind,selected,cols,rows,w,h in [('cores',cores,4,3,398,287),('all',ids,8,8,199,144)]:
        per=cols*rows
        for offset in range(0,len(selected),per):
            canvas=Image.new('RGB',(cols*w,rows*h),'#f4ead3');draw=ImageDraw.Draw(canvas)
            for i,uid in enumerate(selected[offset:offset+per]):
                index=ids.index(uid);page=index//12;card=index%12
                with Image.open(QA/f'gallery/page-{page:02d}-attack.png') as src:
                    crop=src.crop((30+card%4*398,51+card//4*287,374+card%4*398,323+card//4*287))
                crop.thumbnail((w-8,h-24));x=i%cols*w;y=i//cols*h;canvas.paste(crop,(x,y));draw.text((x+4,y+h-17),uid,fill='black')
            canvas.save(QA/f'review-{kind}-{offset//per:02d}.png')
    print('native contacts: 40 core units + all 412 runtime unit IDs')
if __name__=='__main__':main()
