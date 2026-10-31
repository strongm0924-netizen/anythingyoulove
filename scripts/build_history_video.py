from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import subprocess, json, math

ROOT = Path('.')
VIDEO = ROOT / 'video'
BUILD = ROOT / 'build'
FRAMES = BUILD / 'frames'
AUDIO = BUILD / 'audio'
CLIPS = BUILD / 'clips'
for p in (BUILD, FRAMES, AUDIO, CLIPS): p.mkdir(parents=True, exist_ok=True)

W,H = 1280,720
FPS=30
scenes = json.loads((VIDEO/'scenes.json').read_text(encoding='utf-8'))

FONT_REG = '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'
FONT_BOLD = '/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc'
F_TITLE = ImageFont.truetype(FONT_BOLD, 54)
F_KICK = ImageFont.truetype(FONT_BOLD, 30)
F_BODY = ImageFont.truetype(FONT_REG, 24)
F_SMALL = ImageFont.truetype(FONT_REG, 19)
F_TINY = ImageFont.truetype(FONT_REG, 16)
F_BIG = ImageFont.truetype(FONT_BOLD, 96)

NAVY=(8,17,36); BLUE=(70,180,240); CYAN=(95,220,245); GOLD=(255,192,74); RED=(240,90,90); GREEN=(77,205,153); WHITE=(245,248,252); MUTED=(184,204,222)

BULLETS = {
 'hook':['부산 수도?', '제주 금융허브?', '해군 강국?'],
 'map_split':['육상 국경 소멸','전쟁 구조 변화','교역 방향 변화'],
 'invasion':['북방 침입 감소','상륙전 필요','보급 난도 급상승'],
 'navy':['군항 투자','조선소 확대','수군 엘리트화'],
 'merchant':['상인 위상 상승','항해 기술 투자','상업세력 성장'],
 'capital':['부산 수도 가능성','제주 자유항','항구도시 중심'],
 'trade':['중국 ↔ 한국 ↔ 일본','선박 수리·보급','중계무역 수익'],
 'voyage':['오키나와','대만·필리핀','베트남·인도네시아'],
 'diaspora':['해외 상인촌','항구 네트워크','초기 한인사회'],
 'culture':['외국어','해양 음식문화','해외 진출 일상화'],
 'midpoint':['침략↓','무역↑','국력↑'],
 'dependency':['식량','에너지','원자재'],
 'blockade':['항구 봉쇄','상선 차단','공급망 충격'],
 'imperial':['영국','러시아','미국·일본'],
 'rivalry':['해군력','무역로','동남아 영향력'],
 'strategic':['중국 접근','일본 견제','러시아 남하 차단'],
 'colonial':['부산 조차지?','인천 군항?','제주 외국기지?'],
 'division':['38선은 없음','냉전은 존재','다른 분열 가능'],
 'modern':['항만·금융','해운·조선','강력한 해군'],
 'ending':['바다는 방패','위치는 그대로','힘이 운명을 결정']
}

CHAPTERS=[(1,5,'1막 · 바다가 만든 기회'),(6,10,'2막 · 해양강국의 탄생'),(11,13,'3막 · 방패가 족쇄가 될 때'),(14,18,'4막 · 모두가 탐낸 섬'),(19,20,'5막 · 2026년의 다른 한국')]

def chapter_for(i):
    for a,b,name in CHAPTERS:
        if a<=i<=b: return name
    return ''

def grad_bg(top=(6,13,28), bottom=(17,54,91)):
    im=Image.new('RGB',(W,H),top); d=ImageDraw.Draw(im)
    for y in range(H):
        t=y/(H-1); c=tuple(int(top[k]*(1-t)+bottom[k]*t) for k in range(3)); d.line((0,y,W,y), fill=c)
    for x in range(0,W,80): d.line((x,0,x,H), fill=(18,42,68), width=1)
    for y in range(0,H,80): d.line((0,y,W,y), fill=(18,42,68), width=1)
    return im

def rounded_panel(draw, box, fill=(10,23,42), outline=(55,92,125), radius=24, width=2):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)

