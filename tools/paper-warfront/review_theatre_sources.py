"""Make labelled review boards from actual gateway source PNGs, without publishing."""
from pathlib import Path
import hashlib
import json
import sys
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'output/imagegen/paper-warfront/theatre-v3'

def main():
    sys.stdout.reconfigure(encoding='utf-8')
    jobs=json.loads((OUT/'jobs.json').read_text(encoding='utf-8'))['jobs']
    font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',20)
    records=[]
    for category in ['army','props','background']:
        items=[j for j in jobs if j['category']==category]
        for page in range((len(items)+3)//4):
            board=Image.new('RGB',(1200,860),'#FFF1D2')
            draw=ImageDraw.Draw(board)
            for i,job in enumerate(items[page*4:page*4+4]):
                source=OUT/(job['id']+'.png');x=i%2*600;y=i//2*430
                draw.text((x+14,y+8),job['id'],font=font,fill='#292536')
                if not source.exists():
                    draw.text((x+16,y+100),'Missing source',font=font,fill='#D85840')
                    records.append(dict(job=job['id'],status='missing'));continue
                im=Image.open(source).convert('RGBA')
                records.append(dict(job=job['id'],source=source.relative_to(ROOT).as_posix(),size=im.size,sha256=hashlib.sha256(source.read_bytes()).hexdigest(),status='source-review-pending'))
                im.thumbnail((575,370),Image.Resampling.LANCZOS)
                board.paste(im,(x+(600-im.width)//2,y+46+(370-im.height)//2),im)
            board.save(OUT/f'review-{category}-{page}.jpg',quality=94)
    (OUT/'source-review-inventory.json').write_text(json.dumps(dict(records=records),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(source_records=len(records),missing=[r['job'] for r in records if r['status']=='missing'])))

if __name__=='__main__':main()
