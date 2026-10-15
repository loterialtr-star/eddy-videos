#!/usr/bin/env python3
"""Video de fe para Primero Dios (SOLO fe, nunca noticias). Texto propio, sin repetir historias."""
import json, os, re, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import armar
from armar import voz, durac, cuadro, trozos, W, H
AQ = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fe"); SAL = os.environ.get("SALIDA", "salida-fe")
armar.VOZ = os.environ.get("VOZ", "es-DO-RamonaNeural")
armar.COLORES.update({"fe": ((70, 40, 120), (15, 5, 35)), "cita": ((150, 100, 20), (40, 20, 5))})
hist = json.load(open(f"{AQ}/historias.json")); us = json.load(open(f"{AQ}/usadas.json"))
libres = [h for h in hist if h["id"] not in us["usadas"]] or hist  # al agotar la lista, recien ahi se reinicia
h = libres[0]
seg = [
 {"tipo": "cita", "titulo": h["cita"], "fuente": "", "texto": f"{h['mensaje']}"},
 {"tipo": "fe", "titulo": h["historia"], "fuente": "", "texto": f"Hoy recordamos {h['historia'].lower()[0] + h['historia'][1:]}, en {h['cita']}. Te invito a leerlo hoy en tu Biblia."},
 {"tipo": "fe", "titulo": "Reflexión", "fuente": "", "texto": f"La enseñanza es clara: {h['mensaje'][0].lower() + h['mensaje'][1:]} No importa lo que estés viviendo, Dios no te ha soltado de su mano."},
 {"tipo": "fe", "titulo": "Oración", "fuente": "", "texto": "Señor, gracias por este nuevo día. Dame fe para confiar en ti, fuerzas para seguir adelante y paz en mi corazón. Amén."},
 {"tipo": "cita", "titulo": "PRIMERO DIOS", "fuente": "", "texto": "Si esta palabra te bendijo, compártela con alguien que la necesite. Primero Dios."}]
os.makedirs(f"{SAL}/tmp", exist_ok=True); lista = []; k = 0
for i, s in enumerate(seg):
    a = f"{SAL}/tmp/v{i:02}.mp3"; voz(s["texto"], a); s["dur"] = durac(a)
    ts = trozos(s["texto"], 6); tot = sum(map(len, ts))
    for t in ts:
        k += 1; im = cuadro(s, i, t)
        from PIL import ImageDraw, ImageFont
        d = ImageDraw.Draw(im); d.rectangle([0, 0, W, 150], fill=(0, 0, 0)); d.text((50, 45), "PRIMERO DIOS", font=ImageFont.truetype(armar.F_B, 56), fill=(255, 215, 120))
        p = f"{SAL}/tmp/c{k:03}.png"; im.save(p); lista.append((p, s["dur"] * len(t) / tot))
open(f"{SAL}/tmp/a.txt", "w").write("".join(f"file 'v{i:02}.mp3'\n" for i in range(len(seg))))
open(f"{SAL}/tmp/i.txt", "w").write("".join(f"file '{os.path.basename(p)}'\nduration {d:.3f}\n" for p, d in lista) + f"file '{os.path.basename(lista[-1][0])}'\n")
r = lambda c: subprocess.run(c, check=True)
r(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", f"{SAL}/tmp/a.txt", "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-ar", "48000", f"{SAL}/tmp/voz.m4a"])
r(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", f"{SAL}/tmp/i.txt", "-i", f"{SAL}/tmp/voz.m4a", "-vf", "fps=30,format=yuv420p",
   "-c:v", "libx264", "-crf", "20", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", f"{SAL}/video.mp4"])
open(f"{SAL}/guion.txt", "w").write("\n\n".join(s["texto"] for s in seg))
open(f"{SAL}/descripcion.txt", "w").write(f"{h['mensaje']} ({h['cita']}) 🙏 #PrimeroDios #Fe #Dios")
json.dump({"historia_id": h["id"], "cita": h["cita"]}, open(f"{SAL}/fe.json", "w"), ensure_ascii=False)
