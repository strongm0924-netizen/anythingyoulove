from pathlib import Path
import os, numpy as np, soundfile as sf, torch
from qwen_tts import Qwen3TTSModel

OUT=Path('build/qwen_voice_cadence_parallel'); OUT.mkdir(parents=True,exist_ok=True)
variant=os.environ['VOICE_VARIANT']
text=(
 '만약요. 한국에서, 진짜로 사우디급 석유가 터졌다면요? '
 '그냥 부자가 되는 걸로 끝나지 않습니다. '
 '경제도, 외교도, 군사도. 아예 판이 바뀌어요. '
 '특히 1970년대에 발견됐다면? 이야기는 더 커집니다.'
)
base=(
 '20대 중후반의 한국 남성 콘텐츠 크리에이터. 낮고 무거운 성우가 아니라 밝고 가벼운 테너-바리톤 사이의 말소리. '
 '가슴 울림은 적고 앞쪽 공명과 약간의 비음, 공기감이 있어 말이 가볍게 앞으로 튀어나온다. '
 '발음은 또렷하지만 교과서처럼 읽지 않고, 실제 유튜버가 카메라 앞에서 즉흥적으로 설명하는 느낌. '
 '0.4초에서 0.9초 정도의 짧은 의미 단위로 툭툭 던지고, 긴 문장도 한 호흡에 평평하게 읽지 않는다. '
 '짧은 쉼은 0.1~0.25초 정도로 자주 넣고, 중요한 단어 직전에는 아주 짧게 멈췄다가 강세를 준다. '
 '질문형 구절은 끝을 살짝 올리고, 결론형 구절은 짧고 단단하게 떨어뜨린다. '
 '문장 시작마다 같은 높이에서 시작하지 말고, 중간 단어를 살짝 끌어올렸다가 바로 내려오는 자연스러운 억양을 쓴다. '
 '말속도는 빠른 편이지만 숨이 차 보이지 않고, 연결어는 가볍게 넘기며 핵심 명사와 숫자에만 힘을 준다. '
 '약간 웃는 듯한 밝은 에너지와 친근한 말맛이 있지만 광고 성우처럼 과장하지 않는다. '
 '뉴스 앵커 톤, 다큐멘터리 저음, 지나치게 매끈한 TTS 리듬, 매 문장 같은 속도와 같은 억양은 피한다. '
 '특정 실제 인물의 목소리를 복제하지 말고, 이 일반적인 말하기 스타일만 구현한다. '
)
extras={
 'cadence_a':'가장 자연스러운 대화체. 단어 사이 미세한 속도 변화가 많고, 강조 직전 짧은 멈춤이 분명하다. 말끝은 짧게 끊고 호기심과 확신을 번갈아 표현한다.',
 'cadence_b':'조금 더 장난기 있고 생동감 있는 유튜브 설명 말투. 핵심 구절에서는 속도를 순간적으로 늦추고 바로 다음 구절은 빠르게 이어간다. 문장마다 강세 위치가 다르고 가벼운 숨 섞임이 느껴진다.',
 'cadence_c':'조금 더 담백하고 현실적인 말투. 중요한 단어에서는 분명하게 에너지를 올린다. 질문은 가볍게 상승, 설명은 중립, 결론은 짧게 하강한다.'
}
model=Qwen3TTSModel.from_pretrained('Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign',device_map='cpu',dtype=torch.float32)
seed={'cadence_a':3401,'cadence_b':3402,'cadence_c':3403}[variant]; torch.manual_seed(seed)
wavs,sr=model.generate_voice_design(text=text,language='Korean',instruct=base+extras[variant],do_sample=True,temperature=1.0,top_p=0.96)
wav=np.asarray(wavs[0],dtype=np.float32); peak=float(np.max(np.abs(wav))) if wav.size else 1.0
if peak>0.98: wav*=0.98/peak
sf.write(OUT/f'{variant}.wav',wav,sr,subtype='PCM_16')
(OUT/f'{variant}.txt').write_text(base+extras[variant],encoding='utf-8')
print(variant, len(wav)/float(sr))
