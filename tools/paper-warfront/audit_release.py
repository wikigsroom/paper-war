"""Check final workspace links, geometry, archive CRCs and manifest hashes."""
from pathlib import Path
from urllib.parse import unquote
import json, re, hashlib, zipfile, sys

ROOT = Path(__file__).resolve().parents[2]
QA = ROOT / 'output/qa/godot/v2'
RELEASE = ROOT / 'release/2.0.0'

def main():
    sys.stdout.reconfigure(encoding='utf-8')
    checks = []; errors = []
    def require(name, condition):
        checks.append(dict(name=name, passed=bool(condition)))
        if not condition: errors.append(name)
    maps = json.loads((ROOT / 'game/data/maps.json').read_text(encoding='utf-8'))['maps']
    hashes = []
    for m in maps:
        raw = {k:m[k] for k in ['length', 'nodes', 'edges', 'mines', 'build_sites']}
        digest = hashlib.sha256(json.dumps(raw, sort_keys=True).encode()).hexdigest()
        hashes.append(digest)
        require('raw geometry ' + m['id'], digest == m['geometry_sha256'])
        require('spatial brief ' + m['id'], (ROOT / 'docs/paper-warfront/world/maps' / (m['id'] + '.md')).is_file())
    require('200 independent raw geometries', len(maps) == len(set(hashes)) == 200)
    documents = list((ROOT / 'docs/paper-warfront').rglob('*.md')) + [ROOT/'README.md', ROOT/'release/README.md', RELEASE/'README.md', ROOT/'game/README.md', ROOT/'tools/paper-warfront/README.md', ROOT/'docs/README.md']
    link_count = 0
    for path in documents:
        for match in re.finditer(r'!?\[[^\]]*\]\(([^)]+)\)', path.read_text(encoding='utf-8')):
            target = match.group(1).strip().strip('<>')
            if re.match(r'^[A-Za-z]+://', target) or target.startswith(('#', 'mailto:')): continue
            target = unquote(target.partition('#')[0])
            if not target: continue
            link_count += 1
            require(f'link {path.relative_to(ROOT)} -> {target}', (path.parent/target).resolve().exists())
    manifest = json.loads((RELEASE / 'build-manifest.json').read_text(encoding='utf-8'))
    for entry in manifest['builds'] + manifest.get('archives', []):
        path = ROOT / entry['path']
        require('bytes ' + entry['path'], path.stat().st_size == entry['bytes'])
        require('SHA256 ' + entry['path'], hashlib.sha256(path.read_bytes()).hexdigest() == entry['sha256'])
    archive_counts = {}
    for path in RELEASE.glob('*.zip'):
        with zipfile.ZipFile(path) as z:
            require('archive CRC ' + path.name, z.testzip() is None)
            names = z.namelist(); archive_counts[path.name] = len(names)
            forbidden = ['.keys', '.tools', '.godot', '__pycache__', 'rejected']
            require('excluded credentials and cache ' + path.name, not any(any(part in forbidden for part in name.split('/')) or name.endswith(('.keystore', '.jks', 'export_credentials.cfg')) for name in names))
            if 'Source' in path.name:
                for needed in ['game/project.godot', 'game/scripts/map_runtime.gd', 'game/data/maps.json', 'game/data/factions.json', 'game/data/story.json', 'assets/paper-warfront/world-v2-gallery.html', 'docs/paper-warfront/22-双平台验收与发布.md', 'output/qa/godot/v2/campaign-win-coverage.json']:
                    require('source file ' + needed, 'PaperWarfront-Source/' + needed in names)
            else:
                for needed in ['PaperWarfront.exe', 'Launch-Compatibility.cmd', 'licenses/GODOT-LICENSE.txt', 'licenses/OFL-NotoSansSC.txt']:
                    require('Windows file ' + needed, 'PaperWarfront/' + needed in names)
    for name in ['menu.png', 'battle.png', 'menu-compatibility.png']:
        require('new exported program capture ' + name, (QA/'export'/name).is_file())
    report = dict(passed=not errors, checks=len(checks), local_links=link_count, unique_geometry_hashes=len(set(hashes)), archive_counts=archive_counts, errors=errors, scope='Current documentation links, independently recomputed raw geometry, final executable/archive hashes, ZIP CRCs, required source files and exclusions; not Android hardware verification.')
    (QA/'release-audit.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False))
    if errors: raise SystemExit(1)

if __name__ == '__main__': main()
