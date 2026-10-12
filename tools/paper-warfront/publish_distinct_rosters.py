"""Publish curated kits and stable-ID migrations, retaining the actual legacy data."""
from pathlib import Path
import argparse,json,copy
from design_distinct_rosters import KITS
ROOT=Path(__file__).resolve().parents[2];DATA=ROOT/'game/data';ARCHIVE=ROOT/'assets/paper-warfront/frame-rebuild/legacy'
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def write(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

GENERAL=['gold','hp','damage','attack_interval','windup','range','speed','attack','role','tier','faction','economy','cargo','giant','summoned','creates_corpse','lifetime_seconds','manual_recruit','reflectable']
TRAITS=['faction_trait','workshop_bonus','junction_haste_seconds','bounty_gold','regeneration','control_mana','magic_damage_multiplier','physical_damage_multiplier']

def main():
    p=argparse.ArgumentParser();p.add_argument('--development',action='store_true');args=p.parse_args()
    ARCHIVE.mkdir(parents=True,exist_ok=True)
    for filename in ['balance-prototype.json','factions.json','assets.json','campaign.json','technology.json','unit-actions.json','story.json']:
        if not (ARCHIVE/filename).exists():(ARCHIVE/filename).write_bytes((DATA/filename).read_bytes())
    legacy=read(ARCHIVE/'balance-prototype.json');oldfactions=read(ARCHIVE/'factions.json');factions=copy.deepcopy(oldfactions)
    oldassets=read(ARCHIVE/'assets.json');assets=copy.deepcopy(oldassets)
    briefs=read(ROOT/'assets/paper-warfront/frame-rebuild/unit-briefs.json')['units'];lookup={r['id']:r for r in briefs};active=set(lookup)
    frames=read(DATA/'unit-frames.json')['profiles']
    if not args.development:
        assert active<=set(frames),'Every active unit requires a normalized actual frame sheet'
        for uid,row in lookup.items():
            assert row.get('identity_version')==2,uid+' still has the retired identity source'
            assert frames[uid]['source']==row['source'] and frames[uid]['raw']==row['raw'],uid+' frame source is stale'
    balance=copy.deepcopy(legacy);newunits={}
    for uid in lookup:
        row=lookup[uid];old=legacy['units'][uid]
        if old.get('economy') or old.get('summoned'):d=copy.deepcopy(old)
        else:d={k:v for k,v in old.items() if k in GENERAL+TRAITS}
        d.update(row['mechanics']);d.update({'name':row['name'],'hint':row['hint'],'art_source':uid,'art_status':'whole-frame-binding; acceptance-in-frame-rebuild-visual-review','identity_version':row.get('identity_version',1)})
        if not d.get('economy'):
            d['windup']=max(.27,float(d['windup']))
            d['attack_interval']=max(float(d['attack_interval']),d['windup']+.40)
        # Equipment and attack contract agree. These are no longer renamed spear/cannon clones.
        if uid=='unit.mu.warden':d.update(attack='projectile',range=3.2,damage=10,hp=105)
        if uid=='unit.shuang.scribe':d.update(attack='projectile',range=3.7,damage=10)
        if uid=='unit.yuan.artillery':d.update(damage=14,hp=105,speed=.96,range=4.6,attack_interval=2.3)
        if uid=='unit.bai.colossus':d.update(attack='projectile-area',range=2.5,damage=42,hp=540)
        if uid=='unit.mo.warden':d.update(attack='projectile',range=3.1,damage=10,hp=120)
        if uid=='unit.ji.javelin':d.update(range=3.3,damage=11)
        if uid=='unit.ji.vanguard':d.update(range=.8,hp=190,damage=16)
        if uid=='unit.qi.javelin':d.update(range=3.7,damage=10)
        if uid=='unit.jin.artillery':d.update(range=5.3,windup=.55,attack_interval=2.8)
        if uid=='unit.jin.burner':d.update(range=2.8,damage=7,reflectable=False)
        newunits[uid]=d
    balance['units']=newunits;balance['version']='3.0.0-rc5';balance['stage']='distinct-faction-and-whole-frame-rebuild';balance['note']='60 curated combat units, ten economy workers and two summons. Legacy definitions archived; unique equipment and executed kits replace the palette roster.'
    aliases={}
    for f in factions['factions']:
        ids=['unit.'+f['id']+'.'+row[0] for row in KITS[f['id']]]
        f.update(combat_units=ids,core_roster=ids,default_roster=ids[:4],unit_identity_policy='curated-asymmetric-kits-v1')
        for i,uid in enumerate(ids):newunits[uid]['tier']=0 if i<2 else max(1,min(3,i-1))
        for oldid in legacy['units']:
            if oldid in active or oldid.split('.')[1]!=f['id']:continue
            old=legacy['units'][oldid];role=old.get('role','vanguard')
            matches=[uid for uid in ids if newunits[uid].get('role')==role]
            if not matches:
                ranged=str(old.get('attack','')).startswith('projectile')
                matches=[uid for uid in ids if str(newunits[uid]['attack']).startswith('projectile')==ranged]
            if not matches:matches=ids
            aliases[oldid]=min(matches,key=lambda uid:abs(float(newunits[uid]['range'])-float(old.get('range',1)))+abs(float(newunits[uid]['hp'])-float(old.get('hp',100)))*.001)
    for uid in list(assets['assets']):
        if uid.startswith('unit.') and uid not in active:del assets['assets'][uid]
    profiles={}
    for uid,row in lookup.items():
        d=newunits[uid];rec=frames.get(uid);meta=assets['assets'][uid]
        if rec:
            meta['path']=rec['idle'];meta['portrait']=rec['portrait'];meta['animation']={'source_height':rec['source_height'],'foot':rec['anchor'],'frame_version':1,'atlas':rec['atlas'],'frame_profile':uid}
        meta['identity_version']=row.get('identity_version',1)
        profiles[uid]={'id':uid,'role':d.get('role','worker' if d.get('economy') else 'summon'),'gesture':row['gesture'],'projectile':d.get('projectile_style',''), 'windup':d.get('windup',0),'recovery':.30 if float(d.get('attack_interval',1))>=1 else .24,'source_art':uid,'rig':'whole-drawn-frame-sheet','states':['idle','walk','windup','attack','hurt','death','special','bound'] if not d.get('economy') else ['idle','walk','mine','load','unload','queue','hurt','death','bound']}
    assets['version']='3.0.0-rc5'
    technology=read(ARCHIVE/'technology.json')
    technology['nodes']=[n for n in technology['nodes'] if not n['grant'].startswith('unit.') or n['grant'] in active]
    kept={n['id'] for n in technology['nodes']}
    for n in technology['nodes']:n['requires']=[r for r in n.get('requires',[]) if r in kept]
    for faction,values in technology['starting_unlocked'].items():
        out=[aliases.get(uid,uid) for uid in values];out=list(dict.fromkeys(uid for uid in out if not uid.startswith('unit.') or uid in active))
        out+=['unit.'+faction+'.'+r[0] for r in KITS[faction][:2] if 'unit.'+faction+'.'+r[0] not in out]
        technology['starting_unlocked'][faction]=out
    campaign=read(ARCHIVE/'campaign.json');fm={f['id']:f for f in factions['factions']}
    for level in campaign['levels']:
        faction=level.get('faction',level.get('player','yin'));enemy=level.get('enemy','mo')
        if faction not in fm:faction=level.get('player_faction','yin')
        for field,side in [('available_roster',faction),('default_roster',faction),('enemy_roster',enemy)]:
            if field not in level:continue
            values=level[field];out=list(dict.fromkeys(aliases.get(uid,uid) for uid in values));out=[uid for uid in out if uid in active]
            minimum=2 if field!='available_roster' else (6 if len(values)>8 else 5 if len(values)>4 else 4)
            for uid in fm[side]['combat_units']:
                if len(out)>=minimum:break
                if uid not in out:out.append(uid)
            if field!='available_roster':out=out[:4]
            level[field]=out
        for field in ['escort_id','intercept_id']:
            if field in level:level[field]=aliases.get(level[field],level[field])
    def migrate(value):
        if isinstance(value,str):return aliases.get(value,value)
        if isinstance(value,list):return [migrate(v) for v in value]
        if isinstance(value,dict):return {k:migrate(v) for k,v in value.items()}
        return value
    campaign=migrate(campaign)
    story=read(ARCHIVE/'story.json')
    for key,value in story.items():
        if isinstance(value,dict) and any(k.startswith('unit.') for k in value):story[key]={uid:v for uid,v in value.items() if not uid.startswith('unit.') or uid in active}
    story=migrate(story)
    write(DATA/'story.json',story)
    write(DATA/'unit-id-migration.json',{'version':1,'aliases':aliases,'legacy_source':'assets/paper-warfront/frame-rebuild/legacy/balance-prototype.json','note':'Old loadouts map to curated equivalent jobs; retired IDs cannot be recruited directly.'})
    for filename,value in [('balance-prototype.json',balance),('factions.json',factions),('assets.json',assets),('technology.json',technology),('campaign.json',campaign),('unit-actions.json',{'version':5,'profiles':profiles})]:write(DATA/filename,value)
    write(ROOT/'assets/paper-warfront/frame-rebuild/active-rosters.json',{'version':1,'factions':factions['factions'],'active_ids':list(lookup),'retired_ids':list(aliases)})
    print(f'Published {len(newunits)} definitions and {len(aliases)} stable-ID migrations; frames currently {len(frames)}. Development={args.development}')

if __name__=='__main__':main()
