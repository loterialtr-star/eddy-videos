#!/usr/bin/env python3
"""Robot de noticias de Eddy: RSS oficial -> guion -> voz -> video 9:16. No publica nada."""
import asyncio, datetime as dt, email.utils, html, json, os, re, subprocess, sys, textwrap, urllib.request
import xml.etree.ElementTree as ET
from zoneinfo import ZoneInfo
from PIL import Image, ImageDraw, ImageFont

TZ = ZoneInfo("America/Santo_Domingo")
AQUI = os.path.dirname(os.path.abspath(__file__))
SAL = os.environ.get("SALIDA", "salida")
VOZ = os.environ.get("VOZ", "es-DO-EmilioNeural")
MOTOR_VOZ = os.environ.get("MOTOR_VOZ", "edge")  # futuro: "google"
W, H = 1080, 1920
PROHIBIDAS = re.compile(r"loter|sorteo|quiniela|leidsa|loteka|\bloto\b|kino|pal[eé]\b|apuesta|banca de|jackpot|premio mayor|n[uú]meros? de la suerte", re.I)
MESES = "enero febrero marzo abril mayo junio julio agosto septiembre octubre noviembre diciembre".split()
F_B = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
F_R = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

def limpiar(t):
    t = html.unescape(re.sub(r"<[^>]+>", " ", t or ""))
    t = re.sub(r"\s+", " ", t).strip()
    return re.sub(r"^(Santo Domingo|SANTO DOMINGO)[^-]*\.?-\s*", "", t)

def fecha_txt(d):
    return f"{d.day} de {MESES[d.month-1]}"

def leer_feed(f, horas=36):
    req = urllib.request.Request(f["url"], headers={"User-Agent": "Mozilla/5.0 robot-noticias-eddy"})
    raiz = ET.fromstring(urllib.request.urlopen(req, timeout=30).read())
    ahora = dt.datetime.now(TZ); out = []
    for it in raiz.iter("item"):
        tit = limpiar(it.findtext("title")); desc = it.findtext("description") or ""
        m = re.search(r'datetime="([^"]+)"', html.unescape(desc))
        try:
            fe = dt.datetime.fromisoformat(m.group(1)) if m else email.utils.parsedate_to_datetime(it.findtext("pubDate"))
        except Exception:
            continue
        fe = fe.astimezone(TZ)
        if (ahora - fe).total_seconds() > horas * 3600: continue
        cuerpo = limpiar(re.sub(r'<span class="field field--name-(title|uid|created).*?</span>\s*(</span>)?', " ", html.unescape(desc), flags=re.S))
        cuerpo = cuerpo.replace(tit, "").strip()
        if PROHIBIDAS.search(tit + " " + cuerpo): continue
        if re.search(r"resumen|las noticias del|podcast|en breve|bolet[ií]n", tit, re.I): continue
        out.append({"titulo": tit, "cuerpo": cuerpo, "fecha": fe, "link": it.findtext("link"), "fuente": f["nombre"], "corto": f["corto"]})
    return out

def oraciones(t):
    return [o.strip() for o in re.split(r"(?<=[.!?])\s+(?=[A-ZÁÉÍÓÚÑ«“\"])", t) if len(o.strip()) > 25]

def resumir(n, max_pal=52):
    """Version parafraseada sencilla: atribucion + idea principal recortada (sin copiar el articulo completo)."""
    ors = oraciones(n["cuerpo"]) or [n["titulo"] + "."]
    txt, pal = [], 0
    for o in ors[:3]:
        if re.search(r'["“”«»]', o) or "?" in o: continue  # sin citas textuales ajenas
        o = re.sub(r"\([^)]*\)", "", o); o = re.sub(r"\s+([,.;:])", r"\1", re.sub(r"\s+", " ", o)).strip()
        o = re.sub(r"\beste (lunes|martes|miércoles|jueves|viernes|sábado|domingo)\b", "hoy", o)
        p = len(o.split())
        if pal and pal + p > max_pal: break
        if p > max_pal:
            corto = " ".join(o.split()[:max_pal]); c = corto.rfind(",")
            o = (corto[:c] if c > len(corto) * 0.4 else corto).rstrip(",;: ") + "."
            o = re.sub(r"\s+(de|del|la|las|el|los|en|y|a|con|para|por|que)\.$", ".", o)
        txt.append(o); pal += p
    r = " ".join(txt)
    r = re.sub(r"\bhoy \d+( de \w+)?\.$", "hoy.", r)
    return r if len(r.split()) >= 8 else re.sub(r'[“”«»"]', "", n["titulo"]).rstrip(".") + "."

