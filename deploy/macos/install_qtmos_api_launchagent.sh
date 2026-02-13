#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
LINK="$HOME/qtmos"
PLIST_DIR="$HOME/Library/LaunchAgents"
PLIST="$PLIST_DIR/com.qtmos.api.plist"
LOG_DIR="$HOME/Library/Logs"

mkdir -p "$PLIST_DIR" "$LOG_DIR"
ln -sfn "$ROOT" "$LINK"

cat > "$PLIST" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
  <dict>
    <key>Label</key>
    <string>com.qtmos.api</string>

    <key>ProgramArguments</key>
    <array>
      <string>/bin/bash</string>
      <string>-lc</string>
      <string>$LINK/start_qtmos_api.sh</string>
    </array>

    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>

    <key>EnvironmentVariables</key>
    <dict>
      <key>QTMOS_VENV_PY</key>
      <string>$HOME/qtmos-venv/bin/python</string>
      <key>QTMOS_API_HOST</key>
      <string>127.0.0.1</string>
      <key>QTMOS_API_PORT</key>
      <string>8010</string>
      <key>PUTER_LOGIN_DISABLE_SDK</key>
      <string>1</string>
      <key>PUTER_AUTO_INSTALL_SDK</key>
      <string>1</string>
    </dict>

    <key>StandardOutPath</key>
    <string>$LOG_DIR/qtmos-api.log</string>
    <key>StandardErrorPath</key>
    <string>$LOG_DIR/qtmos-api.err.log</string>
  </dict>
</plist>
PLIST

launchctl bootout "gui/$(id -u)" "$PLIST" >/dev/null 2>&1 || true
launchctl bootstrap "gui/$(id -u)" "$PLIST"
launchctl enable "gui/$(id -u)/com.qtmos.api"
launchctl kickstart -k "gui/$(id -u)/com.qtmos.api"

echo "Installed LaunchAgent: $PLIST"
launchctl print "gui/$(id -u)/com.qtmos.api" | head -n 30 || true
