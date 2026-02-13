$ErrorActionPreference = 'Stop'

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$py = $env:QTMOS_VENV_PY
if (-not $py) {
  $py = Join-Path $HOME 'qtmos-venv\Scripts\python.exe'
}
if (-not $env:QTMOS_API_HOST) { $env:QTMOS_API_HOST = '127.0.0.1' }
if (-not $env:QTMOS_API_PORT) { $env:QTMOS_API_PORT = '8010' }

if (-not (Test-Path $py)) {
  Write-Host "[QTMoS API] missing venv python: $py"
  Write-Host "[QTMoS API] fix: py -3 -m venv $HOME\\qtmos-venv"
  exit 1
}

Set-Location $Root
$env:PYTHONPATH = $Root
if (-not $env:PUTER_LOGIN_DISABLE_SDK) { $env:PUTER_LOGIN_DISABLE_SDK = '1' }
if (-not $env:PUTER_AUTO_INSTALL_SDK) { $env:PUTER_AUTO_INSTALL_SDK = '1' }

& $py -m uvicorn qtmos_server:app --host $env:QTMOS_API_HOST --port $env:QTMOS_API_PORT
exit $LASTEXITCODE
