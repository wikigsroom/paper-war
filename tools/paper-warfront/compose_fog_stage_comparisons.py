"""Compose labeled pairs from genuine old/new EXE captures, never concept art."""
import hashlib
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
QA = ROOT / 'output/qa/godot/fog-render-rc21'
destination = QA / 'figures'
destination.mkdir(parents=True, exist_ok=True)
font = ImageFont.truetype('C:/Windows/Fonts/msyh.ttc', 18)
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
index = []
for name, before, after in [
    ('fog-before-after', QA / 'before/desktop/04-lower-road-scout.png', QA / 'release/fog-render/desktop/04-lower-road-scout.png'),
    ('map-and-units-before-after', QA / 'stage-before/desktop/paid-battle-20.png', QA / 'release/stage-proportions/desktop/paid-battle-20.png'),
]:
    sheet = Image.new('RGB', (1280, 404), '#e8deca')
    pen = ImageDraw.Draw(sheet)
    for column, (path, label) in enumerate([(before, '本项目旧版 rc20 · 实际 EXE'), (after, '本项目新版 rc21 · 实际 EXE')]):
        with Image.open(path) as picture:
            assert picture.size == (1280, 720)
            sheet.paste(picture.convert('RGB').resize((640, 360), Image.Resampling.LANCZOS), (column * 640, 44))
        pen.text((column * 640 + 14, 11), label, font=font, fill='#343332')
    output = destination / (name + '.png')
    sheet.save(output)
    index.append({'file': output.relative_to(ROOT).as_posix(), 'sha256': sha(output),
                  'sources': [{'file': path.relative_to(ROOT).as_posix(), 'sha256': sha(path)} for path in [before, after]],
                  'scope': 'Labeled actual project EXE screenshots; same map and seeded fixture or ordinary paid time sampling. Not original Swords & Soldiers screenshots or generated art.'})
(destination / 'comparisons.json').write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding='utf-8')
print('Native screenshot comparisons saved:', len(index))
