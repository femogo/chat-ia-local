# PLAN — Chat IA local (Open WebUI + Ollama)

**Ejecutor previsto:** Sonnet 5
**Directorio de trabajo:** `/opt/chat`
**Objetivo:** un "ChatGPT" propio en la LAN, servido por Open WebUI, conectado **únicamente** a los modelos ya descargados en Ollama. Documentado, con repo git y publicado en GitHub.

---

## 0. Contexto ya verificado (no hace falta volver a comprobarlo)

| Elemento | Estado |
|---|---|
| SO | Ubuntu 24.04 LTS (contenedor LXC), root |
| Docker | **NO instalado** → instalación nativa con `uv`, no contenedores |
| Python | 3.12.3 por defecto; **3.11.15 disponible** en `/usr/bin/python3.11` |
| `uv` | `/root/.local/bin/uv` |
| Ollama | activo (`ollama.service`), API en `http://127.0.0.1:11434` |
| GPU | RTX 4060, 8 GB VRAM |
| RAM | 20 GB |
| Disco `/` | 54 GB libres (78 % usado) |
| IP LAN | `192.168.1.38` |
| `gh` | autenticado como `femogo`, scopes `repo, workflow, gist, read:org` |
| Convención de la máquina | proyecto en `/opt/<nombre>`, `venv` propio, unidad systemd, README en español, LICENSE MIT, repo público |

**Modelos descargados en Ollama (los únicos que debe exponer el chat):**

| Modelo | Tamaño | Uso previsto |
|---|---|---|
| `gemma4:e4b` | 9,6 GB | conversación general (pesado para 8 GB VRAM → offload parcial a CPU) |
| `gemma4:12b-it-qat` | 7,2 GB | conversación general, cuantizado QAT |
| `qwen3:8b` | 5,2 GB | razonamiento / código |
| `llama3.1:8b` | 4,9 GB | conversación general, rápido |
| `nomic-embed-text:latest` | 274 MB | **embeddings para RAG** (no debe aparecer como modelo de chat) |

**Puertos ocupados:** 22, 25, 53, 8000 (debate), 8090 (pipeline), 8188/8189 (ComfyUI), 9090 (portal), 11434 (Ollama).
**Puerto 8080 está reservado** en `/opt/portal/index.html` para el proyecto "Música" (parado ahora mismo, pero no se toca).
→ **Open WebUI usará el puerto `8081`.**

---

## 1. Decisiones de diseño (ya tomadas, no volver a debatirlas)

1. **Instalación nativa con `uv`, no Docker.** No hay Docker y no se instala: añadir un runtime de contenedores a esta máquina es un cambio de infraestructura fuera del encargo.
2. **Python 3.11** en el venv. Open WebUI declara `requires-python >=3.11,<3.13`; 3.11 es la versión con la que se distribuye oficialmente y evita ruedas ausentes.
3. **Solo Ollama local.** `ENABLE_OPENAI_API=false`. Ninguna clave de API externa, ninguna llamada saliente a proveedores.
4. **Embeddings con `nomic-embed-text` vía Ollama**, no con el `sentence-transformers` que Open WebUI descarga por defecto de Hugging Face. Esto respeta el "solo con los modelos descargados", evita ~500 MB de descarga y quita una dependencia de red en el primer arranque.
5. **Autenticación activada.** El primer usuario registrado es administrador. Tras crearlo, se cierra el registro (`ENABLE_SIGNUP=false`). Está en LAN, pero la LAN no es un perímetro de confianza.
6. **Servicio systemd `chat-web.service`**, mismo patrón que `debate.service` / `video-pipeline.service`.
7. **Fuera de alcance por ahora** (documentar como "siguiente paso", no implementar): generación de imágenes vía ComfyUI, búsqueda web, STT/TTS, y exposición fuera de la LAN.

### Riesgo que hay que vigilar (y que debe quedar escrito en la documentación)

Con 8 GB de VRAM, **solo cabe un modelo en GPU cada vez**. Cambiar de modelo en la interfaz provoca una descarga/carga de varios segundos, y `gemma4:e4b` (9,6 GB) **no cabe entero**: irá parcialmente a CPU y responderá despacio. No es un fallo de la instalación; hay que decirlo en el README para que nadie lo diagnostique dos veces.

Segundo riesgo: `pip install open-webui` arrastra un árbol de dependencias grande (del orden de 3–6 GB con `torch` incluido). Hay 54 GB libres, así que entra, pero **comprobar `df -h /opt` antes y después** y abortar si el margen baja de 10 GB.

---

## 2. Estructura final del proyecto

