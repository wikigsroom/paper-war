"""Verify actual Godot resource bindings, fonts, WAVs and provenance."""
from pathlib import Path
from collections import Counter
import argparse, json, hashlib, wave, array, sys, html, re
from PIL import Image, ImageDraw, ImageFont
from fontTools.ttLib import TTFont

ROOT=Path(__file__).resolve().parents[2]
GAME=ROOT/'game';SOURCE=ROOT/'assets/paper-warfront';OUT=ROOT/'output/qa/godot'

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    argparse.ArgumentParser(description='Historical v1 joint-animation asset verifier. The current whole-frame pipeline uses test_frame_contracts.gd and verify_paper_ui_assets.py. This historical verifier writes its v1 inventories when run without --help.').parse_args()
    sys.stdout.reconfigure(encoding='utf-8')
    OUT.mkdir(parents=True,exist_ok=True)
    manifest=json.loads((GAME/'data/assets.json').read_text(encoding='utf-8'))
    source=json.loads((SOURCE/'library-manifest.json').read_text(encoding='utf-8'))
    names={r['id']:r for r in source['assets']}
    errors=[];counts=Counter();integration=[]
    for asset_id,a in manifest['assets'].items():
        try:
            path=GAME/a['path'].removeprefix('res://')
            assert path.is_file() and path.resolve().is_relative_to(GAME.resolve())
            counts[a['category']]+=1
            entry={'id':asset_id,'name':names[asset_id]['name'],'category':a['category'],'runtime_path':a['path'],'source_path':names[asset_id]['asset_path'],'sha256':digest(path),'state':'runtime-linked'}
            if path.suffix=='.png':
                with Image.open(path) as im:im.verify()
            if 'portrait' in a:
                portrait=GAME/a['portrait'].removeprefix('res://')
                with Image.open(portrait) as im:assert im.size==(192,192) and im.mode=='RGBA'
                entry['portrait']=a['portrait']
            if asset_id.startswith('unit.'):
                anim=a['animation'];assert anim['foot']==[256,476] and anim['source_height']>0
                for part_id,part in anim['parts'].items():
                    with Image.open(GAME/part.removeprefix('res://')) as im:
                        assert im.size==(512,512) and im.mode=='RGBA' and im.getchannel('A').getbbox()
                counts['animation-parts']+=len(anim['parts']);entry['parts']=anim['parts']
                entry['scenario_evidence']='Unit rules: simulation-report.json; faction battle: ui-export/08 or 12; individual Android action untested.'
            if path.suffix=='.wav':
                with wave.open(str(path),'rb') as wav:
                    assert wav.getsampwidth()==2 and wav.getnchannels()==1
                    if asset_id.startswith('audio.music.'):
                        assert wav.getframerate()==22050 and abs(wav.getnframes()/22050-40)<.001
                    samples=array.array('h',wav.readframes(wav.getnframes()))
                    assert max(abs(s) for s in samples)<32767
                    assert abs(samples[0])<32 and abs(samples[-1])<32
                    entry['audio']={'rate':wav.getframerate(),'seconds':wav.getnframes()/wav.getframerate(),'peak':max(abs(s) for s in samples)/32767}
            integration.append(entry)
        except Exception as e:errors.append(asset_id+': '+str(e or type(e).__name__))
    # The original source rhythm drafts remain traceable; runtime IDs use new masters.
    assert len(manifest['assets'])==116 and counts['animation-parts']==53
    text=''.join(p.read_text(encoding='utf-8') for p in list((GAME/'scripts').glob('*.gd'))+list((GAME/'data').glob('*.json')) if p.name!='asset-inventory.json')
    required={ord(c) for c in text if '\u4e00'<=c<='\u9fff'}
    for family in ['NotoSansSC','NotoSerifSC']:
        font=TTFont(GAME/'assets/fonts'/f'{family}.ttf');cmap=font.getBestCmap()
        missing=sorted(required-set(cmap))
        if missing:errors.append(f'{family}: missing '+''.join(chr(c) for c in missing))
        counts['font-glyphs-'+family]=len(cmap)
    for f in (GAME/'assets').rglob('*.png'):
        try:
            with Image.open(f) as im:im.verify()
        except Exception as e:errors.append(str(f)+': '+str(e))
    inventory=[]
    for f in sorted((GAME/'assets').rglob('*')):
        if f.is_file() and not f.name.endswith('.import'):
            inventory.append({'path':f.relative_to(GAME).as_posix(),'bytes':f.stat().st_size,'sha256':digest(f)})
    (GAME/'data/asset-inventory.json').write_text(json.dumps(inventory,ensure_ascii=False,indent=2),encoding='utf-8')
    (SOURCE/'godot-integration.json').write_text(json.dumps({'version':'1.0.0','assets':integration},ensure_ascii=False,indent=2),encoding='utf-8')
    (OUT/'runtime-assets-report.json').write_text(json.dumps({'errors':errors,'counts':dict(counts),'files':len(inventory),'bytes':sum(a['bytes'] for a in inventory),'asset_ids':len(integration)},ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'errors':errors,'counts':dict(counts),'files':len(inventory)},ensure_ascii=False))
    if errors:raise SystemExit(1)

if __name__=='__main__':main()
