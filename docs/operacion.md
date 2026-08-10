# Operación

## Arrancar, parar, estado

```bash
systemctl start chat-web.service
systemctl stop chat-web.service
systemctl restart chat-web.service
systemctl status chat-web.service
```

El servicio está `enabled`: arranca solo con la máquina. `Restart=on-failure`
en la unidad lo reinicia solo si el proceso muere; no reinicia si se paró a
mano con `systemctl stop`.

## Logs

```bash
journalctl -u chat-web -f
```

```bash
journalctl -u chat-web -n 50 --no-pager
```

El primer arranque después de instalar o de un `restart` en frío tarda —
Open WebUI migra la base sqlite y monta el frontend—. Hasta 90 segundos no es
un fallo; mirar el log antes de reiniciar otra vez.

## Depurar en primer plano

Si algo falla y el log de systemd no basta, `scripts/arrancar.sh` lanza el
mismo proceso pero en primer plano y con la salida directa en la terminal
(parar el servicio primero para no chocar por el puerto):

```bash
systemctl stop chat-web.service
/opt/chat/scripts/arrancar.sh
```

## Dónde viven los datos

Todo en `/opt/chat/data/` (`DATA_DIR` en `.env`): la base sqlite con
usuarios, chats y configuración, y los vectores de RAG si se suben
documentos. No se sube al repositorio — son datos de una instancia concreta,
no código.

## Backup y restauración

```bash
/opt/chat/scripts/backup.sh
```

Copia `data/` a `/opt/backups/chat-data-<fecha>.tar.gz`. Mejor con el
servicio parado: sqlite puede quedar en un estado inconsistente si se copian
los ficheros mientras alguien escribe en caliente. El script avisa si el
servicio sigue activo, pero no lo para por decisión propia — eso lo decide
quien ejecuta el backup.

Restaurar:

```bash
systemctl stop chat-web.service
rm -rf /opt/chat/data
tar xzf /opt/backups/chat-data-<fecha>.tar.gz -C /opt/chat
systemctl start chat-web.service
```

## Actualizar

```bash
systemctl stop chat-web.service
cd /opt/chat
source venv/bin/activate
uv pip install -U open-webui
systemctl start chat-web.service
```

Revisar el registro de cambios de Open WebUI antes de actualizar en
producción: puede cambiar variables de entorno o el esquema de la base, y
conviene hacer un backup de `data/` justo antes.

## Revertir una actualización

`uv pip install` no borra la versión anterior por sí solo, pero tampoco la
conserva instalada en paralelo. Para volver atrás con garantías:

```bash
systemctl stop chat-web.service
source /opt/chat/venv/bin/activate
uv pip install open-webui==<versión-anterior>
```

Si la actualización tocó el esquema de la base de datos, restaurar además el
backup de `data/` tomado antes de actualizar (ver arriba) — una base migrada
a un esquema nuevo no siempre es compatible con una versión anterior del
código.
