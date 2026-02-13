# Quickstart: Windows Native (No WSL)

## Requirements

- Windows 10/11
- Python 3.10+
- PowerShell
- Optional: Ollama for free local fallback

## Install

Open PowerShell in project root:

```powershell
Set-Location "C:\path\to\systems modulation"
py -3 -m venv "$HOME\qtmos-venv"
& "$HOME\qtmos-venv\Scripts\python.exe" -m pip install --upgrade pip
& "$HOME\qtmos-venv\Scripts\python.exe" -m pip install -r requirements.txt
```

## Auto-start (Task Scheduler)

```powershell
Set-Location "C:\path\to\systems modulation"
.\deploy\windows\install_qtmos_api_task.ps1
```

## Verify

```powershell
& "$HOME\qtmos-venv\Scripts\python.exe" .\skills\qtmos-http-tools\scripts\call_qtmos.py health
& "$HOME\qtmos-venv\Scripts\python.exe" .\skills\qtmos-http-tools\scripts\route_prompt.py "ping" --mode auto
```

## Remove scheduled task

```powershell
.\deploy\windows\uninstall_qtmos_api_task.ps1
```
