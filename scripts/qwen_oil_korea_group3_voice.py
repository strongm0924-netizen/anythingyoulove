from pathlib import Path
import ast, os, json
import numpy as np
import soundfile as sf
import torch
from qwen_tts import Qwen3TTSModel

# Read the scene dictionary without executing the original TTS script.
source = Path('scripts/qwen_oil_korea_60scene_voice.py').read_text(encoding='utf-8')
tree = ast.parse(source)
SCENES = None
for node in tree.body:
    if isinstance(node, ast.Assign):
        if any(isinstance(t, ast.Name) and t.id == 'SCENES' for t in node.targets):
            SCENES = ast.literal_eval(node.value)
            break
if SCENES is None:
    raise RuntimeError('SCENES not found')

start=int(os.environ['START_SCENE']); end=int(os.environ['END_SCENE'])
texts=[SCENES[i] for i in range(start,end+1)]
text=' '.join(texts)

OUT=Path('build/qwen_oil_korea_group3'); OUT.mkdir(parents=True,exist_ok=True)
model=Qwen3TTSModel.from_pretrained('Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice',device_map='cpu',dtype=torch.float32)
instruction=(
 '대한민국 서울 표준어를 사용하는 20대 후반 남성 유튜버처럼 자연스럽게 말한다. '
 '외래어와 숫자도 한국인이 일상적으로 읽는 방식으로 발음한다. '
 '특히 사우디아라비아의 첫 음절 사는 된소리 ㅆ이 아니라 평음 ㅅ으로 자연스럽게 발음한다. '
 '문장 사이와 단어 사이의 쉼은 짧다. 의미상 꼭 필요한 경우가 아니면 길게 멈추지 않는다. '
 '실제 사람이 카메라 앞에서 흥미로운 이야기를 설명하듯 속도와 억양을 자연스럽게 바꾼다. '
 '중요한 단어에서만 자연스럽게 강세를 주며 뉴스 앵커나 광고 성우처럼 과장하지 않는다. '
 '기계적으로 일정한 리듬, 외국인 억양, 과도한 저음, 금속성 발성을 피한다.'
)
torch.manual_seed(18000+start)
wavs,sr=model.generate_custom_voice(text=text,language='Korean',speaker='Dylan',instruct=instruction,do_sample=True,temperature=0.75,top_p=0.9)
wav=np.asarray(wavs[0],dtype=np.float32)
peak=float(np.max(np.abs(wav))) if wav.size else 1.0
if peak>0.96: wav*=0.96/peak
base=f'group_{start:02d}_{end:02d}'
sf.write(OUT/f'{base}.wav',wav,sr,subtype='PCM_16')
(OUT/f'{base}.json').write_text(json.dumps({'start':start,'end':end,'lengths':[len(x) for x in texts],'texts':texts},ensure_ascii=False),encoding='utf-8')
print(base,len(wav)/float(sr))
