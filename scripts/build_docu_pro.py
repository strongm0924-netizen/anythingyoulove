from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import subprocess, json, math, re
import requests

ROOT=Path('.')
VIDEO=ROOT/'video'
BUILD=ROOT/'build'
ASSETS=BUILD/'assets'; FRAMES=BUILD/'frames'; AUDIO=BUILD/'audio'; SHOTS=BUILD/'shots'; SCENECLIPS=BUILD/'sceneclips'
for p in (BUILD,ASSETS,FRAMES,AUDIO,SHOTS,SCENECLIPS): p.mkdir(parents=True,exist_ok=True)

W,H=1920,1080
FPS=30
VOICE='ko-KR-InJoonNeural'
RATE='-8%'
PITCH='-6Hz'

scenes=json.loads((VIDEO/'scenes.json').read_text(encoding='utf-8'))
queries=json.loads((VIDEO/'asset_queries.json').read_text(encoding='utf-8'))

FONT_REG='/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'
FONT_BOLD='/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc'
F_HUGE=ImageFont.truetype(FONT_BOLD,88)
F_TITLE=ImageFont.truetype(FONT_BOLD,62)
F_KICK=ImageFont.truetype(FONT_BOLD,36)
F_BODY=ImageFont.truetype(FONT_REG,30)
F_SMALL=ImageFont.truetype(FONT_REG,23)
F_TINY=ImageFont.truetype(FONT_REG,18)

WHITE=(245,248,252); MUTED=(205,218,230); GOLD=(245,190,75); CYAN=(93,216,236); BLUE=(62,155,220); RED=(222,76,82); GREEN=(77,205,153)
USER_AGENT='IslandKoreaDocumentaryBot/1.0'

VISUAL_LABELS={
'hook':'ISLAND KOREA','map_split':'GEOGRAPHY','invasion':'INVASION','navy':'NAVAL STATE','merchant':'MARITIME COMMERCE','capital':'PORT CAPITAL','trade':'TRANSIT TRADE','voyage':'AGE OF SAIL','diaspora':'MERCHANT NETWORK','culture':'MARITIME CULTURE','midpoint':'THE TURN','dependency':'SEA-LANE DEPENDENCY','blockade':'BLOCKADE','imperial':'IMPERIAL POWERS','rivalry':'NAVAL RIVALRY','strategic':'STRATEGIC PRIZE','colonial':'LEASED PORTS','division':'COLD WAR','modern':'ALTERNATE 2026','ending':'THE THESIS'}

def run(cmd): subprocess.run(cmd,check=True)
def ffprobe_duration(path):
    r=subprocess.run(['ffprobe','-v','error','-show_entries','format=duration','-of','default=nw=1:nk=1',str(path)],capture_output=True,text=True,check=True)
    return float(r.stdout.strip())

def commons_search(query, limit=6):
    api='https://commons.wikimedia.org/w/api.php'
    params={'action':'query','generator':'search','gsrsearch':query,'gsrnamespace':6,'gsrlimit':limit,'prop':'imageinfo','iiprop':'url|extmetadata|size','iiurlwidth':2400,'format':'json','origin':'*'}
    r=requests.get(api,params=params,headers={'User-Agent':USER_AGENT},timeout=25); r.raise_for_status()
    pages=(r.json().get('query') or {}).get('pages') or {}; out=[]
    for p in pages.values():
        info=(p.get('imageinfo') or [{}])[0]; meta=info.get('extmetadata') or {}; url=info.get('thumburl') or info.get('url')
        if not url: continue
        if not any(url.lower().split('?')[0].endswith(ext) for ext in ['.jpg','.jpeg','.png','.webp']): continue
        w=info.get('thumbwidth') or info.get('width') or 0; h=info.get('thumbheight') or info.get('height') or 0
        if w<900 or h<500: continue
        author=(meta.get('Artist') or {}).get('value','')
        out.append({'url':url,'title':p.get('title',''),'license':(meta.get('LicenseShortName') or {}).get('value',''),'author':re.sub('<[^>]+>','',author),'page':info.get('descriptionurl',''),'w':w,'h':h})
    return out

def download_image(url,path):
    r=requests.get(url,headers={'User-Agent':USER_AGENT},timeout=30); r.raise_for_status(); path.write_bytes(r.content)
    im=Image.open(path); im.verify(); return path

