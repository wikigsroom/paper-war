"""Rebuild licensed CJK subsets and record mobile glyph coverage."""
from pathlib import Path
import json,hashlib,runpy,sys,os
from fontTools.ttLib import TTFont

ROOT=Path(__file__).resolve().parents[2]
QA=ROOT/os.environ.get('PAPER_QA_DIR','output/qa/godot/frame-rebuild')
FONT=ROOT/'game/assets/fonts'

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    sys.stdout.reconfigure(encoding='utf-8')
    QA.mkdir(parents=True,exist_ok=True)
    sources=[*sorted((ROOT/'game/scripts').glob('*.gd')),*sorted((ROOT/'game/data').glob('*.json'))]
    required={ch for path in sources for ch in path.read_text(encoding='utf-8') if 0x3400<=ord(ch)<=0x9fff}
    before={}
    for family in ['NotoSansSC','NotoSerifSC']:
        path=FONT/f'{family}.ttf';cmap=TTFont(path).getBestCmap()
        before[family]={'sha256':sha(path),'missing_cjk':sorted(ch for ch in required if ord(ch) not in cmap)}
    runpy.run_path(str(ROOT/'tools/paper-warfront/optimize_fonts.py'),run_name='__main__')
    records=[]
    for family,id in [('NotoSansSC','font.paper.text'),('NotoSerifSC','font.paper.title')]:
        path=FONT/f'{family}.ttf';cmap=TTFont(path).getBestCmap()
        missing=sorted(ch for ch in required if ord(ch) not in cmap);assert not missing,(family,missing)
        source=ROOT/f'assets/paper-warfront/fonts/source/{family}.full.ttf'
        assert sha(source)==sha(ROOT/f'.tools/fonts/{family}.full.ttf')
        records.append({'id':id,'source':source.relative_to(ROOT).as_posix(),'source_sha256':sha(source),'license':f'assets/paper-warfront/fonts/source/OFL-{family}.txt','path':path.relative_to(ROOT).as_posix(),'sha256':sha(path),'before_sha256':before[family]['sha256'],'missing_before':before[family]['missing_cjk'],'missing_after':missing,'glyphs':len(cmap),'bytes':path.stat().st_size,'processing':'Existing SIL OFL font, weight600; subset from current game scripts/data; PaperWarfront reserved-name substitution. No image generation.'})
    report={'version':os.environ.get('PAPER_RELEASE_VERSION','3.0.0-rc5'),'passed':True,'required_cjk':len(required),'scope':'Direct bundled-font cmap checks, independent of Windows/Android system fallback. Current game script/data CJK glyphs only.','records':records}
    text=json.dumps(report,ensure_ascii=False,indent=2)+'\n'
    (QA/'font-coverage.json').write_text(text,encoding='utf-8')
    (ROOT/'game/data/mobile-font-provenance.json').write_text(text,encoding='utf-8')
    print('Bundled font coverage passed:',len(required),'CJK characters, two subsets')

if __name__=='__main__':main()
