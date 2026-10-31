from pathlib import Path
import json, re, subprocess, wave

from melo.api import TTS

ROOT = Path('.')
BUILD = ROOT / 'build'
VIDEO = ROOT / 'video'
MELO = BUILD / 'melo_voice'
MELO.mkdir(parents=True, exist_ok=True)

SCENES = json.loads((VIDEO / 'scenes.json').read_text(encoding='utf-8'))
MODEL = TTS(language='KR', device='cpu')
SPEAKER_ID = MODEL.hps.data.spk2id['KR']

# Slightly brisk delivery. Final timing is fitted to each existing scene.
MELO_SPEED = 1.03
# A very small pitch lift keeps the voice brighter without a chipmunk effect.
PITCH_FACTOR = 1.025


def run(cmd):
    subprocess.run(cmd, check=True)


def duration(path):
    r = subprocess.run(
        ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
         '-of', 'default=nw=1:nk=1', str(path)],
        capture_output=True, text=True, check=True
    )
    return float(r.stdout.strip())


def sentence_chunks(text):
    text = re.sub(r'\s+', ' ', text).strip()
    # Shorter chunks create more human-like breaths and reduce monotonous long-form prosody.
    parts = re.split(r'(?<=[.!?。！？])\s+|(?<=[다요죠])\.\s*', text)
    cleaned = [p.strip() for p in parts if p and p.strip()]
    if not cleaned:
        return [text]
    out = []
    for part in cleaned:
        if len(part) <= 95:
            out.append(part)
            continue
        # Secondary split for long Korean sentences.
        subs = re.split(r'(?<=[,，])\s*|(?=하지만|그리고|그래서|반대로|즉|결국|특히)', part)
        out.extend([s.strip() for s in subs if s.strip()])
    return out


def make_silence(path, ms=155, rate=44100):
    frames = int(rate * ms / 1000)
    with wave.open(str(path), 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(b'\x00\x00' * frames)


def concat_wavs(paths, out):
    lst = out.with_suffix('.txt')
    lst.write_text('\n'.join([f"file '{p.resolve().as_posix()}'" for p in paths]), encoding='utf-8')
    run(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0',
         '-i', str(lst), '-ar', '44100', '-ac', '1', '-c:a', 'pcm_s16le', str(out)])


def atempo_chain(factor):
    # ffmpeg atempo accepts 0.5..2.0. Chain when outside the range.
    vals = []
    while factor > 2.0:
        vals.append(2.0)
        factor /= 2.0
    while factor < 0.5:
        vals.append(0.5)
        factor /= 0.5
    vals.append(factor)
    return ','.join(f'atempo={v:.8f}' for v in vals)


def synth_scene(scene):
    sid = int(scene['id'])
    target = BUILD / 'audio' / f's{sid:02d}.mp3'
    target_dur = duration(target)
    chunks = sentence_chunks(scene['narration'])
    pieces = []
    silence = MELO / f's{sid:02d}_silence.wav'
    make_silence(silence)

    for i, text in enumerate(chunks, start=1):
        wav = MELO / f's{sid:02d}_{i:02d}.wav'
        MODEL.tts_to_file(text, SPEAKER_ID, str(wav), speed=MELO_SPEED)
        pieces.append(wav)
        if i < len(chunks):
            pieces.append(silence)

    raw = MELO / f's{sid:02d}_raw.wav'
    concat_wavs(pieces, raw)

    # First, raise pitch subtly while preserving the raw duration.
    pitched = MELO / f's{sid:02d}_pitched.wav'
    pitch_filter = (
        f'asetrate=44100*{PITCH_FACTOR},aresample=44100,'
        f'atempo={1.0 / PITCH_FACTOR:.8f}'
    )
    run(['ffmpeg', '-y', '-loglevel', 'error', '-i', str(raw), '-af', pitch_filter,
         '-ar', '44100', '-ac', '1', '-c:a', 'pcm_s16le', str(pitched)])

    current = duration(pitched)
    tempo = current / target_dur
    fitted = MELO / f's{sid:02d}_fitted.wav'
    filters = f"{atempo_chain(tempo)},highpass=f=65,lowpass=f=14500,loudnorm=I=-17:LRA=8:TP=-1.5"
    run(['ffmpeg', '-y', '-loglevel', 'error', '-i', str(pitched), '-af', filters,
         '-t', f'{target_dur:.3f}', '-ar', '44100', '-ac', '1', '-c:a', 'pcm_s16le', str(fitted)])
    print(f"scene {sid:02d}: target={target_dur:.2f}s raw={current:.2f}s tempo={tempo:.4f}")
    return fitted


def main():
    scene_audio = [synth_scene(scene) for scene in SCENES]
    narration = BUILD / 'melo_narration.wav'
    concat_wavs(scene_audio, narration)

    base_video = BUILD / 'final_nobgm.mp4'
    ambient = BUILD / 'ambient.m4a'
    final = BUILD / 'final.mp4'

    # Ignore the old temporary Edge narration. Keep only its video track,
    # then mix the commercially usable MeloTTS narration with the existing ambient bed.
    filter_complex = (
        '[1:a]volume=1.08[voice];'
        '[2:a]volume=0.72[bg];'
        '[voice][bg]amix=inputs=2:duration=first:dropout_transition=2,'
        'loudnorm=I=-15:LRA=9:TP=-1.0[a]'
    )
    run([
        'ffmpeg', '-y', '-loglevel', 'error',
        '-i', str(base_video), '-i', str(narration), '-i', str(ambient),
        '-filter_complex', filter_complex,
        '-map', '0:v:0', '-map', '[a]',
        '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k',
        '-shortest', '-movflags', '+faststart', str(final)
    ])

    (BUILD / 'voice_engine.txt').write_text(
        'MeloTTS Korean (MIT) | speed=1.03 | pitch=+2.5% | scene-timed\n',
        encoding='utf-8'
    )
    print('FINAL', final, duration(final))


if __name__ == '__main__':
    main()
