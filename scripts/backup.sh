#!/usr/bin/env bash
# Copia data/ (sqlite, usuarios, chats, vectores) a /opt/backups.
# Mejor con el servicio parado: sqlite puede quedar inconsistente si se
# copia en caliente mientras alguien escribe. Si no se puede parar, este
# script avisa y sigue de todos modos.
set -euo pipefail

DEST=/opt/backups
FECHA=$(date +%F)
ARCHIVO="chat-data-${FECHA}.tar.gz"

mkdir -p "$DEST"

if systemctl is-active --quiet chat-web.service; then
  echo "AVISO: chat-web.service está activo. La copia puede quedar" >&2
  echo "inconsistente si sqlite está escribiendo en este instante." >&2
  echo "Para una copia limpia: systemctl stop chat-web && $0 && systemctl start chat-web" >&2
fi

tar czf "${DEST}/${ARCHIVO}" -C /opt/chat data
echo "Copia creada: ${DEST}/${ARCHIVO}"
