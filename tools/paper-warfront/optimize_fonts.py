from pathlib import Path
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont
from fontTools import subset
import shutil
ROOT=Path(__file__).resolve().parents[2]
GAME=ROOT/'game'
CACHE=ROOT/'.tools/fonts'
CACHE.mkdir(parents=True,exist_ok=True)
text=''.join(chr(n) for n in range(32,256))+'★☆×≥≤—–·‹›…“”「」一二三四五六七八九十分层纸偶原始整身造型实际动作与战场见运行验收截图三军团素材库'
for f in list((GAME/'scripts').glob('*.gd'))+list((GAME/'data').glob('*.json')):
    text+=f.read_text(encoding='utf-8')
for family,weight,rename in [('NotoSansSC',600,'PaperWarfront Text'),('NotoSerifSC',600,'PaperWarfront Title')]:
    src=GAME/'assets/fonts'/f'{family}.ttf'
    original=CACHE/f'{family}.full.ttf'
    if not original.exists():
        shipped=ROOT/'assets/paper-warfront/fonts/source'/f'{family}.full.ttf'
        if not shipped.exists():raise FileNotFoundError('Full licensed source font required: '+str(shipped))
        shutil.copy2(shipped,original)
    font=TTFont(original)
    if 'fvar' in font:font=instantiateVariableFont(font,{'wght':weight},inplace=True)
    opts=subset.Options(); opts.layout_features=['*']; opts.notdef_glyph=True;opts.notdef_outline=True
    worker=subset.Subsetter(options=opts);worker.populate(text=text);worker.subset(font)
    for record in font['name'].names:
        if record.nameID in [1,4,6,16]:
            name=rename.replace(' ','') if record.nameID==6 else rename
            record.string=name.encode(record.getEncoding(),errors='replace')
    font.save(src)
    print(f'{family}: {src.stat().st_size:,} bytes, {len(font.getBestCmap())} glyphs, weight {weight}')
