from pathlib import Path
import os
import numpy as np
import soundfile as sf
import torch
from qwen_tts import Qwen3TTSModel

OUT = Path('build/qwen_reference_style_speakers')
OUT.mkdir(parents=True, exist_ok=True)

speaker = os.environ['SPEAKER']
text = (
    '만약요. 한국에서 진짜로 사우디급 석유가 터졌다면요? '
    '그냥 부자가 되는 걸로 끝나지 않습니다. '
    '경제도, 외교도, 군사도. 아예 판이 바뀌어요. '
    '특히 1970년대에 발견됐다면? 이야기는 더 커집니다.'
)

model = Qwen3TTSModel.from_pretrained(
    'Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice',
    device_map='cpu',
    dtype=torch.float32,
)

instruction = (
    '한국어 서울 표준어. 20대 중후반 남성 유튜버처럼 자연스럽게 말한다. '
    '낮고 무거운 다큐 성우톤이 아니라 밝고 가벼우며 선명한 중고역의 남성 목소리. '
    '평균 음역은 비교적 높은 편이고, 문장 안에서 높낮이 변화가 크다. '
    '쉼은 매우 짧고 말이 거의 끊기지 않으며, 핵심 단어 직전에 아주 짧게 멈췄다가 강세를 준다. '
    '질문형 구절은 끝을 살짝 올리고, 결론형은 짧게 끊는다. '
    '문장 전체를 일정한 속도로 읽지 말고, 연결어는 빨리 넘기고 중요한 단어와 숫자만 살짝 느리게 강조한다. '
    '앞쪽 공명과 약간의 비음, 가벼운 공기감이 있으며, 말이 앞으로 튀어나오는 느낌. '
    '뉴스 앵커, 광고 성우, 무거운 다큐멘터리, 로봇처럼 일정한 리듬은 피한다. '
    '특정 실제 인물의 목소리를 복제하지 않고, 제공된 일반적인 음성 특성만 구현한다.'
)

wavs, sr = model.generate_custom_voice(
    text=text,
    language='Korean',
    speaker=speaker,
    instruct=instruction,
)

wav = np.asarray(wavs[0], dtype=np.float32)
peak = float(np.max(np.abs(wav))) if wav.size else 1.0
if peak > 0.98:
    wav = wav * (0.98 / peak)

sf.write(OUT / f'{speaker.lower()}_korean.wav', wav, sr, subtype='PCM_16')
print(speaker, 'duration_sec', len(wav)/float(sr))
