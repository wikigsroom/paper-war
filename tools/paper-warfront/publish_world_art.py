"""Normalize alpha sprites, build articulated paper rigs, and audit source boundaries."""
from pathlib import Path
import argparse,json,hashlib
import numpy as np
from PIL import Image,ImageChops,ImageDraw,ImageFont
from export_library import clean_alpha,centered,make_portrait,components,extract_character
ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'output/imagegen/paper-warfront/world-v2'
GAME=ROOT/'game'

def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def rig(image,uid,cart):
    bbox=image.getchannel('A').point(lambda x:255 if x>=24 else 0).getbbox()
    top,bottom=bbox[1],bbox[3]
    hip=round(top+(bottom-top)*.73)
    animation=dict(hip=hip,foot=[256,476],source_height=bottom-top,parts={})
    masks={}
    if cart:
        animation['cart']=True
        # Bottom alpha lobes locate the two ground-contact wheels on the normalized cart.
        alpha=np.asarray(image.getchannel('A'))
        band=alpha[round(top+(bottom-top)*.78):bottom,:]>80
        columns=np.sum(band,axis=0)
        middle=(bbox[0]+bbox[2])//2
        peaks=[]
        for a,b in [(bbox[0],middle),(middle,bbox[2])]:
            weights=columns[a:b].astype(float)
            cx=round(np.average(np.arange(a,b),weights=weights)) if weights.sum() else (a+b)//2
            peaks.append(cx)
        radius=max(18,round((bottom-top)*.22))
        cy=bottom-radius
        wheel_union=Image.new('L',image.size)
        for label,cx in zip(['wheel-back','wheel-front'],peaks):
            mask=Image.new('L',image.size);ImageDraw.Draw(mask).ellipse((cx-radius,cy-radius,cx+radius,cy+radius),fill=255)
            masks[label]=mask;wheel_union=ImageChops.lighter(wheel_union,mask)
            animation[label+'_pivot']=[cx,cy]
        masks['body']=ImageChops.invert(wheel_union)
    else:
        # Weapons and banners make the full silhouette asymmetric. Split the actual
        # feet, rather than the canvas centre, so both legs have visible pixels.
        alpha=np.asarray(image.getchannel('A'))
        ground_start=round(top+(bottom-top)*.88)
        weights=np.sum(alpha[ground_start:bottom,:].astype(float),axis=0)
        total=float(weights.sum())
        if not total:raise ValueError('No visible ground-contact pixels: '+uid)
        split=int(np.searchsorted(np.cumsum(weights),total*.5))
        split=max(bbox[0]+1,min(bbox[2]-2,split))
        animation['foot']=[round(np.average(np.arange(512),weights=weights)),476]
        for label,start,end in [('leg-back',bbox[0],split+1),('leg-front',split+1,bbox[2])]:
            region=weights[start:end]
            px=round(np.average(np.arange(start,end),weights=region)) if region.sum() else (start+end)//2
            animation[label+'_pivot']=[px,hip]
        for label in ['body','leg-back','leg-front']:
            mask=Image.new('L',image.size);draw=ImageDraw.Draw(mask)
            if label=='body':draw.rectangle((0,0,511,hip+14),fill=255)
            elif label=='leg-back':draw.rectangle((0,hip-10,split,511),fill=255)
            else:draw.rectangle((split+1,hip-10,511,511),fill=255)
            masks[label]=mask
    for label,mask in masks.items():
        part=image.copy();part.putalpha(ImageChops.multiply(image.getchannel('A'),mask))
        path=GAME/'assets/animation'/f'{uid.replace(".","-")}-{label}.png'
        path.parent.mkdir(parents=True,exist_ok=True);part.save(path,optimize=True)
        animation['parts'][label]='res://'+str(path.relative_to(GAME)).replace('\\','/')
    return animation

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--faction');args=parser.parse_args()
    jobs=json.loads((SOURCE/'jobs.json').read_text(encoding='utf-8'))['jobs']
    manifest=json.loads((GAME/'data/assets.json').read_text(encoding='utf-8'))
    balance=json.loads((GAME/'data/balance-prototype.json').read_text(encoding='utf-8'))
    records=[];missing=[];errors=[]
    font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',18)
    boards={}
    for job in jobs:
        if args.faction and job['faction']!=args.faction:continue
        source=ROOT/job['source']
        if not source.exists():missing.append(job['id']);continue
        try:whole,alpha_method=clean_alpha(Image.open(source))
        except ValueError as e:errors.append(dict(job=job['id'],error=str(e)));continue
        silhouettes=components(whole)
        seen_boxes=set()
        for cell,uid in enumerate(job['units']):
            repair_path=SOURCE/'repairs'/(uid.replace('.','-')+'.png')
            actual_source=source
            if repair_path.exists():
                repair,alpha_method=clean_alpha(Image.open(repair_path));actual_source=repair_path
                source_box=list(repair.getchannel('A').point(lambda x:255 if x>=24 else 0).getbbox())
                cut=repair.crop(source_box);cleanup={'method':'single-sprite-repair','subject_components':1}
                original_size=repair.size
            else:
                cut,source_box,cleanup=extract_character(whole,silhouettes,cell%4,cell//4,4,2);original_size=whole.size
            if tuple(source_box) in seen_boxes:
                errors.append(dict(unit=uid,job=job['id'],error='duplicate source silhouette selected'));continue
            seen_boxes.add(tuple(source_box))
            alpha=np.asarray(cut.getchannel('A'))
            # Match whole connected silhouettes rather than cutting weapons at guessed grid boundaries.
            edge_pixels=0
            if source_box[0]<=1 or source_box[1]<=1 or source_box[2]>=original_size[0]-1 or source_box[3]>=original_size[1]-1:
                errors.append(dict(unit=uid,job=job['id'],error='source silhouette touches canvas boundary',source_box=source_box));continue
            normalized,meta=centered(cut,512,baseline=True)
            defn=balance['units'][uid];role=defn['role'];cart=role in ['artillery','siege','mortar']
            filename=uid.replace('.','-')+'.png'
            destination=GAME/'assets/characters/cutouts'/filename;destination.parent.mkdir(parents=True,exist_ok=True)
            normalized.save(destination,optimize=True)
            portrait_path=GAME/'assets/characters/portraits'/filename;portrait_path.parent.mkdir(parents=True,exist_ok=True)
            if cart:portrait=centered(normalized.crop(normalized.getchannel('A').getbbox()),192)[0]
            else:portrait=make_portrait(normalized)
            portrait.save(portrait_path,optimize=True)
            asset=dict(path='res://'+str(destination.relative_to(GAME)).replace('\\','/'),portrait='res://'+str(portrait_path.relative_to(GAME)).replace('\\','/'),
                       category='unit',world_height=2.75 if role=='colossus' else 1.65 if cart else 1.48,content_box=meta['content_box'],
                       status='runtime-linked-source-review-pending',usage='original-generated-articulated-paper-puppet',source='res://data/world-art-provenance.json')
            asset['animation']=rig(normalized,uid,cart)
            manifest['assets'][uid]=asset
            defn['art_status']='runtime-linked-source-review-pending'
            records.append(dict(id=uid,source=str(actual_source.relative_to(ROOT)).replace('\\','/'),sha256=hashlib.sha256(actual_source.read_bytes()).hexdigest(),alpha_method=alpha_method,edge_pixels=edge_pixels,source_box=source_box,extraction=cleanup,role=role))
            boards.setdefault(job['faction'],[]).append((uid,normalized))
    write(GAME/'data/assets.json',manifest);write(GAME/'data/balance-prototype.json',balance)
    provenance_path=GAME/'data/world-art-provenance.json'
    previous=json.loads(provenance_path.read_text(encoding='utf-8')) if provenance_path.exists() else dict(records=[])
    record_map={r['id']:r for r in previous['records']};record_map.update({r['id']:r for r in records})
    write(provenance_path,dict(model='gpt-image-2.5',skill='sub2-image-gen',records=list(record_map.values()),status='alpha and cutout audit passed; human source review tracked separately'))
    for f,items in boards.items():
        board=Image.new('RGB',(1200,7*258),'#d8d4c9');draw=ImageDraw.Draw(board)
        for n,(uid,im) in enumerate(items):
            thumb=im.copy();thumb.thumbnail((180,215),Image.Resampling.LANCZOS)
            x=n%6*200;y=n//6*258
            board.paste(thumb,(x+(200-thumb.width)//2,y+10),thumb)
            draw.text((x+8,y+227),balance['units'][uid]['name'],font=font,fill='#343332')
        board.save(SOURCE/f'{f}-contact-review.jpg',quality=94)
    write(SOURCE/'publication-audit.json',dict(published=len(records),all_published=len(record_map),missing=missing,errors=errors,status='development publication; missing/error assets retain marked development fallbacks'))
    print(json.dumps(dict(published=len(records),total=len(record_map),missing=len(missing),errors=errors),ensure_ascii=False))

if __name__=='__main__':main()
