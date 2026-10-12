"""Sequential native frame observations, after all competing QA jobs finish."""
import argparse,hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
ap=argparse.ArgumentParser();ap.add_argument('--version',required=True);ap.add_argument('--qa',type=Path,required=True);ap.add_argument('--before-version',default='3.0.0-rc26-preview')
args=ap.parse_args();folder=args.qa.resolve();folder.mkdir(parents=True,exist_ok=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
rows=[]
for name,version,case,duration in [('before-stress',args.before_version,'stress',20),('stress',args.version,'stress',20),('bridge',args.version,'bridge',160),('long',args.version,'long',160),('phone',args.version,'phone',160)]:
 pack=ROOT/f'release/{version}/windows/PaperWarfront.exe'
 dest=folder/name
 cmd=[sys.executable,str(ROOT/'tools/paper-warfront/check_realtime_battle.py'),'--pack',str(pack),'--output',str(dest),'--case',case,'--duration',str(duration)]
 result=subprocess.run(cmd,cwd=ROOT,capture_output=True,encoding='utf-8',errors='replace',timeout=duration+120)
 (folder/(name+'-runner.log')).write_text(result.stdout+result.stderr,'utf-8')
 assert result.returncode==0,result.stdout[-1500:]+result.stderr[-1500:]
 receipt=json.loads((dest/'receipt.json').read_text('utf-8'))
 assert receipt['passed']
 row={'case':name,'version':version,'receipt_sha256':sha(dest/'receipt.json'),'report_sha256':sha(dest/'report.json'),'fps_from_mean_interval':1000/receipt['intervals_steady']['mean_ms'],'p95_frame_ms':receipt['intervals_steady']['p95_ms'],'app_cpu_mean_ms':receipt['app_process_steady']['mean_ms'],'draw_cpu_mean_ms':receipt['draw_callback_steady']['mean_ms'],'wall_seconds':receipt['wall_seconds'],'simulation_seconds':receipt['simulation_seconds'],'max_units':receipt['max_units'],'max_texture_bytes':receipt['max_texture_bytes']}
 rows.append(row);print(json.dumps(row),flush=True)
report={'passed':True,'version':args.version,'runner_sha256':sha(Path(__file__)),'cases':rows,'normal_55fps_target_met':all(r['fps_from_mean_interval']>=55 and r['p95_frame_ms']<=25 for r in rows if r['case'] in ['bridge','long','phone']),'capacity_60fps_target_met':rows[1]['fps_from_mean_interval']>=59 and rows[1]['p95_frame_ms']<=25,'scope':'Sequential native Windows real-time compiled App frames. Normal AI cases and deliberately sustained124-actor capacity fixture are separate. FPS targets are reported honestly, independent of successful capture/integrity checks. Phone layout on Windows is not Android hardware.'}
(folder/'report.json').write_text(json.dumps(report,indent=2),'utf-8')
