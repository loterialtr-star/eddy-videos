# Robot de videos de Eddy (sin depender de ninguna computadora)

- `noticias.yml`: noticias oficiales del día (Presidencia RD + Noticias ONU) → guion con fuente y fecha → voz (edge-tts, gratis) → video 9:16 1080x1920 con subtítulos y audio normalizado (-14 LUFS) → controles → artefacto. Publicación en YouTube / página de noticias de Facebook APAGADA (variables `PUBLICAR`, `PUBLICAR_FB_NOTICIAS`).
- `fe.yml`: un reel de fe diario para Primero Dios (solo fe, sin repetir historias). Publicación APAGADA (`PUBLICAR_FE`).
- Si un control falla, el paso de publicar no se ejecuta.
- Voz futura: `MOTOR_VOZ=google` (Google Cloud TTS, requiere facturación).
- Ninguna clave va en el código: todo en GitHub Secrets.
