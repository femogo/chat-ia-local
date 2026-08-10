# Chat IA local — Open WebUI sobre Ollama

Un "ChatGPT" propio en la LAN, servido por [Open WebUI](https://github.com/open-webui/open-webui)
y conectado **únicamente** a los modelos que ya estaban descargados en Ollama
en esta máquina. Sin Docker, sin claves de API externas, sin llamadas
salientes a ningún proveedor.

Uno de los proyectos del contenedor LXC de Proxmox con una **RTX 4060 de
8 GB**, IP `192.168.1.38`.

---

## Qué es esto en cuatro líneas

Navegador → Open WebUI (puerto `8081`) → Ollama (`127.0.0.1:11434`) → GPU.
Open WebUI es solo la interfaz de chat; quien carga los modelos en VRAM y
genera texto es Ollama, que ya estaba instalado y en marcha antes de este
proyecto. Instalación nativa con `uv` en un venv, arrancada como servicio
systemd (`chat-web.service`).

Detalle de piezas y decisiones en [docs/arquitectura.md](docs/arquitectura.md).

## Los modelos

Solo se exponen los que ya estaban descargados. Ninguno nuevo, ninguna API
externa.

| Modelo | Tamaño | Para qué |
|---|---|---|
| `llama3.1:8b` | 4,9 GB | conversación general, rápido — el que usar por defecto |
| `qwen3:8b` | 5,2 GB | razonamiento y código |
| `gemma4:12b-it-qat` | 7,2 GB | conversación general, cuantizado QAT |
| `gemma4:e4b` | 9,6 GB | conversación general; no cabe entero en 8 GB de VRAM, va lento |
| `nomic-embed-text` | 274 MB | embeddings para RAG — **no es un modelo de chat**, no debe aparecer en el selector |

Detalle y cuándo usar cada uno en [docs/modelos.md](docs/modelos.md).

## La advertencia de los 8 GB

Con 8 GB de VRAM **solo cabe un modelo en GPU a la vez**. Cambiar de modelo en
la interfaz obliga a descargar el anterior y cargar el nuevo: varios segundos
de espera, no un fallo. `gemma4:e4b` (9,6 GB) no entra entero y responde con
parte del cómputo en CPU — más lento, tampoco un fallo. No hace falta
diagnosticarlo dos veces: está aquí y en [docs/modelos.md](docs/modelos.md).

## Arranque rápido

```bash
systemctl status chat-web.service
```

```bash
http://192.168.1.38:8081/
```

El primer registro en la web crea el usuario administrador — eso lo hace el
propietario desde el navegador, no queda automatizado. Ver
[ESTADO.md](ESTADO.md) para el paso pendiente tras ese registro.

Instalación desde cero, arranque, parada, logs y backup:
[docs/instalacion.md](docs/instalacion.md) y [docs/operacion.md](docs/operacion.md).

## Qué queda fuera de alcance

Documentado, no implementado, en esta primera versión:

- Generación de imágenes vía ComfyUI.
- Búsqueda web desde el chat.
- Voz: ni STT ni TTS.
- Exponer el servicio fuera de la LAN.

## Estructura

```
/opt/chat/
├── scripts/instalar.sh    venv + open-webui
├── scripts/arrancar.sh    arranque manual en primer plano, para depurar
├── scripts/backup.sh      copia data/ a /opt/backups
├── systemd/chat-web.service
├── .env.example           plantilla de configuración (se sube)
├── .env                   configuración real, con la clave secreta (NO se sube)
├── docs/                  instalación, operación, modelos, arquitectura
├── venv/                  NO se sube
└── data/                  NO se sube: base sqlite, usuarios, chats, vectores
```

## Licencia

[MIT](LICENSE).
