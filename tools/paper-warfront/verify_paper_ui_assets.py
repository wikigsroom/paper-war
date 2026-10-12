"""Check actual APK imported UI textures against reviewed source and library."""
from pathlib import Path
import argparse, json, zipfile, hashlib
from PIL import Image
ROOT=Path(__file__).resolve().parents[2]
def sha(data):return hashlib.sha256(data).hexdigest()
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--version',default='3.0.0-rc16-preview');ap.add_argument('--qa',type=Path,default=ROOT/'output/qa/godot/ui-rc16/release');args=ap.parse_args()
    apk=ROOT/f'release/{args.version}/android/PaperWarfront-{args.version}.apk'
    metadata_bytes=(ROOT/'game/data/paper-ui.json').read_bytes()
    meta=json.loads(metadata_bytes)
    assert meta['model']=='gpt-image-2.5'
    assert metadata_bytes==(ROOT/'assets/paper-warfront/ui/paper-ui.json').read_bytes()
    # Artwork keeps its generation revision when a later game release reuses
    # it. Bind the requested application to its actual build and APK metadata.
    build=json.loads((ROOT/f'release/{args.version}/build-manifest.json').read_text('utf-8'))
    assert build['version']==args.version
    apk_hash=sha(apk.read_bytes())
    assert any(row['path']==apk.relative_to(ROOT).as_posix() and row['sha256']==apk_hash for row in build['builds'])
    report={'model':meta['model'],'version':args.version,'asset_library_version':meta['version'],'apk_sha256':apk_hash,'assets':[],'passed':True};pixels=0
    with zipfile.ZipFile(apk) as z:
        assert z.read('assets/data/paper-ui.json')==metadata_bytes
        for entry in meta['assets']:
            path=ROOT/'game'/entry['path'].removeprefix('res://');image=Image.open(path).convert('RGBA');pixels+=image.width*image.height
            source_ok=sha(path.read_bytes())==entry['sha256']
            names=[n for n in z.namelist() if n.startswith('assets/.godot/imported/'+path.name+'-') and n.endswith('.ctex')]
            assert len(names)==1,(path.name,names)
            imported=ROOT/'game'/names[0].removeprefix('assets/')
            pack_ok=sha(z.read(names[0]))==sha(imported.read_bytes())
            library_ok=path.read_bytes()==(ROOT/entry['library_path']).read_bytes()
            report['assets'].append({'id':entry['id'],'bytes':path.stat().st_size,'png_sha256':entry['sha256'],'dimensions':image.size,'apk_texture_path':names[0],'apk_texture_sha256':sha(z.read(names[0])),'passed':source_ok and pack_ok and library_ok})
    report['passed']=all(a['passed'] for a in report['assets']);report['png_bytes']=sum(a['bytes'] for a in report['assets']);report['rgba8_bytes_without_mipmaps']=pixels*4
    args.qa.mkdir(parents=True,exist_ok=True);(args.qa/'paper-ui-assets.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(report['passed'],len(report['assets']),report['png_bytes'],report['rgba8_bytes_without_mipmaps']);assert report['passed']
if __name__=='__main__':main()
