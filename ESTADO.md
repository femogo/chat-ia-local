# ESTADO.md

Fecha: 2026-08-10.

## Verificado

- `open-webui` 0.11.0 instalado en `/opt/chat/venv` (Python 3.11.15, vía
  `uv`). Confirmado con `uv pip show open-webui`; el flag `open-webui
  --version` que preveía el plan original no existe en esta versión del CLI
  (solo tiene `main`, `serve`, `dev`) — anotado aquí porque el plan lo daba
  por hecho.
- `df -h /opt` se mantuvo con margen amplio durante la instalación (de 54 GB
  a 47 GB libres): no se acercó al umbral de 10 GB.
- `chat-web.service` activo, `enabled`, y sobrevive a `systemctl restart`.
- `curl http://127.0.0.1:8081/` responde `200`.
- Los 5 modelos que el plan daba por descargados están confirmados en
  `ollama list` / `/api/tags`: `llama3.1:8b`, `qwen3:8b`,
  `gemma4:12b-it-qat`, `gemma4:e4b`, `nomic-embed-text:latest`.
- Generación de extremo a extremo probada directamente contra Ollama
  (`POST /api/generate` con `llama3.1:8b`): responde correctamente.
- `WEBUI_SECRET_KEY` generada con `openssl rand -hex 32` (64 caracteres
  hexadecimales) y escrita solo en `/opt/chat/.env`, que está en
  `.gitignore`. `.env.example` conserva el marcador
  `CAMBIAR_POR_CADENA_ALEATORIA`.
- `/opt/portal/index.html` enlaza el chat en el puerto 8081.

## Pendiente — acción manual del propietario

**El registro del primer usuario (administrador) no está hecho.** Por
diseño: crear ese usuario o inventar credenciales no le corresponde a quien
ejecutó este plan. Pasos que faltan, en orden:

1. Entrar a `http://192.168.1.38:8081/` desde el navegador y registrarse.
   Ese primer usuario registrado es automáticamente administrador
   (`DEFAULT_USER_ROLE=pending` en `.env` aplica a los que se registren
   *después*, no al primero).
2. **Inmediatamente después**, cerrar el alta pública: editar
   `/opt/chat/.env` y poner

   ```
   ENABLE_SIGNUP=false
   ```

3. Reiniciar el servicio para que tome el cambio:

   ```bash
   systemctl restart chat-web.service
   ```

Hasta que se haga el paso 2, cualquiera en la LAN puede registrarse como
usuario nuevo (quedará en estado `pending`, sin acceso, pero sigue siendo
una superficie que conviene cerrar).

## Pendiente — verificación que requiere el paso anterior

`/api/models` exige sesión autenticada (devuelve `401 Not authenticated` sin
login, comprobado). Por tanto, dos cosas del Paso 5 del plan no se han podido
verificar todavía y quedan para después del registro:

- Que la interfaz, ya autenticada, liste efectivamente los 4 modelos de chat
  y ninguno externo.
- Si `nomic-embed-text` aparece también en el selector de modelos de chat
  (no debería, pero Open WebUI no siempre lo distingue automáticamente de un
  modelo conversacional). Si aparece, ocultarlo desde
  *Admin → Ajustes → Modelos* y marcarlo aquí como hecho.

## Fuera de alcance en esta versión (documentado, no implementado)

Ver [docs/arquitectura.md](docs/arquitectura.md#fuera-de-alcance-siguiente-paso-no-implementado):
generación de imágenes vía ComfyUI, búsqueda web, STT/TTS, exposición fuera
de la LAN.

## Riesgo conocido (no es una avería)

Con 8 GB de VRAM, cambiar de modelo tiene coste de varios segundos y
`gemma4:e4b` (9,6 GB) no cabe entero — va parcialmente a CPU y responde más
despacio que los otros tres. Detalle en
[docs/modelos.md](docs/modelos.md#el-límite-de-8-gb-de-vram).
