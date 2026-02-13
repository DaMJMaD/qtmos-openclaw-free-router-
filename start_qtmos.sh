#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY="${QTMOS_VENV_PY:-$HOME/qtmos-venv/bin/python}"

if [ ! -x "$PY" ]; then
  echo "[QTMoS] missing venv python: $PY"
  echo "[QTMoS] fix: python3 -m venv ~/qtmos-venv"
  exit 1
fi

cd "$ROOT"
export QTM_AUTO_START_SERVERS="${QTM_AUTO_START_SERVERS:-1}"
export MCP_ROOT="${MCP_ROOT:-/home/d/Desktop/UniProjects}"
export PUTER_LOGIN_DISABLE_SDK="${PUTER_LOGIN_DISABLE_SDK:-1}"
export PUTER_AUTO_INSTALL_SDK="${PUTER_AUTO_INSTALL_SDK:-1}"

exec "$PY" -m core "$@"
