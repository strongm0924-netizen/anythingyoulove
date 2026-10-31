from pathlib import Path
import os
import numpy as np
import soundfile as sf
import torch
from qwen_tts import Qwen3TTSModel

OUT = Path('build/qwen_reference_style_fast')
OUT.mkdir(parents=True, exist_ok=True)
speaker = os.environ['SPEAKER']
text = (
    '만약요. 한국에서 진짜로 사우디급 석유가 터졌다면요? '
    '그냥 부자가 되는 걸로 끝나지 않습니다. '
    '경제도, 외교도, 군사도. 아예 판이 바뀌어요.'
)
model = Qwen3TTSModel.from_pretrained(
    'Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice',
    device_map='cpu', dtype=torch.float32,
)
instruction = (
    '한국어 서울 표준어. 20대 중후반 남성 유튜버. 밝고 가벼운 중고역 남성 목소리. '
    '평균 음역은 높은 편이고 문장 안에서 억양 변화가 크다. 거의 쉬지 않고 빠르게 연결한다. '
    '연결어는 빠르게 넘기고 핵심 단어만 순간적으로 강하게 강조한다. 질문은 살짝 올리고 결론은 짧게 끊는다. '
    '앞쪽 공명, 약한 비음과 공기감, 말이 앞으로 튀어나오는 느낌. '
    '뉴스 앵커, 광고 성우, 무거운 다큐, 로봇 같은 일정한 리듬은 피한다. 특정 인물을 복제하지 않는다.'
)
wavs, sr = model.generate_custom_voice(text=text, language='Korean', speaker=speaker, instruct=instruction)
wav = np.asarray(wavs[0], dtype=np.float32)
peak = float(np.max(np.abs(wav))) if wav.size else 1.0
if peak > 0.98: wav *= 0.98/peak
sf.write(OUT/f'{speaker.lower()}.wav', wav, sr, subtype='PCM_16')
print(speaker, len(wav)/float(sr))
