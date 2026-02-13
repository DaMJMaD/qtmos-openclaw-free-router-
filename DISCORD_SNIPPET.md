# OpenClaw Discord Snippet

```text
QTMoS OpenClaw free/local router now supports Linux, WSL2, Windows native, and macOS.

Repo quickstart docs:
- QUICKSTART_LINUX_WSL.md
- QUICKSTART_WINDOWS_NATIVE.md
- QUICKSTART_MACOS.md

Fast Linux/WSL path:
1) cd "/home/d/Desktop/systems modulation"
2) python3 -m venv ~/qtmos-venv
3) ~/qtmos-venv/bin/pip install -r requirements.txt
4) ./deploy/systemd/install_qtmos_api_service.sh
5) python skills/qtmos-http-tools/scripts/call_qtmos.py health
6) python skills/qtmos-http-tools/scripts/call_qtmos.py models --providers
7) python skills/qtmos-http-tools/scripts/route_prompt.py "ping" --mode auto

Notes:
- Local API: http://127.0.0.1:8010
- Works with free Ollama fallback
- If PUTER_AUTH_TOKEN exists, cloud models are available too
```

Diagnostics:

```text
systemctl --user status qtmos-api.service
journalctl --user -u qtmos-api.service -n 80 --no-pager
python skills/qtmos-http-tools/scripts/call_qtmos.py health
```
