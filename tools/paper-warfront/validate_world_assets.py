"""Validate the expanded, shipped Godot library without inspecting credentials."""
from pathlib import Path
from collections import Counter
import hashlib,json,sys,wave
import numpy as np
from PIL import Image
from validate_library import acyclic

ROOT=Path(__file__).resolve().parents[2]
GAME=ROOT/'game'
OUT=ROOT/'output/qa/godot/v2'

def read(name):return json.loads((GAME/'data'/name).read_text(encoding='utf-8'))
def local(path):
    assert path.startswith('res://'),path
    result=(GAME/path.removeprefix('res://')).resolve()
    assert result.is_relative_to(GAME.resolve()) and result.is_file(),path
    return result

def main():
    sys.stdout.reconfigure(encoding='utf-8')
    manifest=read('assets.json')['assets'];balance=read('balance-prototype.json')
    factions=read('factions.json');maps=read('maps.json')['maps'];tech=read('technology.json')
    combat=read('world-art-provenance.json');support=read('world-support-provenance.json')
    checks=[];errors=[]
    def check(name,action):
        try:action();checks.append({'name':name,'passed':True})
        except Exception as error:errors.append({'name':name,'error':str(error) or type(error).__name__})
    def require(condition,message='condition failed'):assert condition,message
    combat_ids=[uid for faction in factions['factions'] for uid in faction['combat_units']]
    check('ten factions, 40 manual combat units each',lambda:require(len(factions['factions'])==10 and len(combat_ids)==len(set(combat_ids))==400 and all(len(f['combat_units'])==40 for f in factions['factions']) and all(balance['units'][uid]['manual_recruit'] and not balance['units'][uid].get('economy',False) for uid in combat_ids)))
    check('400 original combat and 87 support provenance records',lambda:require(len(combat['records'])==400 and len(support['records'])==87 and set(r['id'] for r in combat['records'])==set(combat_ids)))
    cutout_hashes=[];rig_parts=0
    for uid in balance['units'].keys()|balance['spells'].keys()|balance['buildings'].keys():
        check('runtime binding '+uid,lambda uid=uid:require(uid in manifest and not manifest[uid].get('development_fallback',False)))
    for uid,asset in manifest.items():
        check('file '+uid,lambda asset=asset:local(asset['path']))
        if asset.get('portrait'):check('portrait '+uid,lambda asset=asset:local(asset['portrait']))
    for record in combat['records']+support['records']:
        def source_check(record=record):
            path=ROOT/record['source'];assert path.is_file()
            assert hashlib.sha256(path.read_bytes()).hexdigest()==record['sha256']
            assert manifest[record['id']]['status']=='runtime-linked-reviewed'
            if 'source_box' in record:
                with Image.open(path) as image:
                    box=record['source_box'];assert 1<box[0]<box[2]<image.width-1 and 1<box[1]<box[3]<image.height-1
        check('source '+record['id'],source_check)
    for uid in combat_ids+[f'unit.{f}.worker' for f in factions['order']]:
        asset=manifest[uid]
        def sprite_check(asset=asset,uid=uid):
            with Image.open(local(asset['path'])) as image:
                assert image.mode=='RGBA' and image.size==(512,512)
                alpha=np.asarray(image.getchannel('A'));assert alpha.max()>=250 and alpha.min()==0
                assert alpha[0].max()==alpha[-1].max()==alpha[:,0].max()==alpha[:,-1].max()==0
                assert image.getchannel('A').getbbox()[3]==476
            with Image.open(local(asset['portrait'])) as portrait:assert portrait.mode=='RGBA' and portrait.size==(192,192)
            anim=asset['animation'];assert 0<anim['foot'][0]<512 and anim['foot'][1]==476 and anim['source_height']>80 and len(anim['parts'])==3
            for path in anim['parts'].values():
                with Image.open(local(path)) as part:assert part.size==(512,512) and part.mode=='RGBA' and part.getchannel('A').getbbox()
        check('alpha, portrait and articulated parts '+uid,sprite_check)
        rig_parts+=len(asset['animation']['parts'])
        if uid in combat_ids:cutout_hashes.append(hashlib.sha256(local(asset['path']).read_bytes()).hexdigest())
    check('400 distinct runtime silhouettes',lambda:require(len(set(cutout_hashes))==400))
    check('technology DAG',lambda:acyclic(tech['nodes'],'requires'))
    grants={n['grant'] for n in tech['nodes']}|{uid for values in tech['starting_unlocked'].values() for uid in values}
    check('combat and magic unlock coverage',lambda:require(set(combat_ids)|set(balance['spells'])<=grants))
    themes=set()
    for m in maps:
        check('region background '+m['id'],lambda m=m:local(manifest['background.'+m['theme']]['path']))
        check('spatial design brief '+m['id'],lambda m=m:require((ROOT/'docs/paper-warfront/world/maps'/f'{m["id"]}.md').is_file()))
        themes.add(m['theme'])
    check('200 maps and ten region themes',lambda:require(len(maps)==200 and len(themes)==10))
    music=[]
    for faction in factions['order']:
        path=GAME/f'assets/audio/music/music-{faction}.wav'
        def audio_check(path=path):
            with wave.open(str(path)) as stream:
                assert stream.getnchannels()==1 and stream.getsampwidth()==2 and stream.getframerate()==22050
                samples=np.frombuffer(stream.readframes(stream.getnframes()),dtype='<i2')
                assert len(samples)==40*22050 and 100<int(np.max(np.abs(samples.astype(np.int32))))<32767
                assert abs(int(samples[0])-int(samples[-1]))<100
        check('original loop '+faction,audio_check);music.append(path.name)
    report={'passed':not errors,'checks':len(checks),'errors':errors,'combat_units':400,'workers':10,'new_source_records':487,'rig_parts':rig_parts,'maps':200,'themes':sorted(themes),'music_loops':music,'visual_review':'output/imagegen/paper-warfront/world-v2/visual-review.json','scope':'runtime files, alpha, baseline anchors, nonempty rig layers, unique combat cutouts, original source hashes, technology grants, ten regional backgrounds, 200 spatial briefs and loop PCM; visual quality and playability rely on the separately recorded source and native UI reviews'}
    OUT.mkdir(parents=True,exist_ok=True);(OUT/'world-assets-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:report[k] for k in ['passed','checks','errors','combat_units','new_source_records','rig_parts','maps']},ensure_ascii=False))
    raise SystemExit(0 if not errors else 1)

if __name__=='__main__':main()
