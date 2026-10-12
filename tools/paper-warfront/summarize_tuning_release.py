"""Verify the rc6 targeted native checks and exported binaries without altering rc5 evidence."""
from pathlib import Path
import hashlib,json,zipfile
ROOT=Path(__file__).resolve().parents[2]
QA=ROOT/'output/qa/godot/tuning-rc6'
RELEASE=ROOT/'release/3.0.0-rc6'
def main():
    names=['recovery.json','test_distinct_factions.gd.json','test_frame_contracts.gd.json','test_combat_ownership.gd.json','test_worker_actions.gd.json','test_world_foundation.gd.json']
    reports=[]
    for name in names:
        report=json.loads((QA/name).read_text(encoding='utf-8'))
        assert report.get('passed') is True or (report.get('failed')==0 and report.get('failures')==[]),name
        count=report['checks']
        reports.append({'path':name,'checks':len(count) if isinstance(count,list) else count,'passed':True})
    for name in ['mobile/mobile-matrix.json','mobile/export/report.json']:
        report=json.loads((QA/name).read_text(encoding='utf-8'))
        assert report['passed'] and report['version']=='3.0.0-rc6',name
        reports.append({'path':name,'checks':report.get('checks',len(report['cases'])),'passed':True})
    manifest=json.loads((RELEASE/'build-manifest.json').read_text())
    for path,digest in manifest['source_inputs'].items():
        assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==digest,path
    sums=[]
    for item in manifest['builds']:
        path=ROOT/item['path']
        assert path.stat().st_size==item['bytes']
        assert hashlib.sha256(path.read_bytes()).hexdigest()==item['sha256']
        sums.append(item['sha256']+'  '+path.relative_to(RELEASE).as_posix())
    archive=RELEASE/'PaperWarfront-Windows-3.0.0-rc6.zip'
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        assert hashlib.sha256(z.read('PaperWarfront.exe')).hexdigest()==manifest['builds'][0]['sha256']
        assert 'licenses/OFL-NotoSansSC.txt' in z.namelist()
    sums.append(hashlib.sha256(archive.read_bytes()).hexdigest()+'  '+archive.name)
    (RELEASE/'SHA256SUMS.txt').write_text('\n'.join(sums)+'\n')
    result={'version':manifest['version'],'passed':True,'reports':reports,'checks':sum(r['checks'] for r in reports),'builds':manifest['builds'],'scope':'Targeted recovery/feedback regressions, asymmetric mechanics, frames, ownership, workers, maps, eight Windows-native injected mobile metrics and six actual EXE launches; Android signing/alignment in build logs. No Android hardware or full human campaign acceptance.'}
    (QA/'release-checks.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False))
if __name__=='__main__':main()
