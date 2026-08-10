# CLAUDE.md

Notas operativas para agentes que trabajen en este repositorio.

## Qué es

Open WebUI (interfaz de chat) instalado nativo con `uv` en `/opt/chat/venv`,
sirviendo los modelos que ya están descargados en Ollama en esta misma
máquina. Servicio systemd `chat-web.service`, puerto `8081`.

Plan original con todo el contexto y las decisiones de diseño:
[PLAN.md](PLAN.md).

## Rutas y datos clave

| Qué | Dónde |
|---|---|
| Proyecto | `/opt/chat` |
| venv | `/opt/chat/venv` (Python 3.11, no se sube al repo) |
| Configuración real | `/opt/chat/.env` (con `WEBUI_SECRET_KEY` real, **no se sube**) |
| Plantilla de configuración | `/opt/chat/.env.example` (sí se sube, con marcador) |
| Datos (sqlite, usuarios, chats, vectores) | `/opt/chat/data` (no se sube) |
| Unidad systemd instalada | `/etc/systemd/system/chat-web.service` |
| Unidad versionada en el repo | `/opt/chat/systemd/chat-web.service` — si se edita una, editar la otra y volver a copiar |
| Servicio | `chat-web.service`, puerto `8081` |
| Ollama (no es parte de este proyecto) | `ollama.service`, `127.0.0.1:11434` |

## Qué NO tocar

1. **`ollama.service` ni sus variables.** Es infraestructura compartida con
   otros proyectos de `/opt` (ComfyUI, plantillas de `/opt/inicio`, etc.).
   Este proyecto solo lo consume vía API.
2. **El puerto `8080`.** Reservado en `/opt/portal/index.html` para el
   proyecto "Música" (parado, pero no se toca).
3. **`data/`.** Contiene usuarios, chats y vectores reales de una instancia
   en marcha. No se sube al repositorio, no se edita a mano, no se borra sin
   confirmación explícita del propietario.
4. **`.env`.** Contiene `WEBUI_SECRET_KEY` real, que firma las sesiones. No
   se sube, no se imprime en logs ni en salidas de comandos, no se pega en
   ningún sitio. Si hay que compartir la configuración, se comparte
   `.env.example`.
5. **Otros proyectos de `/opt`.** La única línea que este proyecto toca fuera
   de `/opt/chat` es la entrada en `/opt/portal/index.html` (Paso 7 del
   plan).
6. **No descargar modelos nuevos con `ollama pull`** como parte de este
   proyecto. Los cuatro modelos de chat y el de embeddings son los que ya
   estaban antes de empezar. Añadir uno es una decisión aparte del
   propietario (ver [docs/modelos.md](docs/modelos.md)).
7. **No crear el usuario administrador ni inventar credenciales.** El primer
   registro en la web lo hace el propietario. Ver [ESTADO.md](ESTADO.md).

## Comandos habituales

```bash
systemctl status chat-web.service
journalctl -u chat-web -n 50 --no-pager
systemctl restart chat-web.service
```

Detalle de arranque, logs, backup y actualización en
[docs/operacion.md](docs/operacion.md).

## Convenciones

- Documentación y comentarios en español, tono directo, sin marketing —
  mismo criterio que `/opt/inicio` y `/opt/debate`.
- README en español, LICENSE MIT con el mismo titular que el resto de
  proyectos de `/opt` (`femogo`).
- Un cambio en la unidad systemd se hace primero en
  `systemd/chat-web.service` (versionado) y se copia después a
  `/etc/systemd/system/`, no al revés.
