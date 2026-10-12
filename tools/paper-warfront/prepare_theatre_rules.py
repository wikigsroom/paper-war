"""Author clear side-view maps, four-role armies and short local research trees."""
from pathlib import Path
import json, math, hashlib, copy, sys
from generate_redesign_assets import ROLES

ROOT=Path(__file__).resolve().parents[2];DATA=ROOT/'game/data'
PROFILES=[
 [.2,.2,-.4,-.1,.2,.2], [.1,.1,-.9,-.7,.1,.1], [.2,.2,.15,-.7,-.7,.2],
 [.1,.1,-.3,-.4,.1,.1], [.2,-.3,-1.15,-1.15,-.3,.2], [.1,-.3,-.5,-.2,.1,.1],
 [.2,.2,-.6,-.2,.2,.2], [.1,-.5,-.5,-.7,-.7,.1], [.1,-.2,.1,.1,-.2,.1],
 [.2,-.8,-.9,.1,.1,.2], [.1,-.6,-1.,-.3,.1,.1], [.1,.1,-.8,-.8,.1,.1],
 [.1,-.2,-.1,-.4,-.1,.1], [.2,-.3,-.4,-.4,-.3,.2], [.1,-.7,-.7,-.2,.1,.1],
 [.1,-.2,-.5,-.4,-.1,.1], [.1,-.4,-1.1,-1.1,-.4,.1], [.2,.2,-.4,-.1,.2,.2],
 [.1,-.3,-.4,-.3,-.1,.1], [.1,-.3,-.8,-.8,-.3,.1],
]
FORKS={3,8,12,15,18}
NAMES=['谷口初阵','近城坡','归金坪','纸桥岔口','高台守位','护书山道','外矿前沿','前哨坡','双径渡口','逆坡推进','灯台岭','峡口交换','侧翼纸桥','破城长坡','炉边短道','信使双径','寒页台','矿线阻击','两路投资','合印门']

