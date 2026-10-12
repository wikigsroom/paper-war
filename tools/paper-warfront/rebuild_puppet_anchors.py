"""Rebuild rig layers from published whole sprites, using actual foot placement."""
from pathlib import Path
import json
from PIL import Image
from publish_world_art import rig,write
ROOT=Path(__file__).resolve().parents[2]
def main():
    path=ROOT/'game/data/assets.json'
    assets=json.loads(path.read_text(encoding='utf-8'))
    balance=json.loads((ROOT/'game/data/balance-prototype.json').read_text(encoding='utf-8'))
    count=0
    for uid,unit in balance['units'].items():
        if uid in ['unit.mo.thrall','unit.deng.guardian']:continue
        meta=assets['assets'][uid]
        if meta.get('status')!='runtime-linked-reviewed':continue
        image=Image.open(ROOT/'game'/meta['path'].removeprefix('res://')).convert('RGBA')
        meta['animation']=rig(image,uid,unit.get('role') in ['artillery','siege','mortar'])
        count+=1
    write(path,assets);print('Rebuilt actual-foot anchors and rig layers:',count)
if __name__=='__main__':main()
