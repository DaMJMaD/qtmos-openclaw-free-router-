#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT_DIR="$ROOT/dist"
STAMP="$(date +%Y%m%d_%H%M%S)"
BUNDLE="$OUT_DIR/qtmos-openclaw-free-router_${STAMP}.tar.gz"

mkdir -p "$OUT_DIR"

cd "$ROOT"

tar -czf "$BUNDLE" \
  qtmos_server.py \
  start_qtmos.sh \
  start_qtmos.ps1 \
  start_qtmos_api.sh \
  start_qtmos_api.ps1 \
  deploy/systemd/install_qtmos_api_service.sh \
  deploy/systemd/qtmos-api.service \
  deploy/healthcheck.sh \
  deploy/windows/install_qtmos_api_task.ps1 \
  deploy/windows/uninstall_qtmos_api_task.ps1 \
  deploy/windows/healthcheck.ps1 \
  deploy/macos/install_qtmos_api_launchagent.sh \
  deploy/macos/uninstall_qtmos_api_launchagent.sh \
  deploy/macos/healthcheck.sh \
  deploy/wsl/install_qtmos_api_profile_start.sh \
  skills/qtmos-http-tools \
  README.md \
  RELEASE_CHECKLIST.md \
  QUICKSTART_LINUX_WSL.md \
  QUICKSTART_WINDOWS_NATIVE.md \
  QUICKSTART_MACOS.md \
  DISCORD_SNIPPET.md \
  .env.example \
  requirements.txt \
  qtmos_server.env.example \
  share_openclaw_qtmos.md

echo "$BUNDLE"
