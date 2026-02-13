# RELEASE_CHECKLIST

Use this before posting to GitHub/Discord.

## 1) Secrets and Data Safety

- [ ] Verify `llm/.env` is not tracked
- [ ] Verify personal memory files are not tracked (`MetaDB/`, `memory/`)
- [ ] Run secret scan:

```bash
git ls-files | rg 'llm/.env|MetaDB|memory/' || true
rg -n 'PUTER_AUTH_TOKEN|GEMINI_API_KEY|OPENAI_API_KEY' --glob '!*llm/.env' .
```

## 2) Required Docs Present

- [ ] `README.md`
- [ ] `QUICKSTART_LINUX_WSL.md`
- [ ] `QUICKSTART_WINDOWS_NATIVE.md`
- [ ] `QUICKSTART_MACOS.md`
- [ ] `DISCORD_SNIPPET.md`
- [ ] `share_openclaw_qtmos.md`
- [ ] `RELEASE_CHECKLIST.md`

Quick check:

```bash
ls README.md QUICKSTART_LINUX_WSL.md QUICKSTART_WINDOWS_NATIVE.md QUICKSTART_MACOS.md DISCORD_SNIPPET.md share_openclaw_qtmos.md RELEASE_CHECKLIST.md
```

## 3) Healthcheck Scripts Present

- [ ] `deploy/healthcheck.sh`
- [ ] `deploy/windows/healthcheck.ps1`
- [ ] `deploy/macos/healthcheck.sh`

Run:

- Linux/WSL:
```bash
./deploy/healthcheck.sh
```

- Windows native (PowerShell):
```powershell
.\deploy\windows\healthcheck.ps1
```

- macOS:
```bash
./deploy/macos/healthcheck.sh
```

## 4) Smoke Tests

- [ ] API health
- [ ] providers list
- [ ] ask ping

Commands:

```bash
python skills/qtmos-http-tools/scripts/call_qtmos.py health
python skills/qtmos-http-tools/scripts/call_qtmos.py models | jq -r '.models[] | .provider' | sort | uniq -c | sort -nr
python skills/qtmos-http-tools/scripts/call_qtmos.py ask "ping" --model claude-opus-4-6
```

## 5) Build Share Bundle

- [ ] Build command succeeds:

```bash
./deploy/make_share_bundle.sh
```

- [ ] Output file exists in `dist/` and matches:

`dist/qtmos-openclaw-free-router_YYYYMMDD_HHMMSS.tar.gz`

- [ ] Archive contains expected files (`README`, quickstarts, deploy scripts, skill folder)

```bash
tar -tzf dist/qtmos-openclaw-free-router_*.tar.gz | head -n 60
```

## 6) First Publish Commands

```bash
git init
git add .
git commit -m "Initial QTMoS OpenClaw free router"
git branch -M main
git remote add origin <YOUR_GITHUB_REPO_URL>
git push -u origin main
```

## 7) Post-Release Confidence

- [ ] Paste `DISCORD_SNIPPET.md` into OpenClaw Discord
- [ ] Keep troubleshooting commands ready:

```bash
systemctl --user status qtmos-api.service
journalctl --user -u qtmos-api.service -n 80 --no-pager
python skills/qtmos-http-tools/scripts/call_qtmos.py health
```