def draw_header(draw, scene):
    sid=scene['id']; ch=chapter_for(sid)
    draw.rounded_rectangle((54,40,430,82), radius=18, fill=WHITE)
    draw.text((74,52),'WHAT IF : KOREA', font=F_SMALL, fill=(10,27,50))
    draw.text((500,54),ch, font=F_SMALL, fill=MUTED)
    pct=int(sid/len(scenes)*100); draw.text((1120,54),f'{pct:02d}%',font=F_SMALL,fill=GOLD)
    draw.rounded_rectangle((55,665,1225,680), radius=7, fill=(30,52,74))
    draw.rounded_rectangle((55,665,55+int(1170*sid/len(scenes)),680), radius=7, fill=BLUE)

def draw_text_block(draw, scene):
    draw.text((70,120),f"{scene['id']:02d}",font=F_BIG,fill=GOLD)
    draw.text((185,136),scene['title'],font=F_TITLE,fill=WHITE)
    draw.text((188,202),scene['kicker'],font=F_KICK,fill=CYAN)
    y=510
    for b in BULLETS.get(scene['visual'],[])[:3]:
        draw.ellipse((78,y+7,90,y+19),fill=GOLD); draw.text((105,y),b,font=F_BODY,fill=WHITE); y+=42

def korea_poly(cx,cy,s=1.0):
    pts=[(-25,-90),(6,-72),(20,-50),(11,-34),(33,-9),(23,15),(38,35),(22,57),(6,91),(-13,76),(-25,55),(-17,34),(-33,17),(-25,-5),(-43,-26),(-31,-50),(-40,-70)]
    return [(cx+x*s,cy+y*s) for x,y in pts]

def draw_ship(draw,x,y,s=1.0,color=WHITE):
    draw.polygon([(x-60*s,y),(x+65*s,y),(x+42*s,y+28*s),(x-45*s,y+28*s)],fill=color)
    draw.rectangle((x-18*s,y-38*s,x+16*s,y),fill=color)
    draw.polygon([(x+16*s,y-38*s),(x+52*s,y-12*s),(x+16*s,y-12*s)],fill=(120,210,245))
    draw.line((x-25*s,y+34*s,x+75*s,y+34*s),fill=BLUE,width=max(1,int(4*s)))

def draw_city(draw,base_y=470,accent=BLUE):
    xs=[780,830,875,920,970,1020,1065,1110,1160]; hs=[130,190,110,235,155,205,120,180,145]; ws=[38,45,34,52,40,48,33,42,38]
    for x,h,w in zip(xs,hs,ws):
        draw.rounded_rectangle((x,base_y-h,x+w,base_y),radius=4,fill=(26,55,83),outline=(64,126,168),width=2)
        for yy in range(base_y-h+18,base_y-8,24): draw.rectangle((x+8,yy,x+w-8,yy+8),fill=accent)

def arrow(draw,a,b,color=RED,width=5):
    draw.line((*a,*b),fill=color,width=width); ang=math.atan2(b[1]-a[1],b[0]-a[0]); l=16
    pts=[b,(b[0]-l*math.cos(ang-0.5),b[1]-l*math.sin(ang-0.5)),(b[0]-l*math.cos(ang+0.5),b[1]-l*math.sin(ang+0.5))]; draw.polygon(pts,fill=color)