def dato_fuerte(noticias):
    for n in noticias:
        for o in oraciones(n["cuerpo"])[:3] + [n["titulo"]]:
            if re.search(r"\d", o) and len(o.split()) <= 30:
                return n, o
    return noticias[0], noticias[0]["titulo"]

def armar_guion():
    fs = json.load(open(os.path.join(AQUI, "fuentes.json")))
    rd = [n for f in fs["rd"] for n in leer_feed(f)]
    mu = [n for f in fs["mundo"] for n in leer_feed(f)]
    rd.sort(key=lambda n: n["fecha"], reverse=True); mu.sort(key=lambda n: n["fecha"], reverse=True)
    # alterna RD y mundo hasta llenar ~2 min 20 s (unas 290 palabras de noticias)
    elegidas, pal = [], 0
    for par in zip(rd + [None]*10, mu + [None]*10):
        for n in par:
            if n and pal < 290 and len(elegidas) < 9:
                elegidas.append(n); pal += len(resumir(n).split()) + 8
    elegidas.sort(key=lambda n: n["fuente"] != fs["rd"][0]["nombre"])
    if len(elegidas) < 3: sys.exit("Muy pocas noticias oficiales de hoy; no se arma video.")
    hoy = dt.datetime.now(TZ)
    nd, dato = dato_fuerte(elegidas)
    gancho = f"Atención: {re.sub(r'[“”«»\"]', '', dato).rstrip('.')}. Lo confirma {nd['corto']}. Te lo cuento."
    seg = [{"tipo": "gancho", "texto": gancho, "titulo": "DATO DEL DÍA", "fuente": nd["fuente"], "fecha": nd["fecha"]}]
    seg.append({"tipo": "intro", "texto": f"Buenas, soy Eddy Infante. Estas son las noticias del {fecha_txt(hoy)}, de la República Dominicana y el mundo, con fuentes oficiales.", "titulo": "NOTICIAS DE HOY", "fuente": "", "fecha": hoy})
    for n in elegidas:
        cuerpo = resumir(n)
        seg.append({"tipo": "noticia", "titulo": n["titulo"], "fuente": n["fuente"], "fecha": n["fecha"], "link": n["link"],
                    "texto": f"Según {n['corto']}, el {fecha_txt(n['fecha'])}: {cuerpo}"})
    seg.append({"tipo": "cierre", "texto": "Esas fueron las noticias de hoy. Las fuentes están en la descripción. Sígueme para más.", "titulo": "GRACIAS POR VER", "fuente": "", "fecha": hoy})
    return seg

async def voz_edge(texto, ruta):
    import edge_tts
    await edge_tts.Communicate(texto, VOZ, rate="+5%").save(ruta)

def voz(texto, ruta):
    if MOTOR_VOZ == "google":
        raise NotImplementedError("Google TTS: activar cuando haya cuenta con facturacion aprobada por Eddy.")
    for i in range(4):
        try:
            asyncio.run(voz_edge(texto, ruta)); return
        except Exception as e:
            print("reintento voz", i, e)
    raise RuntimeError("voz fallo")

def durac(r):
    return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", r]).decode())

COLORES = {"gancho": ((150, 10, 30), (40, 0, 10)), "intro": ((10, 60, 140), (5, 15, 45)), "noticia": ((15, 40, 90), (5, 10, 30)), "cierre": ((10, 90, 70), (3, 25, 20))}

def fondo(s, idx):
    a, b = COLORES[s["tipo"]]
    im = Image.new("RGB", (W, H)); d = ImageDraw.Draw(im)
    for y in range(H):
        k = y / H; d.line([(0, y), (W, y)], fill=tuple(int(a[i]*(1-k)+b[i]*k) for i in range(3)))
    for i in range(9):  # formas propias decorativas
        r = 120 + (idx*37 + i*53) % 260; x = (idx*211 + i*173) % W; y = (idx*97 + i*389) % H
        d.ellipse([x-r, y-r, x+r, y+r], outline=(255, 255, 255, 30), width=3)
    return im

def texto_centrado(d, txt, fuente, y, ancho, color, max_l=6, sombra=True):
    for l in textwrap.wrap(txt, ancho)[:max_l]:
        w = d.textlength(l, font=fuente)
        if sombra: d.text(((W-w)/2+3, y+3), l, font=fuente, fill=(0, 0, 0))
        d.text(((W-w)/2, y), l, font=fuente, fill=color); y += fuente.size + 14
    return y

