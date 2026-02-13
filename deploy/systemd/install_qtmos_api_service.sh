#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
LINK="$HOME/qtmos"
UNIT_DIR="$HOME/.config/systemd/user"
UNIT_FILE="$UNIT_DIR/qtmos-api.service"
VENV_PY="${QTMOS_VENV_PY:-$HOME/qtmos-venv/bin/python}"
HOST="${QTMOS_API_HOST:-127.0.0.1}"
PORT="${QTMOS_API_PORT:-8010}"

mkdir -p "$UNIT_DIR"
ln -sfn "$ROOT" "$LINK"

cat > "$UNIT_FILE" <<UNIT
[Unit]
Description=QTMoS Local Tool API
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
ExecStart=$LINK/start_qtmos_api.sh
Restart=always
RestartSec=3
Environment=QTMOS_VENV_PY=$VENV_PY
Environment=QTMOS_API_HOST=$HOST
Environment=QTMOS_API_PORT=$PORT
Environment=PUTER_LOGIN_DISABLE_SDK=1
Environment=PUTER_AUTO_INSTALL_SDK=1

[Install]
WantedBy=default.target
UNIT

systemctl --user daemon-reload
systemctl --user enable --now qtmos-api.service
systemctl --user --no-pager --full status qtmos-api.service
