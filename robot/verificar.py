#!/usr/bin/env python3
"""Controles automaticos. Si uno falla, sale con error y NO se publica."""
import datetime as dt, json, os, re, subprocess, sys
from zoneinfo import ZoneInfo
SAL = os.environ.get("SALIDA", "salida"); TZ = ZoneInfo("America/Santo_Domingo")
PROHIBIDAS = re.compile(r"loter|sorteo|quiniela|leidsa|loteka|\bloto\b|kino|pal[eé]\b|apuesta|jackpot|premio mayor|para ganar|\bseguro\b|el solo uno", re.I)
fallos = []
def ok(c, m): (None if c else fallos.append(m)); print(("OK   " if c else "FALLA ") + m)
def probe(*a): return subprocess.check_output(["ffprobe", "-v", "error", *a, f"{SAL}/video.mp4"]).decode().strip()
info = json.load(open(f"{SAL}/fuentes.json")); hoy = dt.datetime.now(TZ)
ok(len(info["fuentes"]) >= 3, f"al menos 3 noticias con fuente ({len(info['fuentes'])})")
ok(all(x["link"] and x["medio"] for x in info["fuentes"]), "cada noticia tiene fuente y enlace")
ok(all((hoy - dt.datetime.fromisoformat(x["fecha"])).total_seconds() < 36*3600 for x in info["fuentes"]), "fuentes del dia (menos de 36 h)")
g = open(f"{SAL}/guion.txt").read(); ok(not re.search(r":\s*\n", g), "ninguna noticia vacia")
txt = open(f"{SAL}/guion.txt").read() + open(f"{SAL}/descripcion.txt").read() + " ".join(x["titular_video"] for x in info["fuentes"])
m = PROHIBIDAS.search(txt); ok(not m, f"sin palabras prohibidas{'' if not m else ': ' + m.group(0)}")
d = float(probe("-show_entries", "format=duration", "-of", "csv=p=0")); ok(120 <= d <= 185, f"duracion 2-3 min ({d:.0f}s)")
ok(probe("-select_streams", "v:0", "-show_entries", "stream=width,height", "-of", "csv=p=0") == "1080,1920", "video 1080x1920 (9:16)")
ok(bool(probe("-select_streams", "a:0", "-show_entries", "stream=codec_name", "-of", "csv=p=0")), "tiene audio")
ln = subprocess.run(["ffmpeg", "-hide_banner", "-i", f"{SAL}/video.mp4", "-af", "loudnorm=print_format=json", "-f", "null", "-"], capture_output=True, text=True).stderr
I = float(re.findall(r'"input_i" : "(-?[\d.]+)"', ln)[-1]); ok(-17 <= I <= -11, f"volumen normalizado ({I} LUFS)")
ok(not info.get("subs_faltan"), "subtítulos = guion (sin palabras perdidas)")
ok(all(x["imagen_ia"] for x in info["fuentes"]), "todas las noticias con imagen IA")
srt = open(f"{SAL}/subtitulos.srt").read(); ok(srt.count("-->") >= 20, f"subtitulos presentes ({srt.count('-->')})")
json.dump({"aprobado": not fallos, "fallos": fallos}, open(f"{SAL}/controles.json", "w"), ensure_ascii=False, indent=2)
sys.exit(1 if fallos else 0)
