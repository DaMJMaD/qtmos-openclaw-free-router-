$ErrorActionPreference = 'Stop'

$Root = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$Py = $env:QTMOS_VENV_PY
if (-not $Py) { $Py = Join-Path $HOME 'qtmos-venv\Scripts\python.exe' }
$ApiBase = $env:QTMOS_API_BASE_URL
if (-not $ApiBase) { $ApiBase = 'http://127.0.0.1:8010' }
$TaskName = 'QTMoS-API'

$Failures = 0
$Warnings = 0

function Ok([string]$m)   { Write-Host "[OK] $m" }
function Warn([string]$m) { Write-Host "[WARN] $m"; $script:Warnings++ }
function Fail([string]$m) { Write-Host "[FAIL] $m"; $script:Failures++ }

if (-not (Test-Path $Py)) {
  $fallback = Get-Command python -ErrorAction SilentlyContinue
  if ($fallback) {
    $Py = $fallback.Source
    Warn "Using fallback python at $Py"
  } else {
    Fail "Python not found (expected $Py)"
    Write-Host "`nSummary: failures=$Failures warnings=$Warnings"
    exit 1
  }
}

Write-Host "QTMoS healthcheck (Windows native)"
Write-Host "Root: $Root"
Write-Host "Python: $Py"
Write-Host "API: $ApiBase`n"

# 1) Python version >= 3.10
$verOut = & $Py -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}'); raise SystemExit(0 if sys.version_info[:2] >= (3,10) else 1)" 2>$null
if ($LASTEXITCODE -eq 0) {
  Ok "Python version >= 3.10 ($verOut)"
} else {
  Fail "Python version is below 3.10 or unreadable"
}

# 2) Required imports
$imports = & $Py -c "import importlib.util;mods=['fastapi','uvicorn','requests','dotenv'];miss=[m for m in mods if importlib.util.find_spec(m) is None];print('missing='+','.join(miss) if miss else 'all-imports-ok');raise SystemExit(1 if miss else 0)" 2>$null
if ($LASTEXITCODE -eq 0) {
  Ok "Required imports present (fastapi, uvicorn, requests, dotenv)"
} else {
  Fail "Missing imports: $imports"
}

$tokenPresent = $false

# 3) API /health
try {
  $health = Invoke-RestMethod -Uri ($ApiBase.TrimEnd('/') + '/health') -Method Get -TimeoutSec 10
  if ($health.ok) {
    Ok "API /health reachable"
    if ($health.PSObject.Properties.Name -contains 'token_present') {
      $tokenPresent = [bool]$health.token_present
    }
  } else {
    Fail "API /health returned not-ok"
  }
} catch {
  Fail "API /health failed: $($_.Exception.Message)"
}

# 4) /ask ping (non-fatal)
try {
  $body = @{ prompt = 'ping'; model = 'claude-opus-4-6'; allow_local_fallback = $true } | ConvertTo-Json
  $ask = Invoke-RestMethod -Uri ($ApiBase.TrimEnd('/') + '/ask') -Method Post -ContentType 'application/json' -Body $body -TimeoutSec 45
  if ($ask.ok) {
    Ok "Basic inference /ask succeeded"
  } else {
    if (-not $tokenPresent) {
      Warn "Inference failed (non-fatal): cloud token missing and local fallback may be unavailable"
    } else {
      Warn "Inference failed (non-fatal): backend/model unavailable right now"
    }
  }
} catch {
  if (-not $tokenPresent) {
    Warn "Inference failed (non-fatal): cloud token missing and local fallback may be unavailable"
  } else {
    Warn "Inference failed (non-fatal): backend/model unavailable right now"
  }
}

# 5) Scheduled task status
try {
  $task = Get-ScheduledTask -TaskName $TaskName -ErrorAction Stop
  $state = [string]$task.State
  if ($state -eq 'Running' -or $state -eq 'Ready') {
    Ok "Scheduled task '$TaskName' exists (state=$state)"
  } else {
    Warn "Scheduled task '$TaskName' exists (state=$state)"
  }
} catch {
  Warn "Scheduled task '$TaskName' not found (non-fatal for manual runs)"
}

Write-Host "`nSummary: failures=$Failures warnings=$Warnings"
exit $Failures
