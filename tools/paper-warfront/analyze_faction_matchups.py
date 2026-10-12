"""Summarize paid matchup observations without treating time limits as draws."""
from pathlib import Path
import json,hashlib
ROOT=Path(__file__).resolve().parents[2]
QA=ROOT/'output/qa/godot/core-alignment-rc7'
files=[QA/'faction-matchups-00-09.json',QA/'faction-matchups-10-19.json',QA/'faction-matchups-20-99.json']
records={};inputs=None;sources=[];conditions=None
for path in files:
    if not path.exists():continue
    data=json.loads(path.read_text(encoding='utf-8'))
    if conditions is None:conditions=(data['map'],data['seed'])
    assert conditions==(data['map'],data['seed']),'Different map or seed must be analyzed separately'
    if inputs is None:inputs=data['inputs']
    assert inputs==data['inputs'],'Mixed gameplay revisions cannot be pooled'
    for row in data['records']:
        assert row['index'] not in records,'Duplicate pairing'
        records[row['index']]=row
    sources.append({'path':path.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
factions=[records[i]['east'] for i in range(10)]
matrix=[];totals={f:{'wins':0,'losses':0,'unresolved':0,'games':0} for f in factions}
for west in factions:
    cells=[]
    for east in factions:
        index=factions.index(west)*10+factions.index(east)
        row=records.get(index)
        cells.append('pending' if row is None else 'unresolved' if row['winner']==-2 else 'draw' if row['winner']==-1 else 'west' if row['winner']==0 else 'east')
        if row is None or west==east:continue
        for side,faction in enumerate([west,east]):
            totals[faction]['games']+=1
            totals[faction]['unresolved' if row['winner']==-2 else 'wins' if row['winner']==side else 'losses']+=1
    matrix.append(cells)
reverse_pairs=[]
for a in range(10):
    for b in range(a+1,10):
        left=records.get(a*10+b);right=records.get(b*10+a)
        if left is None or right is None:continue
        if left['winner'] not in [0,1] or right['winner'] not in [0,1]:classification='unresolved_pair'
        elif left['winner']==right['winner']:classification='side_split'
        else:classification='same_faction_wins_both'
        reverse_pairs.append({'factions':[factions[a],factions[b]],'classification':classification,'winners':[left['winner'],right['winner']]})
report={'scope':'One map, one seed, shared AI. Observation limit is unresolved, not a draw or proof of stalemate. Not human balance.',
        'coverage':len(records),'expected':100,'complete':len(records)==100,'factions':factions,'matrix':matrix,'totals':totals,'sources':sources,'inputs':inputs,
        'reverse_pairs':reverse_pairs,'conditions':conditions,
        'mirrors':[{'faction':r['west'],'winner':r['winner'],'time':r['time'],'gold_delivered':[s['stats']['gold_delivered'] for s in r['sides']]} for r in records.values() if r['west']==r['east']]}
(QA/'faction-matchup-summary.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'coverage':report['coverage'],'complete':report['complete'],'totals':totals,'mirrors':report['mirrors']},ensure_ascii=False))
