#!/usr/bin/env bash
set -u

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PY="${QTMOS_VENV_PY:-$HOME/qtmos-venv/bin/python}"
API_URL="${QTMOS_API_BASE_URL:-http://127.0.0.1:8010}"
API_BASE="${API_URL%/}"
PLIST_LABEL="com.qtmos.api"

failures=0
warnings=0

ok() { printf '[OK] %s\n' "$1"; }
warn() { printf '[WARN] %s\n' "$1"; warnings=$((warnings+1)); }
fail() { printf '[FAIL] %s\n' "$1"; failures=$((failures+1)); }

if [[ ! -x "$PY" ]]; then
  if command -v python3 >/dev/null 2>&1; then
    PY="$(command -v python3)"
    warn "Using fallback python3 at $PY"
  else
    fail "Python not found (expected $PY or python3 in PATH)"
    printf '\nSummary: failures=%d warnings=%d\n' "$failures" "$warnings"
    exit 1
  fi
fi

printf 'QTMoS healthcheck (macOS)\n'
printf 'Root: %s\n' "$ROOT"
printf 'Python: %s\n' "$PY"
printf 'API: %s\n\n' "$API_URL"

if "$PY" - <<'PY' >/tmp/qtmos_macos_pyver.txt 2>/tmp/qtmos_macos_pyver.err
import sys
v = sys.version_info
print(f"{v.major}.{v.minor}.{v.micro}")
raise SystemExit(0 if (v.major, v.minor) >= (3, 10) else 1)
PY
then
  ok "Python version >= 3.10 ($(cat /tmp/qtmos_macos_pyver.txt))"
else
  fail "Python version is below 3.10 or unreadable"
fi

if "$PY" - <<'PY' >/tmp/qtmos_macos_imports.txt 2>/tmp/qtmos_macos_imports.err
import importlib.util
mods = ["fastapi", "uvicorn", "requests", "dotenv"]
missing = [m for m in mods if importlib.util.find_spec(m) is None]
if missing:
    print("missing=" + ",".join(missing))
    raise SystemExit(1)
print("all-imports-ok")
PY
then
  ok "Required imports present (fastapi, uvicorn, requests, dotenv)"
else
  miss="$(cat /tmp/qtmos_macos_imports.txt 2>/dev/null || true)"
  fail "Missing imports: ${miss:-unknown}"
fi

if "$PY" - <<PY >/tmp/qtmos_macos_health.json 2>/tmp/qtmos_macos_health.err
import json, urllib.request
url = "${API_BASE}/health"
obj = json.loads(urllib.request.urlopen(url, timeout=10).read().decode())
print(json.dumps(obj))
raise SystemExit(0 if obj.get('ok') else 1)
PY
then
  ok "API /health reachable"
  token_present="$($PY - <<'PY' 2>/dev/null
import json
from pathlib import Path
p = Path('/tmp/qtmos_macos_health.json')
obj = json.loads(p.read_text())
print('1' if obj.get('token_present') else '0')
PY
)"
else
  fail "API /health failed at ${API_URL}/health"
  token_present="0"
fi

if "$PY" - <<PY >/tmp/qtmos_macos_ask.json 2>/tmp/qtmos_macos_ask.err
import json, urllib.request
url = "${API_BASE}/ask"
payload = {
    "prompt": "ping",
    "model": "claude-opus-4-6",
    "allow_local_fallback": True,
}
req = urllib.request.Request(
    url,
    method="POST",
    headers={"Content-Type": "application/json", "Accept": "application/json"},
    data=json.dumps(payload).encode('utf-8'),
)
obj = json.loads(urllib.request.urlopen(req, timeout=45).read().decode())
print(json.dumps(obj))
raise SystemExit(0 if obj.get('ok') else 1)
PY
then
  ok "Basic inference /ask succeeded"
else
  if [[ "$token_present" == "0" ]]; then
    warn "Inference failed (non-fatal): cloud token missing and local fallback may be unavailable"
  else
    warn "Inference failed (non-fatal): backend/model unavailable right now"
  fi
fi

if command -v launchctl >/dev/null 2>&1; then
  if launchctl print "gui/$(id -u)/$PLIST_LABEL" >/tmp/qtmos_macos_launchctl.txt 2>/tmp/qtmos_macos_launchctl.err; then
    ok "LaunchAgent loaded: $PLIST_LABEL"
  else
    warn "LaunchAgent not loaded: $PLIST_LABEL (non-fatal for manual runs)"
  fi
else
  warn "launchctl not available; skipped LaunchAgent check"
fi

printf '\nSummary: failures=%d warnings=%d\n' "$failures" "$warnings"
exit "$failures"
