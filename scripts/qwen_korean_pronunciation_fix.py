from pathlib import Path
import numpy as np
import soundfile as sf
import torch
from qwen_tts import Qwen3TTSModel

OUT = Path('build/qwen_korean_pronunciation_fix')
OUT.mkdir(parents=True, exist_ok=True)

# Wording chosen to sound natural in spoken Korean and avoid an unnatural compound rush.
text = (
    '만약 한국에서, 사우디아라비아에 맞먹는 규모의 석유가 발견됐다면요. '
    '이건 그냥 돈이 많아지는 문제로 끝나지 않습니다. '
    '경제도 바뀌고, 외교도 바뀌고, 군사 전략까지 완전히 달라졌을 가능성이 큽니다. '
    '특히 그 발견 시점이 1970년대였다면, 이야기는 훨씬 더 커집니다.'
)

model = Qwen3TTSModel.from_pretrained(
    'Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice',
    device_map='cpu',
    dtype=torch.float32,
)

instruction = (
    '대한민국 서울 표준어를 사용하는 20대 후반 남성 유튜버처럼 자연스럽게 말한다. '
    '외래어도 한국인이 일상적으로 발음하는 방식으로 읽는다. '
    '특히 "사우디아라비아"의 첫 음절 "사"는 된소리 ㅆ이 아니라 평음 ㅅ으로, '
    '자연스럽게 "사-우-디-아-라-비-아"라고 발음한다. 절대로 "싸우디"처럼 발음하지 않는다. '
    '문장마다 속도와 억양이 조금씩 달라지고, 중요한 단어에서만 자연스럽게 강세를 준다. '
    '뉴스 앵커나 광고 성우처럼 또박또박 과장하지 말고, 실제 사람이 설명하듯 편안하게 말한다. '
    '기계적으로 일정한 리듬, 외국인 억양, 과도한 저음, 금속성 발성을 피한다.'
)

torch.manual_seed(9021)
wavs, sr = model.generate_custom_voice(
    text=text,
    language='Korean',
    speaker='Dylan',
    instruct=instruction,
    do_sample=True,
    temperature=0.8,
    top_p=0.9,
)

wav = np.asarray(wavs[0], dtype=np.float32)
peak = float(np.max(np.abs(wav))) if wav.size else 1.0
if peak > 0.96:
    wav = wav * (0.96 / peak)

sf.write(OUT / 'korean_natural_pronunciation.wav', wav, sr, subtype='PCM_16')
(OUT / 'instruction.txt').write_text(instruction, encoding='utf-8')
print('duration_sec', len(wav)/float(sr))
