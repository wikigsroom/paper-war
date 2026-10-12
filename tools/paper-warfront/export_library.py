"""Export transparent assets, paper textures, prototype SFX, and an offline gallery."""
from pathlib import Path
import hashlib
import html
import json
import math
import random
import struct
import sys
import wave
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

ROOT=Path(__file__).resolve().parents[2]
LIB=ROOT/"assets/paper-warfront"


def write_json(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")


def font(size):
    for path in (Path(r"C:\Windows\Fonts\msyh.ttc"),Path(r"C:\Windows\Fonts\simhei.ttf")):
        if path.exists():
            return ImageFont.truetype(str(path),size)
    return ImageFont.load_default()


def clean_alpha(image):
    image=image.convert("RGBA")
    alpha=image.getchannel("A")
    low,high=alpha.getextrema()
    if low<32:
        image.putalpha(alpha.point(lambda value:0 if value<8 else min(255,round(value*255/max(high,1)))))
        return image,"native-alpha"
    # Only use chroma if the source actually contains an obvious magenta background.
    pixels=list(image.getdata())
    keyed=sum(1 for r,g,b,a in pixels if r>190 and b>190 and g<110)
    if keyed<len(pixels)*.08:
        raise ValueError("No trustworthy alpha or magenta background; regenerate instead of removing paper colors.")
    image.putdata([(r,g,b,0 if r>190 and b>190 and g<110 else a) for r,g,b,a in pixels])
    return image,"magenta-key"


def centered(image,size,baseline=False):
    bbox=image.getchannel("A").point(lambda value:255 if value>=24 else 0).getbbox()
    if not bbox:
        raise ValueError("Empty asset cell")
    crop=image.crop(bbox)
    limit_w=size*.875
    limit_h=size*.84375 if baseline else size*.80
    scale=min(limit_w/crop.width,limit_h/crop.height)
    resized=crop.resize((max(1,round(crop.width*scale)),max(1,round(crop.height*scale))),Image.Resampling.LANCZOS)
    canvas=Image.new("RGBA",(size,size),(0,0,0,0))
    x=(size-resized.width)//2
    y=round(size*.9296875)-resized.height if baseline else (size-resized.height)//2
    canvas.alpha_composite(resized,(x,y))
    return canvas,{"source_content_box":list(bbox),"scale":scale,"content_box":[x,y,x+resized.width,y+resized.height],"anchor":[size//2,round(size*.9296875)] if baseline else [size//2,size//2]}


def components(image):
    width,height=image.size
    data=bytearray(image.getchannel("A").point(lambda value:255 if value>=24 else 0).tobytes())
    found=[]
    for start in range(len(data)):
        if not data[start]:
            continue
        data[start]=0
        stack=[start]
        points=[]
        min_x,max_x,min_y,max_y=width,0,height,0
        while stack:
            point=stack.pop()
            points.append(point)
            x=point%width
            y=point//width
            min_x,min_y=min(min_x,x),min(min_y,y)
            max_x,max_y=max(max_x,x),max(max_y,y)
            for dy in (-1,0,1):
                ny=y+dy
                if ny<0 or ny>=height:
                    continue
                for dx in (-1,0,1):
                    nx=x+dx
                    if (dx==0 and dy==0) or nx<0 or nx>=width:
                        continue
                    neighbor=ny*width+nx
                    if data[neighbor]:
                        data[neighbor]=0
                        stack.append(neighbor)
        found.append({"area":len(points),"box":[min_x,min_y,max_x+1,max_y+1],"points":points})
    return found


def component_mask(image,selected):
    mask=bytearray(image.width*image.height)
    for component in selected:
        for point in component["points"]:
            mask[point]=255
    keep=Image.frombytes("L",image.size,bytes(mask)).filter(ImageFilter.MaxFilter(5))
    result=image.copy()
    result.putalpha(ImageChops.multiply(image.getchannel("A"),keep))
    return result


def extract_character(image,parts,column,row,cols,rows):
    center_x=(column+.5)*image.width/cols
    center_y=(row+.5)*image.height/rows
    candidates=[p for p in parts if p["area"]>=1000]
    if not candidates:
        raise ValueError("No character silhouette found")
    def score(part):
        left,top,right,bottom=part["box"]
        dx=((left+right)/2-center_x)/(image.width/cols)
        dy=((top+bottom)/2-center_y)/(image.height/rows)
        return (dx*dx+dy*dy)-min(part["area"]/100000,.8)*.06
    primary=min(candidates,key=score)
    left,top,right,bottom=primary["box"]
    selected=[primary]
    for part in parts:
        if part is primary or part["area"]<primary["area"]*.008:
            continue
        pl,pt,pr,pb=part["box"]
        cx,cy=(pl+pr)/2,(pt+pb)/2
        if left<=cx<=right and top<=cy<=bottom:
            selected.append(part)
    isolated=component_mask(image,selected)
    box=isolated.getchannel("A").getbbox()
    return isolated.crop(box),list(box),{"subject_components":len(selected),"removed_components":len(parts)-len(selected),"method":"whole-source-connected-silhouette"}


def remove_tiny_noise(image):
    parts=components(image)
    if not parts:
        return image,0
    minimum=max(8,max(p["area"] for p in parts)*.002)
    largest=max(p["area"] for p in parts)
    def keep(part):
        left,top,right,bottom=part["box"]
        at_edge=left<=1 or top<=1 or right>=image.width-1 or bottom>=image.height-1
        return part["area"]>=minimum and not (at_edge and part["area"]<largest*.30)
    selected=[p for p in parts if keep(p)]
    return component_mask(image,selected),len(parts)-len(selected)


def make_portrait(image):
    bbox=image.getchannel("A").point(lambda value:255 if value>=24 else 0).getbbox()
    crop=image.crop(bbox)
    upper=crop.crop((0,0,crop.width,max(1,round(crop.height*.55))))
    return centered(upper,192)[0]


def synth_audio(record,path):
    rate=44100
    duration=record["duration"]
    count=round(rate*duration)
    rng=random.Random(int(hashlib.sha256(record["id"].encode()).hexdigest()[:12],16))
    kind=record["kind"]
    if kind=="music":
        return synth_music(record,path)
    values=[]
    smooth=0
    last_noise=0
    for i in range(count):
        t=i/rate
        noise=rng.uniform(-1,1)
        smooth=.89*smooth+.11*noise
        hiss=noise-last_noise
        last_noise=noise
        fade=min(1,t/.004)*min(1,(duration-t)/.045)
        decay=math.exp(-t/(duration*.29))
        if kind in ("paper","tap","whoosh"):
            swell=math.sin(math.pi*min(1,t/duration)) if kind=="whoosh" else decay
            value=(hiss*.28+smooth*.32)*swell
            if kind=="tap":
                value+=math.sin(2*math.pi*1700*t)*decay*.08
        elif kind in ("wood","stamp","boom"):
            freq={"wood":240,"stamp":115,"boom":65}[kind]
            value=(math.sin(2*math.pi*(freq*t+24*t*math.exp(-t*15)))*.48+smooth*.55+hiss*.07)*decay
        elif kind in ("chime","victory","defeat","warning"):
            base={"chime":740,"victory":523.25,"defeat":392,"warning":440}[kind]
            tones=[1,1.25,1.5] if kind=="victory" else ([1,.8,.667] if kind=="defeat" else [1,2.01])
            value=sum(math.sin(2*math.pi*base*f*t)*.25/(j+1) for j,f in enumerate(tones))*decay
            if kind=="warning":
                value*=.5+.5*math.sin(2*math.pi*6*t)**2
        else:
            value=(smooth*.8+math.sin(2*math.pi*(125*t+15*t*t))*.22)*math.sin(math.pi*t/duration)*decay
        values.append(value*fade)
    peak=max(abs(v) for v in values) or 1
    samples=[max(-32767,min(32767,round(v/peak*.55*32767))) for v in values]
    path.parent.mkdir(parents=True,exist_ok=True)
    with wave.open(str(path),"wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(rate)
        output.writeframes(struct.pack("<"+"h"*len(samples),*samples))
    return {"sample_rate":rate,"channels":1,"bits":16,"frames":count,"duration":count/rate,"peak":max(abs(s) for s in samples)/32767,"method":"deterministic procedural prototype; listening and in-game mix review pending"}


def synth_music(record,path):
    rate=44100
    duration=record["duration"]
    count=round(rate*duration)
    mood=record["mood"]
    scales={"yin":[0,4,7,9,7,4,2,7],"mo":[0,3,7,10,7,3,2,0],"deng":[0,2,7,9,12,9,7,2]}
    base={"yin":196,"mo":146.83,"deng":220}[mood]
    values=[]
    for i in range(count):
        t=i/rate
        step=int(t/.625)
        local=t% .625
        note=base*2**(scales[mood][step%8]/12)
        pluck=(math.sin(2*math.pi*note*t)+.3*math.sin(2*math.pi*note*2*t))*math.exp(-local*9)*.22
        low=math.sin(2*math.pi*(base/2)*t)*math.exp(-local*12)*(.15 if step%2==0 else .05)
        tick=math.sin(2*math.pi*(930+step%3*120)*local)*math.exp(-local*70)*.08
        fade=min(1,t/.015,(duration-t)/.055)
        values.append((pluck+low+tick)*max(0,fade))
    peak=max(abs(v) for v in values)
    samples=[round(v/peak*.35*32767) for v in values]
    path.parent.mkdir(parents=True,exist_ok=True)
    with wave.open(str(path),"wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(rate)
        output.writeframes(struct.pack("<"+"h"*len(samples),*samples))
    return {"sample_rate":rate,"channels":1,"bits":16,"frames":count,"duration":count/rate,"peak":max(abs(s) for s in samples)/32767,"tempo_bpm":96,"method":"procedural rhythm/harmony sketch, not mastered final music; listening review pending"}


def contact_sheet(records,destination,columns=6,cell_w=248,cell_h=272):
    rows=math.ceil(len(records)/columns)
    board=Image.new("RGB",(columns*cell_w,rows*cell_h),"#E8DECA")
    draw=ImageDraw.Draw(board)
    title_font=font(17)
    small_font=font(12)
    for index,record in enumerate(records):
        x=(index%columns)*cell_w
        y=(index//columns)*cell_h
        draw.rectangle((x+6,y+6,x+cell_w-6,y+cell_h-6),fill="#F3EBDD",outline="#BAAA94",width=1)
        path=ROOT/record["asset_path"]
        im=Image.open(path).convert("RGBA")
        im.thumbnail((cell_w-28,cell_h-74),Image.Resampling.LANCZOS)
        board.paste(im,(x+(cell_w-im.width)//2,y+10+(cell_h-74-im.height)//2),im)
        draw.text((x+14,y+cell_h-54),record["name"],font=title_font,fill="#343332")
        draw.text((x+14,y+cell_h-28),record["id"],font=small_font,fill="#746D61")
    destination.parent.mkdir(parents=True,exist_ok=True)
    board.save(destination)


def make_gallery(records,jobs):
    gallery_records=[]
    for record in records:
        item={key:record.get(key,"") for key in ("id","name","category","faction","status","usage")}
        item["path"]=str((ROOT/record["asset_path"]).relative_to(LIB)).replace("\\","/")
        if record.get("portrait_path"):
            item["portrait"]=str((ROOT/record["portrait_path"]).relative_to(LIB)).replace("\\","/")
        gallery_records.append(item)
    data=json.dumps(gallery_records,ensure_ascii=False).replace("<","\\u003c")
    template='''<!doctype html>
<html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>纸上兵戈 · 素材库</title>
<style>
:root{--paper:#e8deca;--ink:#343332;--red:#b74532;--line:#baaa94}*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font:15px/1.6 "Microsoft YaHei",sans-serif}main{max-width:1440px;margin:auto;padding:32px}header{border-bottom:2px solid var(--ink);padding-bottom:18px;display:flex;align-items:end;justify-content:space-between;gap:24px}h1{font:44px/1.1 KaiTi,serif;margin:0}h1 span{display:block;font:13px/2 monospace;letter-spacing:2px;color:var(--red)}p{margin:12px 0 0;color:#746d61}.tools{display:flex;gap:10px;flex-wrap:wrap;padding:22px 0;position:sticky;top:0;background:var(--paper);z-index:1;border-bottom:1px solid var(--line)}input,select,button{font:inherit;color:inherit;background:#f3ebdd;border:1px solid var(--line);padding:10px 12px;border-radius:2px}input{min-width:240px;flex:1}button{cursor:pointer}button[aria-pressed=true]{background:var(--ink);color:#f3ebdd}.count{font:12px monospace;padding:14px 0;color:#746d61}.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(218px,1fr));gap:14px}article{border:1px solid var(--line);background:#f3ebdd;display:flex;flex-direction:column}article[data-faction=yin]{border-top:3px solid #b74532}article[data-faction=mo]{border-top:3px solid #343332}article[data-faction=deng]{border-top:3px solid #377b78}.image{height:210px;padding:14px;display:grid;place-items:center;background-color:#ece6da;background-image:linear-gradient(45deg,#d8d1c3 25%,transparent 25%),linear-gradient(-45deg,#d8d1c3 25%,transparent 25%),linear-gradient(45deg,transparent 75%,#d8d1c3 75%),linear-gradient(-45deg,transparent 75%,#d8d1c3 75%);background-size:20px 20px;background-position:0 0,0 10px,10px -10px,-10px 0}.image img{max-width:100%;max-height:184px;object-fit:contain}.info{padding:12px 14px}.info strong{font-size:17px}.id{display:block;font:11px/1.8 monospace;overflow-wrap:anywhere;color:#746d61}.meta{font-size:11px;color:#746d61;margin-top:6px}a{color:var(--red)}audio{width:100%;height:40px}.audio{height:210px;display:grid;align-content:center;padding:14px;gap:14px}.empty{padding:44px 0;color:#746d61}@media(max-width:650px){main{padding:18px}header{display:block}h1{font-size:36px}.tools{position:static}.grid{grid-template-columns:repeat(2,minmax(0,1fr))}.image{height:170px}.image img{max-height:148px}.info{padding:10px}input{min-width:100%}}@media(prefers-reduced-motion:reduce){*{scroll-behavior:auto}}
</style>
<main><header><div><h1><span>PAPER WARFRONT / ASSET LIBRARY 0.1</span>纸上兵戈 · 素材库</h1><p>三阵营资源、纸材、法术、场景与原型声音。静态素材检查与游戏内验收分别记录。</p></div><a href="../../docs/paper-warfront/README.md">制作资料入口 ↗</a></header>
<div class="tools"><input id="search" aria-label="搜索素材" placeholder="搜索名称或素材 ID"><select id="faction" aria-label="阵营"><option value="all">全部阵营</option><option value="yin">印甲军</option><option value="mo">墨骸社</option><option value="deng">灯符朝</option><option value="common">公共</option></select><select id="category" aria-label="类别"><option value="all">全部类别</option></select><button id="portraits" aria-pressed="false">人物显示头像</button></div><div id="count" class="count"></div><div id="grid" class="grid"></div></main>
<script>
const assets=__DATA__;
const labels={unit:'人物',portrait:'统帅',spell:'法术',building:'建筑',resource:'资源点',texture:'纸材',prop:'道具',fx:'特效母题',background:'背景',audio:'声音'};
const grid=document.querySelector('#grid'),search=document.querySelector('#search'),faction=document.querySelector('#faction'),category=document.querySelector('#category'),portraits=document.querySelector('#portraits');
for(const key of Object.keys(labels)){const option=document.createElement('option');option.value=key;option.textContent=labels[key];category.append(option)}
function render(){grid.replaceChildren();const query=search.value.trim().toLowerCase();const filtered=assets.filter(a=>(faction.value==='all'||a.faction===faction.value)&&(category.value==='all'||a.category===category.value)&&(!query||(a.name+' '+a.id).toLowerCase().includes(query)));document.querySelector('#count').textContent=`${filtered.length} / ${assets.length} 项 · 图像为导出候选，运行验证另行记录`;
for(const a of filtered){const card=document.createElement('article');card.dataset.faction=a.faction;const frame=document.createElement('div');frame.className=a.category==='audio'?'audio':'image';if(a.category==='audio'){const text=document.createElement('span');text.textContent='折纸 / 印刷 / 原型事件声音';frame.append(text);const sound=document.createElement('audio');sound.controls=true;sound.preload='none';sound.src=a.path;frame.append(sound)}else{const img=document.createElement('img');img.loading='lazy';img.alt=a.name;img.src=portraits.getAttribute('aria-pressed')==='true'&&a.portrait?a.portrait:a.path;frame.append(img)}const info=document.createElement('div');info.className='info';const name=document.createElement('strong');name.textContent=a.name;const id=document.createElement('span');id.className='id';id.textContent=a.id;const meta=document.createElement('div');meta.className='meta';meta.textContent=(labels[a.category]||a.category)+' · '+a.status;const link=document.createElement('a');link.href=a.path;link.textContent='打开文件';link.setAttribute('target','_blank');link.setAttribute('rel','noopener');info.append(name,id,meta,link);card.append(frame,info);grid.append(card)}if(!filtered.length){const empty=document.createElement('div');empty.className='empty';empty.textContent='没有匹配素材';grid.append(empty)}}
search.addEventListener('input',render);faction.addEventListener('change',render);category.addEventListener('change',render);portraits.addEventListener('click',()=>{portraits.setAttribute('aria-pressed',portraits.getAttribute('aria-pressed')==='true'?'false':'true');render()});render();
</script></html>'''
    (LIB/"gallery.html").write_text(template.replace("__DATA__",data),encoding="utf-8")


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    plan=json.loads((ROOT/"output/imagegen/paper-warfront/jobs.json").read_text(encoding="utf-8"))
    registry=json.loads((LIB/"library-manifest.json").read_text(encoding="utf-8"))
    records={r["id"]:r for r in registry["assets"]}
    source_info=[]
    for job in plan["jobs"]:
        source=ROOT/job["source_path"]
        with Image.open(source) as source_image:
            source_image.load()
            image=source_image.convert("RGBA")
        source_info.append({"id":job["id"],"path":job["source_path"],"width":image.width,"height":image.height,"bytes":source.stat().st_size,"sha256":hashlib.sha256(source.read_bytes()).hexdigest()})
        cols,rows=job["grid"]
        whole_char=None
        char_parts=None
        if job["kind"]=="characters":
            whole_char,_=clean_alpha(image)
            char_parts=components(whole_char)
        for index,asset_id in enumerate(job["asset_ids"]):
            record=records[asset_id]
            column=index%cols
            row=index//cols
            box=(round(column*image.width/cols),round(row*image.height/rows),round((column+1)*image.width/cols),round((row+1)*image.height/rows))
            cell=image.crop(box)
            category=record["category"]
            path=ROOT/record["asset_path"]
            path.parent.mkdir(parents=True,exist_ok=True)
            cleanup={}
            if category in ("texture","background"):
                if category=="background":
                    opaque=Image.new("RGBA",cell.size,"#E8DECA")
                    opaque.alpha_composite(cell)
                    output=opaque.convert("RGB")
                else:
                    output=cell.convert("RGB")
                if category=="texture":
                    output=output.resize((512,512),Image.Resampling.LANCZOS)
                method="opaque-surface"
                placement={"anchor":[0,0],"content_box":[0,0,output.width,output.height]}
            else:
                if job["kind"]=="characters":
                    cell,box,cleanup=extract_character(whole_char,char_parts,column,row,cols,rows)
                    method="native-alpha"
                else:
                    cell,method=clean_alpha(cell)
                    cell,removed=remove_tiny_noise(cell)
                    cleanup={"removed_tiny_components":removed}
                size=192 if category in ("spell","ui") else (256 if category=="fx" else 512)
                output,placement=centered(cell,size,baseline=category in ("unit","portrait","building","resource","prop"))
                if record.get("portrait_path"):
                    portrait=ROOT/record["portrait_path"]
                    portrait.parent.mkdir(parents=True,exist_ok=True)
                    make_portrait(cell).save(portrait,optimize=True)
            output.save(path,optimize=True)
            record["status"]="derived-candidate"
            record["export_info"]={"width":output.width,"height":output.height,"mode":output.mode,"source_crop":list(box),"alpha_method":method,"cleanup":cleanup,"bytes":path.stat().st_size,"sha256":hashlib.sha256(path.read_bytes()).hexdigest(),**placement}
            edge_alpha=cell.convert("RGBA").getchannel("A")
            content=edge_alpha.point(lambda value:255 if value>=24 else 0).getbbox()
            border_touch=bool(category not in ("texture","background") and job["kind"]!="characters" and content and (content[0]<=1 or content[1]<=1 or content[2]>=cell.width-1 or content[3]>=cell.height-1))
            record["qa"]={"decoded":True,"cell_border_touch":border_touch,"visual_review":"pending","runtime_review":"pending"}
            print(asset_id+": exported"+("; check source-cell boundary" if border_touch else ""))
    for record in records.values():
        if record["category"]=="audio":
            path=ROOT/record["asset_path"]
            record["audio_info"]=synth_audio(record,path)
            record["status"]="derived-candidate"
            record["qa"]={"format_review":"checked","listening_review":"pending","runtime_review":"pending"}
    write_json(LIB/"library-manifest.json",registry)
    write_json(ROOT/"output/imagegen/paper-warfront/source-manifest.json",{"model":"gpt-image-2.5","quality":"high","sources":source_info})
    runtime={"version":"0.1.0","stage":"exported-candidates","assets":{r["id"]:{"path":r["asset_path"],"category":r["category"],"usage":r["usage"],"status":r["status"],**({"world_height":r["height"],"portrait":r["portrait_path"]} if r.get("portrait_path") else {}),**({"rig":r["rig_path"]} if r.get("rig_path") else {})} for r in records.values()}}
    write_json(LIB/"runtime-manifest.json",runtime)
    pictures=[r for r in records.values() if r["category"]!="audio"]
    contact_sheet([r for r in pictures if r["category"] in ("unit","portrait")],LIB/"previews/characters.png")
    contact_sheet([r for r in pictures if r["category"] in ("spell","ui")],LIB/"previews/icons.png")
    contact_sheet([r for r in pictures if r["category"] in ("building","resource","prop")],LIB/"previews/environment.png")
    contact_sheet([r for r in pictures if r["category"] in ("texture","fx","background")],LIB/"previews/materials-fx-backgrounds.png")
    make_gallery(list(records.values()),plan["jobs"])
    print(f"Exported {len(pictures)} images + {sum(bool(r.get('portrait_path')) for r in pictures)} portraits + {sum(r['category']=='audio' for r in records.values())} prototype WAV files; offline gallery and inspection sheets saved.")


if __name__=="__main__":
    main()
