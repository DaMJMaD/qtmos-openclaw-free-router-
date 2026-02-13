# Quickstart: Linux and WSL2

## Requirements

- Python 3.10+
- `bash`
- Optional: `systemd --user` (recommended for auto-start)
- Optional: Ollama for free local fallback

## Install

```bash
cd "/home/d/Desktop/systems modulation"
python3 -m venv ~/qtmos-venv
~/qtmos-venv/bin/pip install --upgrade pip
~/qtmos-venv/bin/pip install -r requirements.txt
```

## Auto-start

### If `systemd --user` is available

```bash
/home/d/Desktop/systems\ modulation/deploy/systemd/install_qtmos_api_service.sh
systemctl --user status qtmos-api.service
```

### If WSL without systemd

```bash
/home/d/Desktop/systems\ modulation/deploy/wsl/install_qtmos_api_profile_start.sh
source ~/.profile
```

## Verify

```bash
python skills/qtmos-http-tools/scripts/call_qtmos.py health
python skills/qtmos-http-tools/scripts/route_prompt.py "ping" --mode auto
```