def collect_assets():
    credits=[]; mapping={}
    for scene in scenes:
        sid=str(scene['id']); selected=[]; seen=set()
        for q in queries.get(sid,[]):
            try:
                for item in commons_search(q,8):
                    if item['url'] in seen: continue
                    seen.add(item['url']); ext='.png' if '.png' in item['url'].lower().split('?')[0] else '.jpg'; dest=ASSETS/f"s{int(sid):02d}_{len(selected)+1}{ext}"
                    try:
                        download_image(item['url'],dest); selected.append({'path':dest,**item}); credits.append({'scene':int(sid),'query':q,**item})
                    except Exception: continue
                    if len(selected)>=2: break
            except Exception as e: print('commons search failed',sid,q,repr(e))
            if len(selected)>=2: break
        mapping[int(sid)]=selected
    (BUILD/'credits.json').write_text(json.dumps(credits,ensure_ascii=False,indent=2),encoding='utf-8')
    lines=['Wikimedia Commons assets used in this documentary. Verify source pages and license terms before publishing.','']
    for c in credits: lines.append(f"Scene {c['scene']:02d} | {c['title']} | {c['license']} | {c['author']} | {c['page']}")
    (BUILD/'credits.txt').write_text('\n'.join(lines),encoding='utf-8'); return mapping

def cover_crop(im,size=(W,H)):
    im=im.convert('RGB'); ratio=max(size[0]/im.width,size[1]/im.height); nw,nh=int(im.width*ratio),int(im.height*ratio); im=im.resize((nw,nh),Image.Resampling.LANCZOS); l=(nw-size[0])//2; t=(nh-size[1])//2
    return im.crop((l,t,l+size[0],t+size[1]))

def gradient_overlay(img,strength=175):
    img=img.convert('RGBA'); ov=Image.new('RGBA',(W,H),(0,0,0,0)); d=ImageDraw.Draw(ov)
    for y in range(H): d.line((0,y,W,y),fill=(2,8,18,min(230,int(30+strength*(y/H)))))
    for x in range(W):
        a=int(max(0,175*(1-x/(W*.7)))) if x<W*.7 else 0; d.line((x,0,x,H),fill=(0,4,12,a))
    return Image.alpha_composite(img,ov)

def wrap(draw,text,font,maxw):
    words=text.split(); lines=[]; cur=''
    for word in words:
        test=(cur+' '+word).strip()
        if draw.textbbox((0,0),test,font=font)[2] <= maxw: cur=test
        else:
            if cur: lines.append(cur)
            cur=word
    if cur: lines.append(cur)
    return lines

def add_title(img,scene,subtle=False):
    d=ImageDraw.Draw(img)
    if subtle:
        d.rounded_rectangle((70,62,410,106),radius=18,fill=(0,0,0,130)); d.text((92,72),VISUAL_LABELS.get(scene['visual'],'DOCUMENTARY'),font=F_SMALL,fill=GOLD); return img
    d.text((90,115),f"{scene['id']:02d}",font=F_HUGE,fill=GOLD); y=225
    for line in wrap(d,scene['title'],F_TITLE,1080)[:2]: d.text((95,y),line,font=F_TITLE,fill=WHITE); y+=76
    y+=8
    for line in wrap(d,scene['kicker'],F_KICK,1120)[:2]: d.text((98,y),line,font=F_KICK,fill=CYAN); y+=48
    d.rounded_rectangle((90,900,880,970),radius=22,fill=(0,0,0,130),outline=(255,255,255,35),width=2); d.text((120,923),VISUAL_LABELS.get(scene['visual'],'DOCUMENTARY'),font=F_SMALL,fill=MUTED); return img

def photo_frame(path,scene,idx):
    try: im=cover_crop(Image.open(path))
    except Exception: im=Image.new('RGB',(W,H),(10,25,45))
    im=gradient_overlay(im,155 if idx==0 else 90); im=add_title(im,scene,subtle=idx!=0); d=ImageDraw.Draw(im)
    if idx==1:
        lines=wrap(d,scene['kicker'],F_KICK,1300)[:2]; y=825; d.rounded_rectangle((70,795,1530,1005),radius=28,fill=(0,0,0,145))
        for line in lines: d.text((105,y),line,font=F_KICK,fill=WHITE); y+=50
    out=FRAMES/f"s{scene['id']:02d}_photo{idx+1}.jpg"; im.convert('RGB').save(out,quality=92); return out

