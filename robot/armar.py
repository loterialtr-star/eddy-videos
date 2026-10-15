def leer_feed(f, horas=36):
    try:
        req = urllib.request.Request(f["url"], headers={"User-Agent": "Mozilla/5.0 robot-noticias-eddy"})
        data = urllib.request.urlopen(req, timeout=30).read()
        raiz = ET.fromstring(data)
    except Exception as e:
        print(f"Feed falló ({f.get('nombre', f.get('url'))}): {e}")
        return []
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