def cuadro(s, idx, sub):
    im = fondo(s, idx); d = ImageDraw.Draw(im)
    d.rectangle([0, 0, W, 150], fill=(0, 0, 0)); d.text((50, 45), "EDDY INFANTE · NOTICIAS", font=ImageFont.truetype(F_B, 50), fill=(255, 210, 0))
    tit = s["titulo"] if s["tipo"] != "gancho" else "DATO DEL DÍA"
    y = texto_centrado(d, tit.upper() if s["tipo"] != "noticia" else tit, ImageFont.truetype(F_B, 66 if s["tipo"] != "noticia" else 56), 260, 26, (255, 255, 255), 6)
    if s["fuente"]:
        texto_centrado(d, f"Fuente: {s['fuente']} · {fecha_txt(s['fecha'])}", ImageFont.truetype(F_R, 38), y+30, 44, (255, 210, 0), 2, False)
    # subtitulo legible: caja negra abajo-centro (zona segura de TikTok)
    fs = ImageFont.truetype(F_B, 64); lineas = textwrap.wrap(sub, 22)[:3]
    alto = len(lineas)*(fs.size+16)+60; y0 = 1180
    d.rounded_rectangle([60, y0, W-60, y0+alto], 30, fill=(0, 0, 0))
    texto_centrado(d, sub, fs, y0+30, 22, (255, 255, 255), 3, False)
    return im

def trozos(texto, n=8):
    p = texto.split(); return [" ".join(p[i:i+n]) for i in range(0, len(p), n)]

def main():
    os.makedirs(SAL, exist_ok=True); tmp = os.path.join(SAL, "tmp"); os.makedirs(tmp, exist_ok=True)
    seg = armar_guion()
    lista, srt, t0, k = [], [], 0.0, 0
    for i, s in enumerate(seg):
        a = os.path.join(tmp, f"v{i:02}.mp3"); voz(s["texto"], a); s["dur"] = durac(a)
        ts = trozos(s["texto"]); tot = sum(len(x) for x in ts)
        for t in ts:
            dd = s["dur"] * len(t) / tot; k += 1
            img = os.path.join(tmp, f"c{k:03}.png"); cuadro(s, i, t).save(img)
            lista.append((img, dd)); srt.append((t0, t0+dd, t)); t0 += dd
    total = t0; print(f"duracion {total:.1f}s")
    with open(os.path.join(tmp, "audios.txt"), "w") as f:
        for i in range(len(seg)): f.write(f"file 'v{i:02}.mp3'\n")
    with open(os.path.join(tmp, "imgs.txt"), "w") as f:
        for img, dd in lista: f.write(f"file '{os.path.basename(img)}'\nduration {dd:.3f}\n")
        f.write(f"file '{os.path.basename(lista[-1][0])}'\n")
    run = lambda c: subprocess.run(c, check=True)
    run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", f"{tmp}/audios.txt", "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-ar", "48000", f"{tmp}/voz.m4a"])
    run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", f"{tmp}/imgs.txt", "-i", f"{tmp}/voz.m4a",
         "-vf", "fps=30,format=yuv420p", "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-c:a", "aac", "-b:a", "192k",
         "-shortest", "-movflags", "+faststart", f"{SAL}/video.mp4"])
    def tc(x): return f"{int(x//3600):02}:{int(x%3600//60):02}:{int(x%60):02},{int((x%1)*1000):03}"
    with open(f"{SAL}/subtitulos.srt", "w") as f:
        for i, (a, b, t) in enumerate(srt, 1): f.write(f"{i}\n{tc(a)} --> {tc(b)}\n{t}\n\n")
    with open(f"{SAL}/guion.txt", "w") as f:
        for s in seg: f.write(f"[{s['tipo'].upper()}] {s['texto']}\n\n")
    fuentes = [{"titulo": s["titulo"], "fuente": s["fuente"], "fecha": s["fecha"].isoformat(), "link": s.get("link")} for s in seg if s["tipo"] == "noticia"]
    json.dump({"duracion_s": round(total, 1), "voz": VOZ, "fuentes": fuentes}, open(f"{SAL}/fuentes.json", "w"), ensure_ascii=False, indent=2)
    with open(f"{SAL}/descripcion.txt", "w") as f:
        f.write("Noticias de hoy de RD y el mundo.\n\nFuentes:\n" + "\n".join(f"- {x['fuente']} ({x['fecha'][:10]}): {x['link']}" for x in fuentes))
    if not 120 <= total <= 185: print("AVISO: duracion fuera de 2-3 min", total)

if __name__ == "__main__":
    main()
