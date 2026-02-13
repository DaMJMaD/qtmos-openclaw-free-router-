# Share QTMoS as an OpenClaw Tool Backend

## 1. Canonical Root

Use one path only:
`/home/d/Desktop/systems modulation`

A stable symlink is also created:
`/home/d/qtmos`

## 2. Run API Locally

Manual run:
`/home/d/qtmos/start_qtmos_api.sh`

Health check:
`curl -sS http://127.0.0.1:8010/health`

## 3. Auto-start as User Service

Install or refresh service:
`/home/d/qtmos/deploy/systemd/install_qtmos_api_service.sh`

Useful commands:
- `systemctl --user status qtmos-api.service`
- `journalctl --user -u qtmos-api.service -f`

## 4. Endpoints

- `GET /health`
- `GET /models`
- `POST /ask` with `{"prompt":"...","model":"..."}`
- `POST /command` with `{"cmd":"health"}`
- `GET /state`

Contract doc:
`/home/d/qtmos/skills/qtmos-http-tools/references/api-contract.md`

## 5. Share Package

Share only:
- `qtmos_server.py`
- `start_qtmos.sh`
- `start_qtmos.ps1`
- `start_qtmos_api.sh`
- `start_qtmos_api.ps1`
- `deploy/systemd/*`
- `deploy/healthcheck.sh`
- `deploy/windows/*`
- `deploy/macos/*`
- `deploy/wsl/*`
- `skills/qtmos-http-tools/*`
- `qtmos_server.env.example`
- `QUICKSTART_*.md`
- `RELEASE_CHECKLIST.md`

Do not share:
- `llm/.env`
- memory packs and personal history
- any raw tokens or keys

Create a clean tarball bundle:
`/home/d/qtmos/deploy/make_share_bundle.sh`

## 6. OpenClaw-Side Calls

Use helper script:
`python /home/d/qtmos/skills/qtmos-http-tools/scripts/call_qtmos.py health`

Provider summary without huge JSON dump:
`python /home/d/qtmos/skills/qtmos-http-tools/scripts/call_qtmos.py models --providers`

Use router script for "subclaw" selection/fallback:
`python /home/d/qtmos/skills/qtmos-http-tools/scripts/route_prompt.py "ping" --mode auto`

Set base URL for remote/tunnel usage:
`export QTMOS_API_BASE_URL=http://127.0.0.1:8010`