```
/opt/chat/
├── CLAUDE.md                 # notas operativas para agentes
├── ESTADO.md                 # estado actual, qué funciona y qué no
├── LICENSE                   # MIT
├── PLAN.md                   # este documento
├── README.md                 # portada del repo, en español
├── .gitignore
├── .env.example              # plantilla de configuración (SÍ se sube)
├── .env                      # configuración real (NO se sube)
├── docs/
│   ├── instalacion.md        # cómo reproducirlo desde cero
│   ├── operacion.md          # arrancar, parar, logs, backup, actualizar
│   ├── modelos.md            # los 5 modelos, cuándo usar cada uno, límite de VRAM
│   └── arquitectura.md       # diagrama de piezas y por qué nativo en vez de Docker
├── systemd/
│   └── chat-web.service      # copia versionada de la unidad
├── scripts/
│   ├── instalar.sh           # crea venv + instala open-webui
│   ├── arrancar.sh           # arranque manual en primer plano (depuración)
│   └── backup.sh             # copia de data/ a /opt/backups
├── venv/                     # NO se sube
└── data/                     # NO se sube: BD sqlite, usuarios, chats, vectores
```

---

## 3. Pasos de ejecución

> Ejecutar en orden. Cada paso tiene su comprobación. Si una comprobación falla, **parar y reportar**, no improvisar un rodeo.

### Paso 1 — Andamiaje del proyecto

```bash
mkdir -p /opt/chat/{docs,systemd,scripts,data}
```

Escribir `.gitignore`:

```gitignore
venv/
data/
.env
__pycache__/
*.pyc
*.log
```

### Paso 2 — Entorno virtual e instalación

`scripts/instalar.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
cd /opt/chat
uv venv --python 3.11 venv
source venv/bin/activate
uv pip install open-webui
open-webui --version
```

**Comprobación:** `open-webui --version` responde y `df -h /opt` conserva más de 10 GB libres.
**Si `uv pip install` falla por una rueda ausente:** reintentar con `uv pip install --python 3.11 open-webui`; si vuelve a fallar, reportar el error tal cual, sin cambiar de versión de Python por iniciativa propia.

### Paso 3 — Configuración

`.env.example` (y copiarlo a `.env`, que es el que lee el servicio):

```dotenv
# --- Red ---
HOST=0.0.0.0
PORT=8081
WEBUI_URL=http://192.168.1.38:8081

# --- Datos ---
DATA_DIR=/opt/chat/data

# --- Proveedores: solo Ollama local ---
OLLAMA_BASE_URL=http://127.0.0.1:11434
ENABLE_OPENAI_API=false

# --- Autenticación: el primer usuario es admin; luego cerrar el registro ---
WEBUI_AUTH=true
ENABLE_SIGNUP=true
DEFAULT_USER_ROLE=pending
WEBUI_SECRET_KEY=CAMBIAR_POR_CADENA_ALEATORIA

# --- RAG con el modelo de embeddings ya descargado ---
RAG_EMBEDDING_ENGINE=ollama
RAG_EMBEDDING_MODEL=nomic-embed-text:latest
RAG_OLLAMA_BASE_URL=http://127.0.0.1:11434

# --- Funciones que quedan fuera de alcance en esta primera versión ---
ENABLE_RAG_WEB_SEARCH=false
ENABLE_IMAGE_GENERATION=false
ENABLE_COMMUNITY_SHARING=false
```

En el `.env` real, generar la clave con `openssl rand -hex 32`. **`WEBUI_SECRET_KEY` no se sube al repo**; en `.env.example` se deja el marcador.

### Paso 4 — Servicio systemd

`systemd/chat-web.service`:

```ini
[Unit]
Description=Chat IA local (Open WebUI sobre Ollama)
After=network.target ollama.service
Wants=ollama.service

[Service]
Type=simple
WorkingDirectory=/opt/chat
EnvironmentFile=/opt/chat/.env
ExecStart=/opt/chat/venv/bin/open-webui serve --host 0.0.0.0 --port 8081
Restart=on-failure
RestartSec=5
User=root

[Install]
WantedBy=multi-user.target
```

```bash
cp /opt/chat/systemd/chat-web.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now chat-web.service
```

**Comprobación:**

```bash
systemctl is-active chat-web.service
curl -sf -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8081/
curl -s http://127.0.0.1:8081/api/models | head -c 400
```

El primer arranque tarda: Open WebUI crea la base sqlite y monta el frontend. Dar hasta 90 s antes de considerarlo un fallo, y mirar `journalctl -u chat-web -n 50` en lugar de reiniciar a ciegas.

### Paso 5 — Verificación funcional

1. `/api/models` debe listar los 4 modelos de chat. Si aparece también `nomic-embed-text`, ocultarlo desde *Admin → Ajustes → Modelos* y anotarlo en `ESTADO.md`.
2. Prueba de generación de extremo a extremo, sin abrir el navegador:

```bash
curl -s http://127.0.0.1:11434/api/generate -d '{"model":"llama3.1:8b","prompt":"Di hola en una frase.","stream":false}' | head -c 300
```

