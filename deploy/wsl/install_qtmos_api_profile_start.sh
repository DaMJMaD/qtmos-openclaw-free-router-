#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
LINK="$HOME/qtmos"
PROFILE="$HOME/.profile"
BEGIN="# >>> qtmos-api autostart >>>"
END="# <<< qtmos-api autostart <<<"

ln -sfn "$ROOT" "$LINK"

if grep -Fq "$BEGIN" "$PROFILE" 2>/dev/null; then
  echo "Autostart block already exists in $PROFILE"
  exit 0
fi

cat >> "$PROFILE" <<EOF
$BEGIN
if ! pgrep -f "uvicorn qtmos_server:app --host 127.0.0.1 --port 8010" >/dev/null 2>&1; then
  nohup "$LINK/start_qtmos_api.sh" > /tmp/qtmos-api.log 2>&1 &
fi
$END
EOF

echo "Added autostart block to $PROFILE"
