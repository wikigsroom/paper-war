"""Contact sheets from native draw-frame captures for visual review."""
from pathlib import Path
import json
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[2];QA=ROOT/'output/qa/godot/frame-rebuild'
def main():
    units=json.loads((ROOT/'assets/paper-warfront/frame-rebuild/unit-briefs.json').read_text(encoding='utf-8'))['units']
    for phase,(col,row) in {'idle':(0,0),'prepare':(2,2),'release':(3,2),'death':(5,4),'special':(3,5)}.items():
        for offset in range(0,len(units),24):
            image=Image.new('RGB',(1320,4*204),'#f4ead3');draw=ImageDraw.Draw(image)
            for i,unit in enumerate(units[offset:offset+24]):
                path=QA/'native-frames'/(unit['id'].replace('.','-')+'.png');x=i%6*220;y=i//6*204
                if path.exists():
                    with Image.open(path) as source:image.paste(source.crop((col*220,row*180,(col+1)*220,(row+1)*180)),(x,y))
                else:draw.text((x+25,y+75),'Not captured',fill='black')
                draw.text((x+6,y+186),unit['id'],fill='black')
            image.save(QA/f'contact-{phase}-{offset//24:02d}.png')
    print('Native contacts assembled; absent captures remain visibly unverified')
if __name__=='__main__':main()