def korea_poly(cx,cy,s=1):
    pts=[(-25,-90),(6,-72),(20,-50),(11,-34),(33,-9),(23,15),(38,35),(22,57),(6,91),(-13,76),(-25,55),(-17,34),(-33,17),(-25,-5),(-43,-26),(-31,-50),(-40,-70)]
    return [(cx+x*s,cy+y*s) for x,y in pts]

def arrow(d,a,b,color=RED,width=8):
    d.line((*a,*b),fill=color,width=width); ang=math.atan2(b[1]-a[1],b[0]-a[0]); L=28
    d.polygon([b,(b[0]-L*math.cos(ang-.5),b[1]-L*math.sin(ang-.5)),(b[0]-L*math.cos(ang+.5),b[1]-L*math.sin(ang+.5))],fill=color)

def ship(d,x,y,s=1,color=WHITE):
    d.polygon([(x-90*s,y),(x+95*s,y),(x+65*s,y+42*s),(x-70*s,y+42*s)],fill=color); d.rectangle((x-28*s,y-55*s,x+22*s,y),fill=color); d.polygon([(x+22*s,y-55*s),(x+75*s,y-18*s),(x+22*s,y-18*s)],fill=CYAN)

def infographic(scene):
    act=1 if scene['id']<=5 else 2 if scene['id']<=10 else 3 if scene['id']<=13 else 4 if scene['id']<=18 else 5
    palettes=[((7,18,35),(15,60,100)),((8,28,40),(18,88,110)),((30,22,26),(73,40,46)),((28,16,22),(85,28,32)),((18,23,30),(70,61,35))]
    top,bottom=palettes[act-1]; im=Image.new('RGB',(W,H),top); d=ImageDraw.Draw(im)
    for y in range(H):
        t=y/(H-1); c=tuple(int(top[i]*(1-t)+bottom[i]*t) for i in range(3)); d.line((0,y,W,y),fill=c)
    for x in range(0,W,100): d.line((x,0,x,H),fill=(30,45,65),width=1)
    for y in range(0,H,100): d.line((0,y,W,y),fill=(30,45,65),width=1)
    v=scene['visual']; d.rounded_rectangle((70,65,560,120),radius=22,fill=(245,245,245)); d.text((100,81),VISUAL_LABELS.get(v,'DOCUMENTARY'),font=F_SMALL,fill=(10,26,45)); d.text((70,165),scene['title'],font=F_TITLE,fill=WHITE); d.text((74,245),scene['kicker'],font=F_KICK,fill=CYAN)
    if v in ('hook','map_split','strategic','division','ending'):
        d.polygon(korea_poly(1450,555,2.5),fill=(55,150,195),outline=WHITE)
        for r in (190,285): d.ellipse((1450-r,555-r,1450+r,555+r),outline=(90,110,140),width=3)
        if v=='strategic':
            for p in [(1120,380),(1690,390),(1300,260),(1680,710)]: arrow(d,p,(1450,555),GOLD,7)
        if v=='division': d.line((1110,555,1780,555),fill=RED,width=7); d.line((1450,270,1450,830),fill=BLUE,width=7)
    elif v in ('navy','blockade','invasion','rivalry'):
        ship(d,1450,610,1.7,WHITE); ship(d,1160,790,.8,(180,225,245)); ship(d,1690,790,.8,(180,225,245))
        if v=='blockade':
            for rr in (230,330): d.ellipse((1450-rr,600-rr,1450+rr,600+rr),outline=RED,width=6)
        if v=='invasion':
            for yy in (420,560,700): arrow(d,(1030,yy),(1260,yy),RED,7)
    elif v in ('capital','modern'):
        x=1080
        for w,h in [(75,280),(90,410),(65,340),(105,490),(80,360),(95,430),(70,300)]:
            d.rounded_rectangle((x,835-h,x+w,835),radius=6,fill=(40,82,115),outline=(100,180,220),width=3)
            for yy in range(835-h+28,810,42): d.rectangle((x+14,yy,x+w-14,yy+13),fill=CYAN)
            x+=w+34
        d.text((1130,890),'BUSAN CAPITAL',font=F_KICK,fill=GOLD)
    elif v in ('trade','voyage','diaspora','merchant','culture'):
        nodes=[(1120,390),(1370,520),(1650,355),(1190,760),(1570,770)]
        for p in nodes: d.ellipse((p[0]-38,p[1]-38,p[0]+38,p[1]+38),fill=(36,96,125),outline=CYAN,width=4)
        for p in nodes[1:]: arrow(d,nodes[0],p,CYAN,5)
        ship(d,1410,660,.8,WHITE)
    elif v in ('dependency','midpoint'):
        vals=[('FOOD',82),('ENERGY',93),('TRADE',88),('NAVY',78)]; y=405
        for name,val in vals:
            d.text((1110,y),name,font=F_SMALL,fill=MUTED); d.rounded_rectangle((1290,y+5,1740,y+35),radius=12,fill=(70,75,85)); d.rounded_rectangle((1290,y+5,1290+int(450*val/100),y+35),radius=12,fill=GOLD if v=='dependency' else CYAN); y+=105
    elif v in ('imperial','colonial'):
        powers=[('UK',(1120,390)),('RUSSIA',(1560,330)),('USA',(1120,730)),('JAPAN',(1580,730))]; d.polygon(korea_poly(1430,555,1.7),fill=(125,65,70),outline=WHITE)
        for name,p in powers:
            d.rounded_rectangle((p[0]-70,p[1]-35,p[0]+70,p[1]+35),radius=15,fill=(72,38,45),outline=(230,130,130),width=3); d.text((p[0]-35,p[1]-12),name,font=F_SMALL,fill=WHITE); arrow(d,p,(1430,555),GOLD,5)
    d.rounded_rectangle((70,890,940,1000),radius=28,fill=(0,0,0),outline=(120,120,120),width=2); lines=wrap(d,scene['kicker'],F_BODY,800)[:2]; y=916
    for line in lines: d.text((105,y),line,font=F_BODY,fill=WHITE); y+=38
    out=FRAMES/f"s{scene['id']:02d}_graphic.jpg"; im.save(out,quality=92); return out

