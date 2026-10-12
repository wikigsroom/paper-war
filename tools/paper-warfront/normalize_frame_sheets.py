"""Normalize complete drawn sheets with ONE scale and fixed cell/ground anchors."""
from pathlib import Path
import argparse,json,hashlib,statistics
import numpy as np
from PIL import Image,ImageDraw
from scipy import ndimage
from paper_alpha import defringe
ROOT=Path(__file__).resolve().parents[2]
SIZE=192;GROUND=180
OUT=ROOT/'game/assets/animation/frames-v1'
QA=ROOT/'output/qa/godot/frame-rebuild'
ADJUSTMENT_PATH=ROOT/'assets/paper-warfront/frame-rebuild/frame-adjustments.json'
ADJUSTMENTS=json.loads(ADJUSTMENT_PATH.read_text(encoding='utf-8'))['units']

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def separate_touching_actors(alpha,columns=6,rows=6):
    """Split a thin painted bridge, never manufacture a missing drawing.

    Whole source components stay intact unless two cell bodies share a label.
    Eroded body cores supply seeds; nearest-core ownership splits only that
    connected component. A missing second body fails rather than duplicating it.
    """
    h,w=alpha.shape
    labels,n=ndimage.label(alpha,structure=np.ones((3,3)))
    owners={};splits=[]
    for index in range(columns*rows):
        x=index%columns;y=index//columns
        region=labels[round(y*h/rows):round((y+1)*h/rows),round(x*w/columns):round((x+1)*w/columns)]
        covered=np.bincount(region.ravel(),minlength=n+1);covered[0]=0
        main=int(np.argmax(covered))
        if not main or covered[main]<250:raise ValueError(f'missing body in frame {index}')
        owners.setdefault(main,[]).append(index)
    next_label=n
    for label,indices in owners.items():
        if len(indices)<2:continue
        component=labels==label
        valid=None
        for erosion in (1,2,3,4):
            cores,core_count=ndimage.label(ndimage.binary_erosion(component,iterations=erosion),structure=np.ones((3,3)))
            selected=[]
            for index in indices:
                x=index%columns;y=index//columns
                region=cores[round(y*h/rows):round((y+1)*h/rows),round(x*w/columns):round((x+1)*w/columns)]
                counts=np.bincount(region.ravel(),minlength=core_count+1);counts[0]=0
                core=int(np.argmax(counts))
                if core==0 or counts[core]<180:break
                selected.append(core)
            if len(selected)==len(indices) and len(set(selected))==len(selected):
                valid=(erosion,cores,selected);break
        if valid is None:raise ValueError(f'grid repeats a body in frames {indices}; regenerate incomplete layout')
        erosion,cores,selected=valid
        markers=np.zeros_like(labels)
        for core,index in zip(selected,indices):markers[cores==core]=index+1
        nearest=ndimage.distance_transform_edt(markers==0,return_distances=False,return_indices=True)
        allocation=markers[tuple(nearest)]
        for index in indices:
            next_label+=1;labels[component&(allocation==index+1)]=next_label
        splits.append({'source_component':int(label),'frames':indices,'core_erosion_px':erosion})
    return labels,next_label,splits

