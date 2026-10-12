"""Read official fog reference metadata with bounded requests. Native Windows only."""
import concurrent.futures
import json
import hashlib
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'output/qa/godot/fog-render-rc21/research'

def fetch(app):
    url = f'https://store.steampowered.com/api/appdetails?appids={app}&l=english'
    record = {'app': app, 'url': url}
    try:
        with urllib.request.urlopen(url, timeout=12) as response:
            data = json.load(response)[str(app)]['data']
        record['screenshots'] = data['screenshots']
        record['movies'] = data.get('movies', [])
    except Exception as exc:
        record['error'] = str(exc)
    return record

def screenshot(item):
    name, url = item
    record = {'id': name, 'url': url, 'purpose': 'Reference visual analysis only; excluded from game assets and exports'}
    try:
        request = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(request, timeout=12) as response:
            raw = response.read()
        path = OUT / (name + '.jpg')
        path.write_bytes(raw)
        record.update(path=path.relative_to(ROOT).as_posix(), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
    except Exception as exc:
        record['error'] = str(exc)
    return record

if __name__ == '__main__':
    OUT.mkdir(parents=True, exist_ok=True)
    if '--images-only' not in sys.argv:
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            records = list(pool.map(fetch, [63500, 703880]))
        (OUT / 'official-screenshot-index.json').write_text(json.dumps(records, indent=2), encoding='utf-8')
        for record in records:
            print(json.dumps(record))
    images = [
        ('ss2-nintendo-3', 'https://assets.nintendo.com/image/upload/f_jpg/store/software/switch/70010000012980/431a1d4839a148817221ea185ba0878a0ebf8798b06a8aa44401d28c6281f698'),
        ('ss2-nintendo-4', 'https://assets.nintendo.com/image/upload/f_jpg/store/software/switch/70010000012980/a07e02ca8d761d7d88c5f1f1e5cc685900c241268656f5609b14425b8fe90d3f'),
        ('ss2-nintendo-6', 'https://assets.nintendo.com/image/upload/f_jpg/store/software/switch/70010000012980/8fab3e24191010faf90e99de81b275d64d2ab78b9bbebd5bee6a1f59b928439b'),
        ('ss2-nintendo-5', 'https://assets.nintendo.com/image/upload/f_jpg/store/software/switch/70010000012980/5b76cff293660bd27924a9a34031e3aa9d67a330b3e3d6a1fac906acd0f58bc2'),
        ('ss2-nintendo-7', 'https://assets.nintendo.com/image/upload/f_jpg/store/software/switch/70010000012980/807fedd6db7688debe6f0162b3069aeb1135e7b6b6cc53cc3537ca4dec776e6b'),
        ('ss2-nintendo-8', 'https://assets.nintendo.com/image/upload/f_jpg/store/software/switch/70010000012980/0f78a3434e414b4ba6dc422d993cf9fd057d4c72b7d5fb62f6bd1c32c0628da0'),
    ]
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        images = list(pool.map(screenshot, images))
    (OUT / 'reference-visual-index.json').write_text(json.dumps(images, indent=2), encoding='utf-8')
    for record in images:
        print(json.dumps(record))