def generate_audio(scene):
    mp3=AUDIO/f"s{scene['id']:02d}.mp3"; vtt=AUDIO/f"s{scene['id']:02d}.vtt"
    run(['edge-tts','--text',scene['narration'],'--voice',VOICE,f'--rate={RATE}',f'--pitch={PITCH}','--write-media',str(mp3),'--write-subtitles',str(vtt)]); return mp3,vtt

def make_shot(frame,out,dur,zoom_in=True):
    frames=max(1,int(round(dur*FPS))); z="min(zoom+0.00065,1.085)" if zoom_in else "max(zoom-0.0006,1.0)"; zexpr=f"if(eq(on,0),{'1.0' if zoom_in else '1.08'},{z})"
    vf=f"zoompan=z='{zexpr}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s={W}x{H}:fps={FPS},fade=t=in:st=0:d=0.35,fade=t=out:st={max(0,dur-0.35):.3f}:d=0.35"
    run(['ffmpeg','-y','-loglevel','error','-loop','1','-i',str(frame),'-t',f'{dur:.3f}','-vf',vf,'-c:v','libx264','-preset','veryfast','-crf','20','-pix_fmt','yuv420p','-r',str(FPS),str(out)])

def subtitles_filter(vtt):
    p=str(vtt).replace('\\','/').replace(':','\\:').replace("'","\\'"); style="FontName=Noto Sans CJK KR,FontSize=26,PrimaryColour=&HFFFFFF&,OutlineColour=&H70000000&,BackColour=&H70000000&,BorderStyle=3,Outline=1,Shadow=0,MarginV=42,Alignment=2"; return f"subtitles='{p}':force_style='{style}'"

