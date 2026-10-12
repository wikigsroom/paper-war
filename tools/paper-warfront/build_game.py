"""Native Windows build/sign/validate. No containers, WSL or emulator."""
from pathlib import Path
from runtime_asset_inputs import runtime_asset_inputs
import os, json, secrets, subprocess, hashlib, zipfile, sys, shutil, tempfile, struct
sys.stdout.reconfigure(encoding='utf-8',errors='replace')

ROOT=Path(__file__).resolve().parents[2]
GAME=ROOT/'game'
ENGINE=ROOT/'.tools/godot/Godot_v4.7.2-stable_win64_console.exe'
SDK=Path(os.environ['LOCALAPPDATA'])/'Android/Sdk'
JAVA=Path('C:/Program Files/Eclipse Adoptium/jdk-21.0.11.10-hotspot')
VERSION=os.environ.get('PAPER_RELEASE_VERSION','3.0.0-rc5')
RELEASE=ROOT/'release'/VERSION
LOG=ROOT/os.environ.get('PAPER_QA_DIR','output/qa/godot/frame-rebuild')/'build'

def sha(path):
    digest=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1048576),b''):digest.update(block)
    return digest.hexdigest()

def run(args, name, env=None):
    result=subprocess.run([str(a) for a in args],cwd=ROOT,env=env,capture_output=True,text=True,encoding='utf-8',errors='replace')
    output=result.stdout+'\n'+result.stderr
    (LOG/(name+'.log')).write_text(output,encoding='utf-8')
    (LOG/(name+'-process.json')).write_text(json.dumps({'exit_code':result.returncode,'completed':True},indent=2),encoding='utf-8')
    if result.returncode or any(line.startswith(('SCRIPT ERROR:','ERROR:')) for line in output.splitlines()):
        print(output[-7000:])
        raise RuntimeError(name+' failed')
    print(name+' OK')
    return output

