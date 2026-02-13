#!/usr/bin/env bash
set -euo pipefail

PROJECT='/mnt/c/Users/Dave/Desktop/UniProjects/Daves Desktop Buddies/Head/Tenchin/systems modulation'
cd "$PROJECT"

if ! command -v node >/dev/null 2>&1; then
  echo "[ERROR] node is required. Install Node.js and retry."
  exit 1
fi

if ! command -v npm >/dev/null 2>&1; then
  echo "[ERROR] npm is required. Install npm and retry."
  exit 1
fi

if [ ! -f "llm/puter_node_bridge.cjs" ]; then
  echo "[ERROR] Missing llm/puter_node_bridge.cjs"
  exit 1
fi

# Keep node resolution pinned to this project first.
export NODE_PATH="$PROJECT/node_modules${NODE_PATH:+:$NODE_PATH}"

# Install Puter SDK if current Node resolution cannot find it.
if ! node -e "require.resolve('@heyputer/puter.js/src/init.cjs')" >/dev/null 2>&1; then
  echo "[SETUP] Installing @heyputer/puter.js in project ..."
  npm install --prefix "$PROJECT" --no-save @heyputer/puter.js
fi

# 1) Get fresh auth token via browser flow
echo "[AUTH] Starting Puter browser handshake..."
payload="$(node llm/puter_node_bridge.cjs auth-token)"

# 2) Extract token from JSON payload (tolerate extra log lines)
if ! token="$(printf '%s' "$payload" | node -e "let d='';process.stdin.on('data',c=>d+=c);process.stdin.on('end',()=>{const lines=String(d||'').split(/\r?\n/).map(s=>s.trim()).filter(Boolean);const cands=[String(d||''),...lines.slice().reverse()];for(const c of cands){if(!(c.startsWith('{')&&c.endsWith('}')))continue;try{const j=JSON.parse(c);if(j&&j.ok&&j.token){process.stdout.write(String(j.token||''));return;}}catch(_e){}}process.exit(2);})")"; then
  echo "[ERROR] Failed to fetch Puter auth token."
  echo "$payload"
  exit 1
fi

# 3) sanitize + export for Node bridge + Python app
token="$(printf '%s' "$token" | tr -d '\t\r\n ')"
export puterAuthToken="$token"
export PUTER_AUTH_TOKEN="$token"

# 4) quick health check
node llm/puter_node_bridge.cjs chat --model "${PUTER_DEFAULT_MODEL:-claude-opus-4-6}" --prompt "handshake check"

# 5) launch app
PYTHONPATH=. python3 core/main.py
