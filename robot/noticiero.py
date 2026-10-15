#!/usr/bin/env python3
"""NOTICIAS CON EDDY - todo corre en GitHub Actions. No publica nada.
RSS -> IA (o guion simple si falla) -> imagenes -> voz -> sello -> MP4 9:16."""
import asyncio, datetime as dt, email.utils, html, io, json, os, random, re, subprocess, sys, time, unicodedata, urllib.parse, urllib.request
import xml.etree.ElementTree as ET
from zoneinfo import ZoneInfo
from PIL import Image, ImageDraw, ImageFilter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sello import *
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
def guion_simple(cands, hoy):
    """Guion básico sin IA si la IA falla."""
    rd = [n for n in cands if n["region"] == "rd"][:4]
    mu = [n for n in cands if n["region"] == "mundo"][:2]
    elegidas = (rd + mu)[:6]
    if len(elegidas) < 4: elegidas = cands[:6]
    noticias = []
    for i, n in enumerate(elegidas):
        texto = f"Según {n['medio']}, {n['titulo']}. {n['resumen'][:180]}"
        noticias.append({
            "i": cands.index(n),
            "categoria": "PAÍS" if n["region"] == "rd" else "MUNDO",
            "titular": n["titulo"][:32].upper(),
            "texto": texto,
            "dato": "",
            "dato_linea": n["medio"][:20].upper(),
            "imagen": f"news illustration about {n['titulo'][:80]}, no text, no logos"
        })
    return {
        "gancho": f"Atención: {elegidas[0]['titulo']}. Lo confirma {elegidas[0]['medio']}.",
        "gancho_cifra": "HOY",
        "gancho_linea": "NOTICIAS DEL DÍA",
        "intro": f"Te habla Eddy Infante. Estas son las noticias de este {DIAS[hoy.weekday()]} {hoy.day} de {MESES[hoy.month-1]}.",
        "noticias": noticias,
        "cierre": "Esas fueron las noticias de hoy. Sígueme y comenta. Con Dios por delante."
    }, "guion-simple"
SISTEMA = """Eres el redactor de "Noticias con Eddy"... Devuelve SOLO JSON."""
def pedir_ia(cands, hoy):
    lista = "\n".join(f"[{i}] ({n['region'].upper()}) {n['medio']} | {n['fecha'][:16]} | {n['titulo']} :: {n['resumen'][:450]}" for i, n in enumerate(cands[:30]))
    usuario = f"""Hoy es {DIAS[hoy.weekday()]} {hoy.day} de {MESES[hoy.month-1]} de {hoy.year}.
Noticias disponibles:
{lista}
Elige las 5 o 6 noticias más importantes. Devuelve SOLO el JSON del guion."""
    clave = os.environ.get("GEMINI_API_KEY")
    for intento in range(3):
        try:
            if clave:
                r = json.loads(get(f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={clave}",
                    json.dumps({"systemInstruction": {"parts": [{"text": SISTEMA}]}, "contents": [{"parts": [{"text": usuario}]}],
                                "generationConfig": {"responseMimeType": "application/json", "temperature": 0.7}}).encode(), {"Content-Type": "application/json"}))
                txt = r["candidates"][0]["content"]["parts"][0]["text"]; motor = "gemini-2.5-flash"
            else:
                r = json.loads(get("https://text.pollinations.ai/openai", json.dumps({"model": "openai", "messages": [{"role": "user", "content": usuario}],
                    "response_format": {"type": "json_object"}}).encode(), {"Content-Type": "application/json"}, 120))
                txt = r["choices"][0]["message"]["content"]; motor = "pollinations"
            g = json.loads(re.search(r"\{.*\}", txt, re.S).group(0))
            if g.get("noticias") and len(g["noticias"]) >= 4:
                return g, motor
        except Exception as e:
            log("IA falla", intento, e); time.sleep(8)
    log("IA no disponible, usando guion simple")
    return guion_simple(cands, hoy)
def _n(x): return [w for w in re.findall(r"\w+", unicodedata.normalize("NFC", x.lower()))]
ESTILO = ", editorial news illustration, cinematic photorealistic, dramatic lighting, high detail, 4k, no text, no letters, no watermark, no logos"
def imagen_ia(prompt, ruta, semilla):
    url = "https://image.pollinations.ai/prompt/" + urllib.parse.quote(prompt[:400] + ESTILO) + f"?width=1200&height=950&nologo=true&model=flux&seed={semilla}"
    for i in range(3):
        try:
            b = get(url, timeout=120); im = Image.open(io.BytesIO(b)).convert("RGB")
            if im.width >= 600: im.save(ruta, quality=90); return True
        except Exception as e: log("imagen falla", i, e); time.sleep(5)
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
async def _voz(texto, ruta):
    import edge_tts
    c = edge_tts.Communicate(tts_texto(texto), VOZ, rate="+8%", boundary="WordBoundary"); words = []
    with open(ruta, "wb") as f:
        async for ch in c.stream():
            if ch["type"] == "audio": f.write(ch["data"])
            elif ch["type"] == "WordBoundary": words.append([ch["offset"]/1e7, (ch["offset"]+ch["duration"])/1e7, ch["text"]])
    return words
