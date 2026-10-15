# SELLO FIJO "NOTICIAS CON EDDY" (rojo, blanco, azul marino). Reusar en cada noticiero.
import math, numpy as np
from PIL import Image, ImageDraw, ImageFont
import os as _os
G=_os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))),"fonts")+"/"
ANTON=G+"Anton-Regular.ttf"; BLK=G+"Barlow-Black.ttf"; BOLD=G+"Barlow-Bold.ttf"; SEMI=G+"Barlow-SemiBold.ttf"
_fc={}
def F(p,s):
    if (p,s) not in _fc: _fc[(p,s)]=ImageFont.truetype(p,s)
    return _fc[(p,s)]
W,H,FPS=1080,1920,30
RED=(227,6,19); NAVY=(10,31,77); BLUE=(0,82,204); WHITE=(255,255,255); INK=(18,24,38); YEL=(255,214,0); GRAY=(90,100,120); LIGHT=(238,242,247)
PX,PY,PW,PH=60,330,960,760
def ease(x): x=max(0,min(1,x)); return 1-(1-x)**3
def tw(d,txt,f): b=d.textbbox((0,0),txt,font=f); return b[2]-b[0], b[3]-b[1], b
def ctext(d,txt,f,cx,y,fill,stroke=0,sf=None):
    w,h,b=tw(d,txt,f); d.text((cx-w/2-b[0],y-b[1]),txt,font=f,fill=fill,stroke_width=stroke,stroke_fill=sf); return h
def fit(d,txt,path,size,maxw):
    while size>20:
        f=F(path,size)
        if tw(d,txt,f)[0]<=maxw: return f
        size-=4
    return F(path,size)
def make_bg():
    bg=Image.new("RGB",(W,H),LIGHT); bd=ImageDraw.Draw(bg)
    for y in range(H):
        c=int(246-14*y/H); bd.line([(0,y),(W,y)],fill=(c-6,c-2,c+4))
    stripe=Image.new("RGBA",(W+200,H),(0,0,0,0)); sd=ImageDraw.Draw(stripe)
    for x in range(-H,W+200,100): sd.line([(x,H),(x+H,0)],fill=(10,31,77,14),width=22)
    return bg,stripe

# ---------- SUBTÍTULOS: agrupación sin perder palabras ----------
# Antes: corte voraz a 4 palabras / 20 letras sin mirar adelante -> la última palabra de cada frase
# quedaba sola ("ELLOS", "TORMENTA", "DIECINUEVE") y se veía ~0,4 s; y la regla de puntuación nunca
# actuaba porque edge-tts entrega las palabras sin signos. Ahora: frases por puntuación del guion
# (o pausa de voz), cada frase se reparte en bloques equilibrados (programación dinámica, sin
# huérfanas cortas) y cada bloque se mantiene en pantalla hasta que empieza el siguiente.
import re as _re, unicodedata as _ud
MAXC=24; MAXW=5; PAUSA=0.25
def _norm(x): return "".join(c for c in _ud.normalize("NFD",x.lower()) if _ud.category(c)[0] in "LN")
def puntuar(words,guion):
    """Devuelve copia de words con el signo final del guion pegado a cada palabra (solo para cortar)."""
    out=[list(w) for w in words]
    if not guion: return out
    toks=[(m.group(1),m.group(2)) for m in _re.finditer(r"([\w]+)([^\w\s]*)",guion)]
    j=0
    for w in out:
        k=j
        while k<len(toks) and _norm(toks[k][0])!=_norm(w[2]): k+=1
        if k<len(toks):
            if any(ch in toks[k][1] for ch in ".,:;?!»"): w.append(True)
            j=k+1
    return out
def _fin(w,nxt):
    if nxt is None: return True
    if len(w)>3 and nxt[3]!=w[3]: return True
    if len(w)>4 and w[4] is True: return True
    return (nxt[0]-w[1])>PAUSA
def _repartir(fr):
    n=len(fr); L=[len(w[2]) for w in fr]; INF=float("inf"); best=[0]+[INF]*n; prv=[0]*(n+1)
    for i in range(1,n+1):
        for j in range(i-1,-1,-1):
            k=i-j; c=sum(L[j:i])+k-1
            if k>MAXW or (c>MAXC and k>1): break
            pen=1000+c*c
            if k==1 and n>1 and L[j]<=6: pen+=250      # evita palabra corta huérfana
            if best[j]+pen<best[i]: best[i]=best[j]+pen; prv[i]=j
    out=[]; i=n
    while i>0: out.append(fr[prv[i]:i]); i=prv[i]
    return out[::-1]
def agrupar(words,guion=None):
    pw=puntuar(words,guion); chunks=[]; fr=[]
    for i,w in enumerate(pw):
        fr.append(words[i]); nxt=pw[i+1] if i+1<len(pw) else None
        if _fin(w,nxt): chunks+=_repartir(fr); fr=[]
    flat=[w for c in chunks for w in c]
    assert [tuple(w[:3]) for w in flat]==[tuple(w[:3]) for w in words], "subtítulos: se perdieron palabras"
    return chunks