def main():
    for p in [RELEASE/'windows',RELEASE/'android',LOG]: p.mkdir(parents=True,exist_ok=True)
    public_inputs=[GAME/'project.godot',GAME/'export_presets.cfg',*sorted((GAME/'scripts').glob('*.gd')),*sorted((GAME/'data').glob('*.json')),*sorted((GAME/'assets/fonts').glob('*.ttf')),*sorted((GAME/'assets/fonts').glob('*.ttf.import')),*sorted((GAME/'assets/animation/frames-v1').glob('*.png'))]
    public_inputs.extend(sorted((GAME/'assets/ui/paper').glob('*.png')))
    # Legacy backdrop, terrain, icons, motifs and music are also runtime
    # dependencies. Bind their source and import settings, plus native scenes.
    for asset in runtime_asset_inputs(GAME):
        public_inputs.append(asset)
        descriptor=Path(str(asset)+'.import')
        if descriptor.exists():public_inputs.append(descriptor)
    for suffix in ['*.tscn','*.tres','*.gdshader','*.gd.uid']:
        public_inputs.extend(p for p in GAME.rglob(suffix) if '.godot' not in p.parts)
    public_inputs.extend((GAME/'licenses').glob('*.txt'))
    public_inputs.extend((GAME/'assets/fonts').glob('OFL-*.txt'))
    public_inputs=sorted(set(public_inputs))
    source_inputs={p.relative_to(ROOT).as_posix():sha(p) for p in public_inputs}
    env=os.environ.copy()
    env['JAVA_HOME']=str(JAVA)
    env['ANDROID_HOME']=str(SDK)
    env['GODOT_ANDROID_SDK_PATH']=str(SDK)
    # Local signing credentials stay outside the exportable Godot project.
    keydir=ROOT/'.keys'; keydir.mkdir(exist_ok=True)
    cfgfile=keydir/'signing.json'
    if cfgfile.exists(): cfg=json.loads(cfgfile.read_text())
    else:
        cfg={'alias':'paperwarfront','password':secrets.token_hex(24)}
        cfgfile.write_text(json.dumps(cfg),encoding='utf-8')
    env['PAPER_SIGNING_PASSWORD']=cfg['password']
    keyfile=keydir/'paperwarfront.keystore'
    if not keyfile.exists():
        run([JAVA/'bin/keytool.exe','-genkeypair','-keystore',keyfile,'-alias',cfg['alias'],'-storepass:env','PAPER_SIGNING_PASSWORD','-keypass:env','PAPER_SIGNING_PASSWORD','-keyalg','RSA','-keysize','2048','-validity','10000','-dname','CN=Paper Warfront Local, OU=Game, O=Paper Warfront, C=CN'],'signing-key',env)
    env['GODOT_ANDROID_KEYSTORE_RELEASE_PATH']=str(keyfile)
    env['GODOT_ANDROID_KEYSTORE_RELEASE_USER']=cfg['alias']
    env['GODOT_ANDROID_KEYSTORE_RELEASE_PASSWORD']=cfg['password']
    run([ENGINE,'--headless','--rendering-method','gl_compatibility','--path',GAME,'--editor','--import','--quit'],'release-import',env)
    run([ENGINE,'--headless','--path',GAME,'--export-release','Windows',RELEASE/'windows/PaperWarfront.exe'],'export-windows',env)
    run([ENGINE,'--headless','--path',GAME,'--export-release','Android',RELEASE/f'android/PaperWarfront-{VERSION}.apk'],'export-android',env)
    buildtools=SDK/'build-tools/35.0.0'
    apk=RELEASE/f'android/PaperWarfront-{VERSION}.apk'
    run(['cmd','/c',str(buildtools/'apksigner.bat'),'verify','--verbose','--print-certs',apk],'apk-signature',env)
    run([buildtools/'zipalign.exe','-c','-P','16','4',apk],'apk-alignment',env)
    # Legacy aapt uses ANSI file APIs on Windows; inspect an ASCII temporary copy.
    verification=Path(tempfile.gettempdir())/'paper-warfront-apk-verify.apk'
    shutil.copy2(apk,verification)
    try:
        run([buildtools/'aapt.exe','dump','badging',verification],'apk-badging',env)
        run([buildtools/'aapt.exe','dump','xmltree',verification,'AndroidManifest.xml'],'apk-manifest',env)
    finally:
        verification.unlink(missing_ok=True)
    with zipfile.ZipFile(apk) as z:
        names=z.namelist()
        assert 'AndroidManifest.xml' in names
        assert any('arm64-v8a/libgodot_android.so' in p for p in names)
        assert not any('.keys' in p or 'signing.json' in p for p in names)
        elf_checks=[]
        for name in names:
            if name.startswith('lib/arm64-v8a/') and name.endswith('.so'):
                data=z.read(name)
                assert data[:5]==b'\x7fELF\x02'
                offset=struct.unpack_from('<Q',data,32)[0]
                size,count=struct.unpack_from('<HH',data,54)
                alignments=[struct.unpack_from('<Q',data,offset+i*size+48)[0] for i in range(count) if struct.unpack_from('<I',data,offset+i*size)[0]==1]
                assert alignments and all(a>=16384 for a in alignments)
                elf_checks.append({'file':name,'load_alignment':alignments,'arm64_16kb_pass':True})
        (LOG/'apk-elf-report.json').write_text(json.dumps(elf_checks,indent=2),encoding='utf-8')
    builds=[]
    for f in [RELEASE/'windows/PaperWarfront.exe',apk]:
        builds.append({'path':str(f.relative_to(ROOT)).replace('\\','/'),'bytes':f.stat().st_size,'sha256':sha(f)})
    assert all(sha(ROOT/path)==digest for path,digest in source_inputs.items()),'Public source changed during export'
    (RELEASE/'build-manifest.json').write_text(json.dumps({'version':VERSION,'engine':'Godot 4.7.2','builds':builds,'source_inputs':source_inputs},indent=2),encoding='utf-8')
    print(json.dumps(builds,indent=2))

if __name__=='__main__':main()
