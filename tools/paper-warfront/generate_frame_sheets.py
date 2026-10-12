"""Bounded native image generation batch; the original skill owns all credentials."""
from pathlib import Path
import argparse,concurrent.futures,json,subprocess,sys,hashlib,time
ROOT=Path(__file__).resolve().parents[2]
SKILL=Path('C:/Users/carzy/.codex/skills/sub2-image-gen/scripts/sub2_image_gen.py')
OUT=ROOT/'output/imagegen/paper-warfront/frame-rebuild'

def generate(row):
    target=ROOT/row['raw']
    if target.exists():return {'id':row['id'],'status':'existing-candidate','bytes':target.stat().st_size}
    args=[sys.executable,str(SKILL),'edit','--image',str(ROOT/row['source']),'--image',str(OUT/'animation-layout-reference.png'),'--prompt-file',str(ROOT/row['prompt']),'--model','gpt-image-2.5','--size','1536x1536','--quality','high','--background','transparent','--out',str(target)]
    if row.get('layout_guide'):args[7:7]=['--image',str(ROOT/row['layout_guide'])]
    start=time.monotonic()
    for retry in range(5):
        log=target.parent/(row['id'].replace('.','-')+'.generation.log')
        attempt=1
        while log.exists():
            attempt+=1;log=target.parent/(row['id'].replace('.','-')+f'.generation-attempt-{attempt}.log')
        with log.open('w',encoding='utf-8') as stream:
            result=subprocess.run(args,cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
        if result.returncode==0 and target.exists():break
        message=log.read_text(encoding='utf-8',errors='replace')
        if retry==4 or not ('429' in message or 'gateway_concurrency_limit' in message or 'timed out' in message):break
        time.sleep(20)
    return {'id':row['id'],'status':'candidate-generated' if result.returncode==0 and target.exists() else 'generation-failed','exit':result.returncode,'seconds':round(time.monotonic()-start,1),'bytes':target.stat().st_size if target.exists() else 0}

def main():
    sys.stdout.reconfigure(encoding='utf-8');p=argparse.ArgumentParser();p.add_argument('--workers',type=int,default=3);p.add_argument('--ids',nargs='*');args=p.parse_args()
    rows=json.loads((ROOT/'assets/paper-warfront/frame-rebuild/unit-briefs.json').read_text(encoding='utf-8'))['units']
    if args.ids:rows=[r for r in rows if r['id'] in args.ids]
    results=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(3,max(1,args.workers))) as pool:
        futures={pool.submit(generate,r):r for r in rows}
        for future in concurrent.futures.as_completed(futures):
            r=future.result();results.append(r);print(json.dumps(r,ensure_ascii=False),flush=True)
            (OUT/'generation-progress.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
    failures=[r['id'] for r in results if r['status']=='generation-failed']
    print(json.dumps({'complete':len(results),'failed':failures},ensure_ascii=False),flush=True)
    if failures:raise SystemExit(1)

if __name__=='__main__':main()
