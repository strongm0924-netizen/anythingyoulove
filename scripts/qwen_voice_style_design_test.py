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

variants = {
    'tenor_a': (
        '20대 초중반의 젊은 한국 남성. 매우 밝은 테너 계열의 자연스러운 말소리. '
        '말할 때 가슴 저음보다 머리 울림과 중고역이 강하고, 평소 남성보다 분명히 높은 음역에서 말한다. '
        '대화체 유튜브 내레이터처럼 약간 빠르게, 문장 사이 쉼은 짧게, 단어마다 생동감 있게 억양을 바꾼다. '
        '핵심 단어에서 자연스럽게 음을 올리고 문장 끝을 너무 낮게 떨어뜨리지 않는다. '
        '저음 다큐 성우, 뉴스 앵커, 로봇 같은 일정한 억양은 절대 피한다. 특정 인물은 복제하지 않는다.'
    ),
    'tenor_b': (
        '젊고 가벼운 한국 남성 유튜버 목소리. 남성으로 분명하게 들리지만 높은 테너 음역이며 밝고 선명하다. '
        '약간 웃는 듯한 발성, 빠르고 매끄러운 연결, 짧은 호흡, 큰 억양 변화가 있다. '
        '대부분의 문장을 높은 중음역에서 유지하고 중요한 단어에서 더 올라간다. '
        '차분한 다큐멘터리 톤보다 흥미로운 사실을 빠르게 설명하는 콘텐츠 크리에이터 말투에 가깝다. '
        '무겁거나 낮은 저음, 과도한 성우 톤, 외국인 억양, 단조로운 리듬은 피한다. 특정 인물은 복제하지 않는다.'
    ),
    'tenor_c': (
        '소년처럼 들리지는 않는 20대 후반 한국 남성. 밝고 높은 테너형 말소리, 얇지 않으면서도 중고역이 선명하다. '
        '말속도는 일반 회화보다 조금 빠르고, 쉼 없이 자연스럽게 이어지며, 문장 안에서 피치가 크게 움직인다. '
        '친구에게 신기한 역사 이야기를 들려주듯 편하고 생동감 있다. '
        '문장 끝을 지나치게 낮추지 말고, 핵심 구절마다 가볍게 상승 억양을 준다. '
        '저음 성우톤과 AI 특유의 일정한 리듬은 피한다. 특정 인물은 복제하지 않는다.'
    )
}

for idx, (name, instruction) in enumerate(variants.items(), start=1):
    torch.manual_seed(1200 + idx)
    wavs, sr = model.generate_voice_design(
        text=text,
        language='Korean',
        instruct=instruction,
        do_sample=True,
        temperature=0.95,
        top_p=0.95,
    )
    wav = np.asarray(wavs[0], dtype=np.float32)
    peak = float(np.max(np.abs(wav))) if wav.size else 1.0
    if peak > 0.98:
        wav = wav * (0.98 / peak)
    sf.write(OUT / f'{name}.wav', wav, sr, subtype='PCM_16')
    (OUT / f'{name}.txt').write_text(instruction, encoding='utf-8')
    print(name, 'duration_sec', len(wav)/float(sr))
