from pathlib import Path
import numpy as np
import soundfile as sf
import torch
from qwen_tts import Qwen3TTSModel

OUT = Path('build/qwen_humanlike_voice_test')
OUT.mkdir(parents=True, exist_ok=True)

text = (
    '만약 한국에서 진짜 사우디급 석유가 터졌다면요. '
    '이건 그냥 돈이 많아지는 문제가 아닙니다. '
    '경제도 바뀌고요, 외교도 바뀌고, 군사 전략까지 완전히 달라졌을 가능성이 큽니다. '
    '특히 그 발견 시점이 1970년대였다면, 이야기는 훨씬 더 커집니다.'
)

model = Qwen3TTSModel.from_pretrained(
    'Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign',
    device_map='cpu',
    dtype=torch.float32,
)

instruction = (
    '한국의 실제 20대 후반 남성이 마이크 앞에서 자연스럽게 말하는 듯한 음성. '
    '성우처럼 완벽하게 다듬어진 목소리가 아니라, 실제 사람이 말할 때 생기는 미세한 불균일함이 있어야 한다. '
    '문장마다 말속도가 조금씩 다르고, 같은 높이와 같은 리듬을 반복하지 않는다. '
    '짧은 들숨과 아주 미세한 숨 섞임, 살짝 거친 성대 질감, 약한 비음과 앞쪽 공명이 자연스럽게 섞인다. '
    '자음은 또렷하지만 지나치게 정제하지 말고, 모음 길이도 완전히 균일하지 않게 한다. '
    '강조 단어 앞에서는 속도가 아주 조금 느려지고, 강조 뒤에는 자연스럽게 다시 빨라진다. '
    '문장 끝은 매번 똑같이 떨어뜨리지 말고, 질문은 약하게 상승하고 설명은 중립적으로 끝내며 결론은 짧게 내려준다. '
    '전체 음역은 밝은 남성 중음에서 중고음 사이. 너무 높거나 너무 저음이지 않다. '
    '친구에게 흥미로운 이야기를 설명하는 유튜버 같은 에너지는 있지만, 방송 성우나 광고 성우처럼 과장하지 않는다. '
    '완벽한 발음, 완벽한 박자, 지나치게 매끈한 음질, 로봇처럼 일정한 억양, 합성음 특유의 금속성은 피한다. '
    '특정 실존 인물의 목소리는 복제하지 않는다.'
)

torch.manual_seed(7319)
wavs, sr = model.generate_voice_design(
    text=text,
    language='Korean',
    instruct=instruction,
    do_sample=True,
    temperature=1.05,
    top_p=0.97,
)

wav = np.asarray(wavs[0], dtype=np.float32)
peak = float(np.max(np.abs(wav))) if wav.size else 1.0
if peak > 0.95:
    wav = wav * (0.95 / peak)

sf.write(OUT / 'humanlike_voice.wav', wav, sr, subtype='PCM_16')
(OUT / 'instruction.txt').write_text(instruction, encoding='utf-8')
print('duration_sec', len(wav)/float(sr))
