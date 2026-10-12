"""Extract originals for ten armies; retain source provenance and reject clipped silhouettes."""
from pathlib import Path
import json,hashlib,shutil
from PIL import Image
from export_library import clean_alpha,components,extract_character,centered,make_portrait
from publish_world_art import rig,write
ROOT=Path(__file__).resolve().parents[2];GAME=ROOT/'game';OUT=ROOT/'output/imagegen/paper-warfront/world-support'

def main():
    jobs=json.loads((OUT/'jobs.json').read_text(encoding='utf-8'))['jobs']
    manifest=json.loads((GAME/'data/assets.json').read_text(encoding='utf-8'))
    balance=json.loads((GAME/'data/balance-prototype.json').read_text(encoding='utf-8'))
    records=[];missing=[];errors=[]
    for job in jobs:
        source=ROOT/job['source']
        if not source.exists():missing.append(job['id']);continue
        source_sha=hashlib.sha256(source.read_bytes()).hexdigest()
        if job['kind']=='background':
            destination=GAME/'assets/backgrounds'/f'background-{job["faction"]}.png';destination.parent.mkdir(parents=True,exist_ok=True)
            Image.open(source).convert('RGB').save(destination,optimize=True)
            uid=job['assets'][0];manifest['assets'][uid]=dict(path='res://'+str(destination.relative_to(GAME)).replace('\\','/'),category='background',status='runtime-linked-source-review-pending')
            records.append(dict(id=uid,source=job['source'],sha256=source_sha));continue
        try:image,method=clean_alpha(Image.open(source))
        except ValueError as e:errors.append(dict(job=job['id'],error=str(e)));continue
        parts=components(image);seen=set()
        for cell,uid in enumerate(job['assets']):
            isolated,bbox,cleanup=extract_character(image,parts,cell%4,cell//4,4,2)
            if tuple(bbox) in seen:errors.append(dict(id=uid,error='repeated silhouette'));continue
            seen.add(tuple(bbox))
            if bbox[0]<=1 or bbox[1]<=1 or bbox[2]>=image.width-1 or bbox[3]>=image.height-1:errors.append(dict(id=uid,error='canvas boundary clipping',box=bbox));continue
            normalized,meta=centered(isolated,512,baseline=True)
            category=uid.split('.')[0]
            subdir={'unit':'characters/cutouts','portrait':'portraits','building':'buildings','prop':'props'}[category]
            path=GAME/'assets'/subdir/(uid.replace('.','-')+'.png');path.parent.mkdir(parents=True,exist_ok=True);normalized.save(path,optimize=True)
            asset=dict(path='res://'+str(path.relative_to(GAME)).replace('\\','/'),category=category,content_box=meta['content_box'],status='runtime-linked-source-review-pending',usage='original-paper-world-support')
            if category in ['unit','portrait']:
                face=make_portrait(normalized);facepath=GAME/'assets/characters/portraits'/(uid.replace('.','-')+'.png');facepath.parent.mkdir(parents=True,exist_ok=True);face.save(facepath,optimize=True)
                asset['portrait']='res://'+str(facepath.relative_to(GAME)).replace('\\','/');asset['world_height']=1.35 if category=='unit' else 2.4
                if category=='unit':asset['animation']=rig(normalized,uid,False);balance['units'][uid]['art_status']='runtime-linked-source-review-pending'
            manifest['assets'][uid]=asset
            records.append(dict(id=uid,source=job['source'],sha256=source_sha,source_box=bbox,extraction=cleanup,alpha_method=method))
    write(GAME/'data/assets.json',manifest);write(GAME/'data/balance-prototype.json',balance)
    previous_path=GAME/'data/world-support-provenance.json'
    previous=json.loads(previous_path.read_text(encoding='utf-8')) if previous_path.exists() else dict(records=[])
    merged={r['id']:r for r in previous['records']};merged.update({r['id']:r for r in records})
    write(previous_path,dict(model='gpt-image-2.5',skill='sub2-image-gen',records=list(merged.values())))
    write(OUT/'publication-audit.json',dict(published=len(records),total=len(merged),missing=missing,errors=errors))
    print(json.dumps(dict(published=len(records),total=len(merged),missing=len(missing),errors=errors),ensure_ascii=False))
if __name__=='__main__':main()
