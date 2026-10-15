#!/usr/bin/env python3
"""Sube un Reel a una pagina de Facebook con la Graph API.
Solo publica si PUBLICAR=si, controles aprobados y hay FB_PAGE_ID + FB_PAGE_TOKEN.
TIPO=fe -> solo pagina Primero Dios. TIPO=noticias -> otra pagina (NUNCA Primero Dios)."""
import json, os, sys, urllib.parse, urllib.request
SAL = os.environ.get("SALIDA", "salida"); V = "v23.0"
pid, tok, tipo = os.environ.get("FB_PAGE_ID"), os.environ.get("FB_PAGE_TOKEN"), os.environ.get("TIPO")
PRIMERO_DIOS = os.environ.get("FB_PRIMERO_DIOS_ID", "")
if os.environ.get("PUBLICAR") != "si": sys.exit(print("PUBLICAR no es 'si': no se publica (modo prueba)."))
if not json.load(open(f"{SAL}/controles.json"))["aprobado"]: sys.exit("Controles fallaron: no se publica.")
if not (pid and tok): sys.exit(print("Faltan secretos de Facebook: no se publica."))
if tipo == "noticias" and pid == PRIMERO_DIOS: sys.exit("BLOQUEADO: noticias nunca van a Primero Dios.")
def post(url, data=None, headers=None):
    return json.load(urllib.request.urlopen(urllib.request.Request(url, data, headers or {}, method="POST")))
g = f"https://graph.facebook.com/{V}/{pid}/video_reels"
vid = post(g, urllib.parse.urlencode({"upload_phase": "start", "access_token": tok}).encode())["video_id"]
data = open(f"{SAL}/video.mp4", "rb").read()
post(f"https://rupload.facebook.com/video-upload/{V}/{vid}", data, {"Authorization": f"OAuth {tok}", "offset": "0", "file_size": str(len(data))})
r = post(g, urllib.parse.urlencode({"upload_phase": "finish", "video_id": vid, "video_state": "PUBLISHED",
    "description": open(f"{SAL}/descripcion.txt").read(), "access_token": tok}).encode())
print("Facebook:", r)
