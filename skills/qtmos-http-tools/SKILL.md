---
name: qtmos-http-tools
description: Call a local QTMoS HTTP tool backend from OpenClaw-style workflows. Use when a task needs QTMoS capabilities over HTTP endpoints at /health, /models, /ask, /command, or /state, including scripted checks and safe command execution.
---

# QTMoS HTTP Tools

Use this skill to call a running QTMoS API service.

## Quick Start

1. Set `QTMOS_API_BASE_URL` (default `http://127.0.0.1:8010`).
2. Verify service health:
`python scripts/call_qtmos.py health`
3. Ask model-backed question:
`python scripts/call_qtmos.py ask "ping" --model claude-opus-4-6`
4. Run safe QTMoS command:
`python scripts/call_qtmos.py command "health"`
5. Check provider/model inventory without terminal flood:
`python scripts/call_qtmos.py models --providers`
6. Route with fallback/compare:
`python scripts/route_prompt.py "summarize this log" --mode auto`

## Safety Rules

- Call `/command` only for allowlisted, non-destructive commands.
- Never send secrets in command arguments or prompts.
- Keep API bind local (`127.0.0.1`) unless tunneled securely.
- Keep compare fanout small (`--max-fanout 3` recommended).

## Contract

Read `references/api-contract.md` for request/response shapes.
