from __future__ import annotations

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import subprocess, json, math, wave, struct
from functools import lru_cache

ROOT = Path('.')
DATA = ROOT / 'drama' / 'episode01.json'
BUILD = ROOT / 'build_drama'
AUDIO = BUILD / 'audio'
CLIPS = BUILD / 'clips'
for p in (BUILD, AUDIO, CLIPS):
    p.mkdir(parents=True, exist_ok=True)

W, H = 720, 1280
FPS = 24
SR = 48000

FONT_REG = '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'
FONT_BOLD = '/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc'
F_BIG = ImageFont.truetype(FONT_BOLD, 64)
F_TITLE = ImageFont.truetype(FONT_BOLD, 44)
F_BODY = ImageFont.truetype(FONT_BOLD, 34)
F_SMALL = ImageFont.truetype(FONT_REG, 25)
F_TINY = ImageFont.truetype(FONT_REG, 20)

WHITE=(246,247,250); MUTED=(190,197,210); RED=(229,69,82); BLUE=(70,135,220)
GOLD=(239,188,86); DARK=(10,12,18); CYAN=(104,215,235)

VOICES = {
    '林夏雨': ('zh-CN-XiaoxiaoNeural', '+0%', '+0Hz'),
    '顾言': ('zh-CN-YunxiNeural', '-6%', '-2Hz'),
    '神秘声音': ('zh-CN-XiaoxiaoNeural', '-14%', '-8Hz'),
    '旁白': ('zh-CN-YunjianNeural', '-8%', '-4Hz'),
}

def run(cmd, **kwargs):
    print('RUN:', ' '.join(map(str, cmd)))
    subprocess.run(cmd, check=True, **kwargs)

def ffprobe_duration(path: Path) -> float:
    r = subprocess.run(['ffprobe','-v','error','-show_entries','format=duration','-of','default=nw=1:nk=1',str(path)], capture_output=True, text=True, check=True)
    return float(r.stdout.strip())

def text_width(draw, text, font):
    b = draw.textbbox((0,0), text, font=font)
    return b[2]-b[0]

def wrap_cn(draw, text, font, maxw):
    if not text: return []
    lines=[]; cur=''
    for ch in text:
        test=cur+ch
        if text_width(draw,test,font) <= maxw: cur=test
        else:
            if cur: lines.append(cur)
            cur=ch
    if cur: lines.append(cur)
    return lines

def gradient_bg(top=(10,14,24), bottom=(24,27,40)):
    im = Image.new('RGB',(W,H),top); d = ImageDraw.Draw(im)
    for y in range(H):
        t=y/(H-1); c=tuple(int(top[i]*(1-t)+bottom[i]*t) for i in range(3)); d.line((0,y,W,y),fill=c)
    return im

