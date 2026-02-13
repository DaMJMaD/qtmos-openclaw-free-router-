# QTMoS API Contract

Base URL: `http://127.0.0.1:8010`

## `GET /health`
Response:
```json
{
  "ok": true,
  "service": "qtmos-tool-api",
  "version": "1.0.0",
  "token_present": true,
  "time": 1739462400
}
```

## `GET /models?provider=<name>`
Response:
```json
{
  "ok": true,
  "provider": "anthropic",
  "count": 4,
  "models": [
    {"id": "claude-opus-4-6", "provider": "claude"}
  ]
}
```

## `POST /ask`
Request:
```json
{
  "prompt": "ping",
  "model": "claude-opus-4-6",
  "allow_local_fallback": true
}
```
Response:
```json
{
  "ok": true,
  "provider": "puter",
  "model": "claude-opus-4-6",
  "prompt": "ping",
  "reply": "Pong",
  "fallback_used": false
}
```

Notes:
- To force local Ollama, pass `model` as `ollama/<tag>`, e.g. `ollama/llama3:latest`.
- With `allow_local_fallback=true`, server tries local Ollama if Puter has no response.

## `POST /command`
Request:
```json
{
  "cmd": "health"
}
```
Response:
```json
{
  "ok": true,
  "command": "health",
  "stdout": "...",
  "stderr": "",
  "elapsed_ms": 42
}
```

## `GET /state`
Response:
```json
{
  "ok": true,
  "status": {"stdout": "..."},
  "whoami": {"stdout": "..."},
  "health": {"stdout": "..."}
}
```

## Errors

- `400`: malformed input
- `403`: blocked or non-allowlisted command
- `503`: backend unavailable / no model response
