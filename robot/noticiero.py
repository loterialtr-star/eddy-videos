#!/usr/bin/env python3
"""NOTICIAS CON EDDY - todo corre en GitHub Actions. No publica nada.
RSS (oficiales + medios RD + mundo) -> IA redacta con palabras propias (cita medio y fecha) -> imagenes IA
(nunca fotos de los medios) -> voz edge-tts -> sello de App (rojo/blanco/azul) -> MP4 9:16."""
import asyncio, datetime as dt, email.utils, html, io, json, os, random, re, subprocess, sys, time, unicodedata, urllib.parse, urllib.request
import xml.etree.ElementTree as ET
from zoneinfo import ZoneInfo
from PIL import Image, ImageDraw, ImageFilter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sello import *  # noqa  (W,H,FPS,PX,PY,PW,PH,colores,fuentes,Sello,ctext,fit,tw,ease,tts_texto,restaurar)

TZ = ZoneInfo("America/Santo_Domingo"); AQ = os.path.dirname(os.path.abspath(__file__))
SAL = os.environ.get("SALIDA", "salida"); VOZ = os.environ.get("VOZ", "es-MX-JorgeNeural")
PROHIBIDAS = re.compile(r"loter|sorteo|quiniela|leidsa|loteka|\bloto\b|kino|\bpal[eé]\b|apuesta|jackpot|premio mayor|para ganar|\bseguro\b|el solo uno", re.I)
MESES = "enero febrero marzo abril mayo junio julio agosto septiembre octubre noviembre diciembre".split()
DIAS = "lunes martes miércoles jueves viernes sábado domingo".split()
UA = {"User-Agent": "Mozilla/5.0 (robot noticias Eddy)"}
def log(*a): print(*a, flush=True)
def get(url, data=None, headers=None, timeout=120):
    r = urllib.request.Request(url, data, {**UA, **(headers or {})}); return urllib.request.urlopen(r, timeout=timeout).read()
def limpiar(t):
    t = html.unescape(re.sub(r"<[^>]+>", " ", html.unescape(t or ""))); return re.sub(r"\s+", " ", t).strip()

# ---------- 1. FUENTES ----------
def leer_feed(f, region, horas=24):
    try: raiz = ET.fromstring(get(f["url"], timeout=30))
    except Exception as e: log("feed falla", f["nombre"], e); return []
    ahora = dt.datetime.now(TZ); out = []
    for it in raiz.iter():
        if not it.tag.endswith("item"): continue
        c = {ch.tag.split("}")[-1]: (ch.text or "") for ch in it}
        tit = limpiar(c.get("title")); desc = c.get("encoded") or c.get("description") or ""
        m = re.search(r'datetime="([^"]+)"', html.unescape(desc)); fe = None
        try:
            if m: fe = dt.datetime.fromisoformat(m.group(1))
            elif c.get("pubDate"): fe = email.utils.parsedate_to_datetime(c["pubDate"])
            elif c.get("date"): fe = dt.datetime.fromisoformat(c["date"].replace("Z", "+00:00"))
        except Exception: pass
        if not fe or not tit: continue
        fe = fe.astimezone(TZ)
        if (ahora - fe).total_seconds() > horas * 3600: continue
        cuerpo = limpiar(re.sub(r'<span class="field field--name-(title|uid|created).*?</span>\s*(</span>)?', " ", html.unescape(desc), flags=re.S)).replace(tit, "").strip()
        if PROHIBIDAS.search(tit + " " + cuerpo): continue
        out.append({"region": region, "medio": f["nombre"], "titulo": tit, "resumen": cuerpo[:700], "fecha": fe.isoformat(), "link": c.get("link") or ""})
    return out

def candidatas():
    fs = json.load(open(os.path.join(AQ, "fuentes.json"))); todas = []
    for reg in ("rd", "mundo"):
        for f in fs[reg]:
            n = leer_feed(f, reg); log(f"{f['nombre']}: {len(n)}"); todas += n[:8]
    vistos, out = set(), []
    for n in sorted(todas, key=lambda n: n["fecha"], reverse=True):
        k = re.sub(r"\W+", "", n["titulo"].lower())[:40]
        if k not in vistos: vistos.add(k); out.append(n)
    return out