def load(name):return json.loads((DATA/name).read_text(encoding='utf-8'))
def save(name,value):(DATA/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def anchor(edge,t):
 pts=edge['points'];lengths=[math.dist(a,b) for a,b in zip(pts,pts[1:])];s=sum(lengths)*t;left=s
 for i,d in enumerate(lengths):
  if left<=d+1e-8:
   q=left/d if d else 0;x=pts[i][0]+(pts[i+1][0]-pts[i][0])*q;y=pts[i][1]+(pts[i+1][1]-pts[i][1])*q
   return dict(edge=edge['id'],s=round(s,5),x=round(x,4),y=round(y,4))
  left-=d
 return dict(edge=edge['id'],s=round(s,5),x=pts[-1][0],y=pts[-1][1])

def make_map(old,region,local):
 m=copy.deepcopy(old);length=round(34+local%5*2.4+region*.58+(4 if local in [13,19] else 0),3)
 xs=[2,round(length*.2,3),round(length*.35,3),round(length*.66,3),round(length*.81,3),round(length-2,3)]
 ys=[v+.06*math.sin(region*.8+i*.9) for i,v in enumerate(PROFILES[local])]
 ids=['west','home','fork','merge','away','east'];nodes=[dict(id=n,position=[x,round(y,4)]) for n,x,y in zip(ids,xs,ys)];edges=[]
 for i in range(5):
  a,b=nodes[i]['position'],nodes[i+1]['position'];points=[]
  for j in range(9):
   t=j/8;smooth=t*t*(3-2*t)
   points.append([round(a[0]+(b[0]-a[0])*t,4),round(a[1]+(b[1]-a[1])*smooth,4)])
  edges.append(dict(id='ground.'+str(i),**{'from':ids[i],'to':ids[i+1]},points=points,route_role='ground'))
 if local in FORKS:
  a,b=nodes[2]['position'],nodes[3]['position'];bridge_y=min(a[1],b[1])-2.15-region*.015
  points=[a,[round(a[0]+1.8,4),round(bridge_y+.08,4)],[round(a[0]+(b[0]-a[0])*.35,4),round(bridge_y,4)],[round(a[0]+(b[0]-a[0])*.68,4),round(bridge_y-.1,4)],[round(b[0]-1.8,4),round(bridge_y+.08,4)],b]
  edges.append(dict(id='bridge',**{'from':'fork','to':'merge'},points=points,route_role='bridge'))
 bases=[dict(node='west',owner=0),dict(node='east',owner=1)];mines=[];sites=[]
 for side in [0,1]:
  near=edges[0 if side==0 else 4];outer=edges[1 if side==0 else 3]
  capacity=2 if m['region']=='qi' else 3
  for j,e,t in [(0,near,.55 if side==0 else .45),(1,outer,.68 if side==0 else .32)]:
   mines.append(dict(id=f'mine.{side}.{j}',owner=side,capacity=capacity if j==0 else 2,cargo_bonus=0 if j==0 else 3,mine_seconds=1.05 if j==0 else 1.15,resource=-1,**anchor(e,t)))
  for j,e,t in [(0,near,.29 if side==0 else .71),(1,outer,.83 if side==0 else .17)]:
   sites.append(dict(id=f'site.{side}.{j}',owner=side,types=['tower','mana'],**anchor(e,t)))
  if local in FORKS and local in [8,18]:
   sites.append(dict(id=f'site.{side}.2',owner=side,types=['tower','mana'],**anchor(edges[-1],.28 if side==0 else .72)))
 objective=anchor(edges[4],.84)
 direct=sum(sum(math.dist(a,b) for a,b in zip(e['points'],e['points'][1:])) for e in edges[:5])
 longest=direct if local not in FORKS else direct-sum(math.dist(a,b) for a,b in zip(edges[2]['points'],edges[2]['points'][1:]))+sum(math.dist(a,b) for a,b in zip(edges[-1]['points'],edges[-1]['points'][1:]))
 region_name=old['name'].split('·')[0]
 decision=('主路较短，适合快速集中军团；纸桥绕行能分离近战、避开主路阵地，但要承担坡道与汇流等待。' if local in FORKS else '连续主路将矿线、前位与纸城串联；近矿安全回款，外矿每趟多运3金但暴露更靠前，塔位与研究争用当前兵力预算。')
 m.update(name=region_name+'·'+NAMES[local],length=length,nodes=nodes,edges=edges,bases=bases,mines=mines,build_sites=sites,objective_anchor=objective,route_lengths=dict(shortest=round(direct,3),longest=round(longest,3)),decision=decision,alternative='早投入外矿和前哨，以较少即时军力换持续回款或施法空间。',schema_version=3,
          presentation=dict(style='paper-theatre',archetype=NAMES[local],ground_edges=[e['id'] for e in edges[:5]],forks=1 if local in FORKS else 0,terrain_color=['#857052','#615364','#537D6B','#806550','#73765D','#977646','#597348','#627787','#7E6052','#767185'][region]),regional_rule=old['regional_rule'])
 m['geometry_sha256']=hashlib.sha256(json.dumps({k:m[k] for k in ['length','nodes','edges','mines','build_sites']},sort_keys=True).encode()).hexdigest()
 return m

def main():
 sys.stdout.reconfigure(encoding='utf-8');balance=load('balance-prototype.json');factions=load('factions.json');maps=load('maps.json');campaign=load('campaign.json');tech=load('technology.json');nodes=[];initial={}
 for f in factions['factions']:
  fid=f['id'];core=[next(uid for uid in f['combat_units'] if balance['units'][uid]['role']==r) for r in ROLES[fid]]
  f['default_roster']=core;f['core_roster']=core;f['production_limit']=5
  spells=[s for s in balance['spells'] if s.split('.')[1]==fid];f['opening_spells']=spells[:3]
  initial[fid]=core[:2]+['unit.'+fid+'.worker','building.'+fid+'.tower','building.'+fid+'.mana']+spells[:3]
  for uid in f['combat_units']:
   d=balance['units'][uid]
   # Short unlocks remain meaningful investment; four global doctrine gates are removed.
   nodes.append(dict(id='tech.'+fid+'.unit.'+uid.split('.')[-1],faction=fid,grant=uid,gold=max(35,min(130,round(d['gold']*.7))),seconds=max(4,min(10,round(d['gold']/20))),requires=[]))
  for i,uid in enumerate(spells):nodes.append(dict(id='tech.'+fid+'.spell.'+uid.split('.')[-1],faction=fid,grant=uid,gold=55 if i<3 else 85,seconds=5 if i<3 else 8,requires=[]))
  for tier in [1,2]:
   uid='upgrade.'+fid+'.mana-'+str(tier)
   if uid in balance['upgrades']:nodes.append(dict(id='tech.'+fid+'.mana-'+str(tier),faction=fid,grant=uid,gold=75 if tier==1 else 130,seconds=6 if tier==1 else 9,requires=[] if tier==1 else ['tech.'+fid+'.mana-1']))
 for i,m in enumerate(maps['maps']):maps['maps'][i]=make_map(m,i//20,i%20)
 by_id={m['id']:m for m in maps['maps']};by_f={f['id']:f for f in factions['factions']}
 for i,level in enumerate(campaign['levels']):
  local=i%20;f=by_f[level['faction']];enemy=by_f[level['enemy']];m=by_id[level['map']]
  # Keep continuous plot/flags/IDs, while both armies obey a four-role combat roster.
  level['available_roster']=f['combat_units'][:min(40,4+(local//3)*6)]
  for uid in f['core_roster'][:2 if local<2 else 3 if local<5 else 4]:
   if uid not in level['available_roster']:level['available_roster'].append(uid)
  level['default_roster']=f['core_roster'][:2 if local<2 else 3 if local<5 else 4]
  level['enemy_roster']=enemy['core_roster'][:2 if local<2 else 3 if local<5 else 4]
  level['starting_gold']=max(170,min(280,int(level.get('starting_gold',200))))
  level['enemy_starting_gold']=max(145,min(260,int(level.get('enemy_starting_gold',180))))
  level['ai_warmup']=7 if local<3 else 3
  level['objective_anchor']=m['objective_anchor']
  level['map_brief']=m['decision'];level['production_limit']=5
  level['initial_unlocked']=f['core_roster'][:2];level['enemy_unlocked']=enemy['core_roster'][:2]
  if level.get('win')=='intercept':level['objective_anchor']=m['mines'][0]
 for challenge in campaign['challenges']:
  for key,sidekey in [('player_roster','faction'),('enemy_roster','enemy')]:challenge[key]=by_f[challenge[sidekey]]['core_roster']
  challenge['production_limit']=5
 balance['version']='3.0.0-dev';balance['stage']='theatre-redesign';balance['simulation']['production_roster_max']=4
 # Faster first contact while keeping walking, status control and economy in real world space.
 for d in balance['units'].values():
  if 'pre_theatre_speed' not in d:d['pre_theatre_speed']=d['speed']
  d['speed']=round(d['pre_theatre_speed']*(1.22 if not d.get('economy') else 1.1),4)
 save('balance-prototype.json',balance);factions['schema_version']=3;save('factions.json',factions)
 maps['schema_version']=3;save('maps.json',maps);campaign['schema_version']=3;save('campaign.json',campaign)
 save('technology.json',dict(schema_version=3,starting_unlocked=initial,nodes=nodes))
 print(json.dumps(dict(maps=len(maps['maps']),single_line=sum(not m['presentation']['forks'] for m in maps['maps']),one_fork=sum(m['presentation']['forks'] for m in maps['maps']),unique=len({m['geometry_sha256'] for m in maps['maps']}),production='2-4 combat + worker; rule and UI integration pending'),ensure_ascii=False))

if __name__=='__main__':main()
