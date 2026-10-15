#!/usr/bin/env python3
"""Sube a YouTube SOLO si: PUBLICAR=si, controles aprobados y existen los secretos. Si falta algo, no hace nada."""
import json, os, sys, urllib.parse, urllib.request
SAL = os.environ.get("SALIDA", "salida")
if os.environ.get("PUBLICAR") != "si": sys.exit(print("PUBLICAR no es 'si': no se publica (modo prueba)."))
if not json.load(open(f"{SAL}/controles.json"))["aprobado"]: sys.exit("Controles fallaron: no se publica.")
cid, cs, rt = (os.environ.get(k) for k in ("YT_CLIENT_ID", "YT_CLIENT_SECRET", "YT_REFRESH_TOKEN"))
if not (cid and cs and rt): sys.exit(print("Faltan secretos de YouTube: no se publica."))
tok = json.load(urllib.request.urlopen("https://oauth2.googleapis.com/token", urllib.parse.urlencode(
    {"client_id": cid, "client_secret": cs, "refresh_token": rt, "grant_type": "refresh_token"}).encode()))["access_token"]
desc = open(f"{SAL}/descripcion.txt").read()
meta = {"snippet": {"title": os.environ.get("TITULO", "Noticias de hoy RD y el mundo")[:100], "description": desc, "categoryId": "25", "defaultLanguage": "es"},
        "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": False, "containsSyntheticMedia": True}}
r = urllib.request.Request("https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status",
    json.dumps(meta).encode(), {"Authorization": f"Bearer {tok}", "Content-Type": "application/json", "X-Upload-Content-Type": "video/mp4"})
url = urllib.request.urlopen(r).headers["Location"]
up = urllib.request.Request(url, open(f"{SAL}/video.mp4", "rb").read(), {"Authorization": f"Bearer {tok}", "Content-Type": "video/mp4"}, method="PUT")
print("Publicado:", json.load(urllib.request.urlopen(up))["id"])
