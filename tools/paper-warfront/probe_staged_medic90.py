"""Explicit research-before-arrival pilot; no shipping configuration changes."""
from pathlib import Path
import subprocess,json,hashlib
ROOT=Path(__file__).resolve().parents[2]
QA=ROOT/'output/qa/godot/core-alignment-rc12/investment'
QA.mkdir(parents=True,exist_ok=True)
tracked=['game/scripts/tactical_ai.gd','game/scripts/battle_sim.gd','game/scripts/recruitment_readiness.gd','game/tests/probe_faction_matchups.gd','game/data/balance-prototype.json','game/data/maps.json','game/data/technology.json']
before={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in tracked}
results=[]
for label,map_id in [('short','map.01.01'),('mid','map.01.04'),('long','map.01.11')]:
 for policy in ['baseline','trial']:
  dest=QA/f'staged-medic90-{label}-{policy}.json'
  cmd=[str(ROOT/'.tools/godot/Godot_v4.7.2-stable_win64_console.exe'),'--headless','--path',str(ROOT/'game'),'--script','res://tests/probe_faction_matchups.gd','--','--indices','6,60','--map',map_id,'--seed','271','--timeline','--sample-seconds','5','--investment-trace','--output',str(dest)]
  if policy=='trial':cmd+=['--staged-deployment-trial','--trial-faction','mu','--price-overrides',str(QA/'medic90-price-pilot.json')]
  run=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=120)
  log=run.stdout+run.stderr;dest.with_suffix('.log').write_text(log,encoding='utf-8')
  assert run.returncode==0 and 'ERROR:' not in log and 'SCRIPT ERROR' not in log,log
  data=json.loads(dest.read_text(encoding='utf-8'));assert len(data['records'])==2
  for path,digest in data['inputs'].items():assert hashlib.sha256((ROOT/'game'/path.removeprefix('res://')).read_bytes()).hexdigest()==digest,path
  assert data['experimental_ai_staged_deployment']==(policy=='trial')
  assert data['experimental_price_overrides']==({'unit.mu.medic':90} if policy=='trial' else {})
  for row in data['records']:
   side=0 if row['west']=='mu' else 1
   results.append({'map':map_id,'policy':policy,'index':row['index'],'winner':row['winner'],'time':row['time'],'workers':[s['workers'] for s in row['sides']],'bases':[s['base_hp'] for s in row['sides']],'wood_studied':row['sides'][side]['studied'],'wood_healed':row['sides'][side]['stats']['healed']})
  print(label,policy,'verified',flush=True)
assert all(hashlib.sha256((ROOT/n).read_bytes()).hexdigest()==v for n,v in before.items())
(QA/'staged-medic90-comparison.json').write_text(json.dumps({'source_unchanged':True,'inputs':before,'scope':'12 paid full-AI observations, seed271, three maps and two side assignments; candidate disabled by default, not balance acceptance','records':results},indent=2),encoding='utf-8')
print(json.dumps(results),flush=True)
