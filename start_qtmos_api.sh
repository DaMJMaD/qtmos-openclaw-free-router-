#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY="${QTMOS_VENV_PY:-$HOME/qtmos-venv/bin/python}"
HOST="${QTMOS_API_HOST:-127.0.0.1}"
PORT="${QTMOS_API_PORT:-8010}"

if [ ! -x "$PY" ]; then
  echo "[QTMoS API] missing venv python: $PY"
  echo "[QTMoS API] fix: python3 -m venv ~/qtmos-venv"
  exit 1
fi

cd "$ROOT"
export PYTHONPATH="$ROOT"
export PUTER_LOGIN_DISABLE_SDK="${PUTER_LOGIN_DISABLE_SDK:-1}"
export PUTER_AUTO_INSTALL_SDK="${PUTER_AUTO_INSTALL_SDK:-1}"

exec "$PY" -m uvicorn qtmos_server:app --host "$HOST" --port "$PORT"