def add_vignette(im):
    ov=Image.new('RGBA',(W,H),(0,0,0,0)); d=ImageDraw.Draw(ov)
    for i in range(150):
        a=int(2.2*i); d.rectangle((i,i,W-i-1,H-i-1),outline=(0,0,0,min(120,a//3)))
    return Image.alpha_composite(im.convert('RGBA'),ov).convert('RGB')

@lru_cache(maxsize=1)
def hallway_base():
    im=gradient_bg((16,18,25),(31,31,38)); d=ImageDraw.Draw(im)
    for x in (130,360,590):
        glow=Image.new('RGBA',(W,H),(0,0,0,0)); gd=ImageDraw.Draw(glow); gd.ellipse((x-95,40,x+95,230),fill=(255,242,200,20))
        glow=glow.filter(ImageFilter.GaussianBlur(34)); im=Image.alpha_composite(im.convert('RGBA'),glow).convert('RGB'); d=ImageDraw.Draw(im)
        d.rounded_rectangle((x-45,72,x+45,94),radius=8,fill=(245,235,205))
    d.polygon([(0,300),(270,420),(270,1030),(0,1280)],fill=(32,34,42)); d.polygon([(720,300),(450,420),(450,1030),(720,1280)],fill=(28,30,38))
    d.polygon([(270,420),(450,420),(450,1030),(270,1030)],fill=(46,46,52)); d.polygon([(0,1280),(270,1030),(450,1030),(720,1280)],fill=(20,21,27))
    d.rectangle((292,465,428,965),fill=(55,58,65),outline=(115,119,126),width=3); d.line((360,465,360,965),fill=(25,26,30),width=4)
    d.rectangle((440,610,458,670),fill=(18,18,21),outline=(100,100,105)); d.ellipse((446,625,452,631),fill=RED)
    return add_vignette(im)

@lru_cache(maxsize=1)
def elevator_base():
    im=gradient_bg((18,20,24),(28,28,31)); d=ImageDraw.Draw(im)
    d.rectangle((85,120,635,1140),fill=(66,68,72),outline=(124,126,130),width=4); d.rectangle((110,145,610,1115),fill=(45,47,52))
    for x in (110,360,610): d.line((x,145,x,1115),fill=(90,92,97),width=2)
    d.rectangle((292,170,428,218),fill=(10,10,12)); d.text((334,177),'10',font=F_SMALL,fill=RED); d.rectangle((535,430,575,570),fill=(20,20,23),outline=(115,115,118))
    for yy in (460,510,550): d.ellipse((550,yy,560,yy+10),fill=(175,175,178))
    return add_vignette(im)

@lru_cache(maxsize=12)
def phone_ui(title, body, sender='未知号码', warning=False):
    im=gradient_bg((8,11,18),(15,18,28)); d=ImageDraw.Draw(im)
    d.rounded_rectangle((120,110,600,1165),radius=54,fill=(12,13,17),outline=(70,72,80),width=5); d.rounded_rectangle((145,160,575,1110),radius=36,fill=(235,237,241))
    d.rounded_rectangle((300,125,420,150),radius=10,fill=(35,35,38)); d.text((180,205),'22:47',font=F_SMALL,fill=(30,30,33)); d.text((180,270),sender,font=F_BODY,fill=(20,20,23)); d.line((180,325,540,325),fill=(205,207,212),width=2)
    if title: d.text((180,370),title,font=F_SMALL,fill=RED if warning else (40,82,165))
    y=430
    for line in wrap_cn(d,body,F_BODY,330)[:8]: d.text((180,y),line,font=F_BODY,fill=(24,24,27)); y+=52
    d.ellipse((190,890,260,960),fill=(35,74,150)); d.polygon([(220,908),(220,942),(245,925)],fill=WHITE)
    for i,h in enumerate([18,32,50,27,42,20,55,31,45,24]):
        x=290+i*21; d.rounded_rectangle((x,925-h//2,x+8,925+h//2),radius=3,fill=(60,85,130))
    d.text((180,1030),'00:08',font=F_TINY,fill=(90,90,96)); return add_vignette(im)

def draw_person(im, who, x, y, scale=1.0, emotion='neutral', mouth=False, blink=False, face='front', alpha=255):
    layer=Image.new('RGBA',(W,H),(0,0,0,0)); d=ImageDraw.Draw(layer); sx=int(110*scale); sy=int(145*scale); skin=(233,205,184,alpha)
    if who=='林夏雨':
        hair=(24,22,26,alpha); coat=(25,27,33,alpha); shirt=(232,234,238,alpha); d.rounded_rectangle((x-sx//2-12,y-sy//2-20,x+sx//2+12,y+sy//2+110),radius=int(45*scale),fill=hair)
        d.polygon([(x-105*scale,y+120*scale),(x+105*scale,y+120*scale),(x+145*scale,y+420*scale),(x-145*scale,y+420*scale)],fill=coat); d.polygon([(x-45*scale,y+115*scale),(x+45*scale,y+115*scale),(x+28*scale,y+260*scale),(x-28*scale,y+260*scale)],fill=shirt)
    else:
        hair=(20,19,20,alpha); coat=(18,20,25,alpha); shirt=(48,50,57,alpha); d.polygon([(x-120*scale,y+115*scale),(x+120*scale,y+115*scale),(x+155*scale,y+440*scale),(x-155*scale,y+440*scale)],fill=coat); d.polygon([(x-55*scale,y+115*scale),(x+55*scale,y+115*scale),(x+30*scale,y+245*scale),(x-30*scale,y+245*scale)],fill=shirt)
    d.rounded_rectangle((x-30*scale,y+65*scale,x+30*scale,y+145*scale),radius=int(18*scale),fill=skin); fx=x + (14*scale if face=='right' else -14*scale if face=='left' else 0); d.ellipse((fx-sx//2,y-sy//2,fx+sx//2,y+sy//2),fill=skin)
    if who=='林夏雨': d.pieslice((fx-sx//2-5,y-sy//2-25,fx+sx//2+5,y+sy//2-15),180,350,fill=hair)
    else:
        d.pieslice((fx-sx//2-5,y-sy//2-34,fx+sx//2+5,y+sy//2-20),185,355,fill=hair); d.polygon([(fx-55*scale,y-65*scale),(fx-18*scale,y-105*scale),(fx+10*scale,y-68*scale),(fx+45*scale,y-105*scale),(fx+58*scale,y-58*scale)],fill=hair)
    brow_y=y-22*scale; brow_col=(65,52,47,alpha)
    if emotion in ('afraid','shocked'):
        d.line((fx-38*scale,brow_y+5,fx-10*scale,brow_y-5),fill=brow_col,width=max(2,int(4*scale))); d.line((fx+10*scale,brow_y-5,fx+38*scale,brow_y+5),fill=brow_col,width=max(2,int(4*scale)))
    elif emotion=='cold':
        d.line((fx-40*scale,brow_y-4,fx-8*scale,brow_y+2),fill=brow_col,width=max(2,int(4*scale))); d.line((fx+8*scale,brow_y+2,fx+40*scale,brow_y-4),fill=brow_col,width=max(2,int(4*scale)))
    else:
        d.line((fx-38*scale,brow_y,fx-10*scale,brow_y-2),fill=brow_col,width=max(2,int(4*scale))); d.line((fx+10*scale,brow_y-2,fx+38*scale,brow_y),fill=brow_col,width=max(2,int(4*scale)))
    ey=y+2*scale
    if blink:
        d.line((fx-38*scale,ey,fx-10*scale,ey),fill=(35,31,32,alpha),width=max(2,int(4*scale))); d.line((fx+10*scale,ey,fx+38*scale,ey),fill=(35,31,32,alpha),width=max(2,int(4*scale)))
    else:
        eh=13*scale if emotion not in ('afraid','shocked') else 18*scale; d.ellipse((fx-39*scale,ey-eh/2,fx-9*scale,ey+eh/2),fill=(248,248,248,alpha)); d.ellipse((fx+9*scale,ey-eh/2,fx+39*scale,ey+eh/2),fill=(248,248,248,alpha)); iris=(38,35,36,alpha); d.ellipse((fx-29*scale,ey-6*scale,fx-18*scale,ey+6*scale),fill=iris); d.ellipse((fx+18*scale,ey-6*scale,fx+29*scale,ey+6*scale),fill=iris)
    my=y+47*scale
    if mouth:
        d.ellipse((fx-16*scale,my-7*scale,fx+16*scale,my+10*scale),fill=(110,45,50,alpha)); d.line((fx-10*scale,my+1*scale,fx+10*scale,my+1*scale),fill=(230,185,185,alpha),width=max(1,int(2*scale)))
    elif emotion=='shocked': d.ellipse((fx-10*scale,my-5*scale,fx+10*scale,my+15*scale),fill=(104,44,48,alpha))
    else: d.line((fx-16*scale,my,fx+16*scale,my),fill=(110,66,67,alpha),width=max(2,int(3*scale)))
    d.line((fx,my-35*scale,fx-3*scale,my-12*scale),fill=(195,160,145,alpha),width=max(1,int(2*scale))); return Image.alpha_composite(im.convert('RGBA'),layer).convert('RGB')

def subtitle_box(im, subtitle, speaker=None):
    if not subtitle: return im
    ov=Image.new('RGBA',(W,H),(0,0,0,0)); d=ImageDraw.Draw(ov); lines=wrap_cn(d,subtitle,F_BODY,610)[:3]; box_h=60+48*len(lines); top=H-110-box_h
    d.rounded_rectangle((42,top,678,H-72),radius=24,fill=(4,5,8,210),outline=(255,255,255,38),width=2)
    if speaker: d.text((70,top+18),speaker,font=F_TINY,fill=GOLD if speaker=='顾言' else CYAN); y=top+52
    else: y=top+28
    for line in lines:
        x=(W-text_width(d,line,F_BODY))//2; d.text((x,y),line,font=F_BODY,fill=WHITE,stroke_width=1,stroke_fill=(0,0,0)); y+=46
    return Image.alpha_composite(im.convert('RGBA'),ov).convert('RGB')

def header(im, ep, label='悬疑短剧'):
    d=ImageDraw.Draw(im); d.rounded_rectangle((28,28,168,70),radius=17,fill=(0,0,0,145)); d.text((46,39),f'EP.{ep:02d}',font=F_TINY,fill=WHITE); d.rounded_rectangle((530,28,692,70),radius=17,fill=(0,0,0,145)); d.text((552,39),label,font=F_TINY,fill=GOLD); return im

def render_scene_frame(scene, t, duration):
    kind=scene.get('visual','hallway')
    if kind=='phone': im=phone_ui(scene.get('phone_title','语音消息'),scene.get('phone_body',''),scene.get('sender','未知号码'),scene.get('warning',False)).copy()
    elif kind=='elevator': im=elevator_base().copy()
    else: im=hallway_base().copy()
    progress=0 if duration<=0 else max(0,min(1,t/duration)); blink=(int((t+scene['id']*.41)*10)%31) in (0,1); mouth_active=scene.get('speaker') in ('林夏雨','顾言') and 0.18<progress<0.82 and (int(t*8)%2==0)
    if kind in ('hallway','elevator'):
        if scene.get('actors') in ('both','guyan'):
            gx=int(scene.get('guyan_x',500)+scene.get('guyan_move',0)*progress); im=draw_person(im,'顾言',gx,int(scene.get('guyan_y',500)),scale=scene.get('guyan_scale',1.25),emotion=scene.get('guyan_emotion','neutral'),mouth=(mouth_active and scene.get('speaker')=='顾言'),blink=blink,face=scene.get('guyan_face','front'))
        if scene.get('actors') in ('both','xiayu'):
            xx=int(scene.get('xiayu_x',220)+scene.get('xiayu_move',0)*progress); im=draw_person(im,'林夏雨',xx,int(scene.get('xiayu_y',520)),scale=scene.get('xiayu_scale',1.15),emotion=scene.get('xiayu_emotion','afraid'),mouth=(mouth_active and scene.get('speaker')=='林夏雨'),blink=blink,face=scene.get('xiayu_face','front'))
    d=ImageDraw.Draw(im)
    if scene.get('overlay')=='message':
        d.rounded_rectangle((80,160,640,410),radius=26,fill=(245,246,248),outline=(210,212,218),width=2); d.text((112,190),scene.get('message_sender','未知联系人'),font=F_SMALL,fill=(35,35,38)); y=248
        for line in wrap_cn(d,scene.get('message',''),F_BODY,480)[:3]: d.text((112,y),line,font=F_BODY,fill=(22,22,25)); y+=52
    if scene.get('big_text'):
        lines=wrap_cn(d,scene['big_text'],F_BIG,620)[:4]; y=410
        for line in lines:
            x=(W-text_width(d,line,F_BIG))//2; d.text((x,y),line,font=F_BIG,fill=WHITE,stroke_width=3,stroke_fill=(0,0,0)); y+=82
    im=header(im,1); im=subtitle_box(im,scene.get('subtitle',''),scene.get('speaker')); z=1.0+(0.075 if scene.get('shot')=='push' else 0.035)*progress
    if z>1.001:
        nw,nh=int(W*z),int(H*z); im=im.resize((nw,nh),Image.Resampling.BICUBIC); cx=(nw-W)//2+int(scene.get('pan_x',0)*progress); cy=(nh-H)//2+int(scene.get('pan_y',0)*progress); cx=max(0,min(nw-W,cx)); cy=max(0,min(nh-H,cy)); im=im.crop((cx,cy,cx+W,cy+H))
    return im

def make_tts(scene, idx):
    text=scene.get('tts') or scene.get('subtitle') or ''; speaker=scene.get('speaker')
    if not text or not speaker: return None
    voice,rate,pitch=VOICES.get(speaker,VOICES['旁白']); out=AUDIO/f'{idx:02d}_tts.mp3'; run(['edge-tts','--voice',voice,'--rate',rate,'--pitch',pitch,'--text',text,'--write-media',str(out)]); return out

def write_sfx(name, out, duration=1.0):
    n=int(SR*duration); samples=[]
    for i in range(n):
        t=i/SR; v=0.0
        if name=='vibration':
            env=1.0 if ((t%0.42)<0.17) else 0.0; v=0.22*math.sin(2*math.pi*118*t)*env
        elif name=='ding':
            env=math.exp(-3.8*t); v=0.18*(math.sin(2*math.pi*880*t)+0.55*math.sin(2*math.pi*1320*t))*env
        elif name=='hit':
            env=math.exp(-5.8*t); v=0.32*(math.sin(2*math.pi*58*t)+0.4*math.sin(2*math.pi*116*t))*env
        elif name=='step':
            beat=1.0 if (t<0.08 or 0.52<t<0.60) else 0.0; v=0.19*math.sin(2*math.pi*82*t)*beat
        samples.append(int(max(-1,min(1,v))*32767))
    with wave.open(str(out),'w') as wf:
        wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(SR); wf.writeframes(b''.join(struct.pack('<h',s) for s in samples))

def build_scene_audio(scene, idx, duration, tts):
    out=AUDIO/f'{idx:02d}_scene.m4a'; inputs=['-f','lavfi','-t',f'{duration:.3f}','-i',f'anullsrc=r={SR}:cl=mono']; filters=[]; mix=['[0:a]']; n=1
    if tts:
        inputs+=['-i',str(tts)]; delay=int(scene.get('tts_delay_ms',220)); filters.append(f'[{n}:a]adelay={delay}|{delay},volume=1.16[tts]'); mix.append('[tts]'); n+=1
    sfx=scene.get('sfx')
    if sfx:
        sfx_path=AUDIO/f'sfx_{sfx}.wav'
        if not sfx_path.exists(): write_sfx(sfx,sfx_path,1.4)
        inputs+=['-i',str(sfx_path)]; delay=int(scene.get('sfx_delay_ms',0)); filters.append(f'[{n}:a]adelay={delay}|{delay},volume=1.0[sfx]'); mix.append('[sfx]'); n+=1
    filters.append(f"aevalsrc='0.018*sin(2*PI*55*t)+0.010*sin(2*PI*82*t)':s={SR}:d={duration:.3f}[bed]"); mix.append('[bed]'); filters.append(''.join(mix)+f'amix=inputs={len(mix)}:duration=first:dropout_transition=0,alimiter=limit=0.92[mix]')
    run(['ffmpeg','-y',*inputs,'-filter_complex',';'.join(filters),'-map','[mix]','-c:a','aac','-b:a','160k','-t',f'{duration:.3f}',str(out)]); return out

def build_scene_video(scene, idx, duration):
    out=CLIPS/f'{idx:02d}_video.mp4'; cmd=['ffmpeg','-y','-f','rawvideo','-vcodec','rawvideo','-pix_fmt','rgb24','-s',f'{W}x{H}','-r',str(FPS),'-i','-','-an','-c:v','libx264','-preset','veryfast','-crf','19','-pix_fmt','yuv420p',str(out)]; proc=subprocess.Popen(cmd,stdin=subprocess.PIPE); total=max(1,int(round(duration*FPS)))
    for f in range(total): proc.stdin.write(render_scene_frame(scene,f/FPS,duration).convert('RGB').tobytes())
    proc.stdin.close(); rc=proc.wait()
    if rc!=0: raise RuntimeError(f'ffmpeg scene render failed: {idx}')
    return out

def mux_scene(v,a,idx,duration):
    out=CLIPS/f'{idx:02d}_mux.mp4'; run(['ffmpeg','-y','-i',str(v),'-i',str(a),'-c:v','copy','-c:a','aac','-shortest','-t',f'{duration:.3f}',str(out)]); return out

def concat_clips(clips):
    list_path=BUILD/'concat.txt'; list_path.write_text('\n'.join(f"file '{p.resolve()}'" for p in clips),encoding='utf-8'); joined=BUILD/'joined.mp4'; run(['ffmpeg','-y','-f','concat','-safe','0','-i',str(list_path),'-c','copy',str(joined)]); final=BUILD/'short_drama_ep01.mp4'; run(['ffmpeg','-y','-i',str(joined),'-vf','scale=1080:1920:flags=lanczos,fps=30','-af','loudnorm=I=-16:LRA=8:TP=-1.5','-c:v','libx264','-preset','medium','-crf','18','-c:a','aac','-b:a','192k','-movflags','+faststart',str(final)]); return final

def make_poster():
    im=hallway_base().copy(); im=draw_person(im,'顾言',500,510,1.35,emotion='cold'); im=draw_person(im,'林夏雨',205,545,1.22,emotion='afraid'); d=ImageDraw.Draw(im); d.rounded_rectangle((48,105,672,430),radius=35,fill=(0,0,0,155)); d.text((84,145),'今晚别回家',font=F_BIG,fill=WHITE,stroke_width=2,stroke_fill=(0,0,0)); d.text((88,240),'“明天的我”发来了一段语音',font=F_SMALL,fill=CYAN); d.text((88,295),'可门口站着的人，真的是男友吗？',font=F_SMALL,fill=MUTED); d.rounded_rectangle((88,350,238,400),radius=18,fill=RED); d.text((120,363),'第1集',font=F_SMALL,fill=WHITE); im.save(BUILD/'poster.png')

def main():
    spec=json.loads(DATA.read_text(encoding='utf-8')); clips=[]; total=0.0
    for i,scene in enumerate(spec['scenes'],1):
        tts=make_tts(scene,i); duration=float(scene.get('duration',4.0))
        if tts: duration=max(duration,ffprobe_duration(tts)+0.75)
        print(f'SCENE {i}/{len(spec["scenes"])} duration={duration:.2f}s'); v=build_scene_video(scene,i,duration); a=build_scene_audio(scene,i,duration,tts); clips.append(mux_scene(v,a,i,duration)); total+=duration
    final=concat_clips(clips); make_poster(); (BUILD/'duration.txt').write_text(f'{total:.2f} seconds\n',encoding='utf-8'); (BUILD/'episode_info.json').write_text(json.dumps(spec,ensure_ascii=False,indent=2),encoding='utf-8'); print('DONE:',final)

if __name__=='__main__':
    main()