3. Dejar creado el usuario administrador es cosa del propietario (primer registro en la web). **No inventar credenciales ni crear el usuario por él.** Documentar en `ESTADO.md` que, tras registrarse, hay que poner `ENABLE_SIGNUP=false` en `.env` y `systemctl restart chat-web`.

### Paso 6 — Documentación

Escribir, en español y con el tono de los otros repos de `/opt` (directo, sin marketing):

- **README.md** — qué es, captura de la arquitectura en cuatro líneas, los cinco modelos y para qué sirve cada uno, arranque rápido, la advertencia de los 8 GB de VRAM, y qué queda fuera de alcance.
- **docs/instalacion.md** — reproducirlo desde cero en otra máquina, incluido el porqué de Python 3.11 y de no usar Docker.
- **docs/operacion.md** — `systemctl start/stop/status`, `journalctl -u chat-web -f`, dónde viven los datos, backup y restauración, cómo actualizar (`uv pip install -U open-webui` + reinicio) y cómo revertir.
- **docs/modelos.md** — tabla de modelos, tamaño, uso recomendado, comportamiento al cambiar de modelo con 8 GB, cómo añadir uno nuevo con `ollama pull`.
- **docs/arquitectura.md** — navegador → Open WebUI (8081) → Ollama (11434) → GPU; dónde encaja `nomic-embed-text` en el RAG; decisiones y sus motivos.
- **CLAUDE.md** — rutas, puerto, nombre del servicio, dónde está el `.env`, qué no tocar (`data/`, el puerto 8080 de Música).
- **ESTADO.md** — fecha (2026-08-10), qué está verificado, qué queda pendiente.
- **LICENSE** — MIT, mismo titular que los otros repos de `/opt` (copiar de `/opt/inicio/LICENSE`).

`scripts/backup.sh` debe hacer `tar czf /opt/backups/chat-data-$(date +%F).tar.gz -C /opt/chat data`, con el servicio parado o avisando de que sqlite puede quedar inconsistente en caliente.

### Paso 7 — Portal

Añadir la entrada en `/opt/portal/index.html`, respetando el formato exacto de las líneas existentes:

```html
<li><a href="http://192.168.1.38:8081/"><span class="dot"></span><span class="name">Chat</span><span class="port">:8081</span></a></li>
```

### Paso 8 — Git y GitHub

```bash
cd /opt/chat
git init -b main
git add -A
git status   # ← comprobar que NI venv/, NI data/, NI .env están en el índice
git commit -m "Chat IA local: Open WebUI sobre Ollama con modelos descargados"
gh repo create femogo/chat-ia-local --public --source=. --push \
  --description "ChatGPT propio en local: Open WebUI sobre Ollama, sin Docker y sin APIs externas. Cuatro modelos de chat y embeddings locales en una RTX 4060 de 8 GB."
```

**Comprobación previa al push, obligatoria:** `git status` y confirmar que `.env` (con la clave secreta), `venv/` y `data/` (que contiene usuarios y chats) están excluidos. Si alguno aparece, **parar antes del push**: una clave publicada en GitHub no se retira borrando el commit.

Después: `gh repo view femogo/chat-ia-local --web` no, mejor `gh repo view femogo/chat-ia-local` y confirmar que el remoto tiene los ficheros esperados.

---

## 4. Criterios de aceptación

- [ ] `systemctl is-active chat-web.service` → `active`
- [ ] `http://192.168.1.38:8081/` responde 200 desde la LAN
- [ ] La interfaz lista los 4 modelos de chat de Ollama y ninguno externo
- [ ] Una conversación de prueba genera respuesta con `llama3.1:8b`
- [ ] El servicio sobrevive a `systemctl restart` y está `enabled` para el arranque
- [ ] `/opt/portal/index.html` enlaza el chat en el 8081
- [ ] Documentación completa según el Paso 6
- [ ] Repo `femogo/chat-ia-local` público, con historial y **sin** `.env`, `venv/` ni `data/`
- [ ] `ESTADO.md` explica el paso manual pendiente (registrar admin y cerrar el registro)

## 5. Reversión

```bash
systemctl disable --now chat-web.service
rm /etc/systemd/system/chat-web.service && systemctl daemon-reload
# los datos siguen en /opt/chat/data; borrar solo si se confirma
```

Revertir la línea añadida en `/opt/portal/index.html`. El repo de GitHub se borra a mano si procede: eso lo decide el propietario, no el ejecutor.

## 6. Límites del encargo

No instalar Docker. No tocar `ollama.service` ni sus variables. No descargar modelos nuevos. No ocupar el puerto 8080. No modificar otros proyectos de `/opt` salvo la única línea del portal. No exponer el servicio fuera de la LAN ni abrir puertos en el router.
