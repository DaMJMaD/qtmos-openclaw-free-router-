param(
  [string]$TaskName = 'QTMoS-API'
)

$ErrorActionPreference = 'Stop'
if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
  Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
  Write-Host "Removed task: $TaskName"
} else {
  Write-Host "Task not found: $TaskName"
}
