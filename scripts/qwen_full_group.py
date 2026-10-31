from pathlib import Path
import json, os
import numpy as np
import soundfile as sf
import torch
from qwen_tts import Qwen3TTSModel

ROOT = Path('.')
OUT = ROOT / 'build' / 'qwen_full'
OUT.mkdir(parents=True, exist_ok=True)
SCENES = json.loads((ROOT / 'video' / 'scenes.json').read_text(encoding='utf-8'))

start = int(os.environ['START_SCENE'])
end = int(os.environ['END_SCENE'])

model = Qwen3TTSModel.from_pretrained(
    'Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice',
    device_map='cpu',
    dtype=torch.float32,
)

instruction = (
    '한국어를 서울 표준어로 자연스럽게 말한다. '
    '20대 후반에서 30대 초반의 남성 지식·역사 유튜버 같은 목소리. '
    '밝고 선명한 중음역이며 과하게 저음이거나 광고톤이 아니다. '
    '실제 사람이 흥미로운 이야기를 설명하듯 문장마다 억양과 속도를 자연스럽게 변화시킨다. '
    '핵심 문장은 살짝 힘을 주고, 연결 문장은 편안하게 넘긴다. '
    '문장 사이에 짧고 자연스러운 호흡이 느껴져야 한다. '
    '뉴스 앵커처럼 지나치게 딱딱한 발성, 외국인 억양, 로봇처럼 일정한 리듬, '
    '감정을 과장하는 연기, 속삭임, 과도한 저음은 피한다.'
)

manifest = []
for scene in SCENES:
    sid = int(scene['id'])
    if not (start <= sid <= end):
        continue
    wavs, sr = model.generate_custom_voice(
        text=scene['narration'],
        language='Korean',
        speaker='Aiden',
        instruct=instruction,
    )
    wav = np.asarray(wavs[0], dtype=np.float32)
    peak = float(np.max(np.abs(wav))) if wav.size else 1.0
    if peak > 0.98:
        wav = wav * (0.98 / peak)
    out = OUT / f'scene_{sid:02d}.wav'
    sf.write(out, wav, sr, subtype='PCM_16')
    duration = len(wav) / float(sr)
    manifest.append({'id': sid, 'duration': duration, 'sample_rate': sr, 'file': out.name})
    print(f'scene {sid:02d}: {duration:.2f}s')

(OUT / f'manifest_{start:02d}_{end:02d}.json').write_text(
    json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8'
)
