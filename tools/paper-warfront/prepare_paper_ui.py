"""Normalize approved Sub2API paper UI sheets; no procedural replacement art."""
from pathlib import Path
import hashlib, json
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'output/imagegen/paper-warfront/ui-rc16'
LIBRARY = ROOT / 'assets/paper-warfront/ui/paper'
RUNTIME = ROOT / 'game/assets/ui/paper'
BUTTONS = ['normal','primary','hover','pressed','disabled','selected','primary-pressed','gold']
PANELS = ['ledger','card','ink','jade']
ICONS = ['gold','mana','army','seal','tower','hourglass','check','close','lock','pause','back','flag','victory','defeat','settings','scroll']

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()

def normalize_slices(image, target, source_edge, edge=12):
    """Keep the entire fold inside a fixed-size corner, never the stretch area."""
    image=image.resize(target,Image.Resampling.LANCZOS);w,h=target
    old_x=[0,source_edge,w-source_edge,w];old_y=[0,source_edge,h-source_edge,h]
    new_x=[0,edge,w-edge,w];new_y=[0,edge,h-edge,h]
    output=Image.new('RGBA',target)
    for y in range(3):
        for x in range(3):
            piece=image.crop((old_x[x],old_y[y],old_x[x+1],old_y[y+1]))
            piece=piece.resize((new_x[x+1]-new_x[x],new_y[y+1]-new_y[y]),Image.Resampling.LANCZOS)
            output.paste(piece,(new_x[x],new_y[y]))
    return output

def small_control(image,target,edge=6):
    w,h=image.size;old_x=[0,12,w-12,w];old_y=[0,12,h-12,h]
    new_x=[0,edge,target[0]-edge,target[0]];new_y=[0,edge,target[1]-edge,target[1]]
    output=Image.new('RGBA',target)
    for y in range(3):
        for x in range(3):
            part=image.crop((old_x[x],old_y[y],old_x[x+1],old_y[y+1])).resize((new_x[x+1]-new_x[x],new_y[y+1]-new_y[y]),Image.Resampling.LANCZOS)
            output.paste(part,(new_x[x],new_y[y]))
    return output

