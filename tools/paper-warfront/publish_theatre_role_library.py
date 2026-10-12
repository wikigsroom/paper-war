"""Publish shared role masters with explicit faction palette variants, not 400 generated originals."""
from __future__ import annotations
from pathlib import Path
import colorsys
import hashlib
import json
import sys
import time
import zipfile
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from export_library import clean_alpha, components, extract_character, centered
from publish_world_art import rig
from publish_theatre_assets import portrait

ROOT=Path(__file__).resolve().parents[2]
GAME=ROOT/'game';OUT=ROOT/'output/imagegen/paper-warfront/theatre-v3'
PALETTES={'yin':'D85840','mo':'7469B1','deng':'42A8A7','ji':'E29643','yuan':'528DC9','qi':'CBAC43','mu':'60975A','shuang':'84C7D9','jin':'DA773D','bai':'425883'}

def read(path):return json.loads(path.read_text(encoding='utf-8'))
def write(path,data):path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def hsv(hex_color):return colorsys.rgb_to_hsv(*(int(hex_color[i:i+2],16)/255 for i in [0,2,4]))

def recolor(image,donor,target):
    source_h,source_s,_=hsv(donor);target_h,target_s,_=hsv(target)
    raw=np.asarray(image.convert('RGB').convert('HSV')).copy();original=np.asarray(image)
    h=raw[:,:,0].astype(float)/255;s=raw[:,:,1].astype(float)/255;v=raw[:,:,2].astype(float)/255
    hue_distance=np.minimum(np.abs(h-source_h),1-np.abs(h-source_h))
    # Preserve ink outlines, cream paper, skin and gold; recolor only the donor uniform range.
    mask=(hue_distance<.080)&(s>.27)&(v>.20)&(original[:,:,3]>0)
    raw[:,:,0][mask]=np.round(((h[mask]+target_h-source_h)%1)*255).astype(np.uint8)
    raw[:,:,1][mask]=np.round(np.clip(s[mask]*np.clip(target_s/max(.1,source_s),.65,1.35),0,1)*255).astype(np.uint8)
    result=Image.fromarray(raw,'HSV').convert('RGB').convert('RGBA');result.putalpha(image.getchannel('A'))
    return result,int(mask.sum())

