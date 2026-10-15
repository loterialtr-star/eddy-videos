#!/usr/bin/env python3
"""Controles del video de fe. Si falla, no se publica."""
import json, os, re, subprocess, sys
SAL = os.environ.get("SALIDA", "salida-fe"); f = []
def ok(c, m): (None if c else f.append(m)); print(("OK   " if c else "FALLA ") + m)
t = open(f"{SAL}/guion.txt").read() + open(f"{SAL}/descripcion.txt").read()
m = re.search(r"loter|sorteo|leidsa|loto|kino|quiniela|apuesta|noticia|gobierno|presidente|ministro|pol[ií]tic|para ganar|seguro|el solo uno", t, re.I)
ok(not m, "solo fe (sin noticias ni loteria)" + ("" if not m else ": " + m.group(0)))
us = json.load(open("robot/fe/usadas.json"))["usadas"]; hid = json.load(open(f"{SAL}/fe.json"))["historia_id"]
ok(hid not in us or len(us) >= len(json.load(open("robot/fe/historias.json"))), "historia no repetida")
p = lambda *a: subprocess.check_output(["ffprobe", "-v", "error", *a, f"{SAL}/video.mp4"]).decode().strip()
d = float(p("-show_entries", "format=duration", "-of", "csv=p=0")); ok(30 <= d <= 90, f"duracion reel 30-90 s ({d:.0f}s)")
ok(p("-select_streams", "v:0", "-show_entries", "stream=width,height", "-of", "csv=p=0") == "1080,1920", "1080x1920")
ln = subprocess.run(["ffmpeg", "-i", f"{SAL}/video.mp4", "-af", "loudnorm=print_format=json", "-f", "null", "-"], capture_output=True, text=True).stderr
I = float(re.findall(r'"input_i" : "(-?[\d.]+)"', ln)[-1]); ok(-17 <= I <= -11, f"volumen normalizado ({I} LUFS)")
json.dump({"aprobado": not f, "fallos": f}, open(f"{SAL}/controles.json", "w")); sys.exit(1 if f else 0)
