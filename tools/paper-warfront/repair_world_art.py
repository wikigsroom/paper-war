"""Regenerate the three silhouettes rejected by the boundary audit, same selected model."""
from pathlib import Path
import json,subprocess,sys,os
from generate_world_art import SKILL,WEAPONS
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'output/imagegen/paper-warfront/world-v2/repairs'
def main():
    OUT.mkdir(parents=True,exist_ok=True);sys.stdout.reconfigure(encoding='utf-8')
    balance=json.loads((ROOT/'game/data/balance-prototype.json').read_text(encoding='utf-8'))
    factions={f['id']:f for f in json.loads((ROOT/'game/data/factions.json').read_text(encoding='utf-8'))['factions']}
    for uid in ['unit.shuang.medic','unit.shuang.javelin','unit.bai.berserker']:
        dest=OUT/(uid.replace('.','-')+'.png')
        if dest.exists():continue
        u=balance['units'][uid];f=factions[u['faction']]
        prompt=f'''One isolated FULL-BODY game sprite on TRANSPARENT background. Canvas 1024x1024. Entire soldier AND all weapons AND two feet strictly within an 800x800 centered safe box, at least 112 pixels of completely transparent margin on every side. Nothing touches the canvas boundary. No shadow on the background. Only ONE character. Facing right in side/three-quarter view. Two separated feet suitable for paper-puppet animation. Neutral ready pose, no text or symbols resembling letters, no frame, scenery, ground or other characters.
Original cut-paper soldier from Paper Warfront. Faction {f['name']}. Motifs {f['motif']}. Main accent #{f['color']}, ivory rag paper, muted tan, dark charcoal contour. Original cute large-head martial paper puppet with layered folded-cardboard armor, clearly cut beveled paper edges, very subtle fiber texture, crisp clean broad opaque silhouette, flat even studio light. The texture exists ONLY inside the sprite silhouette. Weapon and role: {WEAPONS[u['role']]}. Big clearly readable weapon shape that stays fully inside the safe box. Keep the distinctive faction material motifs. No existing game character imitation. Transparent empty canvas, absolutely no beige paper background, no gradient, no vignette.''' 
        prompt_path=dest.with_suffix('.txt');prompt_path.write_text(prompt,encoding='utf-8')
        print('Repairing '+uid,flush=True)
        result=subprocess.run([sys.executable,str(SKILL),'generate','--prompt-file',str(prompt_path),'--model','gpt-image-2.5','--quality','high','--size','1024x1024','--background','transparent','--output-format','png','--out',str(dest)],capture_output=True,env={**os.environ,'PYTHONIOENCODING':'utf-8'})
        if result.returncode:print('Selected gateway repair failed; no fallback.');raise SystemExit(result.returncode)
        print(uid+' regenerated; boundary review pending',flush=True)
if __name__=='__main__':main()
