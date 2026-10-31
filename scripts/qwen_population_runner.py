from pathlib import Path
import os, numpy as np, soundfile as sf, torch
from qwen_tts import Qwen3TTSModel

ROOT=Path('scripts/population_chunks')
OUT=Path('build/qwen_population_100'); OUT.mkdir(parents=True,exist_ok=True)
SCENES={}
for p in sorted(ROOT.glob('*.txt')):
    for line in p.read_text(encoding='utf-8').splitlines():
        if not line.strip(): continue
        k,v=line.split('\t',1); SCENES[int(k)]=v
start=int(os.environ['START_SCENE']); end=int(os.environ['END_SCENE'])
model=Qwen3TTSModel.from_pretrained('Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice',device_map='cpu',dtype=torch.float32)
instruction=('대한민국 서울 표준어를 사용하는 20대 후반 남성 유튜버처럼 자연스럽게 말한다. 외래어와 숫자는 한국인이 일상적으로 읽는 방식으로 자연스럽게 발음한다. 문장 사이와 단어 사이의 쉼은 짧게 유지한다. 실제 사람이 흥미로운 이야기를 설명하듯 문장마다 속도와 억양을 조금씩 바꾼다. 중요한 단어에서만 자연스럽게 강세를 주고 뉴스 앵커나 광고 성우처럼 과장하지 않는다. 기계적으로 일정한 리듬, 외국인 억양, 과도한 저음, 금속성 발성을 피한다.')
for idx in range(start,end+1):
    torch.manual_seed(25000+idx)
    wavs,sr=model.generate_custom_voice(text=SCENES[idx],language='Korean',speaker='Dylan',instruct=instruction,do_sample=True,temperature=0.75,top_p=0.9)
    wav=np.asarray(wavs[0],dtype=np.float32)
    peak=float(np.max(np.abs(wav))) if wav.size else 1.0
    if peak>0.96: wav*=0.96/peak
    sf.write(OUT/f'scene_{idx:03d}.wav',wav,sr,subtype='PCM_16')
    print(idx,len(wav)/float(sr))