def voz(texto, ruta):
    for i in range(4):
        try:
            w = asyncio.run(_voz(texto, ruta))
            if w: return w
        except Exception as e: log("voz falla", i, e); time.sleep(4)
    raise RuntimeError("voz")
def durac(r): return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", r]).decode())
def main():
    os.makedirs(f"{SAL}/tmp", exist_ok=True); os.makedirs(f"{SAL}/imagenes", exist_ok=True)
    hoy = dt.datetime.now(TZ); cands = candidatas(); log("candidatas:", len(cands))
    if len(cands) < 4: sys.exit("Muy pocas noticias del día: no se arma video.")
    g, motor = pedir_ia(cands, hoy); log("IA:", motor)
    fecha_c = f"{DIAS[hoy.weekday()][:3].upper()} {hoy.day} {MESES[hoy.month-1][:3].upper()} {hoy.year}"
    fecha_l = f"{DIAS[hoy.weekday()]} {hoy.day} de {MESES[hoy.month-1]}"
    segs = [{"id": "s0", "texto": g["gancho"], "cat": "HOY", "head": g["gancho_linea"][:30], "src": None, "panel": None},
            {"id": "s1", "texto": g["intro"], "cat": "HOY", "head": fecha_l.upper(), "src": None, "panel": panel_intro(fecha_l)}]
    fuentes = []
    for k, n in enumerate(g["noticias"]):
        c = cands[n["i"]]; ruta = f"{SAL}/imagenes/n{k+1}.jpg"
        ok = imagen_ia(n.get("imagen", "news"), ruta, 1000 + k + hoy.day*10); log("imagen", k+1, "OK" if ok else "FALLO")
        fd = dt.datetime.fromisoformat(c["fecha"])
        src = f"Fuente: {c['medio']}, {fd.day} {MESES[fd.month-1][:3]} {fd.year}"
        segs.append({"id": f"s{k+2}", "texto": n["texto"], "cat": f"{n['categoria']} · {k+1}/{len(g['noticias'])}", "head": n["titular"][:34],
                     "src": src, "panel": panel_imagen(ruta if ok else None, n.get("dato"), n.get("dato_linea")), "img_ok": ok})
        fuentes.append({"medio": c["medio"], "titulo": c["titulo"], "fecha": c["fecha"], "link": c["link"], "titular_video": n["titular"], "imagen_ia": ok})
    segs[0]["src"] = segs[2]["src"]
    segs[0]["panel"] = panel_gancho(g["gancho_cifra"], g["gancho_linea"], f"{SAL}/imagenes/n1.jpg" if segs[2].get("img_ok") else None)
    segs.append({"id": f"s{len(segs)}", "texto": g["cierre"], "cat": "SÍGUEME", "head": "COMENTA Y COMPARTE", "src": None, "panel": panel_cierre()})
    words, t0, TL, audios = [], 0.0, {}, []
    for s in segs:
        a = f"{SAL}/tmp/{s['id']}.mp3"; w = restaurar(voz(s["texto"], a)); d = durac(a) + 0.15
        for x in w: words.append([x[0]+t0, x[1]+t0, x[2], s["id"]])
        TL[s["id"]] = (t0, t0+d); audios.append(a); t0 += d
    TOTAL = t0; log(f"duración {TOTAL:.1f}s")
    guion = "\n\n".join(s["texto"] for s in segs)
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
        z = 1 + 0.06 * min(1, lt / max(1, b - a))
        p = s["panel"]
        if z > 1.001:
            w2, h2 = int(PW*z), int(PH*z); p = p.resize((w2, h2), Image.BILINEAR).crop(((w2-PW)//2, (h2-PH)//2, (w2-PW)//2+PW, (h2-PH)//2+PH))
        cort = (t - CORT) / 0.9 if CORT <= t < CORT + 0.9 else None
        im = S.frame(t, p, lt, s["id"] == "s0", (a if s["id"] != "s0" else 0, s["cat"], s["head"], s["src"]), cort)
        ff.stdin.write(im.tobytes())
    ff.stdin.close(); ff.wait()
    def tc(x): return f"{int(x//3600):02}:{int(x%3600//60):02}:{int(x%60):02},{int((x%1)*1000):03}"
    with open(f"{SAL}/subtitulos.srt", "w") as f:
        for i, (c, (a, b)) in enumerate(zip(S.chunks, S.win), 1): f.write(f"{i}\n{tc(a)} --> {tc(b)}\n{' '.join(w[2] for w in c)}\n\n")
    open(f"{SAL}/guion.txt", "w").write(guion)
    json.dump({"duracion_s": round(TOTAL, 1), "voz": VOZ, "ia_texto": motor, "fuentes": fuentes}, open(f"{SAL}/fuentes.json", "w"), ensure_ascii=False, indent=2)
    titulo = f"{g['gancho_cifra']}: Noticias con Eddy {hoy.day} {MESES[hoy.month-1]}"
    open(f"{SAL}/titulo.txt", "w").write(titulo[:100])
    open(f"{SAL}/descripcion.txt", "w").write(g["gancho"] + "\n\nFuentes:\n" + "\n".join(f"- {x['medio']}: {x['link']}" for x in fuentes) + "\n\n#NoticiasRD")
if __name__ == "__main__":
    main()
