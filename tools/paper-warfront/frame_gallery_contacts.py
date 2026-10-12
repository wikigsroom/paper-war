"""Assemble review contacts from actual native Godot screenshots, not mockups."""
from pathlib import Path
import json
from PIL import Image,ImageDraw,ImageFont
from frame_contacts import main as phase_contacts

ROOT=Path(__file__).resolve().parents[2]
QA=ROOT/'output/qa/godot/frame-rebuild'

def main():
    phase_contacts()
    rows=json.loads((ROOT/'assets/paper-warfront/frame-rebuild/unit-briefs.json').read_text(encoding='utf-8'))['units']
    definitions=json.loads((ROOT/'game/data/balance-prototype.json').read_text(encoding='utf-8'))['units']
    for start in range(0,len(rows),9):
        canvas=Image.new('RGB',(1320,1158),'#efe3ca');draw=ImageDraw.Draw(canvas)
        for i,row in enumerate(rows[start:start+9]):
            with Image.open(QA/'native-frames'/(row['id'].replace('.','-')+'.png')) as source:im=source.resize((440,360))
            x=i%3*440;y=i//3*386;canvas.paste(im,(x,y));draw.text((x+6,y+366),row['id'],fill='black')
        canvas.save(QA/f'full-review-{start//9:02d}.png')
    workers=[row for row in rows if definitions[row['id']].get('economy')]
    for start in range(0,len(workers),5):
        canvas=Image.new('RGB',(1320,1900),'#efe3ca');draw=ImageDraw.Draw(canvas)
        for i,row in enumerate(workers[start:start+5]):
            with Image.open(QA/'native-frames'/(row['id'].replace('.','-')+'.png')) as source:
                canvas.paste(source.crop((0,360,1320,540)),(0,i*380))
                canvas.paste(source.crop((0,900,1320,1080)),(0,i*380+180))
            draw.text((6,i*380+365),row['id']+' MINE / UNLOAD',fill='black')
        canvas.save(QA/f'worker-rows-{start//5:02d}.png')
    font=ImageFont.truetype(str(ROOT/'game/assets/fonts/NotoSansSC.ttf'),21)
    small=ImageFont.truetype(str(ROOT/'game/assets/fonts/NotoSansSC.ttf'),17)
    canvas=Image.new('RGB',(1320,760),'#f4ead3');draw=ImageDraw.Draw(canvas)
    draw.text((24,12),'纸上兵戈 · 原生 Godot 静帧',font=font,fill='#293d40')
    for index,(faction,title) in enumerate([('ji','纸械工坊 · 发条、钉枪、维修与重弩'),('mu','植纤古庭 · 根藤、孢籽、花冠与叶蛾'),('bai','空白档案 · 空框、镂字、执笔与折兽')]):
        top=52+index*232;draw.text((24,top),title,font=font,fill='#293d40')
        units=[r for r in rows if r['faction']==faction and not definitions[r['id']].get('economy') and not definitions[r['id']].get('summoned')]
        for col,row in enumerate(units):
            with Image.open(QA/'native-frames'/(row['id'].replace('.','-')+'.png')) as source:im=source.crop((0,0,220,162))
            canvas.paste(im,(col*220,top+34))
            draw.text((col*220+12,top+196),row['name'],font=small,fill='#293d40')
    canvas.save(QA/'distinct-units-preview.png')
    print('Native full sheets, worker action strips and 18-unit preview assembled')

if __name__=='__main__':main()
