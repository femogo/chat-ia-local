# Instalación desde cero

Para reproducir esto en otra máquina con Ollama ya instalado y con los
modelos ya descargados.

## Requisitos previos

- Ubuntu (probado en 24.04 LTS).
- Ollama activo (`ollama.service`) con los modelos de chat que se quieran
  exponer ya descargados con `ollama pull`. Este proyecto no descarga
  modelos: solo expone los que ya están.
- [`uv`](https://github.com/astral-sh/uv) instalado (`/root/.local/bin/uv`
  en esta máquina).
- Python 3.11 disponible en el sistema. En esta máquina, además del 3.12 por
  defecto, está en `/usr/bin/python3.11`.

## Por qué Python 3.11 y no el 3.12 del sistema

Open WebUI declara `requires-python >=3.11,<3.13`. El 3.11 es con el que se
distribuye y se prueba oficialmente el proyecto, y evita encontrarse con
alguna rueda (`wheel`) de una dependencia que todavía no publique build para
3.12 o 3.13. `uv venv --python 3.11` resuelve el intérprete sin tocar el
Python por defecto del sistema.

## Por qué instalación nativa y no Docker

Esta máquina no tiene Docker instalado. Añadir un runtime de contenedores
solo para este proyecto es un cambio de infraestructura que no pedía el
encargo: instalar Docker, mantenerlo, y la propia superficie que añade, no se
justifican para un único servicio. `uv` ya resuelve el problema que Docker
resolvería aquí —aislar las dependencias de Python en un venv propio— sin la
capa extra.

## Pasos

```bash
mkdir -p /opt/chat/{docs,systemd,scripts,data}
cd /opt/chat
```

Crear el venv e instalar Open WebUI (`scripts/instalar.sh` hace exactamente
esto):

```bash
uv venv --python 3.11 venv
source venv/bin/activate
uv pip install open-webui
```

Esto instala Open WebUI y su árbol de dependencias (torch incluido): del
orden de varios GB. Comprobar espacio libre antes y después:

```bash
df -h /opt
```

Si el margen baja de 10 GB, parar y revisar antes de seguir.

Copiar la plantilla de configuración y generar la clave secreta real:

```bash
cp .env.example .env
sed -i "s/^WEBUI_SECRET_KEY=.*/WEBUI_SECRET_KEY=$(openssl rand -hex 32)/" .env
```

`.env` no se sube al repositorio (está en `.gitignore`). Contiene la clave
que firma las sesiones: si se filtra, cualquiera puede falsificar una sesión
de administrador.

Instalar el servicio:

```bash
cp systemd/chat-web.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now chat-web.service
```

## Verificar

El primer arranque tarda: Open WebUI crea la base sqlite y monta el
frontend. Dar hasta 90 segundos antes de considerarlo un fallo.

```bash
systemctl is-active chat-web.service
curl -sf -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8081/
```

Si no responde en ese margen, mirar los logs antes de reiniciar a ciegas:

```bash
journalctl -u chat-web -n 50
```

Por último, entrar por el navegador a `http://<ip-de-la-máquina>:8081/` y
registrar el primer usuario (será el administrador). Ver
[ESTADO.md](../ESTADO.md) para el paso que hay que hacer justo después de
ese registro.