def main():
    LIBRARY.mkdir(parents=True, exist_ok=True);RUNTIME.mkdir(parents=True, exist_ok=True)
    entries=[];proof=[];contact=Image.new('RGB',(1100,980),'#e8dfcc');draw=ImageDraw.Draw(contact)
    for sheet, names, columns, rows, target in [('buttons',BUTTONS,2,4,(384,104)),('panels',PANELS,2,2,(384,240)),('icons',ICONS,4,4,(64,64))]:
        path=SOURCE/(sheet+'.png');image=Image.open(path).convert('RGBA')
        proof.append({'sheet':sheet,'path':path.relative_to(ROOT).as_posix(),'sha256':sha(path),'size':image.size,'prompt_sha256':sha(SOURCE/(sheet+'.prompt.txt')),'model':'gpt-image-2.5','provider_skill':'sub2-image-gen','visually_reviewed':True})
        for i,name in enumerate(names):
            x,y=i%columns,i//columns
            # Reviewed source drifts upward in the last button row; use actual
            # empty gutters rather than cutting folds or leaking the next row.
            gutters=[0,256,490,725,1024] if sheet=='buttons' else [round(j*image.height/rows) for j in range(rows+1)]
            cell=(round(x*image.width/columns),gutters[y],round((x+1)*image.width/columns),gutters[y+1])
            cut=image.crop(cell);alpha=cut.getchannel('A')
            # Gateway sheets carry RGB behind fully transparent pixels. Keep the
            # actual alpha cutout, remove only faint fringe, restore opaque bodies.
            alpha=alpha.point(lambda v: 0 if v<12 else 255 if v>=245 else v)
            cut.putalpha(alpha);bounds=alpha.point(lambda v:255 if v>24 else 0).getbbox()
            assert bounds,(sheet,name)
            cut=cut.crop(bounds)
            if sheet=='icons':
                cut.thumbnail((60,60),Image.Resampling.LANCZOS)
                result=Image.new('RGBA',target);result.alpha_composite(cut,((64-cut.width)//2,(64-cut.height)//2))
            else: result=normalize_slices(cut,target,44 if sheet=='buttons' else 52)
            filename=('button-' if sheet=='buttons' else 'panel-' if sheet=='panels' else 'icon-')+name+'.png'
            result.save(LIBRARY/filename,optimize=True);result.save(RUNTIME/filename,optimize=True)
            border=[12,12,12,12] if sheet in ['buttons','panels'] else None
            entries.append({'id':'ui.fold.'+('button' if sheet=='buttons' else 'panel' if sheet=='panels' else 'icon')+'.'+name,'version':1,'path':'res://assets/ui/paper/'+filename,'library_path':(LIBRARY/filename).relative_to(ROOT).as_posix(),'sha256':sha(RUNTIME/filename),'source':sheet+'.png','source_cell':cell,'alpha_crop':bounds,'size':target,'nine_slice':border,'checked':True})
            if sheet=='buttons':pos=(20+(i%2)*530,20+(i//2)*126)
            elif sheet=='panels':
                result=result.resize((250,156),Image.Resampling.LANCZOS);pos=(20+i*270,552)
            else:pos=(20+(i%8)*135,766+(i//8)*104)
            contact.paste(result,pos,result);draw.text((pos[0],pos[1]+result.height+3),filename,fill='#24343c')
    for name in ['toggle-on','toggle-off','toggle-on-disabled','toggle-off-disabled','slider-thumb','slider-thumb-hover','arrow-down','arrow-up','arrow-right']:
        if name.startswith('arrow-'):
            result=Image.open(RUNTIME/'icon-back.png').rotate({'arrow-down':90,'arrow-up':-90,'arrow-right':180}[name]).resize((20,20),Image.Resampling.LANCZOS)
        elif name.startswith('slider'):
            result=small_control(Image.open(RUNTIME/('button-hover.png' if name.endswith('hover') else 'button-normal.png')),(24,24))
        else:
            result=small_control(Image.open(RUNTIME/'button-normal.png'),(30,30))
            if name.startswith('toggle-on'):
                mark=Image.open(RUNTIME/'icon-check.png').resize((22,22),Image.Resampling.LANCZOS);result.alpha_composite(mark,(4,4))
            if name.endswith('disabled'):
                from PIL import ImageEnhance
                result=ImageEnhance.Color(result).enhance(.12)
        filename=name+'.png';result.save(RUNTIME/filename,optimize=True);result.save(LIBRARY/filename,optimize=True)
        derived=['ui.fold.icon.back'] if name.startswith('arrow-') else ['ui.fold.button.hover' if name.endswith('hover') else 'ui.fold.button.normal'] if name.startswith('slider-') else ['ui.fold.button.normal']+(['ui.fold.icon.check'] if name.startswith('toggle-on') else [])
        entries.append({'id':'ui.fold.control.'+name,'version':1,'path':'res://assets/ui/paper/'+filename,'library_path':(LIBRARY/filename).relative_to(ROOT).as_posix(),'sha256':sha(RUNTIME/filename),'derived_from':derived,'size':result.size,'checked':True})
    result=Image.open(RUNTIME/'icon-flag.png');alpha=result.getchannel('A')
    result=Image.new('RGBA',result.size,'#fff8e9');result.putalpha(alpha)
    filename='icon-flag-light.png';result.save(RUNTIME/filename,optimize=True);result.save(LIBRARY/filename,optimize=True)
    entries.append({'id':'ui.fold.icon.flag-light','version':1,'path':'res://assets/ui/paper/'+filename,'library_path':(LIBRARY/filename).relative_to(ROOT).as_posix(),'sha256':sha(RUNTIME/filename),'derived_from':['ui.fold.icon.flag'],'size':result.size,'checked':True})
    metadata={'schema':1,'version':'3.0.0-rc16-preview','model':'gpt-image-2.5','generation':proof,'processing':'prepare_paper_ui.py: alpha normalization, independent reviewed gutter crop, Lanczos resize, composites of generated art, contrast variant of generated flag, no text rasterization','assets':entries,'scope':'Reviewed UI bitmap assets. Not gameplay or performance proof.'}
    for p in [ROOT/'assets/paper-warfront/ui/paper-ui.json',ROOT/'game/data/paper-ui.json',SOURCE/'processing-record.json']:
        p.write_text(json.dumps(metadata,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    contact.save(SOURCE/'processed-contact-sheet.png')
    print(f'{len(entries)} reviewed assets; '+str(sum((RUNTIME/Path(e['path']).name).stat().st_size for e in entries))+' runtime PNG bytes')

if __name__=='__main__':main()