# ---------- 2. REDACCION IA ----------
SISTEMA = """Eres el redactor de "Noticias con Eddy", un noticiero dominicano para TikTok y YouTube al estilo Telemicro / Teleantillas: directo, claro, con energía, español dominicano neutro.
Reglas OBLIGATORIAS:
- Escribe con TUS PALABRAS. Prohibido copiar frases de las fuentes (nunca más de 5 palabras seguidas iguales). Sin comillas textuales.
- Cada noticia cita su medio y la fecha dentro del texto ("según Diario Libre, este miércoles 14 de octubre, ...").
- Solo hechos que estén en las fuentes. No inventes cifras, nombres ni lugares. No opines.
- Prohibido: lotería, sorteos, apuestas, "para ganar", la palabra "seguro".
- Números escritos para leerse en voz alta (ej. "veinte mil setecientos médicos").
Devuelve SOLO JSON."""
def pedir_ia(cands, hoy):
    lista = "\n".join(f"[{i}] ({n['region'].upper()}) {n['medio']} | {n['fecha'][:16]} | {n['titulo']} :: {n['resumen'][:450]}" for i, n in enumerate(cands[:30]))
    usuario = f"""Hoy es {DIAS[hoy.weekday()]} {hoy.day} de {MESES[hoy.month-1]} de {hoy.year}.
Noticias disponibles:
{lista}

Elige las 5 o 6 noticias más importantes e interesantes (al menos 3 de RD y al menos 1 del mundo; temas distintos).
Arma un guion de 2 min 20 s en total (330 a 380 palabras sumando todo). JSON con esta forma:
{{"gancho": "1 o 2 frases (máx. 22 palabras) que abren con el DATO MÁS FUERTE del día (una cifra o hecho impactante) y dicen el medio",
 "gancho_cifra": "la cifra o palabra clave del gancho, muy corta (máx. 12 caracteres), ej. RD$288,500",
 "gancho_linea": "explicación corta en MAYÚSCULAS (máx. 26 caracteres)",
 "intro": "Te habla Eddy Infante. Estas son las noticias de este <día> <fecha>.",
 "noticias": [{{"i": <número de la lista>, "categoria": "PAÍS|ECONOMÍA|SALUD|SEGURIDAD|MUNDO|DEPORTES|EDUCACIÓN|CULTURA",
   "titular": "titular en MAYÚSCULAS, máx. 32 caracteres", "texto": "50 a 70 palabras con tus palabras, citando medio y fecha",
   "dato": "cifra o palabra clave corta (máx. 12 caracteres)", "dato_linea": "MAYÚSCULAS máx. 24 caracteres",
   "imagen": "prompt EN INGLÉS para una ilustración/escena fotorrealista genérica que represente el tema, SIN texto, SIN logos, SIN personas reales identificables"}}],
 "cierre": "1 o 2 frases: invita a seguir la cuenta y comentar. Sin pedir dinero."}}"""
    msgs = [{"role": "system", "content": SISTEMA}, {"role": "user", "content": usuario}]
    clave = os.environ.get("GEMINI_API_KEY")
    for intento in range(4):
        try:
            if clave:
                r = json.loads(get(f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={clave}",
                    json.dumps({"systemInstruction": {"parts": [{"text": SISTEMA}]}, "contents": [{"parts": [{"text": usuario}]}],
                                "generationConfig": {"responseMimeType": "application/json", "temperature": 0.7}}).encode(), {"Content-Type": "application/json"}))
                txt = r["candidates"][0]["content"]["parts"][0]["text"]; motor = "gemini-2.5-flash"
            else:
                r = json.loads(get("https://text.pollinations.ai/openai", json.dumps({"model": "openai", "messages": msgs,
                    "response_format": {"type": "json_object"}, "seed": random.randint(1, 99999)}).encode(), {"Content-Type": "application/json"}, 240))
                txt = r["choices"][0]["message"]["content"]; motor = "pollinations/" + r.get("model", "openai")
            g = json.loads(re.search(r"\{.*\}", txt, re.S).group(0))
            problemas = revisar_guion(g, cands)
            if not problemas: return g, motor
            log("guion rechazado:", problemas); msgs.append({"role": "assistant", "content": txt})
            msgs.append({"role": "user", "content": "Corrige esto y devuelve el JSON completo: " + "; ".join(problemas)})
            usuario += "\n\nATENCIÓN, corrige: " + "; ".join(problemas)
        except Exception as e:
            log("IA falla", intento, e); time.sleep(15)
    sys.exit("La IA no entregó un guion válido: no se arma video.")

def _n(x): return [w for w in re.findall(r"\w+", unicodedata.normalize("NFC", x.lower()))]
def copia_max(texto, fuente):
    a, b = _n(texto), _n(fuente); s = {tuple(b[i:i+6]) for i in range(len(b)-5)}
    return sum(1 for i in range(len(a)-5) if tuple(a[i:i+6]) in s)
