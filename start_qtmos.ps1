$ErrorActionPreference = 'Stop'

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$py = $env:QTMOS_VENV_PY
if (-not $py) {
  $py = Join-Path $HOME 'qtmos-venv\Scripts\python.exe'
}

if (-not (Test-Path $py)) {
  Write-Host "[QTMoS] missing venv python: $py"
  Write-Host "[QTMoS] fix: py -3 -m venv $HOME\\qtmos-venv"
  exit 1
}

Set-Location $Root
if (-not $env:QTM_AUTO_START_SERVERS) { $env:QTM_AUTO_START_SERVERS = '1' }
if (-not $env:MCP_ROOT) { $env:MCP_ROOT = "$HOME\\Desktop\\UniProjects" }
if (-not $env:PUTER_LOGIN_DISABLE_SDK) { $env:PUTER_LOGIN_DISABLE_SDK = '1' }
if (-not $env:PUTER_AUTO_INSTALL_SDK) { $env:PUTER_AUTO_INSTALL_SDK = '1' }

& $py -m core @args
exit $LASTEXITCODE
