from pathlib import Path
import argparse, json
import numpy as np
import soundfile as sf
import torch
from qwen_tts import Qwen3TTSModel

parser = argparse.ArgumentParser()
parser.add_argument('--start', type=int, required=True)
parser.add_argument('--end', type=int, required=True)
args = parser.parse_args()

ROOT = Path('.')
OUT = ROOT / 'build' / 'qwen_parts'
OUT.mkdir(parents=True, exist_ok=True)
scenes = json.loads((ROOT / 'video' / 'scenes.json').read_text(encoding='utf-8'))

model = Qwen3TTSModel.from_pretrained(
    'Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice',
    device_map='cpu',
    dtype=torch.float32,
)

instruction = (
    '한국어 서울 표준어로 말한다. 20대 후반에서 30대 초반의 한국 남성 지식 유튜버 느낌. '
    '밝고 선명한 중음역이며 따뜻하고 자연스럽다. 다큐멘터리 내레이션이지만 뉴스 앵커처럼 딱딱하지 않다. '
    '친한 사람에게 흥미로운 역사 이야기를 들려주듯 자연스럽고 자신감 있게 말한다. '
    '문장마다 높낮이와 속도를 조금씩 바꾸고 쉼표와 마침표에서 실제 사람처럼 짧게 호흡한다. '
    '중요한 단어에는 자연스러운 강세를 주되 연기하듯 과장하지 않는다. '
    '로봇처럼 일정한 리듬, 외국인 억양, 과한 저음, 과한 감정, 광고 성우 같은 억양은 피한다.'
)

for scene in scenes:
    sid = int(scene['id'])
    if not (args.start <= sid <= args.end):
        continue
    print(f'Generating scene {sid:02d}', flush=True)
    wavs, sr = model.generate_custom_voice(
        text=scene['narration'],
        language='Korean',
        speaker='Aiden',
        instruct=instruction,
    )
    wav = np.asarray(wavs[0], dtype=np.float32)
    peak = float(np.max(np.abs(wav))) if wav.size else 1.0
    if peak > 0.98:
        wav *= 0.98 / peak
    sf.write(OUT / f's{sid:02d}.wav', wav, sr, subtype='PCM_16')

print('done', args.start, args.end)
