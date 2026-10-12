"""Sequential existing paid combat recipes, kept distinct from story UI fixtures."""
from pathlib import Path
import argparse,subprocess
ROOT=Path(__file__).resolve().parents[2]
p=argparse.ArgumentParser();p.add_argument('--qa',type=Path,required=True);a=p.parse_args();qa=a.qa.resolve()
engine=ROOT/'.tools/godot/Godot_v4.7.2-stable_win64_console.exe'
def run(script,arguments,path):
 assert not path.exists(), 'Completed paid recipes are immutable'
 path.parent.mkdir(parents=True,exist_ok=True)
 result=subprocess.run([str(engine),'--headless','--path',str(ROOT/'game'),'--script',str(script),'--',*map(str,arguments)],cwd=ROOT,capture_output=True,encoding='utf-8',errors='replace',timeout=360)
 path.with_suffix('.runtime.log').write_text(result.stdout+result.stderr,'utf-8')
 assert result.returncode==0 and 'SCRIPT ERROR' not in result.stdout+result.stderr and path.exists(),result.stdout[-1500:]+result.stderr[-1500:]
 print(path.name,'passed',flush=True)
for label,map_id in [('short','map.01.01'),('mid','map.01.04'),('long','map.01.11')]:
 path=qa/f'formal-reach/{label}-paid-exchange.json'
 run(ROOT/'game/tests/probe_paid_premium_exchange.gd',[path,'--map',map_id,'--formal-price','--reach-trial'],path)
for name,flags in [('paid-recipes',['--formal-range']),('reach-controls',[])]:
 path=qa/f'formal-hammer/{name}.json'
 run(ROOT/'tools/paper-warfront/probe_paid_hammer_screen.gd',['--output',path,*flags],path)
