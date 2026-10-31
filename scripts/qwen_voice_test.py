from pathlib import Path
import json
import numpy as np
import soundfile as sf
import torch
from qwen_tts import Qwen3TTSModel

ROOT = Path('.')
BUILD = ROOT / 'build' / 'qwen_voice_test'
BUILD.mkdir(parents=True, exist_ok=True)
scenes = json.loads((ROOT / 'video' / 'scenes.json').read_text(encoding='utf-8'))

# First scene is short enough to audition timbre and Korean prosody.
text = scenes[0]['narration']

# 0.6B keeps CPU inference practical on a GitHub-hosted runner while using
# the same Qwen3-TTS family/prosody controls as the larger model.
model = Qwen3TTSModel.from_pretrained(
    'Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice',
    device_map='cpu',
    dtype=torch.float32,
)

instruction = (
    '한국어를 서울 표준어로 자연스럽게 말한다. '
    '20대 후반에서 30대 초반의 남성 지식 유튜버 같은 목소리. '
    '밝고 선명한 중음역이지만 가볍지 않고, 차분한 자신감이 있다. '
    '문장마다 실제 사람처럼 높낮이와 속도가 조금씩 변하며 자연스럽게 호흡한다. '
    '뉴스 앵커처럼 과하게 딱딱하지 않고 친구에게 흥미로운 역사를 설명하듯 말한다. '
    '외국인 억양, 로봇처럼 일정한 리듬, 과장된 감정, 과도한 저음은 피한다.'
)

for speaker in ['Aiden', 'Ryan']:
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
    sf.write(BUILD / f'{speaker.lower()}_korean.wav', wav, sr, subtype='PCM_16')

(BUILD / 'script.txt').write_text(text, encoding='utf-8')
print('generated', sorted(str(p) for p in BUILD.glob('*.wav')))
