import sys, json, random, os
from PIL import Image, ImageDraw, ImageFont, ImageFilter
D=sys.argv[1]; OUT=sys.argv[2]; G='/usr/share/fonts/truetype/google-fonts/'
CREAM=(253,250,241); PAPER=(255,253,247); MAROON=(132,36,38); INK=(92,40,38); TAPE=(232,214,196,210)
SIZES={'instagram':(1080,1350),'tiktok':(1080,1920),'youtube':(1080,1080)}
def F(f,s,w=None):
    ft=ImageFont.truetype(G+f,s)
    if w:
        try: ft.set_variation_by_axes([w])
        except Exception: pass
    return ft
HEART=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',34)
def wrap(d,text,ft,maxw):
    out=[]
    for para in text.split('\n'):
        line=''
        for w in para.split():
            t=(line+' '+w).strip()
            if d.textlength(t,font=ft)<=maxw: line=t
            else: out.append(line); line=w
        out.append(line)
    return out
def background(W,H,seed):
    random.seed(seed); im=Image.new('RGB',(W,H),CREAM)
    g=Image.effect_noise((W,H),12).convert('RGB')
    return Image.blend(im,Image.composite(im,g,Image.new('L',(W,H),235)),0.35).convert('RGBA')
def logo(base,W,H,lw,bottom_pad):
    lg=Image.open(f'{D}/wm/tinynotes_wm_maroon.png').convert('RGBA')
    lg=lg.resize((lw,int(lg.height*lw/lg.width)),Image.LANCZOS)
    base.alpha_composite(lg,((W-lw)//2,H-lg.height-bottom_pad)); return lg.height
def card(note,sign,cw,maxh,seed,fsize=54):
    n=len(note); fsize={True:fsize}[True]
    tmp=ImageDraw.Draw(Image.new('RGB',(10,10)))
    while True:
        nf=F('Lora-Italic-Variable.ttf',fsize,500); lh=int(fsize*1.45)
        lines=wrap(tmp,note,nf,cw-170)
        ch=len(lines)*lh+(110 if sign else 0)+170
        if ch<=maxh or fsize<=34: break
        fsize-=2
    c=Image.new('RGBA',(cw+80,ch+80),(0,0,0,0)); cd=ImageDraw.Draw(c)
    cd.rounded_rectangle((40,40,40+cw,40+ch),18,fill=PAPER+(255,))
    ty=40+85
    for l in lines: cd.text((110,ty),l,font=nf,fill=INK); ty+=lh
    if sign:
        sf=F('Lora-Italic-Variable.ttf',int(fsize*0.74),400); sw=cd.textlength(sign,font=sf)
        hx=40+cw-70-40; cd.text((hx-14-sw,ty+24),sign,font=sf,fill=MAROON); cd.text((hx,ty+30),'♥',font=HEART,fill=MAROON)
    cd.rectangle((40+cw/2-80,22,40+cw/2+80,72),fill=TAPE)
    random.seed(seed); c=c.rotate(random.choice([-2.2,-1.4,1.5,2.0]),resample=Image.BICUBIC,expand=True)
    sh=Image.new('RGBA',c.size,(0,0,0,0)); sh.putalpha(c.split()[3].point(lambda v:int(v*0.22)).filter(ImageFilter.GaussianBlur(18)))
    return c,sh
def hook_text(d,W,y,text,size=34):
    hf=F('Poppins-Medium.ttf',size)
    for l in wrap(d,text.upper(),hf,W-200):
        d.text(((W-d.textlength(l,font=hf))/2,y),l,font=hf,fill=MAROON); y+=int(size*1.42)
    return y
def layout(platform):
    W,H=SIZES[platform]
    # TikTok: keep clear of top bar and bottom caption/right rail UI
    return dict(W=W,H=H,top={'instagram':100,'tiktok':260,'youtube':70}[platform],
                bottom={'instagram':50,'tiktok':430,'youtube':40}[platform],
                lw={'instagram':150,'tiktok':160,'youtube':120}[platform],
                cw={'instagram':820,'tiktok':820,'youtube':760}[platform])
def note_slide(platform,hook,note,sign,seed):
    L=layout(platform); W,H=L['W'],L['H']
    base=background(W,H,seed); d=ImageDraw.Draw(base)
    y=hook_text(d,W,L['top'],hook,40 if platform=='tiktok' else 34) if hook else L['top']
    lh=logo(base,W,H,L['lw'],L['bottom'])
    area_top=y+30; area_bot=H-L['bottom']-lh-40
    n=len(note); base_fs=78 if n<60 else 64 if n<110 else 56
    if platform=='tiktok': base_fs+=8
    if platform=='youtube': base_fs-=4
    c,sh=card(note,sign,L['cw'],area_bot-area_top-60,seed,base_fs)
    cx=(W-c.width)//2; cy=area_top+max(0,(area_bot-area_top-c.height)//2)
    base.alpha_composite(sh,(cx+10,cy+18)); base.alpha_composite(c,(cx,cy)); return base.convert('RGB')
def cover_slide(platform,kicker,title,sub,seed):
    L=layout(platform); W,H=L['W'],L['H']
    base=background(W,H,seed); d=ImageDraw.Draw(base)
    lh=logo(base,W,H,L['lw'],L['bottom'])
    kf=F('Poppins-Medium.ttf',34); tf=F('Lora-Variable.ttf',96 if platform!='youtube' else 84,600); sf=F('Lora-Italic-Variable.ttf',46,400)
    tl=wrap(d,title,tf,W-200); block=60+len(tl)*int(tf.size*1.2)+40+70
    y=L['top']+((H-L['bottom']-lh-L['top'])-block)//2
    d.text(((W-d.textlength(kicker.upper(),font=kf))/2,y),kicker.upper(),font=kf,fill=MAROON); y+=80
    for l in tl: d.text(((W-d.textlength(l,font=tf))/2,y),l,font=tf,fill=INK); y+=int(tf.size*1.2)
    y+=30; d.text(((W-d.textlength(sub,font=sf))/2,y),sub,font=sf,fill=MAROON)
    return base.convert('RGB')
spec=json.load(open(sys.argv[3]))
for item in spec:
    folder=os.path.join(OUT,item['id']); os.makedirs(folder,exist_ok=True)
    for p in SIZES:
        if item['type']=='single':
            note_slide(p,item['hook'],item['note'],item['sign'],item['id']).save(f"{folder}/{p}.png")
        else:
            sl=item['slides']
            for i,s in enumerate(sl,1):
                img=cover_slide(p,*s['cover'],item['id']) if 'cover' in s else note_slide(p,s.get('hook'),s['note'],s.get('sign'),item['id']+str(i))
                img.save(f"{folder}/{p}_{i:02d}.png")
print('done')
