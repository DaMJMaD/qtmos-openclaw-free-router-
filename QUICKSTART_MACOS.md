# Quickstart: macOS

## Requirements

- macOS 13+
- Python 3.10+
- bash/zsh
- Optional: Ollama for free local fallback

## Install

```bash
cd "/path/to/systems modulation"
python3 -m venv ~/qtmos-venv
~/qtmos-venv/bin/pip install --upgrade pip
~/qtmos-venv/bin/pip install -r requirements.txt
```

## Auto-start (LaunchAgent)

```bash
./deploy/macos/install_qtmos_api_launchagent.sh
```

## Verify

```bash
python3 skills/qtmos-http-tools/scripts/call_qtmos.py health
python3 skills/qtmos-http-tools/scripts/route_prompt.py "ping" --mode auto
```

## Remove LaunchAgent

```bash
./deploy/macos/uninstall_qtmos_api_launchagent.sh
```
