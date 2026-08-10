#!/usr/bin/env bash
# Arranque manual en primer plano, para depuración.
# El servicio real lo gestiona systemd (chat-web.service); esto es solo
# para ver los logs en directo sin pasar por journalctl.
set -euo pipefail
cd /opt/chat
source venv/bin/activate
set -a
source .env
set +a
open-webui serve --host "${HOST:-0.0.0.0}" --port "${PORT:-8081}"