def make_scene(scene,assets):
    audio,vtt=generate_audio(scene); dur=ffprobe_duration(audio); frames=[]
    for idx,item in enumerate(assets[:2]): frames.append(photo_frame(item['path'],scene,idx))
    while len(frames)<2: frames.append(infographic(scene))
    frames.append(infographic(scene)); weights=[0.36,0.33,0.31] if scene['id'] in (1,11,20) else [0.34,0.33,0.33]; shotpaths=[]
    for i,(frame,w) in enumerate(zip(frames,weights),start=1):
        sp=SHOTS/f"s{scene['id']:02d}_{i}.mp4"; make_shot(frame,sp,dur*w,zoom_in=(i%2==1)); shotpaths.append(sp)
    lst=BUILD/f"scene_{scene['id']:02d}_shots.txt"; lst.write_text('\n'.join([f"file '{p.resolve().as_posix()}'" for p in shotpaths]),encoding='utf-8'); noaud=BUILD/f"scene_{scene['id']:02d}_noaud.mp4"; run(['ffmpeg','-y','-loglevel','error','-f','concat','-safe','0','-i',str(lst),'-c','copy',str(noaud)])
    out=SCENECLIPS/f"scene_{scene['id']:02d}.mp4"; run(['ffmpeg','-y','-loglevel','error','-i',str(noaud),'-i',str(audio),'-vf',subtitles_filter(vtt),'-map','0:v:0','-map','1:a:0','-c:v','libx264','-preset','veryfast','-crf','20','-pix_fmt','yuv420p','-c:a','aac','-b:a','192k','-shortest',str(out)]); return out

def concat_final(sceneclips):
    lst=BUILD/'scenes.txt'; lst.write_text('\n'.join([f"file '{p.resolve().as_posix()}'" for p in sceneclips]),encoding='utf-8'); base=BUILD/'final_nobgm.mp4'; run(['ffmpeg','-y','-loglevel','error','-f','concat','-safe','0','-i',str(lst),'-c','copy',str(base)]); total=ffprobe_duration(base); bgm=BUILD/'ambient.m4a'
    lavfi=("sine=frequency=55:sample_rate=48000:duration=%s[a];sine=frequency=82.41:sample_rate=48000:duration=%s[b];anoisesrc=color=pink:sample_rate=48000:duration=%s,lowpass=f=900,highpass=f=90[n];[a]volume=0.025[a1];[b]volume=0.016[b1];[n]volume=0.008[n1];[a1][b1][n1]amix=inputs=3:normalize=0,afade=t=in:st=0:d=3,afade=t=out:st=%s:d=4"%(total,total,total,max(0,total-4)))
    run(['ffmpeg','-y','-loglevel','error','-f','lavfi','-i',lavfi,'-t',f'{total:.2f}','-c:a','aac','-b:a','128k',str(bgm)]); final=BUILD/'final.mp4'; run(['ffmpeg','-y','-loglevel','error','-i',str(base),'-i',str(bgm),'-filter_complex','[0:a][1:a]amix=inputs=2:duration=first:dropout_transition=2[a]','-map','0:v','-map','[a]','-c:v','copy','-c:a','aac','-b:a','192k','-movflags','+faststart',str(final)]); (BUILD/'duration.txt').write_text(f'{ffprobe_duration(final):.2f} seconds',encoding='utf-8'); return final

def thumbnail(assetmap):
    scene=scenes[0]; assets=assetmap.get(1,[]); im=cover_crop(Image.open(assets[0]['path'])) if assets else Image.new('RGB',(W,H),(8,22,42)); im=gradient_overlay(im,185); d=ImageDraw.Draw(im); d.rounded_rectangle((90,90,430,150),radius=22,fill=GOLD); d.text((125,107),'WHAT IF',font=F_SMALL,fill=(10,20,35)); d.text((90,250),'한국이',font=F_HUGE,fill=WHITE); d.text((90,360),'섬나라였다면?',font=F_HUGE,fill=GOLD); d.text((95,505),'더 강해졌을까, 더 위험해졌을까',font=F_KICK,fill=CYAN); d.rounded_rectangle((95,850,860,955),radius=28,fill=(0,0,0)); d.text((135,883),'11분 가상역사 다큐멘터리',font=F_KICK,fill=WHITE); out=BUILD/'thumbnail.png'; im.convert('RGB').save(out,quality=94); return out

def main():
    assetmap=collect_assets(); thumbnail(assetmap); clips=[]
    for scene in scenes:
        print(f"Building scene {scene['id']:02d} / {len(scenes)}"); clips.append(make_scene(scene,assetmap.get(scene['id'],[])))
    print('FINAL',concat_final(clips))

if __name__=='__main__': main()
