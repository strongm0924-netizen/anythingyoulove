from pathlib import Path
import subprocess, wave

ROOT=Path('.')
BUILD=ROOT/'build'
PARTS=BUILD/'qwen_parts'
FIT=BUILD/'qwen_fitted'
FIT.mkdir(parents=True,exist_ok=True)

TARGETS=[25,30,30,30]+[35]*14+[30,28.502]

def run(cmd): subprocess.run(cmd,check=True)
def duration(path):
    r=subprocess.run(['ffprobe','-v','error','-show_entries','format=duration','-of','default=nw=1:nk=1',str(path)],capture_output=True,text=True,check=True)
    return float(r.stdout.strip())

fitted=[]
for sid,target in enumerate(TARGETS,start=1):
    src=PARTS/f's{sid:02d}.wav'
    if not src.exists(): raise FileNotFoundError(src)
    raw=duration(src)
    tempo=raw/target
    out=FIT/f's{sid:02d}.wav'
    # Rubber Band time-stretching preserves pitch and is far cleaner than pitch-shifting an already compressed TTS track.
    filt=f'rubberband=tempo={tempo:.8f},highpass=f=60,lowpass=f=12000,loudnorm=I=-17:LRA=7:TP=-1.5'
    run(['ffmpeg','-y','-loglevel','error','-i',str(src),'-af',filt,'-t',f'{target:.3f}','-ar','48000','-ac','1','-c:a','pcm_s16le',str(out)])
    fitted.append(out)
    print(f'scene {sid:02d}: raw={raw:.2f}s target={target:.2f}s tempo={tempo:.3f}',flush=True)

lst=BUILD/'qwen_concat.txt'
lst.write_text('\n'.join([f"file '{p.resolve().as_posix()}'" for p in fitted]),encoding='utf-8')
fullwav=BUILD/'qwen_aiden_full.wav'
run(['ffmpeg','-y','-loglevel','error','-f','concat','-safe','0','-i',str(lst),'-c:a','pcm_s16le','-ar','48000','-ac','1',str(fullwav)])
fullm4a=BUILD/'qwen_aiden_full.m4a'
run(['ffmpeg','-y','-loglevel','error','-i',str(fullwav),'-c:a','aac','-b:a','160k',str(fullm4a)])
(BUILD/'qwen_voice_info.txt').write_text('Qwen3-TTS 0.6B CustomVoice | Aiden | Korean | Apache-2.0\n',encoding='utf-8')
print('FINAL',fullwav,duration(fullwav))
