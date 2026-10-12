"""Freeze the complete reference helper closure, replacing only resource paths."""
from pathlib import Path
import hashlib,json,re
ROOT=Path(__file__).resolve().parents[2]
QA=ROOT/'output/qa/godot/packed-query-rc28'
source=QA/'baseline-runtime/scripts';target=QA/'oracle-runtime/scripts'
assert not target.exists(), 'Never overwrite a frozen reference'
target.mkdir(parents=True)
records={}
for original in sorted(source.glob('*.gd')):
    text=original.read_text('utf-8')
    def replace(match):
        file=source/match.group(1)
        assert file.is_file(),file
        return (target/match.group(1)).as_posix()
    rewritten=re.sub(r'res://scripts/([^"\s]+\.gd)',replace,text)
    destination=target/original.name
    destination.write_bytes(rewritten.encode('utf-8'))
    records[original.name]={'original_sha256':hashlib.sha256(original.read_bytes()).hexdigest(),'oracle_sha256':hashlib.sha256(destination.read_bytes()).hexdigest()}
(target.parent/'closure-inputs.json').write_text(json.dumps({'source':source.relative_to(ROOT).as_posix(),'scope':'Original rc27 helper closure. Only res://scripts references are redirected to this isolated absolute native path; no gameplay edits. Candidate data remain shared and must match the frozen data.','generator_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'scripts':records},ensure_ascii=False,indent=2)+'\n','utf-8')
print('Frozen original helper closure',len(records),'scripts')
