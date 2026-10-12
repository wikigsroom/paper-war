"""Native Godot asset bridge. Source IDs and images remain traceable."""
from pathlib import Path
import json, shutil, hashlib
from PIL import Image, ImageDraw, ImageChops

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'assets/paper-warfront'
GAME = ROOT / 'game'

def main():
    for name in ['scripts', 'data', 'assets', 'tests']:
        (GAME / name).mkdir(parents=True, exist_ok=True)
    for name in ['characters', 'ui/portraits', 'ui/icons', 'backgrounds', 'props', 'materials', 'fx/motifs', 'buildings/reference', 'audio/sfx']:
        shutil.copytree(SOURCE / name, GAME / 'assets' / name, dirs_exist_ok=True)
    for name in ['balance-prototype.json', 'technology.json', 'style-tokens.json', 'library-definition.json']:
        shutil.copy2(SOURCE / name, GAME / 'data' / name)
    manifest = json.loads((SOURCE / 'runtime-manifest.json').read_text(encoding='utf-8'))
    manifest['version']='1.0.0'
    manifest['stage']='godot-runtime-linked'
    manifest['engine']='Godot 4.7.2'
    manifest['verification']='See docs/paper-warfront/15-运行验收与交付报告.md; linkage is not real-device approval.'
    if (SOURCE/'audio/music').exists():
        shutil.copytree(SOURCE/'audio/music',GAME/'assets/audio/music',dirs_exist_ok=True)
        for faction in ['yin','mo','deng']:
            manifest['assets']['audio.music.'+faction]['path']='res://assets/audio/music/music-'+faction+'.wav'
    parts = GAME / 'assets/animation'
    parts.mkdir(exist_ok=True)
    for asset_id, asset in manifest['assets'].items():
        asset['path'] = asset['path'].replace('assets/paper-warfront/', 'res://assets/')
        if 'portrait' in asset:
            asset['portrait'] = asset['portrait'].replace('assets/paper-warfront/', 'res://assets/')
        if asset['category'] in ['building','resource','prop']:
            with Image.open(GAME/asset['path'].replace('res://','')) as reference:
                asset['content_box']=list(reference.getchannel('A').getbbox())
                asset['source_size']=list(reference.size)
        asset.pop('rig', None)
        if asset_id.startswith(('unit.','portrait.')):
            source_image=Image.open(GAME/asset['path'].replace('res://','')).convert('RGBA')
            bound=source_image.getchannel('A').getbbox()
            centres={'unit.yin.axe':285,'unit.yin.spear':267,'unit.yin.hammer':273,'unit.yin.worker':325,
                     'unit.mo.blade':267,'unit.mo.needle':278,'unit.mo.priest':246,'unit.mo.giant':260,'unit.mo.worker':295,'unit.mo.thrall':258,
                     'unit.deng.mirror':287,'unit.deng.fire':280,'unit.deng.shadow':273,'unit.deng.effigy':261,'unit.deng.worker':297,'unit.deng.guardian':280}
            if asset_id.endswith('cannon'):
                portrait=source_image.crop(bound)
            else:
                head_size=round((bound[3]-bound[1])*.44)
                cx=centres.get(asset_id,round((bound[0]+bound[2])*.5+22))
                portrait=source_image.crop((cx-head_size//2,bound[1],cx+head_size//2,bound[1]+head_size))
            portrait.thumbnail((180,180),Image.Resampling.LANCZOS)
            face=Image.new('RGBA',(192,192))
            face.alpha_composite(portrait,((192-portrait.width)//2,(192-portrait.height)//2))
            face.save(GAME/asset['portrait'].replace('res://',''))
            asset['portrait_usage']='head-crop-for-godot-action-card'
        if not asset_id.startswith('unit.'):
            continue
        image = Image.open(ROOT / 'assets/paper-warfront/characters/cutouts' / (asset_id.replace('.', '-')+'.png')).convert('RGBA')
        bbox = image.getchannel('A').getbbox()
        top, bottom = bbox[1], bbox[3]
        hip = round(top + (bottom-top) * .68)
        # Overlapping paper joints prevent light seams when the two legs swing.
        masks = {}
        for label in ['body', 'leg-back', 'leg-front']:
            mask = Image.new('L', image.size, 0)
            draw = ImageDraw.Draw(mask)
            if label == 'body':
                draw.rectangle((0,0,511,hip+16), fill=255)
            elif label == 'leg-back':
                draw.rectangle((0,hip-12,256,511), fill=255)
            else:
                draw.rectangle((257,hip-12,511,511), fill=255)
            masks[label] = mask
        asset['animation'] = {'hip': hip, 'foot': [256,476], 'source_height': bottom-top, 'parts': {}}
        if asset_id.endswith('cannon'):
            asset['animation']['cart'] = True
            # The wheel centres were measured on the normalized source image.
            for label, cx in [('wheel-back',145),('wheel-front',359)]:
                mask = Image.new('L', image.size, 0)
                ImageDraw.Draw(mask).ellipse((cx-76,324,cx+76,476), fill=255)
                masks[label] = mask
                asset['animation'][label+'_pivot'] = [cx,400]
            masks['body'] = Image.new('L', image.size, 255)
        for label, mask in masks.items():
            out = image.copy()
            out.putalpha(ImageChops.multiply(image.getchannel('A'),mask))
            file = parts / f"{asset_id.replace('.','-')}-{label}.png"
            out.save(file)
            asset['animation']['parts'][label] = 'res://assets/animation/'+file.name
        asset['usage'] = 'godot-articulated-paper-puppet'
        asset['status'] = 'runtime-linked'
    (GAME / 'data/assets.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2), encoding='utf-8')
    inventory = []
    for f in sorted((GAME / 'assets').rglob('*')):
        if f.is_file() and not f.name.endswith('.import'):
            inventory.append({'path':str(f.relative_to(GAME)).replace('\\','/'),'bytes':f.stat().st_size,'sha256':hashlib.sha256(f.read_bytes()).hexdigest()})
    (GAME / 'data/asset-inventory.json').write_text(json.dumps(inventory,ensure_ascii=False,indent=2), encoding='utf-8')
    print(f'Godot asset bridge: {len(inventory)} files, {len(manifest["assets"])} stable IDs')

if __name__ == '__main__':
    main()
