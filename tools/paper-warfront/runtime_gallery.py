"""A local reference library of the files actually bound in Godot."""
from pathlib import Path
import json,html,os
from PIL import Image,ImageDraw,ImageFont

ROOT=Path(__file__).resolve().parents[2];GAME=ROOT/'game';SOURCE=ROOT/'assets/paper-warfront'

def main():
    assets=json.loads((GAME/'data/assets.json').read_text(encoding='utf-8'))['assets']
    records={r['id']:r for r in json.loads((SOURCE/'library-manifest.json').read_text(encoding='utf-8'))['assets']}
    cards=[]
    for asset_id,a in assets.items():
        path=a['path'].removeprefix('res://assets/')
        escaped=html.escape(path,quote=True)
        preview=f'<audio controls preload="none" src="{escaped}"></audio>' if path.endswith('.wav') else f'<img loading="lazy" src="{escaped}" alt="{html.escape(records[asset_id]["name"])}">'
        parts=''
        if 'animation' in a:
            parts='<details><summary>Godot纸偶分件</summary><div class="parts">'+''.join(f'<figure><img loading="lazy" src="{html.escape(p.removeprefix("res://assets/"),quote=True)}"><figcaption>{html.escape(label)}</figcaption></figure>' for label,p in a['animation']['parts'].items())+'</div></details>'
        if 'portrait' in a:parts+=f'<details><summary>运行头像</summary><img width="96" src="{html.escape(a["portrait"].removeprefix("res://assets/"),quote=True)}"></details>'
        cards.append(f'<article data-search="{html.escape(asset_id+" "+records[asset_id]["name"]+" "+a["category"],quote=True)}" data-category="{html.escape(a["category"],quote=True)}"><div class="preview">{preview}</div><h2>{html.escape(records[asset_id]["name"])}</h2><code>{html.escape(asset_id)}</code><p>{html.escape(a["category"])} · 已绑定运行资源</p>{parts}</article>')
    categories=sorted({a['category'] for a in assets.values()})
    document='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>纸上兵戈 · Godot运行素材</title><style>
*{box-sizing:border-box}body{margin:0;background:#e8deca;color:#343332;font:16px/1.7 "Microsoft YaHei",sans-serif}header{padding:36px 6vw;border-bottom:2px solid #baa994}h1{font-size:36px;margin:0;color:#b74532}header p{max-width:1000px}input,select{background:#f3ebdd;border:1px solid #baa994;padding:12px;font:inherit;border-radius:3px;margin:8px 10px 0 0}main{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:22px;padding:28px 6vw}article{padding:18px;background:#f3ebdd;border:1px solid #baa994;border-radius:4px;min-width:0}article h2{font-size:22px;margin:14px 0 0}code{font-size:13px;word-break:break-all}article p{font-size:13px;color:#746d61}.preview{height:210px;background:repeating-conic-gradient(#e5dac5 0% 25%,#e8deca 0% 50%) 50%/24px 24px;display:flex;align-items:center;justify-content:center}.preview img{max-width:100%;max-height:210px;object-fit:contain}audio{width:100%}summary{cursor:pointer;color:#377b78}.parts{display:flex;flex-wrap:wrap}.parts figure{margin:4px;width:100px;font-size:11px}.parts img{width:100px}article[hidden]{display:none}footer{padding:25px 6vw;color:#746d61}
</style><header><h1>纸上兵戈 · 运行素材库</h1><p>116个稳定资产ID。查看Godot实际使用的切图、头部头像、53张分件、图标和正式40秒音乐。此页用于素材查阅；动作、命中和设备验收以Godot运行与报告为准。</p><input id="search" placeholder="搜索名称、ID、分类"><select id="category"><option value="">全部分类</option>OPTIONS</select><span id="count"></span></header><main>CARDS</main><footer>原始生成与加工记录：assets/paper-warfront/library-manifest.json；Godot绑定：game/data/assets.json；规则与运行证据：docs/paper-warfront。</footer><script>
const cards=[...document.querySelectorAll('article')],search=document.getElementById('search'),category=document.getElementById('category');function filter(){const q=search.value.trim().toLowerCase();let n=0;for(const c of cards){c.hidden=!(c.dataset.search.toLowerCase().includes(q)&&(!category.value||c.dataset.category===category.value));if(!c.hidden)n++;}document.getElementById('count').textContent=`显示 ${n} / ${cards.length}`;}search.addEventListener('input',filter);category.addEventListener('change',filter);filter();
</script></html>'''
    document=document.replace('OPTIONS',''.join(f'<option>{html.escape(c)}</option>' for c in categories)).replace('CARDS',''.join(cards))
    (GAME/'assets/runtime-gallery.html').write_text(document,encoding='utf-8')
    # Static visual contact sheet uses only the runtime portraits and transparent cuts.
    canvas=Image.new('RGB',(1500,1250),'#e8deca');draw=ImageDraw.Draw(canvas)
    font=ImageFont.truetype(str(GAME/'assets/fonts/NotoSansSC.ttf'),23)
    title=ImageFont.truetype(str(GAME/'assets/fonts/NotoSerifSC.ttf'),40)
    draw.text((38,22),'纸上兵戈 · Godot纸偶与素材',font=title,fill='#b74532')
    ids=[k for k in assets if k.startswith('unit.')]
    for i,asset_id in enumerate(ids):
        x=30+(i%6)*245;y=103+(i//6)*330
        draw.rounded_rectangle((x,y,x+230,y+309),5,fill='#f3ebdd',outline='#baa994',width=2)
        im=Image.open(GAME/assets[asset_id]['path'].removeprefix('res://')).convert('RGBA')
        im=im.crop(im.getchannel('A').getbbox());im.thumbnail((210,230),Image.Resampling.LANCZOS)
        canvas.paste(im,(x+(230-im.width)//2,y+246-im.height),im)
        draw.text((x+12,y+260),records[asset_id]['name'],font=font,fill='#343332')
    draw.text((38,1131),'分层纸偶 / 53张分件 / 17单位 / 3军团',font=font,fill='#343332')
    draw.text((38,1176),'原始整身造型 · 实际动作与战场见运行验收截图',font=font,fill='#746d61')
    out=SOURCE/'previews/godot-runtime-library.png';canvas.save(out)
    print('Runtime asset gallery and contact sheet written.')

if __name__=='__main__':main()
