"""Original pentatonic paper-stage music. Offline native synthesis, no audio service."""
from pathlib import Path
import numpy as np, wave, json, hashlib, shutil
ROOT=Path(__file__).resolve().parents[2]
RATE=22050
BPM=96
BEAT=60/BPM
DURATION=32*BEAT*2

def add_pluck(out,at,midi,length,gain,wood=.25):
    n=int(length*RATE); t=np.arange(n)/RATE
    f=440*2**((midi-69)/12)
    env=(1-np.exp(-t*800))*np.exp(-t*6/max(.15,length))
    sound=(np.sin(2*np.pi*f*t)+wood*np.sin(2*np.pi*f*2*t)+.14*np.sin(2*np.pi*f*3*t))*env*gain
    offset=int(at*RATE)
    end=min(len(out),offset+n)
    if end>offset:out[offset:end]+=sound[:end-offset]

def main():
    dest=ROOT/'assets/paper-warfront/audio/music';dest.mkdir(exist_ok=True)
    runtime=ROOT/'game/assets/audio/music';runtime.mkdir(parents=True,exist_ok=True)
    patterns={'yin':[0,4,7,9,7,4,2,0,4,7,12,9,7,4,2,4],
              'mo':[0,3,7,10,7,3,0,-2,3,7,10,12,10,7,3,0],
              'deng':[0,2,4,7,9,12,9,7,4,7,9,14,12,9,7,4],
              'ji':[0,7,0,4,7,9,7,4,2,7,2,5,9,7,5,2],
              'yuan':[0,2,7,9,14,12,9,7,2,4,9,12,16,14,12,9],
              'qi':[0,4,7,4,9,7,4,2,0,7,9,12,9,7,4,2],
              'mu':[0,2,5,7,9,7,5,2,0,5,7,12,9,7,5,0],
              'shuang':[0,7,2,9,4,12,7,14,12,9,7,4,9,7,2,0],
              'jin':[0,3,5,7,10,7,5,3,0,7,10,12,10,7,5,0],
              'bai':[0,2,7,2,9,4,12,7,2,9,14,12,7,4,2,0]}
    records=[]
    for faction,melody in patterns.items():
        out=np.zeros(int(DURATION*RATE),dtype=np.float64)
        rng=np.random.default_rng(int(hashlib.sha256(faction.encode()).hexdigest()[:8],16))
        root={'yin':50,'mo':45,'deng':55,'ji':47,'yuan':57,'qi':52,'mu':48,'shuang':54,'jin':43,'bai':51}[faction]
        for step in range(128):
            at=step*BEAT*.5
            bar=step//8
            harmony=[0,-2,5,0][(bar//2)%4]
            if step%2==0:
                note=melody[(step//2)%16]+root+12+(12 if bar in [6,7,14,15] and step%8==6 else 0)
                add_pluck(out,at,note,.65,.075 if faction!='mo' else .065,.33 if faction=='yin' else .16)
            if step%4==0:
                add_pluck(out,at,root+harmony,1.1,.1,.16)
                add_pluck(out,at+.015,root+harmony+7,.8,.035,.1)
            if step%2==1 and faction=='deng': add_pluck(out,at,root+24+melody[(step//2+3)%16],.35,.03,.1)
            # Paper brush texture and two-register wooden drum.
            length=.095 if step%4 else .22
            t=np.arange(int(length*RATE))/RATE
            tone=110 if step%4==0 else 225
            drum=np.sin(2*np.pi*(tone*t-60*t*t))*np.exp(-t*27)
            noise=rng.uniform(-1,1,len(t));noise=np.convolve(noise,np.ones(6)/6,mode='same')
            click=(drum*.065+noise*.045)*np.minimum(1,t/.002)*np.exp(-t*8)
            offset=int(at*RATE);end=min(len(out),offset+len(t))
            out[offset:end]+=click[:end-offset]
        # A seamless release into the loop start; no hard PCM boundary.
        fade=int(RATE*.02);out[:fade]*=np.linspace(0,1,fade);out[-fade:]*=np.linspace(1,0,fade)
        out=np.tanh(out*1.35);peak=float(np.max(np.abs(out)));out*=.46/max(peak,.46)
        file=dest/f'music-{faction}.wav'
        with wave.open(str(file),'wb') as wav:
            wav.setnchannels(1);wav.setsampwidth(2);wav.setframerate(RATE);wav.writeframes((out*32767).astype('<i2').tobytes())
        shutil.copy2(file,runtime/file.name)
        records.append({'id':'audio.music.'+faction,'path':str(file.relative_to(ROOT)).replace('\\','/'),'duration':DURATION,'sample_rate':RATE,'peak':float(np.max(np.abs(out))),'sha256':hashlib.sha256(file.read_bytes()).hexdigest(),'generator':'tools/paper-warfront/master_music.py'})
    (dest/'music-manifest.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Ten original 40-second faction music loops mastered at 22050 Hz')

if __name__=='__main__':main()
