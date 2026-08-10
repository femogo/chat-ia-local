#!/usr/bin/env bash
set -euo pipefail
cd /opt/chat
uv venv --python 3.11 venv
source venv/bin/activate
uv pip install open-webui
open-webui --version