def draw_visual(draw, scene):
    v=scene['visual']; x0,y0,x1,y1=740,110,1220,600
    rounded_panel(draw,(x0,y0,x1,y1),fill=(8,21,39),outline=(44,89,126),radius=28,width=2)
    if v=='hook':
        draw.polygon(korea_poly(980,335,1.5),fill=(40,155,210),outline=WHITE)
        for r in (120,175,230): draw.ellipse((980-r,335-r,980+r,335+r),outline=(38,82,118),width=2)
        draw.text((830,520),'ISLAND KOREA',font=F_KICK,fill=GOLD)
    elif v=='map_split':
        draw.line((980,145,980,565),fill=(70,100,130),width=2); draw.polygon(korea_poly(850,345,1.2),fill=(42,92,124),outline=MUTED); draw.text((785,510),'REAL',font=F_SMALL,fill=MUTED); draw.polygon(korea_poly(1100,345,1.2),fill=(40,165,215),outline=WHITE); draw.ellipse((1022,250,1178,440),outline=BLUE,width=4); draw.text((1030,510),'ISLAND',font=F_SMALL,fill=CYAN)
    elif v=='invasion':
        draw.polygon(korea_poly(1030,360,1.25),fill=(30,115,155),outline=WHITE)
        for y in (240,310,380): arrow(draw,(770,y),(930,y),RED,5)
        draw.line((935,185,935,525),fill=CYAN,width=8); draw.text((785,180),'LAND ARMY',font=F_SMALL,fill=RED); draw.text((948,190),'SEA',font=F_SMALL,fill=CYAN)
    elif v=='navy':
        draw_ship(draw,980,355,1.4,WHITE)
        for xx in (810,1120): draw_ship(draw,xx,470,0.7,(130,195,225))
        draw.arc((800,180,1160,540),200,340,fill=BLUE,width=5); draw.text((860,165),'NAVAL STATE',font=F_KICK,fill=CYAN)
    elif v=='merchant':
        draw_ship(draw,960,420,1.0,WHITE); boxes=[(800,210,890,280),(925,170,1025,250),(1050,230,1150,305)]
        for i,b in enumerate(boxes): draw.rounded_rectangle(b,radius=10,fill=(38,80,105),outline=GOLD,width=2); draw.text((b[0]+16,b[1]+18),['SILK','SPICE','METAL'][i],font=F_SMALL,fill=WHITE)
        arrow(draw,(825,340),(1110,340),GREEN,5)
    elif v=='capital':
        draw_city(draw,480,CYAN); draw.polygon(korea_poly(835,300,0.8),fill=(42,108,145),outline=WHITE); draw.ellipse((807,340,827,360),fill=GOLD); draw.text((760,375),'BUSAN',font=F_SMALL,fill=GOLD); draw.ellipse((800,430,820,450),fill=CYAN); draw.text((760,455),'JEJU',font=F_SMALL,fill=CYAN)
    elif v=='trade':
        pts={'CHINA':(810,270),'KOREA':(980,360),'JAPAN':(1140,260)}
        for name,(x,y) in pts.items(): draw.ellipse((x-35,y-35,x+35,y+35),fill=(30,83,115),outline=WHITE,width=2); draw.text((x-38,y+50),name,font=F_TINY,fill=MUTED)
        arrow(draw,pts['CHINA'],pts['KOREA'],GREEN,5); arrow(draw,pts['KOREA'],pts['JAPAN'],GREEN,5); draw.text((840,505),'TRANSIT TRADE',font=F_KICK,fill=GOLD)
    elif v=='voyage':
        route=[(800,220),(865,275),(920,340),(990,390),(1080,445),(1160,500)]
        for a,b in zip(route,route[1:]): arrow(draw,a,b,CYAN,4)
        for p in route: draw.ellipse((p[0]-8,p[1]-8,p[0]+8,p[1]+8),fill=GOLD)
        draw.text((775,180),'BUSAN',font=F_TINY,fill=WHITE); draw.text((1060,520),'S.E. ASIA',font=F_TINY,fill=WHITE); draw_ship(draw,990,310,0.6,WHITE)
    elif v=='diaspora':
        hubs=[(815,250),(920,210),(1030,270),(1130,220),(880,420),(1040,450)]
        for a in hubs: draw.ellipse((a[0]-22,a[1]-22,a[0]+22,a[1]+22),fill=(24,73,102),outline=CYAN,width=3)
        for a in hubs[1:]: draw.line((*hubs[0],*a),fill=(55,105,130),width=2)
        draw.text((815,520),'KOREAN MERCHANT NETWORK',font=F_SMALL,fill=GOLD)
    elif v=='culture':
        labels=[('LANGUAGE',800,210),('FOOD',1025,210),('SAILING',800,390),('MIGRATION',1025,390)]
        for t,x,y in labels: draw.rounded_rectangle((x,y,x+160,y+105),radius=18,fill=(23,58,86),outline=(70,120,150),width=2); draw.text((x+18,y+38),t,font=F_TINY,fill=WHITE)
    elif v=='midpoint':
        vals=[('INVASION',35,RED),('TRADE',88,GREEN),('NAVY',82,CYAN),('WEALTH',75,GOLD)]; y=205
        for name,val,c in vals: draw.text((790,y),name,font=F_TINY,fill=MUTED); draw.rounded_rectangle((900,y+2,1160,y+22),radius=8,fill=(29,53,76)); draw.rounded_rectangle((900,y+2,900+int(260*val/100),y+22),radius=8,fill=c); y+=80
        draw.text((875,525),'TOO GOOD?',font=F_KICK,fill=WHITE)
    elif v=='dependency':
        items=[('FOOD',0.82),('ENERGY',0.92),('METAL',0.75)]; y=225
        for name,val in items: draw.text((790,y),name,font=F_SMALL,fill=MUTED); draw.line((900,y+15,1160,y+15),fill=(45,70,92),width=14); draw.line((900,y+15,900+260*val,y+15),fill=GOLD,width=14); y+=90
        draw_ship(draw,970,500,0.8,WHITE)
    elif v=='blockade':
        draw.polygon(korea_poly(980,350,1.1),fill=(36,115,145),outline=WHITE)
        for r,c in [(110,RED),(165,(180,70,70)),(220,(120,55,55))]: draw.ellipse((980-r,350-r,980+r,350+r),outline=c,width=4)
        draw.text((860,520),'SEA BLOCKADE',font=F_KICK,fill=RED)
    elif v=='imperial':
        draw.polygon(korea_poly(980,350,1.0),fill=(40,140,180),outline=WHITE); starts=[(790,170),(1170,170),(780,510),(1180,510)]
        for s in starts: arrow(draw,s,(980,350),RED,4)
        for t,x,y in [('UK',770,135),('RU',1160,135),('US',750,525),('JP',1170,525)]: draw.text((x,y),t,font=F_KICK,fill=WHITE)
    elif v=='rivalry':
        draw.line((980,150,980,550),fill=(70,95,115),width=3); draw.text((815,190),'KOREA',font=F_KICK,fill=CYAN); draw.text((1035,190),'JAPAN',font=F_KICK,fill=RED); draw_ship(draw,850,360,0.8,WHITE); draw_ship(draw,1110,360,0.8,(230,170,170)); draw.text((930,490),'VS',font=F_TITLE,fill=GOLD)
    elif v=='strategic':
        draw.polygon(korea_poly(980,350,1.05),fill=(42,145,183),outline=WHITE); draw.ellipse((860,230,1100,470),outline=GOLD,width=3); draw.line((980,180,980,520),fill=GOLD,width=2); draw.line((810,350,1150,350),fill=GOLD,width=2)
        for label,pos in [('CHINA',(790,260)),('JAPAN',(1110,260)),('RUSSIA',(915,165)),('PACIFIC',(1015,515))]: draw.text(pos,label,font=F_TINY,fill=MUTED)
    elif v=='colonial':
        draw.polygon(korea_poly(980,350,1.1),fill=(38,93,126),outline=WHITE); ports=[('BUSAN',(1015,420),RED),('INCHEON',(945,320),GOLD),('JEJU',(960,480),CYAN)]
        for name,(x,y),c in ports: draw.ellipse((x-12,y-12,x+12,y+12),fill=c); draw.line((x,y,x+120,y-40),fill=c,width=3); draw.text((x+125,y-55),name,font=F_TINY,fill=WHITE)
        draw.text((820,190),'FOREIGN PORTS?',font=F_KICK,fill=RED)
    elif v=='division':
        draw.polygon(korea_poly(980,350,1.2),fill=(36,120,155),outline=WHITE); draw.line((860,350,1100,350),fill=RED,width=4)
        for x in range(880,1080,30): draw.line((x,270,x,440),fill=(230,150,70),width=2)
        draw.text((835,505),'NO 38TH PARALLEL, BUT...',font=F_SMALL,fill=GOLD)
    elif v=='modern':
        draw_city(draw,490,CYAN); draw_ship(draw,870,555,0.65,WHITE); draw_ship(draw,1080,555,0.65,(160,210,230)); draw.text((830,165),'BUSAN 2026',font=F_KICK,fill=GOLD); draw.text((828,205),'FINANCE · PORT · NAVY',font=F_TINY,fill=MUTED)
    elif v=='ending':
        draw.polygon(korea_poly(980,340,1.35),fill=(42,155,195),outline=WHITE)
        for r in (120,180,240): draw.ellipse((980-r,340-r,980+r,340+r),outline=(34,70,105),width=2)
        draw.text((835,525),'POWER > GEOGRAPHY',font=F_KICK,fill=GOLD)