def revisar_guion(g, cands):
    p = []
    ns = g.get("noticias") or []
    if not 4 <= len(ns) <= 7: p.append("deben ser 5 o 6 noticias")
    regs = [cands[n["i"]]["region"] for n in ns if isinstance(n.get("i"), int) and n["i"] < len(cands)]
    if len(regs) != len(ns): p.append("índice de noticia inválido"); return p
    if regs.count("rd") < 3 or regs.count("mundo") < 1: p.append("mínimo 3 de RD y 1 del mundo")
    total = " ".join([g.get("gancho", ""), g.get("intro", ""), g.get("cierre", "")] + [n["texto"] for n in ns])
    pal = len(total.split())
    if not 290 <= pal <= 420: p.append(f"el total debe tener 330-380 palabras (tiene {pal})")
    m = PROHIBIDAS.search(total + " ".join(n["titular"] for n in ns))
    if m: p.append(f"palabra prohibida: {m.group(0)}")
    for n in ns:
        c = cands[n["i"]]
        if c["medio"].lower().split()[-1] not in n["texto"].lower(): p.append(f"la noticia {n['i']} debe citar a {c['medio']}")
        if copia_max(n["texto"], c["titulo"] + " " + c["resumen"]) > 0: p.append(f"la noticia {n['i']} copia frases de la fuente; reescribe con tus palabras")
    return p

# ---------- 3. IMAGENES IA (nunca fotos de medios) ----------
ESTILO = ", editorial news illustration, cinematic photorealistic, dramatic lighting, high detail, 4k, no text, no letters, no watermark, no logos"
def imagen_ia(prompt, ruta, semilla):
    url = "https://image.pollinations.ai/prompt/" + urllib.parse.quote(prompt[:400] + ESTILO) + f"?width=1200&height=950&nologo=true&model=flux&seed={semilla}"
    for i in range(4):
        try:
            b = get(url, timeout=180); im = Image.open(io.BytesIO(b)).convert("RGB")
            if im.width >= 800: im.save(ruta, quality=92); return True
        except Exception as e: log("imagen falla", i, e); time.sleep(10 + 10*i)
    return False

