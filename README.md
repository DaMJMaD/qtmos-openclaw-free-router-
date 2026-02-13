# QTMoS OpenClaw Free Router

Local-first tool backend for OpenClaw.

- One HTTP API service (`qtmos_server.py`)
- Safe command bridge (`/command` allowlist)
- Router script for model "subclaws" (`route_prompt.py`)
- Local fallback (`ollama`) so first boot can work without paid keys

## Platform Support

- Linux: supported
- WSL2: supported
- Windows native: supported (Task Scheduler install script)
- macOS: supported (LaunchAgent install script)

## Dependencies

- Python 3.10+
- Python packages in `requirements.txt`
- Optional: Node.js + npm (Puter SDK paths)
- Optional: Ollama for free local fallback

Install Python deps:

```bash
python3 -m pip install -r requirements.txt
```

## Pick Your Quickstart

- Linux/WSL: `QUICKSTART_LINUX_WSL.md`
- Windows native: `QUICKSTART_WINDOWS_NATIVE.md`
- macOS: `QUICKSTART_MACOS.md`

## One-Command Healthchecks

- Linux/WSL: `./deploy/healthcheck.sh`
- Windows native (PowerShell): `.\deploy\windows\healthcheck.ps1`
- macOS: `./deploy/macos/healthcheck.sh`

Release confidence checklist: `RELEASE_CHECKLIST.md`

## API Endpoints

- `GET /health`
- `GET /models`
- `POST /ask`
- `POST /command`
- `GET /state`

Contract: `skills/qtmos-http-tools/references/api-contract.md`

## OpenClaw Skill + Scripts

- Skill definition: `skills/qtmos-http-tools/SKILL.md`
- Basic caller: `skills/qtmos-http-tools/scripts/call_qtmos.py`
- Router/fallback script: `skills/qtmos-http-tools/scripts/route_prompt.py`

Examples:

```bash
python skills/qtmos-http-tools/scripts/call_qtmos.py health
python skills/qtmos-http-tools/scripts/call_qtmos.py command "health"
python skills/qtmos-http-tools/scripts/call_qtmos.py models --provider anthropic
python skills/qtmos-http-tools/scripts/call_qtmos.py models | jq -r '.models[] | .provider' | sort | uniq -c | sort -nr
python skills/qtmos-http-tools/scripts/route_prompt.py "explain this stacktrace" --mode auto
python skills/qtmos-http-tools/scripts/route_prompt.py "compare answers" --mode compare --candidates "claude-opus-4-6,gpt-4.1-mini,ollama/llama3:latest"
```

## Share Safely

Share:

- `qtmos_server.py`
- `start_qtmos.sh`
- `start_qtmos.ps1`
- `start_qtmos_api.sh`
- `start_qtmos_api.ps1`
- `deploy/systemd/*`
- `deploy/windows/*`
- `deploy/macos/*`
- `deploy/wsl/*`
- `skills/qtmos-http-tools/*`
- `README.md`
- `RELEASE_CHECKLIST.md`
- `QUICKSTART_*.md`
- `.env.example`
- `qtmos_server.env.example`

Do not share:

- `llm/.env`
- personal data in `MetaDB/` and `memory/`

## Build Share Bundle

```bash
./deploy/make_share_bundle.sh
```

## Discord Post Template

Use: `DISCORD_SNIPPET.md`

## First GitHub Publish

```bash
git init
git add .
git commit -m "Initial QTMoS OpenClaw free router"
git branch -M main
git remote add origin <YOUR_GITHUB_REPO_URL>
git push -u origin main
```

Pre-push secret check:

```bash
git ls-files | rg 'llm/.env|MetaDB|memory/' || true
```
