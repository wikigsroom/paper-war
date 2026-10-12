"""Label genuine rc21/rc22 EXE captures with their exact source provenance."""
import hashlib
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
QA = ROOT / 'output/qa/godot/observer-camera-rc22'
out = QA / 'figures'
out.mkdir(parents=True, exist_ok=True)
font = ImageFont.truetype('C:/Windows/Fonts/msyh.ttc', 18)
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
index = []
for name, shot in [('opening-before-after', '01-opening.png'), ('own-front-before-after', '02-west-paid-march.png')]:
    sources = [QA / 'render-before/desktop' / shot, QA / 'release/camera-render/desktop' / shot]
    sheet = Image.new('RGB', (1280, 404), '#e8deca')
    pen = ImageDraw.Draw(sheet)
    for column, (source, label) in enumerate(zip(sources, ['本项目 rc21 · 实际 EXE', '本项目 rc22 · 实际 EXE'])):
        with Image.open(source) as picture:
            assert picture.size == (1280, 720)
            sheet.paste(picture.convert('RGB').resize((640, 360), Image.Resampling.LANCZOS), (column * 640, 44))
        pen.text((column * 640 + 14, 11), label, font=font, fill='#343332')
    path = out / (name + '.png')
    sheet.save(path)
    index.append({'file': path.relative_to(ROOT).as_posix(), 'sha256': sha(path),
                  'sources': [{'file': p.relative_to(ROOT).as_posix(), 'sha256': sha(p)} for p in sources],
                  'scope': 'Same authored map and paid recruitment/seed/timing through the same native observer, actual project EXE packs. Not original game captures or generated concept art.'})
(out / 'comparisons.json').write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding='utf-8')
print('Native camera comparisons saved:', len(index))