def main():
    sys.stdout.reconfigure(encoding='utf-8')
    balance=read(GAME/'data/balance-prototype.json');factions=read(GAME/'data/factions.json')['factions']
    manifest=read(GAME/'data/assets.json');provenance=read(GAME/'data/theatre-art-provenance.json')
    records={r['id']:r for r in provenance['records']};combat=read(GAME/'data/world-art-provenance.json');cr={r['id']:r for r in combat['records']}
    support=read(GAME/'data/world-support-provenance.json');sr={r['id']:r for r in support['records']}
    masters={};master_meta={};core=set()
    for faction in factions:
        for uid in faction['core_roster']:
            core.add(uid);role=balance['units'][uid]['role']
            if role in masters:continue
            path=GAME/manifest['assets'][uid]['path'].removeprefix('res://')
            masters[role]=Image.open(path).convert('RGBA')
            master_meta[role]=dict(master_id=uid,master_path=path.relative_to(ROOT).as_posix(),master_sha256=sha(path),donor_palette=PALETTES[faction['id']],**{k:records[uid][k] for k in ['source','sha256','model','job']})
    sources=read(OUT/'role-families/jobs.json')['jobs']
    master_folder=OUT/'role-families/masters';master_folder.mkdir(exist_ok=True)
    for job in sources:
        source=OUT/'role-families'/(job['id']+'.png');whole,method=clean_alpha(Image.open(source));parts=components(whole);seen=set()
        for n,role in enumerate(job['roles']):
            cut,bbox,extraction=extract_character(whole,parts,n%3,n//3,3,2)
            assert tuple(bbox) not in seen,'duplicate role '+role;seen.add(tuple(bbox))
            assert 1<bbox[0]<bbox[2]<whole.width-1 and 1<bbox[1]<bbox[3]<whole.height-1,'clipped role '+role
            image,meta=centered(cut,512,baseline=True);path=master_folder/(role+'.png');image.save(path,optimize=True)
            masters[role]=image;master_meta[role]=dict(master_id='role.'+role,master_path=path.relative_to(ROOT).as_posix(),master_sha256=sha(path),donor_palette='435AA3',source=source.relative_to(ROOT).as_posix(),sha256=sha(source),model='gpt-image-2.5',job=job['id'],alpha_method=method,source_box=bbox,extraction=extraction)
    ids=[uid for faction in factions for uid in faction['combat_units'] if uid not in core]
    aliases={'unit.mo.thrall':'unit.mo.raider','unit.deng.guardian':'unit.deng.guard'}
    # Preserve every replaced derivative and data record before publication.
    backup=ROOT/'output/backups'/('before-role-library-'+time.strftime('%Y%m%d-%H%M%S')+'.zip');backup.parent.mkdir(exist_ok=True)
    paths=set((GAME/'data').glob('*.json'))
    for uid in ids+list(aliases):
        asset=manifest['assets'].get(uid,{})
        for path in [asset.get('path'),asset.get('portrait'),*asset.get('animation',{}).get('parts',{}).values()]:
            if path and (GAME/path.removeprefix('res://')).exists():paths.add(GAME/path.removeprefix('res://'))
    with zipfile.ZipFile(backup,'w',zipfile.ZIP_DEFLATED) as z:
        for path in sorted(paths):z.write(path,path.relative_to(ROOT).as_posix())
    boards={};published=[]
    for uid in ids+list(aliases):
        faction=uid.split('.')[1];role=balance['units'][uid].get('role','')
        if uid in aliases:
            donor=aliases[uid];image=Image.open(GAME/manifest['assets'][donor]['path'].removeprefix('res://')).convert('RGBA')
            role=balance['units'][donor]['role'];meta=dict(records[donor],master_id=donor,master_sha256=sha(GAME/manifest['assets'][donor]['path'].removeprefix('res://')),donor_palette=PALETTES[faction]);pixels=0
        else:
            assert role in masters,'missing role '+role
            meta=master_meta[role].copy();image,pixels=recolor(masters[role],meta['donor_palette'],PALETTES[faction])
        filename=uid.replace('.','-')+'.png';path=GAME/'assets/characters/cutouts'/filename;image.save(path,optimize=True)
        face=GAME/'assets/characters/portraits'/filename;portrait(image,role).save(face,optimize=True)
        cart=role in ['artillery','mortar','siege'];animation=rig(image,uid,cart)
        box=list(image.getchannel('A').point(lambda v:255 if v>=24 else 0).getbbox())
        manifest['assets'][uid]=dict(path='res://'+path.relative_to(GAME).as_posix(),portrait='res://'+face.relative_to(GAME).as_posix(),category='unit',style='paper-theatre-v3',status='runtime-linked-source-review-pending',content_box=box,world_height=2.0 if role=='colossus' else 1.12 if cart else 1.42,animation=animation)
        balance['units'][uid]['art_status']='runtime-linked-source-review-pending'
        rec=dict(id=uid,role=role,**{k:v for k,v in meta.items() if k not in ['id','role']},variant_method='shared_role_master_uniform_hue_recolor' if uid not in aliases else 'summoned_role_alias',target_palette=PALETTES[faction],recolored_pixels=pixels,output_sha256=sha(path),portrait_sha256=sha(face))
        records[uid]=rec
        if uid in aliases:sr[uid]=rec
        else:cr[uid]=rec
        boards.setdefault(faction,[]).append((uid,image));published.append(uid)
    write(GAME/'data/assets.json',manifest);write(GAME/'data/balance-prototype.json',balance)
    provenance['records']=list(records.values());write(GAME/'data/theatre-art-provenance.json',provenance)
    combat['records']=list(cr.values());write(GAME/'data/world-art-provenance.json',combat)
    support['records']=list(sr.values());write(GAME/'data/world-support-provenance.json',support)
    write(GAME/'data/theatre-role-library.json',dict(role_count=len(masters),variant_count=len(ids),bespoke_core_count=len(core),summoned_aliases=aliases,masters=master_meta,palettes=PALETTES,scope='40 roles shared across ten faction palettes; 40 bespoke core troops, 360 palette variants and two summoned aliases. Not 400 independently generated illustrations.'))
    font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',15)
    for faction,items in boards.items():
        board=Image.new('RGB',(1200,((len(items)+5)//6)*230),'#FFF1D2');draw=ImageDraw.Draw(board)
        for n,(uid,image) in enumerate(items):
            im=image.copy();im.thumbnail((184,192),Image.Resampling.LANCZOS);x=n%6*200;y=n//6*230
            board.paste(im,(x+(200-im.width)//2,y+8),im);draw.text((x+8,y+205),uid,font=font,fill='#292536')
        board.save(OUT/('role-variants-'+faction+'.jpg'),quality=94)
    write(OUT/'role-publication-audit.json',dict(published=published,role_masters=len(masters),backup=backup.relative_to(ROOT).as_posix(),status='runtime linked; native and visual review pending'))
    print(json.dumps(dict(published=len(published),masters=len(masters),backup=str(backup)),ensure_ascii=False))

if __name__=='__main__':main()