def render_frame(scene):
    im=grad_bg(); d=ImageDraw.Draw(im); draw_header(d,scene); draw_text_block(d,scene); draw_visual(d,scene); d.text((70,690),'가정 역사 시나리오 · 사실과 추정을 구분해 감상하세요',font=F_TINY,fill=(115,140,160)); path=FRAMES/f"scene_{scene['id']:02d}.png"; im.save(path,quality=95); return path

def ffprobe_duration(path):
    r=subprocess.run(['ffprobe','-v','error','-show_entries','format=duration','-of','default=nw=1:nk=1',str(path)],capture_output=True,text=True,check=True); return float(r.stdout.strip())

def run(cmd): subprocess.run(cmd,check=True)

def build_audio(scene):
    out=AUDIO/f"scene_{scene['id']:02d}.mp3"; run(['edge-tts','--text',scene['narration'],'--voice','ko-KR-SunHiNeural','--rate','-5%','--write-media',str(out)]); return out

def build_clip(scene, frame, audio):
    dur=ffprobe_duration(audio); out=CLIPS/f"scene_{scene['id']:02d}.mp4"; frames=max(1,int(math.ceil(dur*FPS))); fade_out=max(0,dur-0.45)
    vf=(f"zoompan=z='min(zoom+0.00018,1.06)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s={W}x{H}:fps={FPS},fade=t=in:st=0:d=0.35,fade=t=out:st={fade_out:.3f}:d=0.4,format=yuv420p")
    run(['ffmpeg','-y','-loop','1','-i',str(frame),'-i',str(audio),'-vf',vf,'-t',f'{dur:.3f}','-c:v','libx264','-preset','veryfast','-crf','21','-c:a','aac','-b:a','160k','-shortest',str(out)]); return out,dur