def ventanas(chunks,total,hold=0.9,minvis=0.8,cola=0.45):
    """Intervalo [a,b) de cada bloque; sin solaparse, nunca se salta un bloque."""
    win=[]
    for i,c in enumerate(chunks):
        a=c[0][0]-0.05; nx=chunks[i+1][0][0]-0.05 if i+1<len(chunks) else total
        b=nx if nx-c[-1][1]<=hold else max(c[-1][1]+cola,a+minvis)
        win.append([a,min(b,nx,total)])
    for i in range(1,len(win)): win[i][0]=max(win[i][0],win[i-1][1]) if win[i][0]<win[i-1][1] else win[i][0]
    return win
def verificar_subs(chunks,win,fps=30):
    """Lista de palabras que se ven en pantalla en algún fotograma, en orden."""
    vis=[]
    for c,(a,b) in zip(chunks,win):
        if int(b*fps)-int(a*fps)<1: raise AssertionError("bloque sin fotogramas: "+" ".join(w[2] for w in c))
        vis+=[w[2] for w in c]
    return vis
class Sello:
    def __init__(s,fecha,ticker,words,total,guion=None):
        s.fecha=fecha; s.total=total; s.bg,s.stripe=make_bg()
        tf=F(BOLD,36); d=ImageDraw.Draw(s.bg); s.TW=tw(d,ticker,tf)[0]
        s.tick=Image.new("RGB",(s.TW*2+40,52),NAVY); td=ImageDraw.Draw(s.tick)
        td.text((0,6),ticker,font=tf,fill=WHITE); td.text((s.TW+40,6),ticker,font=tf,fill=WHITE)
        s.chunks=agrupar(words,guion); s.win=ventanas(s.chunks,total)
        s.mask=Image.new("L",(PW,PH),0); ImageDraw.Draw(s.mask).rounded_rectangle([0,0,PW-1,PH-1],radius=30,fill=255)
        s.shadow=Image.new("RGBA",(PW+40,PH+40),(0,0,0,0)); ImageDraw.Draw(s.shadow).rounded_rectangle([20,24,PW+20,PH+24],radius=30,fill=(0,0,0,60))
    def frame(s,t,pim,lt,first,story,cort=None):
        im=s.bg.copy(); off=int(t*60)%100; sc=s.stripe.crop((off,0,off+W,H)); im.paste(sc,(0,0),sc); d=ImageDraw.Draw(im)
        # barra NOTICIAS CON EDDY
        d.rectangle([40,150,330,240],fill=RED); ctext(d,"NOTICIAS",F(ANTON,62),185,163,WHITE)
        d.rectangle([330,150,720,240],fill=NAVY); ctext(d,"CON EDDY",F(ANTON,62),525,163,WHITE)
        ctext(d,s.fecha,F(BLK,40),880,175,NAVY)
        d.rectangle([40,240,1040,248],fill=(205,212,225)); d.rectangle([40,240,40+int(1000*min(1,t/s.total)),248],fill=RED)
        tx=int(t*140)%(s.TW+40); im.paste(s.tick.crop((tx,0,tx+880,52)),(160,256)); d.rectangle([40,256,160,308],fill=RED); ctext(d,"HOY",F(ANTON,38),100,262,WHITE)
        # panel: SIEMPRE opaco (solo deslizamiento). El fundido con máscara alfa dejaba el panel
        # semitransparente (presentador "fantasma" y cuadros de color sólido parpadeando).
        e=ease(lt/0.35); dx=0 if first else int((1-e)*60)
        im.paste(s.shadow,(PX-20+dx,PY-20),s.shadow)
        im.paste(pim,(PX+dx,PY),s.mask)
        # rótulo de sección + titular
        s0,cat,head,src=story; le=1.0 if s0==0 else ease((t-s0)/0.35)
        cf=F(BLK,40); cw=tw(d,cat,cf)[0]+50; x0=40-int((1-le)*600)
        d.rectangle([x0,1108,x0+cw,1162],fill=RED); ctext(d,cat,cf,x0+cw/2,1115,WHITE)
        hf=fit(d,head,ANTON,64,840); d.rectangle([x0,1162,x0+900,1262],fill=WHITE); d.rectangle([x0,1162,x0+14,1262],fill=NAVY)
        hw,hh,hb=tw(d,head,hf); d.text((x0+36-hb[0],1212-hh/2-hb[1]),head,font=hf,fill=INK)
        # subtítulos
        ch=None
        for c,(a,b) in zip(s.chunks,s.win):
            if a<=t<b: ch=c; break
        if ch:
            sf=F(BLK,70); txt=" ".join(w[2].upper() for w in ch)
            if tw(d,txt,sf)[0]>860: sf=fit(d,txt,BLK,70,860)
            tot=tw(d,txt,sf)[0]; x=490-tot/2; y=1290
            d.rounded_rectangle([x-26,y-14,x+tot+26,y+96],radius=20,fill=NAVY)
            for w in ch:
                wt=w[2].upper(); d.text((x,y),wt,font=sf,fill=YEL if w[0]<=t<=w[1]+0.08 else WHITE); x+=tw(d,wt+" ",sf)[0]
        if src:
            f=F(BOLD,34); sw=tw(d,src,f)[0]
            d.rounded_rectangle([40,1428,40+sw+80,1486],radius=29,fill=WHITE,outline=(200,206,218),width=2)
            d.ellipse([60,1446,82,1468],fill=BLUE); d.text((96,1435),src,font=f,fill=INK)
        if cort is not None: s.cortinilla(im,cort)
        return im
    def cortinilla(s,im,p):
        # p 0..1: tres bloques rojo/blanco/azul barren la pantalla JUNTOS (sin desfase entre bandas,
        # antes la banda azul llegaba tarde y quedaba un hueco). Banda blanca con filete azul para
        # que se lea como bloque y no como hueco sobre fondo claro.
        # Logo recortado al área de las barras: si se dibuja entero al salir (p>0.5) flotaba
        # encima del presentador o del gráfico anterior.
        hb=-(-H//3)
        if p<0.5: xa,x1=0,int(W*ease(p*2.2))
        else: xa,x1=int(W*ease((p-0.5)*2.2)),W
        if x1<=xa: return
        lay=im.copy(); d=ImageDraw.Draw(lay)
        for k,col in enumerate([RED,WHITE,NAVY]):
            y0=k*hb; d.rectangle([xa,y0,x1,min(H,y0+hb)],fill=col)
        d.rectangle([xa,hb-6,x1,hb+6],fill=NAVY); d.rectangle([xa,2*hb-6,x1,2*hb+6],fill=RED)
        if 0.3<p<0.8:
            d.rectangle([140,860,540,1000],fill=RED); ctext(d,"NOTICIAS",F(ANTON,90),340,875,WHITE)
            d.rectangle([540,860,940,1000],fill=NAVY); ctext(d,"CON EDDY",F(ANTON,90),740,875,WHITE)
        im.paste(lay.crop((xa,0,min(W,x1+1),H)),(xa,0))

# ---------- CIFRAS: la cifra que dice la voz va FIJA desde el primer fotograma ----------
# Antes cada escena hacía un contador (int(1000*ease(lt))) y en pantalla salía "RD$ 613" mientras
# la voz decía "mil pesos". Usar siempre cifra(): devuelve el valor final, sin contador.
def cifra(final,lt=None): return final

# ---------- PRONUNCIACIÓN: grafía fonética solo para la voz ----------
# es-MX-JorgeNeural lee "Eddy Infante" con acento inglés. tts_texto() se usa SOLO para lo que se
# manda a edge-tts; restaurar() devuelve los WordBoundary a la grafía real para subtítulos/guion.
FONETICA={"Eddy":"Edi","Infante":"Infánte"}
def tts_texto(txt):
    for a,b in FONETICA.items(): txt=_re.sub(r"\b%s\b"%a,b,txt)
    return txt
def restaurar(words):
    inv={_norm(b):a for a,b in FONETICA.items()}
    for w in words:
        w[2]=w[2].strip(".,;:!?¡¿«»\"'")   # edge-tts a veces entrega "B." -> el diff con el guion falla
        if _norm(w[2]) in inv: w[2]=inv[_norm(w[2])]
    return words

def cover(eddy_img,l1,l2,fecha,out):
    im=Image.new("RGB",(W,H),NAVY); e=eddy_img.convert("RGB")
    r=max(W/e.width,1300/e.height); e=e.resize((int(e.width*r),int(e.height*r)),Image.LANCZOS)
    im.paste(e.crop(((e.width-W)//2,0,(e.width-W)//2+W,1300)),(0,330)); d=ImageDraw.Draw(im)
    d.rectangle([0,0,W,330],fill=NAVY); d.rectangle([40,150,330,240],fill=RED); ctext(d,"NOTICIAS",F(ANTON,62),185,163,WHITE)
    d.rectangle([330,150,720,240],fill=WHITE); ctext(d,"CON EDDY",F(ANTON,62),525,163,NAVY); ctext(d,fecha,F(BLK,40),880,175,WHITE)
    d.rectangle([0,1180,W,H],fill=NAVY); d.rectangle([0,1180,W,1196],fill=RED)
    f=fit(d,l1,ANTON,230,980); ctext(d,l1,f,W/2,1240,YEL); f=fit(d,l2,ANTON,150,980); ctext(d,l2,f,W/2,1500,WHITE)
    im.save(out,quality=92)
