from pathlib import Path
import numpy as np
import soundfile as sf
import torch
from qwen_tts import Qwen3TTSModel

OUT = Path('build/qwen_voice_style_design_test')
OUT.mkdir(parents=True, exist_ok=True)

text = (
    '만약 대한민국 땅 아래에 사우디아라비아급 석유가 묻혀 있었다면 어떨까요. '
    '그것도 1970년대, 한국이 아직 가난한 개발도상국이던 시절에 초대형 유전이 발견됐다고 가정해 보겠습니다.'
)

model = Qwen3TTSModel.from_pretrained(
    'Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign',
    device_map='cpu',
    dtype=torch.float32,
)

instruction = (
    '젊은 성인 남성, 밝은 테너 계열의 자연스러운 한국어 유튜브 내레이터. '
    '평균 음역은 일반 남성보다 약간 높고 약 170Hz 전후의 밝은 중심감을 가지며, '
    '문장 안에서 높낮이가 크게 움직이고 핵심 단어에서 자연스럽게 음을 올린다. '
    '말속도는 보통보다 약간 빠르고, 문장 사이 쉼은 짧으며 끊김 없이 매끄럽게 이어간다. '
    '발음은 또렷하지만 뉴스 앵커처럼 힘주지 않고, 친한 사람에게 흥미로운 이야기를 설명하듯 편안하다. '
    '가볍고 생동감 있는 에너지, 선명한 중고역, 자연스러운 호흡, 약간의 미소가 느껴지는 발성. '
    '저음이 과하거나 무거운 다큐멘터리 톤, 로봇처럼 일정한 리듬, 광고 성우처럼 과장된 톤은 피한다. '
    '특정 실제 인물의 목소리를 복제하지 말고, 위의 일반적인 음성 스타일만 구현한다.'
)

wavs, sr = model.generate_voice_design(
    text=text,
    language='Korean',
    instruct=instruction,
    do_sample=True,
    temperature=0.85,
    top_p=0.9,
)

wav = np.asarray(wavs[0], dtype=np.float32)
peak = float(np.max(np.abs(wav))) if wav.size else 1.0
if peak > 0.98:
    wav = wav * (0.98 / peak)

sf.write(OUT / 'style_test.wav', wav, sr, subtype='PCM_16')
(OUT / 'instruction.txt').write_text(instruction, encoding='utf-8')
print('duration_sec', len(wav)/float(sr))
