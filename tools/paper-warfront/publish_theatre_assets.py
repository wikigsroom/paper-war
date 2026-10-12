"""Publish whole alpha silhouettes and record the new theatre art separately."""
from pathlib import Path
import json, hashlib, argparse, sys
from PIL import Image, ImageDraw, ImageFont
from export_library import clean_alpha, components, extract_character, centered
from publish_world_art import rig

ROOT=Path(__file__).resolve().parents[2];GAME=ROOT/'game';OUT=ROOT/'output/imagegen/paper-warfront/theatre-v3'
def read(path):return json.loads(path.read_text(encoding='utf-8'))
def write(path,value):path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def portrait(image,role):
 bbox=image.getchannel('A').point(lambda v:255 if v>=24 else 0).getbbox()
 if role in ['artillery','mortar','siege']:return centered(image.crop(bbox),192)[0]
 height=bbox[3]-bbox[1];width=bbox[2]-bbox[0]
 # Horizontal weapons must not shrink the actual face to fit their whole width.
 rx=.34 if role in ['javelin','archer','poisoner','repeater'] else .5 if role=='colossus' else .59
 ry=.40 if role in ['necromancer','oracle','warden'] else .32
 side=max(96,round(height*.56));cx=round(bbox[0]+width*rx);cy=round(bbox[1]+height*ry)
 return centered(image.crop((cx-side//2,cy-side//2,cx+side//2,cy+side//2)),192)[0]

def main():
 sys.stdout.reconfigure(encoding='utf-8');p=argparse.ArgumentParser();p.add_argument('--faction');a=p.parse_args()
 jobs=read(OUT/'jobs.json')['jobs'];manifest=read(GAME/'data/assets.json');balance=read(GAME/'data/balance-prototype.json')
 if (OUT/'repairs/common-mine.png').exists():jobs=jobs+[dict(id='common-mine',category='props',faction='common',assets=['resource.common.mine'],cols=1,rows=1)]
 combat=read(GAME/'data/world-art-provenance.json');support=read(GAME/'data/world-support-provenance.json')
 provenance_path=GAME/'data/theatre-art-provenance.json';prior=read(provenance_path) if provenance_path.exists() else dict(records=[])
 records={r['id']:r for r in prior['records']};combat_records={r['id']:r for r in combat['records']};support_records={r['id']:r for r in support['records']}
 errors=[];published=[];boards=[]
 for job in jobs:
  if a.faction and job['faction']!=a.faction:continue
  repair=OUT/'repairs'/(job['id']+'.png')
  source=repair if repair.exists() else OUT/(job['id']+'.png')
  if not source.exists():continue
  digest=hashlib.sha256(source.read_bytes()).hexdigest();candidates=[]
  if job['category']=='background':
   uid=job['assets'][0];path=GAME/'assets/backgrounds'/('theatre-'+job['faction']+'.png');path.parent.mkdir(parents=True,exist_ok=True)
   Image.open(source).convert('RGB').save(path,optimize=True)
   asset=dict(path='res://'+path.relative_to(GAME).as_posix(),category='background',status='runtime-linked-source-review-pending',style='paper-theatre-v3')
   rec=dict(id=uid,source=source.relative_to(ROOT).as_posix(),sha256=digest,model='gpt-image-2.5',job=job['id'])
   manifest['assets'][uid]=asset;records[uid]=rec;support_records[uid]=rec;published.append(uid);continue
  try:
   whole,method=clean_alpha(Image.open(source));parts=components(whole);seen=set()
   for cell,uid in enumerate(job['assets']):
    cut,bbox,extraction=extract_character(whole,parts,cell%job['cols'],cell//job['cols'],job['cols'],job['rows'])
    assert tuple(bbox) not in seen,'duplicated subject';seen.add(tuple(bbox))
    assert 1<bbox[0]<bbox[2]<whole.width-1 and 1<bbox[1]<bbox[3]<whole.height-1,'clipped canvas boundary '+uid
    normalized,meta=centered(cut,512,baseline=True);candidates.append((uid,normalized,meta,bbox,extraction,method))
  except Exception as error:
   errors.append(dict(job=job['id'],reason=str(error)));continue
  for uid,normalized,meta,bbox,extraction,method in candidates:
   category=uid.split('.')[0];folder={'unit':'characters/cutouts','building':'buildings','prop':'props','resource':'buildings'}[category]
   path=GAME/'assets'/folder/(uid.replace('.','-')+'.png');path.parent.mkdir(parents=True,exist_ok=True);normalized.save(path,optimize=True)
   asset=dict(path='res://'+path.relative_to(GAME).as_posix(),category=category,content_box=meta['content_box'],status='runtime-linked-source-review-pending',style='paper-theatre-v3')
   role=balance['units'][uid].get('role','worker') if category=='unit' else category
   if category=='unit':
    cart=role in ['artillery','mortar','siege'];face_image=portrait(normalized,role)
    face=GAME/'assets/characters/portraits'/(uid.replace('.','-')+'.png');face.parent.mkdir(parents=True,exist_ok=True);face_image.save(face,optimize=True)
    asset.update(portrait='res://'+face.relative_to(GAME).as_posix(),world_height=2.0 if role=='colossus' else 1.12 if cart else 1.22 if role=='worker' else 1.42,animation=rig(normalized,uid,cart))
    balance['units'][uid]['art_status']='runtime-linked-source-review-pending'
   manifest['assets'][uid]=asset
   rec=dict(id=uid,source=source.relative_to(ROOT).as_posix(),sha256=digest,alpha_method=method,source_box=bbox,extraction=extraction,role=role,model='gpt-image-2.5',job=job['id'])
   records[uid]=rec
   if uid in combat_records:combat_records[uid]=rec
   else:support_records[uid]=rec
   boards.append((uid,normalized));published.append(uid)
 write(GAME/'data/assets.json',manifest);write(GAME/'data/balance-prototype.json',balance)
 combat['records']=list(combat_records.values());support['records']=list(support_records.values());write(GAME/'data/world-art-provenance.json',combat);write(GAME/'data/world-support-provenance.json',support)
 write(provenance_path,dict(model='gpt-image-2.5',skill='sub2-image-gen',records=list(records.values()),status='new source art; visual and runtime review recorded separately'))
 if boards:
  cols=6;rows=(len(boards)+cols-1)//cols;board=Image.new('RGB',(1200,rows*230),'#FFF1D2');draw=ImageDraw.Draw(board);font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',15)
  for i,(uid,im) in enumerate(boards):
   im=im.copy();im.thumbnail((185,192),Image.Resampling.LANCZOS);x=i%cols*200;y=i//cols*230;board.paste(im,(x+(200-im.width)//2,y+8),im);draw.text((x+8,y+205),uid,font=font,fill='#292536')
  board.save(OUT/('contact-'+(a.faction or 'all')+'.jpg'),quality=94)
 write(OUT/'publication-audit.json',dict(published=published,total=len(records),errors=errors))
 print(json.dumps(dict(published=len(published),total=len(records),errors=errors),ensure_ascii=False))
 if errors:raise SystemExit(1)

if __name__=='__main__':main()