def recorta(im):
    r = max(PW/im.width, PH/im.height); im = im.resize((int(im.width*r)+1, int(im.height*r)+1), Image.LANCZOS)
    return im.crop(((im.width-PW)//2, (im.height-PH)//2, (im.width-PW)//2+PW, (im.height-PH)//2+PH))

def panel_imagen(ruta, dato, linea):
    if ruta and os.path.exists(ruta): base = recorta(Image.open(ruta).convert("RGB"))
    else: base = Image.new("RGB", (PW, PH), NAVY)
    ov = Image.new("RGBA", (PW, PH), (0, 0, 0, 0)); od = ImageDraw.Draw(ov)
    for y in range(PH//2, PH): od.line([(0, y), (PW, y)], fill=(10, 31, 77, int(235*(y-PH//2)/(PH//2))))
    base = Image.alpha_composite(base.convert("RGBA"), ov).convert("RGB"); d = ImageDraw.Draw(base)
    if dato:
        f = fit(d, dato.upper(), ANTON, 150, PW-80); ctext(d, dato.upper(), f, PW/2, PH-300, YEL, 4, NAVY)
    if linea:
        f = fit(d, linea.upper(), BLK, 56, PW-80); w = tw(d, linea.upper(), f)[0]
        d.rectangle([PW/2-w/2-24, PH-120, PW/2+w/2+24, PH-40], fill=RED); ctext(d, linea.upper(), f, PW/2, PH-108, WHITE)
    return base

def panel_gancho(cifra, linea, ruta=None):
    im = panel_imagen(ruta, None, None) if ruta else Image.new("RGB", (PW, PH), NAVY)
    ov = Image.new("RGBA", (PW, PH), (10, 31, 77, 170)); im = Image.alpha_composite(im.convert("RGBA"), ov).convert("RGB"); d = ImageDraw.Draw(im)
    f = fit(d, cifra.upper(), ANTON, 260, PW-60); ctext(d, cifra.upper(), f, PW/2, 170, YEL, 5, NAVY)
    for k, l in enumerate(textwrap_lines(linea.upper(), 18)[:3]):
        f = fit(d, l, ANTON, 96, PW-80); ctext(d, l, f, PW/2, 470 + k*100, WHITE)
    return im
def textwrap_lines(t, n):
    import textwrap; return textwrap.wrap(t, n)
def panel_intro(fecha_larga):
    im = Image.new("RGB", (PW, PH), NAVY); d = ImageDraw.Draw(im)
    d.rectangle([0, 0, PW, 300], fill=RED); ctext(d, "NOTICIAS", F(ANTON, 170), PW/2, 50, WHITE)
    ctext(d, "CON EDDY", F(ANTON, 170), PW/2, 330, WHITE)
    f = fit(d, fecha_larga.upper(), BLK, 64, PW-80); ctext(d, fecha_larga.upper(), f, PW/2, 600, YEL); return im
def panel_cierre():
    im = Image.new("RGB", (PW, PH), RED); d = ImageDraw.Draw(im)
    ctext(d, "SÍGUEME", F(ANTON, 200), PW/2, 120, WHITE); ctext(d, "Y COMENTA", F(ANTON, 130), PW/2, 380, YEL)
    ctext(d, "@eddy_infante · @VIPFuerte", F(BLK, 54), PW/2, 600, WHITE); return im

# ---------- 4. VOZ ----------
async def _voz(texto, ruta):
    import edge_tts
    c = edge_tts.Communicate(tts_texto(texto), VOZ, rate="+8%", boundary="WordBoundary"); words = []
    with open(ruta, "wb") as f:
        async for ch in c.stream():
            if ch["type"] == "audio": f.write(ch["data"])
            elif ch["type"] == "WordBoundary": words.append([ch["offset"]/1e7, (ch["offset"]+ch["duration"])/1e7, ch["text"]])
    return words
def voz(texto, ruta):
    for i in range(5):
        try:
            w = asyncio.run(_voz(texto, ruta))
            if w: return w
        except Exception as e: log("voz falla", i, e); time.sleep(5)
    raise RuntimeError("voz")
def durac(r): return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", r]).decode())

# ---------- 5. ARMADO ----------
def main():
    os.makedirs(f"{SAL}/tmp", exist_ok=True); os.makedirs(f"{SAL}/imagenes", exist_ok=True)
    hoy = dt.datetime.now(TZ); cands = candidatas(); log("candidatas:", len(cands))
    if len(cands) < 6: sys.exit("Muy pocas noticias del día: no se arma video.")
    g, motor = pedir_ia(cands, hoy); log("IA:", motor)
    fecha_c = f"{DIAS[hoy.weekday()][:3].upper()} {hoy.day} {MESES[hoy.month-1][:3].upper()} {hoy.year}"
    fecha_l = f"{DIAS[hoy.weekday()]} {hoy.day} de {MESES[hoy.month-1]}"
    segs = [{"id": "s0", "texto": g["gancho"], "cat": "HOY", "head": g["gancho_linea"][:30], "src": None, "panel": None},
            {"id": "s1", "texto": g["intro"], "cat": "HOY", "head": fecha_l.upper(), "src": None, "panel": panel_intro(fecha_l)}]
    fuentes = []
    for k, n in enumerate(g["noticias"]):
        c = cands[n["i"]]; ruta = f"{SAL}/imagenes/n{k+1}.jpg"
        ok = imagen_ia(n["imagen"], ruta, 1000 + k + hoy.day*10); log("imagen", k+1, "OK" if ok else "FALLO -> panel gráfico")
        fd = dt.datetime.fromisoformat(c["fecha"])
        src = f"Fuente: {c['medio']}, {fd.day} {MESES[fd.month-1][:3]} {fd.year}"
        segs.append({"id": f"s{k+2}", "texto": n["texto"], "cat": f"{n['categoria']} · {k+1}/{len(g['noticias'])}", "head": n["titular"][:34],
                     "src": src, "panel": panel_imagen(ruta if ok else None, n.get("dato"), n.get("dato_linea")), "img_ok": ok})
        fuentes.append({"medio": c["medio"], "titulo": c["titulo"], "fecha": c["fecha"], "link": c["link"], "titular_video": n["titular"], "imagen_ia": ok})
    segs[0]["src"] = segs[2]["src"]
    segs[0]["panel"] = panel_gancho(g["gancho_cifra"], g["gancho_linea"], f"{SAL}/imagenes/n1.jpg" if segs[2].get("img_ok") else None)
    segs.append({"id": f"s{len(segs)}", "texto": g["cierre"], "cat": "SÍGUEME", "head": "COMENTA Y COMPARTE", "src": None, "panel": panel_cierre()})
    # voz por segmento con tiempos de cada palabra
    words, t0, TL, audios = [], 0.0, {}, []
    for s in segs:
        a = f"{SAL}/tmp/{s['id']}.mp3"; w = restaurar(voz(s["texto"], a)); d = durac(a) + 0.15
        for x in w: words.append([x[0]+t0, x[1]+t0, x[2], s["id"]])
        TL[s["id"]] = (t0, t0+d); audios.append(a); t0 += d
    TOTAL = t0; log(f"duración {TOTAL:.1f}s")
    guion = "\n\n".join(s["texto"] for s in segs)
    # audio: concat con 0.15 s de aire + normalizado
    with open(f"{SAL}/tmp/a.txt", "w") as f:
        for a in audios: f.write(f"file '{os.path.basename(a)}'\nfile 'aire.wav'\n")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono", "-t", "0.15", f"{SAL}/tmp/aire.wav"], check=True)
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", f"{SAL}/tmp/a.txt", "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-ar", "48000", "-ac", "2", f"{SAL}/tmp/voz.wav"], check=True)
    ticker = "  ·  ".join(f"{n['categoria']}: {n['titular']}" for n in g["noticias"]) + "  ·  "
    S = Sello(fecha_c, ticker, words, TOTAL, guion=guion)
    ff = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
        "-i", f"{SAL}/tmp/voz.wav", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
        "-shortest", "-movflags", "+faststart", f"{SAL}/video.mp4"], stdin=subprocess.PIPE)
    CORT = TL["s1"][0]
    for fr in range(int(TOTAL*FPS)):
        t = fr / FPS; s = next(x for x in segs if TL[x["id"]][0] <= t < TL[x["id"]][1] + 1e-6) if t < TOTAL else segs[-1]
        a, b = TL[s["id"]]; lt = t - a
        z = 1 + 0.06 * min(1, lt / max(1, b - a))  # zoom lento (Ken Burns)
        p = s["panel"]
        if z > 1.001:
            w2, h2 = int(PW*z), int(PH*z); p = p.resize((w2, h2), Image.BILINEAR).crop(((w2-PW)//2, (h2-PH)//2, (w2-PW)//2+PW, (h2-PH)//2+PH))
        cort = (t - CORT) / 0.9 if CORT <= t < CORT + 0.9 else None
        im = S.frame(t, p, lt, s["id"] == "s0", (a if s["id"] != "s0" else 0, s["cat"], s["head"], s["src"]), cort)
        ff.stdin.write(im.tobytes())
    ff.stdin.close(); ff.wait()
    # subtítulos srt (mismos bloques que en pantalla)
    def tc(x): return f"{int(x//3600):02}:{int(x%3600//60):02}:{int(x%60):02},{int((x%1)*1000):03}"
    with open(f"{SAL}/subtitulos.srt", "w") as f:
        for i, (c, (a, b)) in enumerate(zip(S.chunks, S.win), 1): f.write(f"{i}\n{tc(a)} --> {tc(b)}\n{' '.join(w[2] for w in c)}\n\n")
    vis = verificar_subs(S.chunks, S.win); dif = [w for w in _n(guion) if w not in set(_n(" ".join(vis)))]
    open(f"{SAL}/guion.txt", "w").write(guion)
    json.dump({"duracion_s": round(TOTAL, 1), "voz": VOZ, "ia_texto": motor, "ia_imagen": "pollinations/flux", "subs_faltan": dif[:20], "fuentes": fuentes}, open(f"{SAL}/fuentes.json", "w"), ensure_ascii=False, indent=2)
    json.dump(g, open(f"{SAL}/ia.json", "w"), ensure_ascii=False, indent=2)
    titulo = f"{g['gancho_cifra']}: {g['noticias'][0]['titular'].capitalize()} | Noticias con Eddy {hoy.day} {MESES[hoy.month-1]}"
    open(f"{SAL}/titulo.txt", "w").write(titulo[:100])
    open(f"{SAL}/descripcion.txt", "w").write(g["gancho"] + "\n\nFuentes (redactado con palabras propias; imágenes ilustrativas generadas con IA):\n" +
        "\n".join(f"- {x['medio']} ({x['fecha'][:10]}): {x['link']}" for x in fuentes) + "\n\n#NoticiasRD #RepúblicaDominicana #Noticias")
    for fr_t in (1, 4, 30, 70, 110): subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(fr_t), "-i", f"{SAL}/video.mp4", "-frames:v", "1", "-vf", "scale=360:-1", f"{SAL}/cuadro-{fr_t}s.jpg"])

if __name__ == "__main__":
    main()
