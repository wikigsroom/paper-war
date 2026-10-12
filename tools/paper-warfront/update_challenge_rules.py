"""Six independent timed objectives; stable challenge identities remain intact."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
path=ROOT/'game/data/campaign.json'
data=json.loads(path.read_text(encoding='utf-8'))
world=json.loads((ROOT/'game/data/maps.json').read_text(encoding='utf-8'))
maps={m['id']:m for m in world['maps']}
rules=[('time',150,150,'守城'),('healed',255,150,'有效治疗'),('interrupts',5,180,'打断出手'),('summons',8,180,'召回纸兵'),('reflections',6,180,'反弹投射'),('facility_mana',60,180,'设施法力')]
for c,(metric,target,deadline,label) in zip(data['challenges'],rules):
    c['win']='challenge'
    c['challenge_rule']={'metric':metric,'target':target,'deadline':deadline,'label':label}
    c['challenge_rule']['star_scores']=[1200,1400] if metric=='time' else [1500,2000]
    c['duration']=deadline
    c['tip']=f'{deadline}秒内完成{label}{target}；纸城失守即失败。仅统计实际效果，胜利按时间、城防和损失计分。'
    if metric=='interrupts':
        c['faction']='shuang'
        c['player_roster']=['unit.shuang.shield','unit.shuang.javelin','unit.shuang.warden','unit.shuang.mortar']
    c['ai_phases']=[{'id':c['id']+'.pressure','at':4,'style':'rush','workers':3,'prefer_units':c['enemy_roster'][:2]}]
    if metric=='interrupts':
        m=maps[world['aliases'].get(c['map'],c['map'])]
        edge=next(e for e in m['edges'] if e['to']==m['bases'][1]['node'])
        points=edge['points']
        import math
        length=sum(math.dist(a,b) for a,b in zip(points,points[1:]))
        c['opening_forces']=[{'side':1,'id':'unit.mo.giant','edge':edge['id'],'s':length,'x':points[-1][0],'y':points[-1][1],'label':'重击巨兵'}]
        c['ai_phases'][0]['prefer_units']=['unit.mo.giant','unit.mo.needle']
    elif metric=='reflections':
        c['ai_phases'][0]['prefer_units']=['unit.yin.spear','unit.yin.cannon']
    elif metric=='summons':
        # Heavy front plus two priests is a real 380-gold opening investment.
        # Provide an explicit budget for that choice, without free units.
        c['starting_gold']=510
        c['tip']+=' 本题起始金币510，可投资巨兵护住祭司。'
data['challenge_revision']='rc7-effective-objectives-scores'
text=json.dumps(data,ensure_ascii=False,indent=2)+'\n'
path.write_text(text,encoding='utf-8')
(ROOT/'assets/paper-warfront/campaign.json').write_text(text,encoding='utf-8')
print('Updated six independent timed challenge objectives')