def normalize(row):
    raw=ROOT/row['raw'];im=Image.open(raw).convert('RGBA');w,h=im.size
    frames=[];boxes=[];bottoms=[];counts=[];selected_labels=[]
    sheet=np.array(im)
    try:labels,n,splits=separate_touching_actors(sheet[:,:,3]>48)
    except ValueError as error:raise ValueError(row['id']+' '+str(error)) from error
    areas=np.bincount(labels.ravel());components=ndimage.find_objects(labels)
    adjustment=ADJUSTMENTS.get(row['id'],{})
    pad=150;canvas_w=round(w/6)+pad*2;canvas_h=round(h/6)+pad*2
    for index in range(36):
        c=index%6;r=index//6
        left=round(c*w/6);top=round(r*h/6);right=round((c+1)*w/6);bottom=round((r+1)*h/6)
        covered=np.bincount(labels[top:bottom,left:right].ravel(),minlength=n+1);covered[0]=0
        main_label=int(np.argmax(covered))
        if main_label==0 or areas[main_label]<250:raise ValueError(row['id']+f' missing complete actor in frame {index}')
        if main_label in selected_labels:raise ValueError(row['id']+f' grid repeats a cross-cell actor in frame {index}; regenerate incomplete layout')
        selected_labels.append(main_label)
        keep=np.zeros(n+1,dtype=bool);keep[main_label]=True
        main_box=components[main_label-1]
        for label in np.flatnonzero(areas>=12):
            if label==0 or label==main_label:continue
            if index in adjustment.get('omit_detached_components_frames',[]):continue
            region=components[label-1]
            cx=(region[1].start+region[1].stop)/2;cy=(region[0].start+region[0].stop)/2
            if left+3<=cx<right-3 and top+3<=cy<bottom-3 and region[1].start>=main_box[1].start-35 and region[1].stop<=main_box[1].stop+35:keep[label]=True
        # Mask complete components BEFORE cropping. Limbs crossing a logical
        # grid boundary belong to their actor and must remain connected.
        data=sheet.copy();alpha=np.where(keep[labels],sheet[:,:,3],0).astype(np.uint8)
        data[:,:,3]=alpha;data[alpha==0,:3]=0
        cell=Image.fromarray(data).crop((left-pad,top-pad,left-pad+canvas_w,top-pad+canvas_h));cell=defringe(cell)
        box=cell.getbbox()
        if box is None:raise ValueError(row['id']+f' empty frame {index}')
        frames.append(cell);boxes.append(box);bottoms.append(box[3]);counts.append(int(np.count_nonzero(alpha)))
    # A common scale is mandatory: a tall attack pose must not shrink the body.
    maxw=max(b[2]-b[0] for b in boxes);maxh=max(b[3]-b[1] for b in boxes)
    reach=max(max(canvas_w/2-b[0],b[2]-canvas_w/2) for b in boxes)
    shared=min((SIZE/2-7)/reach,(GROUND-7)/maxh)
    atlas=Image.new('RGBA',(SIZE*6,SIZE*6));normalized=[]
    for index,(cell,bottom) in enumerate(zip(frames,bottoms)):
        resized=cell.resize((round(cell.width*shared),round(cell.height*shared)),Image.Resampling.LANCZOS)
        frame=Image.new('RGBA',(SIZE,SIZE))
        # Shared center and planted ground, no bbox centering or per-pose resizing.
        x=round(SIZE/2-cell.width/2*shared);y=round(GROUND-bottom*shared)
        frame.alpha_composite(resized,(x,y));normalized.append(frame)
        for rect in adjustment.get('clear_regions',{}).get(str(index),[]):
            frame.paste((0,0,0,0),tuple(rect))
        atlas.alpha_composite(frame,((index%6)*SIZE,(index//6)*SIZE))
    stem=row['id'].replace('.','-');dest=OUT/(stem+'-atlas.png');atlas.save(dest)
    idle=OUT/(stem+'-idle.png');normalized[0].save(idle)
    portrait=normalized[0].copy();b=portrait.getbbox();portrait=portrait.crop(b);portrait.thumbnail((128,128),Image.Resampling.LANCZOS)
    icon=Image.new('RGBA',(144,144));icon.alpha_composite(portrait,((144-portrait.width)//2,(144-portrait.height)//2));ip=OUT/(stem+'-portrait.png');icon.save(ip)
    preview=Image.new('RGB',atlas.size,'#f4ead3');preview.paste(atlas,(0,0),atlas);pp=QA/'sheets'/(stem+'.png');pp.parent.mkdir(parents=True,exist_ok=True);preview.save(pp)
    height=statistics.median(b[3]-b[1] for b in boxes[:6])*shared
    origin={
       'bow':(.80,.50),'throw':(.72,.37),'crossbow':(.86,.50),'blowpipe':(.83,.43),
       'ballista':(.88,.54),'mortar':(.67,.45),'kite_launcher':(.72,.45),
       'stamp_machine':(.72,.46),'beast':(.84,.52),'ram':(.89,.61)
    }.get(row['gesture'],(.72,.50))
    origin_px=adjustment.get('release_origin',[round(SIZE*origin[0],2),round(SIZE*origin[1],2)])
    return {'id':row['id'],'atlas':'res://'+dest.relative_to(ROOT/'game').as_posix(),'idle':'res://'+idle.relative_to(ROOT/'game').as_posix(),'portrait':'res://'+ip.relative_to(ROOT/'game').as_posix(),'frame_size':[SIZE,SIZE],'columns':6,'rows':6,'anchor':[SIZE/2,GROUND],'source_height':round(height,3),'release_origin':origin_px,'frame_adjustment':adjustment,'fps':12,'clips':{'idle':list(range(6)),'walk':list(range(6,12)),'windup':[12,13,14],'attack':[15,16,17],'hurt':list(range(18,24)),'death':list(range(24,30)),'special':list(range(30,36)),'mine':list(range(12,18)),'unload':list(range(30,36)),'load':[30,31,32],'queue':[0],'bound':[0]},'frame_count':36,'raw':row['raw'],'raw_sha256':sha(raw),'source':row['source'],'source_sha256':sha(ROOT/row['source']),'prompt':row['prompt'],'prompt_sha256':sha(ROOT/row['prompt']),'model':'gpt-image-2.5','generation_reference_inputs':{path:sha(ROOT/path) for path in ['output/imagegen/paper-warfront/frame-rebuild/animation-layout-reference.png']+([row['layout_guide']] if row.get('layout_guide') else [])},'requested_size':[1536,1536],'actual_size':[w,h],'normalization':{'shared_scale':shared,'alpha_component_min_area':12,'thin_bridge_splits':splits,'original_bottoms':bottoms,'alpha_pixels':counts,'one_scale_for_all_36_frames':True,'fixed_anchor':True},'atlas_sha256':sha(dest),'idle_sha256':sha(idle),'portrait_sha256':sha(ip),'preview':pp.relative_to(ROOT).as_posix(),'preview_sha256':sha(pp),'status':'normalized-candidate-needs-native-review'}

def main():
    p=argparse.ArgumentParser();p.add_argument('--ids',nargs='*');p.add_argument('--existing',action='store_true');args=p.parse_args()
    OUT.mkdir(parents=True,exist_ok=True);QA.mkdir(parents=True,exist_ok=True)
    rows=json.loads((ROOT/'assets/paper-warfront/frame-rebuild/unit-briefs.json').read_text(encoding='utf-8'))['units']
    if args.ids:rows=[r for r in rows if r['id'] in args.ids]
    if args.existing:rows=[r for r in rows if (ROOT/r['raw']).exists()]
    dest=ROOT/'game/data/unit-frames.json';existing=json.loads(dest.read_text(encoding='utf-8')) if dest.exists() else {'version':1,'method':'whole-sheet authored image frames, fixed anchors, no bone transform','profiles':{}}
    for row in rows:
        rec=normalize(row);existing['profiles'][row['id']]=rec;print(row['id']+' normalized 36 actual drawings',flush=True)
    existing['processor']='tools/paper-warfront/normalize_frame_sheets.py';existing['processor_sha256']=sha(Path(__file__))
    existing['processor_inputs']={'tools/paper-warfront/paper_alpha.py':sha(ROOT/'tools/paper-warfront/paper_alpha.py'),'assets/paper-warfront/frame-rebuild/frame-adjustments.json':sha(ADJUSTMENT_PATH)}
    dest.write_text(json.dumps(existing,ensure_ascii=False,indent=2),encoding='utf-8')
    (CAT:=ROOT/'assets/paper-warfront/frame-rebuild') .mkdir(exist_ok=True)
    (CAT/'frame-provenance.json').write_text(json.dumps(existing,ensure_ascii=False,indent=2),encoding='utf-8')

if __name__=='__main__':main()