def make_thumbnail():
    im=grad_bg((6,10,24),(17,55,92)); d=ImageDraw.Draw(im); d.polygon(korea_poly(1010,360,1.55),fill=(42,155,205),outline=WHITE)
    for r in (135,205): d.ellipse((1010-r,360-r,1010+r,360+r),outline=(52,100,140),width=3)
    d.text((70,110),'만약 한국이',font=ImageFont.truetype(FONT_BOLD,62),fill=WHITE); d.text((70,190),'섬나라였다면?',font=ImageFont.truetype(FONT_BOLD,82),fill=GOLD); d.rounded_rectangle((72,315,650,388),radius=24,fill=(230,70,70)); d.text((105,330),'지금보다 강했을까?',font=F_KICK,fill=WHITE); d.text((72,445),'부산 수도 · 해군강국 · 그리고 예상 못 한 대가',font=F_BODY,fill=MUTED); im.save(BUILD/'thumbnail.png',quality=95)

def main():
    concat=[]; total=0.0
    for scene in scenes:
        frame=render_frame(scene); audio=build_audio(scene); clip,dur=build_clip(scene,frame,audio); total+=dur; concat.append(f"file '{clip.resolve().as_posix()}'")
    (BUILD/'concat.txt').write_text('\n'.join(concat),encoding='utf-8'); run(['ffmpeg','-y','-f','concat','-safe','0','-i',str(BUILD/'concat.txt'),'-c','copy',str(BUILD/'final.mp4')]); make_thumbnail(); (BUILD/'duration.txt').write_text(f'{total:.2f} seconds\n',encoding='utf-8')

if __name__=='__main__': main()
